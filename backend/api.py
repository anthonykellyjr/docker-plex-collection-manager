"""
Plex Collection Manager API
Flask backend for creating and managing Plex collections via drag-and-drop UI.
Proxied by nginx at /capi/
"""

import os
import time
import yaml
import hashlib
import tempfile
import threading
import requests
from functools import wraps
from flask import Flask, request, jsonify, Response
from flask_cors import CORS

# Prevent plexapi from phoning home to plex.tv
# MUST be set before importing plexapi
import plexapi
plexapi.X_PLEX_IDENTIFIER = 'collection-manager'
plexapi.BASE_HEADERS['X-Plex-Client-Identifier'] = 'collection-manager'
plexapi.BASE_HEADERS['X-Plex-Provides'] = ''
plexapi.BASE_HEADERS['X-Plex-Product'] = 'Collection Manager'
plexapi.BASE_HEADERS['X-Plex-Version'] = '1.0.0'

from plexapi.server import PlexServer

# =============================================================================
# CONFIGURATION
# =============================================================================
# DEMO_MODE runs the app with no Plex and no real secrets, it serves the fixture
# data in demo.py instead. Handy for trying it out, and for the public demo.
DEMO_MODE = os.environ.get('DEMO_MODE', '').lower() in ('1', 'true', 'yes', 'on')

PLEX_URL = os.environ.get('PLEX_URL', 'http://host.docker.internal:32400')
PLEX_TOKEN = os.environ.get('PLEX_TOKEN')
# In demo mode the admin key defaults to "demo" so the login screen just works.
ADMIN_KEY = os.environ.get('ADMIN_KEY') or ('demo' if DEMO_MODE else None)

if not ADMIN_KEY:
    raise RuntimeError('Set ADMIN_KEY (or DEMO_MODE=1)')
if not DEMO_MODE and not PLEX_TOKEN:
    raise RuntimeError('Set PLEX_TOKEN (or DEMO_MODE=1 to run without Plex)')

KOMETA_MOVIE_YML = '/app/kometa/movie_collections.yml'
KOMETA_TV_YML = '/app/kometa/tv_collections.yml'

app = Flask(__name__)
CORS(app)

if DEMO_MODE:
    import demo

# =============================================================================
# PLEX CONNECTION
# =============================================================================
_plex_server = None

def get_server():
    global _plex_server
    if _plex_server is None:
        _plex_server = PlexServer(PLEX_URL, PLEX_TOKEN)
    return _plex_server

def reset_server():
    """Reset cached server connection (e.g. after error)."""
    global _plex_server
    _plex_server = None

# =============================================================================
# CACHING (same pattern as announcement-api)
# =============================================================================
_cache = {}

def cached(key, ttl_seconds, fetcher):
    now = time.time()
    entry = _cache.get(key)
    if entry and (now - entry['ts']) < ttl_seconds:
        return entry['data']
    try:
        data = fetcher()
        _cache[key] = {'data': data, 'ts': now}
        return data
    except Exception as e:
        if entry:
            return entry['data']
        raise e

# =============================================================================
# POSTER CACHE (filesystem), Plex stream protection
# =============================================================================
# Plex's photo transcoder is hit ONCE per (ratingKey,size), ever, results are
# written to disk and served from there. A semaphore caps how many transcodes
# can run at Plex concurrently so a cold cache can't starve active streams.
POSTER_CACHE_DIR = os.environ.get('POSTER_CACHE_DIR', '/cache')
# Only two sizes are allowed, so the cache stays small and Plex only ever
# transcodes these dimensions: small thumbs (rows) and grid posters.
POSTER_SIZES = {(120, 180), (300, 450)}
DEFAULT_POSTER_SIZE = (300, 450)
# At most 3 simultaneous transcode requests to Plex (cache hits don't count).
_plex_fetch_sem = threading.Semaphore(3)

try:
    os.makedirs(POSTER_CACHE_DIR, exist_ok=True)
except OSError:
    pass


def _clamp_poster_size():
    """Read w/h from the query string, clamp to the allowlist (default = grid)."""
    try:
        w = int(request.args.get('w', DEFAULT_POSTER_SIZE[0]))
        h = int(request.args.get('h', DEFAULT_POSTER_SIZE[1]))
    except (TypeError, ValueError):
        return DEFAULT_POSTER_SIZE
    return (w, h) if (w, h) in POSTER_SIZES else DEFAULT_POSTER_SIZE


