"""
Demo data for running the app with no Plex server.

Everything here lives in memory and resets when the process restarts. It exists
so anyone can `docker compose up` and click around without a Plex token. The API
endpoints fall through to these functions when DEMO_MODE is set.

Run the demo backend with a single worker (the store is plain in-memory state).
"""

from datetime import date, timedelta
from flask import jsonify, Response

LIBRARY_KEY = '1'

# Film pool. (key, title, year). The order doubles as recency for the Recent tab.
_FILMS = [
    ('m1',  'Oppenheimer', 2023),
    ('m2',  'Past Lives', 2023),
    ('m3',  'Everything Everywhere All at Once', 2022),
    ('m4',  'The Batman', 2022),
    ('m5',  'Dune', 2021),
    ('m6',  'Nomadland', 2020),
    ('m7',  'Soul', 2020),
    ('m8',  'Tenet', 2020),
    ('m9',  'Parasite', 2019),
    ('m10', 'Knives Out', 2019),
    ('m11', 'Joker', 2019),
    ('m12', '1917', 2019),
    ('m13', 'Blade Runner 2049', 2017),
    ('m14', 'Get Out', 2017),
    ('m15', 'Arrival', 2016),
    ('m16', 'La La Land', 2016),
    ('m17', 'Moonlight', 2016),
    ('m18', 'The Revenant', 2015),
    ('m19', 'Sicario', 2015),
    ('m20', 'Mad Max: Fury Road', 2015),
    ('m21', 'Ex Machina', 2014),
    ('m22', 'Whiplash', 2014),
    ('m23', 'Birdman', 2014),
    ('m24', 'Gone Girl', 2014),
    ('m25', 'The Grand Budapest Hotel', 2014),
    ('m26', 'Her', 2013),
    ('m27', 'Prisoners', 2013),
    ('m28', 'Gravity', 2013),
    ('m29', 'Drive', 2011),
    ('m30', 'Inception', 2010),
    ('m31', 'The Social Network', 2010),
    ('m32', 'There Will Be Blood', 2007),
    ('m33', 'No Country for Old Men', 2007),
    ('m34', 'The Dark Knight', 2008),
    ('m35', 'Interstellar', 2014),
    ('m36', 'The Matrix', 1999),
]

_BY_KEY = {k: {'key': k, 'title': t, 'year': y} for (k, t, y) in _FILMS}

# Fake added dates, newest first, so the Recent sort has something to order by.
_ADDED = {}
_base = date(2025, 3, 1)
for _i, (_k, _t, _y) in enumerate(_FILMS):
    _ADDED[_k] = (_base - timedelta(days=_i * 3)).isoformat()

# Collections, in display order. Each maps to an ordered list of film keys.
_COLLECTIONS = {
    'c1': {
        'title': 'Mind-Benders',
        'summary': 'Movies that fold back on themselves. Watch twice.',
        'items': ['m30', 'm36', 'm8', 'm15', 'm21', 'm35'],
    },
    'c2': {
        'title': 'Modern Noir',
        'summary': 'Slow dread, bad outcomes, great lighting.',
        'items': ['m29', 'm19', 'm27', 'm33', 'm24'],
    },
    'c3': {
        'title': 'Best Picture Winners',
        'summary': 'The ones that actually took the statue.',
        'items': ['m9', 'm17', 'm23', 'm6', 'm3', 'm1'],
    },
    'c4': {
        'title': 'Villeneuve',
        'summary': 'Big, cold, beautiful.',
        'items': ['m13', 'm5', 'm15', 'm19', 'm27'],
    },
    'c5': {
        'title': 'A24 Picks',
        'summary': '',
        'items': ['m17', 'm21', 'm2', 'm3'],
    },
    'c6': {
        'title': 'Sci-Fi Spectacle',
        'summary': 'Best seen on the biggest screen you can find.',
        'items': ['m28', 'm35', 'm5', 'm13', 'm8', 'm15'],
    },
}
_order = list(_COLLECTIONS.keys())
_next_id = 7


# --- serializers ---------------------------------------------------------------

def _item(key):
    f = _BY_KEY[key]
    return {
        'ratingKey': key,
        'title': f['title'],
        'year': f['year'],
        'type': 'movie',
        'thumb': f'/capi/poster/{key}',
        'addedAt': _ADDED.get(key),
    }


def _collection(cid):
    c = _COLLECTIONS[cid]
    first = c['items'][0] if c['items'] else None
    return {
        'ratingKey': cid,
        'title': c['title'],
        'titleSort': c['title'],
        'summary': c['summary'],
        'thumb': f'/capi/poster/{first}' if first else None,
        'smart': False,
        'childCount': len(c['items']),
        'kometaManaged': False,
    }


# --- endpoint handlers ---------------------------------------------------------

def list_libraries():
    return jsonify({'libraries': [
        {'key': LIBRARY_KEY, 'title': 'Movies', 'type': 'movie', 'count': len(_FILMS)},
    ]})