def serve_cached_poster(rating_key):
    """Serve a poster from the on-disk cache, fetching from Plex once on a miss.

    Honors If-None-Match (304) and sets a 30-day immutable cache header so the
    browser caches too. Used by both the admin and Kelly poster routes.
    """
    w, h = _clamp_poster_size()
    safe_key = str(rating_key).replace('/', '_')
    path = os.path.join(POSTER_CACHE_DIR, f'{safe_key}_{w}x{h}.jpg')
    etag = f'"{safe_key}-{w}x{h}"'

    data = None
    if os.path.exists(path):
        try:
            with open(path, 'rb') as fh:
                data = fh.read()
        except OSError:
            data = None

    if data is None:
        # Cache miss, fetch from Plex under the concurrency cap.
        # Use the PHOTO TRANSCODER (not /metadata/thumb, which ignores width/height
        # and returns the full ~230KB original) so we get a real ~7-33KB resized
        # image. Plex transcodes each poster size once, then it's served from disk.
        with _plex_fetch_sem:
            try:
                resp = requests.get(
                    f'{PLEX_URL}/photo/:/transcode',
                    params={
                        'X-Plex-Token': PLEX_TOKEN,
                        'width': w,
                        'height': h,
                        'minSize': 1,
                        'upscale': 1,
                        'url': f'/library/metadata/{rating_key}/thumb',
                    },
                    timeout=10,
                )
            except Exception:
                return Response('Error', status=500)
        if resp.status_code != 200:
            return Response('Not found', status=404)
        data = resp.content
        try:
            tmp = f'{path}.{os.getpid()}.tmp'
            with open(tmp, 'wb') as fh:
                fh.write(data)
            os.replace(tmp, path)  # atomic, no torn reads under concurrency
        except OSError:
            pass

    if request.headers.get('If-None-Match') == etag:
        return Response(status=304, headers={'ETag': etag,
                                             'Cache-Control': 'public, max-age=2592000, immutable'})

    return Response(data, headers={
        'Content-Type': 'image/jpeg',
        'Cache-Control': 'public, max-age=2592000, immutable',
        'ETag': etag,
    })

def invalidate_cache(prefix=''):
    keys_to_delete = [k for k in _cache if k.startswith(prefix)] if prefix else list(_cache.keys())
    for k in keys_to_delete:
        del _cache[k]

def delete_poster_cache(rating_key):
    """Drop cached poster files for a rating key, e.g. after its art changes."""
    safe = str(rating_key).replace('/', '_')
    try:
        for name in os.listdir(POSTER_CACHE_DIR):
            if name.startswith(f'{safe}_') and name.endswith('.jpg'):
                try:
                    os.remove(os.path.join(POSTER_CACHE_DIR, name))
                except OSError:
                    pass
    except OSError:
        pass

# =============================================================================
# KOMETA DETECTION
# =============================================================================
_kometa_titles = set()

def load_kometa_titles():
    global _kometa_titles
    titles = set()
    for path in [KOMETA_MOVIE_YML, KOMETA_TV_YML]:
        try:
            with open(path, 'r') as f:
                data = yaml.safe_load(f)
            if data and 'collections' in data:
                for title in data['collections']:
                    titles.add(title)
        except Exception:
            pass
    _kometa_titles = titles

load_kometa_titles()

def is_kometa_managed(title):
    return title in _kometa_titles

# =============================================================================
# AUTH
# =============================================================================
def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Accept key from header or query param (needed for <img src=> tags)
        key = request.headers.get('X-Admin-Key') or request.args.get('k')
        if key != ADMIN_KEY:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated

# =============================================================================
# HELPER: serialize items
# =============================================================================
def serialize_item(item):
    return {
        'ratingKey': str(item.ratingKey),
        'title': item.title,
        'year': getattr(item, 'year', None),
        'type': item.type,
        'thumb': f'/capi/poster/{item.ratingKey}' if item.thumb else None,
        'addedAt': item.addedAt.isoformat() if getattr(item, 'addedAt', None) else None,
    }

def serialize_collection(col, include_kometa=True):
    result = {
        'ratingKey': str(col.ratingKey),
        'title': col.title,
        'titleSort': getattr(col, 'titleSort', col.title) or col.title,
        'summary': getattr(col, 'summary', '') or '',
        'thumb': f'/capi/poster/{col.ratingKey}' if col.thumb else None,
        'smart': col.smart if hasattr(col, 'smart') else False,
        'childCount': col.childCount if hasattr(col, 'childCount') else 0,
    }
    if include_kometa:
        result['kometaManaged'] = is_kometa_managed(col.title)
    return result

# =============================================================================
# ENDPOINTS
# =============================================================================

@app.route('/capi/health')
def health():
    return jsonify({'status': 'ok', 'demo': DEMO_MODE})


@app.route('/capi/libraries')
@require_admin
def list_libraries():
    if DEMO_MODE:
        return demo.list_libraries()

    def fetch():
        server = get_server()
        sections = server.library.sections()
        return {
            'libraries': [
                {
                    'key': str(s.key),
                    'title': s.title,
                    'type': s.type,
                    'count': s.totalSize,
                }
                for s in sections
            ]
        }
    try:
        data = cached('libraries', 300, fetch)
        return jsonify(data)
    except Exception as e:
        reset_server()
        return jsonify({'error': str(e)}), 500


@app.route('/capi/libraries/<key>/items')
@require_admin
def get_library_items(key):
    page = int(request.args.get('page', 1))
    size = int(request.args.get('size', 50))
    search = request.args.get('search', '').strip()
    sort = request.args.get('sort', 'titleSort')
    offset = (page - 1) * size

    if DEMO_MODE:
        return demo.get_library_items(key, page, size, search, sort)

    try:
        server = get_server()
        section = server.library.sectionByID(int(key))

        if search:
            # Search returns all matches, paginate in Python
            cache_key = f'search:{key}:{search}'
            def do_search():
                results = section.search(title=search)
                return [serialize_item(item) for item in results]
            all_results = cached(cache_key, 60, do_search)
            total = len(all_results)
            items = all_results[offset:offset + size]
        elif sort == 'addedAt':
            # Newest-added first, fetched server-side ONE PAGE at a time. Plex sorts
            # and slices via the container args (~40ms/page), so we never pull the
            # whole library just to show the latest 50. The container-pagination
            # caveat that bites section.all() does NOT apply to a sorted search -
            # verified reliable across pages on this server.
            def do_recent():
                results = section.search(
                    sort='addedAt:desc',
                    container_start=offset,
                    container_size=size,
                    maxresults=size,
                )
                return [serialize_item(item) for item in results]
            items = cached(f'recent:{key}:{offset}:{size}', 60, do_recent)
            total = cached(f'recent_total:{key}', 60, lambda: section.totalSize)
        else:
            # Fetch all and cache, then slice for pagination
            # plexapi container_start/container_size are unreliable
            cache_key = f'items_all:{key}'
            def do_fetch():
                results = section.all()
                return [serialize_item(item) for item in results]
            all_results = cached(cache_key, 120, do_fetch)
            total = len(all_results)
            items = all_results[offset:offset + size]

        return jsonify({
            'items': items,
            'totalSize': total,
            'page': page,
            'pageSize': size,
        })
    except Exception as e:
        reset_server()
        return jsonify({'error': str(e)}), 500


@app.route('/capi/poster/<rating_key>')
@require_admin
def get_poster(rating_key):
    if DEMO_MODE:
        return demo.get_poster(rating_key)
    return serve_cached_poster(rating_key)


@app.route('/capi/libraries/<key>/collections')
@require_admin
def get_library_collections(key):
    if DEMO_MODE:
        return demo.get_library_collections(key)

    def fetch():
        server = get_server()
        section = server.library.sectionByID(int(key))
        collections = section.collections()
        return {
            'collections': [serialize_collection(c) for c in collections]
        }
    try:
        data = cached(f'collections:{key}', 30, fetch)
        return jsonify(data)
    except Exception as e:
        reset_server()
        return jsonify({'error': str(e)}), 500


@app.route('/capi/collections/<rating_key>/items')
@require_admin
def get_collection_items(rating_key):
    if DEMO_MODE:
        return demo.get_collection_items(rating_key)
    try:
        server = get_server()
        collection = server.fetchItem(int(rating_key))
        items = collection.items()
        return jsonify({
            'collection': serialize_collection(collection),
            'items': [serialize_item(item) for item in items],
        })
    except Exception as e:
        reset_server()
        return jsonify({'error': str(e)}), 500