def get_library_items(page, size, search, sort):
    items = [_item(k) for (k, _t, _y) in _FILMS]
    if search:
        q = search.lower()
        items = [i for i in items if q in i['title'].lower()]
    elif sort == 'addedAt':
        items.sort(key=lambda i: i['addedAt'] or '', reverse=True)
    else:
        items.sort(key=lambda i: i['title'].lower())
    total = len(items)
    offset = (page - 1) * size
    return jsonify({
        'items': items[offset:offset + size],
        'totalSize': total,
        'page': page,
        'pageSize': size,
    })


def get_library_collections():
    return jsonify({'collections': [_collection(cid) for cid in _order]})


def get_collection_items(cid):
    if cid not in _COLLECTIONS:
        return jsonify({'error': 'Collection not found'}), 404
    return jsonify({
        'collection': _collection(cid),
        'items': [_item(k) for k in _COLLECTIONS[cid]['items']],
    })


def create_collection(data):
    global _next_id
    title = (data.get('title') or '').strip()
    item_keys = [k for k in (data.get('itemKeys') or []) if k in _BY_KEY]
    if not title or not item_keys:
        return jsonify({'error': 'title and itemKeys are required'}), 400
    cid = f'c{_next_id}'
    _next_id += 1
    _COLLECTIONS[cid] = {'title': title, 'summary': (data.get('summary') or '').strip(),
                         'items': item_keys}
    _order.append(cid)
    return jsonify({'success': True, 'collection': _collection(cid)})


def update_collection(cid, data):
    if cid not in _COLLECTIONS:
        return jsonify({'error': 'Collection not found'}), 404
    c = _COLLECTIONS[cid]
    before = list(c['items'])
    if data.get('title') is not None:
        c['title'] = data['title'].strip()
    if data.get('summary') is not None:
        c['summary'] = data['summary'].strip()
    stats = {'added': 0, 'removed': 0, 'reordered': 0, 'plexCalls': 0, 'elapsed': 0}
    if data.get('itemKeys') is not None:
        new = [k for k in data['itemKeys'] if k in _BY_KEY]
        stats['added'] = len([k for k in new if k not in before])
        stats['removed'] = len([k for k in before if k not in new])
        if new != before:
            stats['reordered'] = len(new)
        c['items'] = new
    stats['totalItems'] = len(c['items'])
    return jsonify({'success': True, 'stats': stats})


def delete_collection(cid):
    if cid in _COLLECTIONS:
        del _COLLECTIONS[cid]
        if cid in _order:
            _order.remove(cid)
    return jsonify({'success': True})


def reorder_collections(data):
    keys = data.get('collectionKeys') or []
    kept = [k for k in keys if k in _COLLECTIONS]
    # keep any not mentioned, in their old relative order
    _order[:] = kept + [k for k in _order if k not in kept]
    return jsonify({'success': True})


# --- placeholder posters -------------------------------------------------------

_GRADIENTS = [
    ('#7c3aed', '#2563eb'), ('#db2777', '#7c3aed'), ('#0891b2', '#1e3a8a'),
    ('#ea580c', '#b91c1c'), ('#059669', '#0f766e'), ('#c026d3', '#6d28d9'),
    ('#d97706', '#b45309'), ('#4f46e5', '#0ea5e9'),
]


def _esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _wrap(title, width=13):
    lines, cur = [], ''
    for word in title.split():
        if cur and len(cur) + 1 + len(word) > width:
            lines.append(cur)
            cur = word
        else:
            cur = f'{cur} {word}'.strip()
    if cur:
        lines.append(cur)
    return lines[:4]


def get_poster(key):
    f = _BY_KEY.get(key)
    title = f['title'] if f else 'Untitled'
    year = f['year'] if f else ''
    c1, c2 = _GRADIENTS[sum(ord(ch) for ch in key) % len(_GRADIENTS)]
    lines = _wrap(title)
    start_y = 225 - (len(lines) - 1) * 18
    tspans = ''.join(
        f'<tspan x="150" y="{start_y + i * 36}">{_esc(ln)}</tspan>'
        for i, ln in enumerate(lines)
    )
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 450">'
        f'<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/>'
        f'</linearGradient></defs>'
        f'<rect width="300" height="450" fill="url(#g)"/>'
        f'<rect width="300" height="450" fill="#000" opacity="0.18"/>'
        f'<g font-family="-apple-system,Segoe UI,Roboto,sans-serif" text-anchor="middle">'
        f'<text fill="#fff" font-size="26" font-weight="700">{tspans}</text>'
        f'<text x="150" y="410" fill="#ffffffcc" font-size="18">{year}</text>'
        f'</g></svg>'
    )
    return Response(svg, mimetype='image/svg+xml',
                    headers={'Cache-Control': 'public, max-age=86400'})