@app.route('/capi/collections', methods=['POST'])
@require_admin
def create_collection():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    if DEMO_MODE:
        return demo.create_collection(data)

    library_key = data.get('libraryKey')
    title = data.get('title', '').strip()
    summary = data.get('summary', '').strip()
    item_keys = data.get('itemKeys', [])

    if not library_key or not title or not item_keys:
        return jsonify({'error': 'libraryKey, title, and itemKeys are required'}), 400

    try:
        server = get_server()
        section = server.library.sectionByID(int(library_key))

        # Fetch items in the specified order
        items = []
        for rk in item_keys:
            try:
                items.append(server.fetchItem(int(rk)))
            except Exception:
                pass

        if not items:
            return jsonify({'error': 'No valid items found'}), 400

        collection = section.createCollection(title=title, items=items)
        if summary:
            collection.editSummary(summary)

        # Invalidate collection cache
        invalidate_cache(f'collections:{library_key}')

        return jsonify({
            'success': True,
            'collection': serialize_collection(collection),
        })
    except Exception as e:
        reset_server()
        return jsonify({'error': str(e)}), 500


@app.route('/capi/collections/<rating_key>', methods=['PUT'])
@require_admin
def update_collection(rating_key):
    t_start = time.time()
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    if DEMO_MODE:
        return demo.update_collection(rating_key, data)

    title = data.get('title')
    summary = data.get('summary')
    item_keys = data.get('itemKeys')

    stats = {'added': 0, 'removed': 0, 'reordered': 0, 'plexCalls': 0}

    try:
        server = get_server()
        collection = server.fetchItem(int(rating_key))
        stats['plexCalls'] += 1

        # Update title
        if title is not None:
            collection.editTitle(title.strip())
            stats['plexCalls'] += 1

        # Update summary
        if summary is not None:
            collection.editSummary(summary.strip())
            stats['plexCalls'] += 1

        # Update items and ordering
        if item_keys is not None:
            current_items = collection.items()
            stats['plexCalls'] += 1
            current_keys = set(str(item.ratingKey) for item in current_items)
            new_keys = set(item_keys)

            # Add new items
            to_add = [k for k in item_keys if k not in current_keys]
            if to_add:
                add_items = []
                for rk in to_add:
                    try:
                        add_items.append(server.fetchItem(int(rk)))
                        stats['plexCalls'] += 1
                    except Exception:
                        pass
                if add_items:
                    collection.addItems(add_items)
                    stats['plexCalls'] += 1
                    stats['added'] = len(add_items)

            # Remove items no longer in the list
            to_remove = [item for item in current_items if str(item.ratingKey) not in new_keys]
            if to_remove:
                collection.removeItems(to_remove)
                stats['plexCalls'] += 1
                stats['removed'] = len(to_remove)

            # Reorder: move each item after the previous one
            if len(item_keys) > 1:
                # Refresh the items list after add/remove
                refreshed = collection.items()
                stats['plexCalls'] += 1
                items_map = {str(i.ratingKey): i for i in refreshed}

                # Move first item to beginning
                first = items_map.get(item_keys[0])
                if first:
                    try:
                        collection.moveItem(first)
                        stats['plexCalls'] += 1
                        stats['reordered'] += 1
                    except Exception:
                        pass

                # Move remaining items after the previous one
                for i in range(1, len(item_keys)):
                    current = items_map.get(item_keys[i])
                    prev = items_map.get(item_keys[i - 1])
                    if current and prev:
                        try:
                            collection.moveItem(current, after=prev)
                            stats['plexCalls'] += 1
                            stats['reordered'] += 1
                        except Exception:
                            pass

        # Invalidate caches
        invalidate_cache('collections:')

        elapsed = round(time.time() - t_start, 2)
        stats['elapsed'] = elapsed
        stats['totalItems'] = len(item_keys) if item_keys else 0

        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        reset_server()
        return jsonify({'error': str(e)}), 500


@app.route('/capi/collections/<rating_key>/poster', methods=['POST'])
@require_admin
def set_collection_poster(rating_key):
    # Three ways to set a collection's poster: a member item's artwork
    # (ratingKey), a pasted image URL (url), or an uploaded image file (file).
    MAX_UPLOAD = 8 * 1024 * 1024
    upload = request.files.get('file')
    file_bytes = file_mime = item_key = poster_url = None

    if upload is not None and upload.filename:
        file_mime = (upload.mimetype or '').lower()
        if not file_mime.startswith('image/'):
            return jsonify({'error': 'file must be an image'}), 400
        file_bytes = upload.read()
        if not file_bytes:
            return jsonify({'error': 'empty file'}), 400
        if len(file_bytes) > MAX_UPLOAD:
            return jsonify({'error': 'image too large (max 8 MB)'}), 413
    else:
        data = request.get_json(silent=True) or {}
        item_key = data.get('ratingKey')
        poster_url = (data.get('url') or '').strip()
        if not item_key and not poster_url:
            return jsonify({'error': 'ratingKey, url, or file required'}), 400
        if poster_url and not poster_url.lower().startswith(('http://', 'https://')):
            return jsonify({'error': 'url must be http(s)'}), 400

    if DEMO_MODE:
        if file_bytes is not None:
            return demo.set_collection_cover(rating_key, data=(file_mime, file_bytes))
        if poster_url:
            return demo.set_collection_cover(rating_key, url=poster_url)
        return demo.set_collection_cover(rating_key, item_key=item_key)

    tmp_path = None
    try:
        server = get_server()
        collection = server.fetchItem(int(rating_key))
        if file_bytes is not None:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.img') as tf:
                tf.write(file_bytes)
                tmp_path = tf.name
            collection.uploadPoster(filepath=tmp_path)
        elif poster_url:
            collection.uploadPoster(url=poster_url)
        else:
            # Point the collection's poster at the chosen member item's artwork.
            thumb_url = f'{PLEX_URL}/library/metadata/{item_key}/thumb?X-Plex-Token={PLEX_TOKEN}'
            collection.uploadPoster(url=thumb_url)
        delete_poster_cache(rating_key)
        invalidate_cache('collections:')
        return jsonify({'success': True})
    except Exception as e:
        reset_server()
        return jsonify({'error': str(e)}), 500
    finally:
        if tmp_path:
            try:
                os.remove(tmp_path)
            except OSError:
                pass


@app.route('/capi/collections/<rating_key>', methods=['DELETE'])
@require_admin
def delete_collection(rating_key):
    if DEMO_MODE:
        return demo.delete_collection(rating_key)
    try:
        server = get_server()
        collection = server.fetchItem(int(rating_key))
        collection.delete()

        invalidate_cache('collections:')

        return jsonify({'success': True})
    except Exception as e:
        reset_server()
        return jsonify({'error': str(e)}), 500


@app.route('/capi/libraries/<key>/collections/order', methods=['PUT'])
@require_admin
def reorder_collections(key):
    """Reorder collections by setting titleSort to zero-padded indices."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    collection_keys = data.get('collectionKeys', [])
    if not collection_keys:
        return jsonify({'error': 'collectionKeys required'}), 400

    if DEMO_MODE:
        return demo.reorder_collections(data)

    try:
        server = get_server()
        for idx, rk in enumerate(collection_keys):
            try:
                col = server.fetchItem(int(rk))
                sort_title = f'{idx:06d}'
                col.editSortTitle(sort_title)
            except Exception as e:
                print(f"Failed to set sort title for {rk}: {e}")

        invalidate_cache('collections:')
        return jsonify({'success': True})
    except Exception as e:
        reset_server()
        return jsonify({'error': str(e)}), 500


# =============================================================================
# OPTIONAL PRIVATE EXTENSIONS
# =============================================================================
# Loaded only if a kelly_routes.py is sitting next to this file. It isn't in the
# repo, so this is a no-op for everyone but me. Keeps a personal feature off the
# public project without forking the code.
try:
    import kelly_routes
    kelly_routes.register_kelly(
        app,
        get_server=get_server,
        reset_server=reset_server,
        cached=cached,
        serialize_collection=serialize_collection,
        serve_cached_poster=serve_cached_poster,
    )
except ImportError:
    pass
except Exception as e:
    print(f'kelly_routes not loaded: {e}')


# =============================================================================
# RUN
# =============================================================================
if __name__ == '__main__':
    print('Collection Manager API starting')
    print(f'Demo mode: {DEMO_MODE}')
    if not DEMO_MODE:
        print(f'Plex URL: {PLEX_URL}')
    app.run(host='0.0.0.0', port=5000, debug=False)
