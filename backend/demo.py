"""
Demo data for running the app with no Plex server.

Everything here lives in memory and resets when the process restarts. It exists
so anyone can `docker compose up` and click around without a Plex token. The API
endpoints fall through to these functions when DEMO_MODE is set.

Run the demo backend with a single worker (the store is plain in-memory state).
"""

from datetime import date, timedelta
from flask import jsonify, Response, redirect, request

# Libraries, in the order they show as tabs. Counts are filled in below.
_LIBRARIES = [
    {'key': '3', 'title': '4K Movies', 'type': 'movie'},
    {'key': '1', 'title': 'Movies',    'type': 'movie'},
    {'key': '2', 'title': 'TV Shows',  'type': 'show'},
    {'key': '4', 'title': 'Music',     'type': 'artist'},
]

# Items per library: (key, title, year). Order doubles as recency for Recent.
_ITEMS = {
    '1': [
        ('m1', 'Oppenheimer', 2023), ('m2', 'Past Lives', 2023),
        ('m3', 'Everything Everywhere All at Once', 2022), ('m4', 'The Batman', 2022),
        ('m5', 'Dune', 2021), ('m6', 'Nomadland', 2020), ('m7', 'Soul', 2020),
        ('m8', 'Tenet', 2020), ('m9', 'Parasite', 2019), ('m10', 'Knives Out', 2019),
        ('m11', 'Joker', 2019), ('m12', '1917', 2019), ('m13', 'Blade Runner 2049', 2017),
        ('m14', 'Get Out', 2017), ('m15', 'Arrival', 2016), ('m16', 'La La Land', 2016),
        ('m17', 'Moonlight', 2016), ('m18', 'The Revenant', 2015), ('m19', 'Sicario', 2015),
        ('m20', 'Mad Max: Fury Road', 2015), ('m21', 'Ex Machina', 2014), ('m22', 'Whiplash', 2014),
        ('m23', 'Birdman', 2014), ('m24', 'Gone Girl', 2014), ('m25', 'The Grand Budapest Hotel', 2014),
        ('m26', 'Her', 2013), ('m27', 'Prisoners', 2013), ('m28', 'Gravity', 2013),
        ('m29', 'Drive', 2011), ('m30', 'Inception', 2010), ('m31', 'The Social Network', 2010),
        ('m32', 'There Will Be Blood', 2007), ('m33', 'No Country for Old Men', 2007),
        ('m34', 'The Dark Knight', 2008), ('m35', 'Interstellar', 2014), ('m36', 'The Matrix', 1999),
    ],
    '3': [
        ('k1', 'Dune', 2021), ('k2', 'Blade Runner 2049', 2017), ('k3', 'The Batman', 2022),
        ('k4', 'Interstellar', 2014), ('k5', 'Mad Max: Fury Road', 2015), ('k6', 'Tenet', 2020),
        ('k7', 'Oppenheimer', 2023), ('k8', '1917', 2019),
    ],
    '2': [
        ('t1', 'Severance', 2022), ('t2', 'The Bear', 2022), ('t3', 'Succession', 2018),
        ('t4', 'Better Call Saul', 2015), ('t5', 'Chernobyl', 2019), ('t6', 'Fleabag', 2016),
        ('t7', 'True Detective', 2014), ('t8', 'Breaking Bad', 2008), ('t9', 'The Wire', 2002),
        ('t10', 'The Sopranos', 1999), ('t11', 'Mad Men', 2007), ('t12', 'Band of Brothers', 2001),
    ],
    '4': [
        ('a1', 'Radiohead', None), ('a2', 'Kendrick Lamar', None), ('a3', 'Frank Ocean', None),
        ('a4', 'Bon Iver', None), ('a5', 'Tame Impala', None), ('a6', 'Fleetwood Mac', None),
        ('a7', 'Daft Punk', None), ('a8', 'The National', None),
    ],
}

# key -> (lib, title, year)
_BY_KEY = {k: (lib, t, y) for lib, items in _ITEMS.items() for (k, t, y) in items}

# Fake added dates, newest first per library.
_ADDED = {}
for _lib, _items in _ITEMS.items():
    _base = date(2025, 3, 1)
    for _i, (_k, _t, _y) in enumerate(_items):
        _ADDED[_k] = (_base - timedelta(days=_i * 3)).isoformat()

# Collections. Each belongs to a library.
_COLLECTIONS = {
    'c1': {'lib': '1', 'title': 'Mind-Benders', 'summary': 'Movies that fold back on themselves. Watch twice.',
           'items': ['m30', 'm36', 'm8', 'm15', 'm21', 'm35']},
    'c2': {'lib': '1', 'title': 'Modern Noir', 'summary': 'Slow dread, bad outcomes, great lighting.',
           'items': ['m29', 'm19', 'm27', 'm33', 'm24']},
    'c3': {'lib': '1', 'title': 'Best Picture Winners', 'summary': 'The ones that actually took the statue.',
           'items': ['m9', 'm17', 'm23', 'm6', 'm3', 'm1']},
    'c4': {'lib': '1', 'title': 'Villeneuve', 'summary': 'Big, cold, beautiful.',
           'items': ['m13', 'm5', 'm15', 'm19', 'm27']},
    'c5': {'lib': '1', 'title': 'A24 Picks', 'summary': '',
           'items': ['m17', 'm21', 'm2', 'm3']},
    'c6': {'lib': '1', 'title': 'Sci-Fi Spectacle', 'summary': 'Best on the biggest screen you can find.',
           'items': ['m28', 'm35', 'm5', 'm13', 'm8', 'm15']},
    'c7': {'lib': '3', 'title': '4K Showcase', 'summary': 'Reference-quality discs.',
           'items': ['k1', 'k2', 'k4', 'k5', 'k3']},
    'c8': {'lib': '2', 'title': 'Prestige Drama', 'summary': 'The heavy hitters.',
           'items': ['t9', 't10', 't8', 't11', 't3']},
    'c9': {'lib': '2', 'title': 'Recent Favorites', 'summary': 'Lately on repeat.',
           'items': ['t1', 't2', 't5', 't6']},
    'c10': {'lib': '4', 'title': 'On Repeat', 'summary': '',
            'items': ['a1', 'a3', 'a4', 'a8']},
}
_order = list(_COLLECTIONS.keys())
_next_id = 11

for _l in _LIBRARIES:
    _l['count'] = len(_ITEMS.get(_l['key'], []))


# --- serializers ---------------------------------------------------------------

def _item(key):
    lib, title, year = _BY_KEY[key]
    return {
        'ratingKey': key,
        'title': title,
        'year': year,
        'type': next((l['type'] for l in _LIBRARIES if l['key'] == lib), 'movie'),
        'thumb': f'/capi/poster/{key}',
        'addedAt': _ADDED.get(key),
    }


def _collection(cid):
    c = _COLLECTIONS[cid]
    # A custom cover (uploaded file or pasted URL) is served via a synthetic
    # `col-<cid>` poster key; otherwise fall back to the chosen/first member.
    if c.get('coverUrl') or c.get('coverData'):
        thumb = f'/capi/poster/col-{cid}'
    else:
        cover = c.get('cover') or (c['items'][0] if c['items'] else None)
        thumb = f'/capi/poster/{cover}' if cover else None
    return {
        'ratingKey': cid,
        'title': c['title'],
        'titleSort': c['title'],
        'summary': c['summary'],
        'thumb': thumb,
        'smart': False,
        'childCount': len(c['items']),
        'kometaManaged': False,
    }


# --- endpoint handlers ---------------------------------------------------------

def list_libraries():
    return jsonify({'libraries': _LIBRARIES})


def get_library_items(key, page, size, search, sort):
    pool = _ITEMS.get(key, [])
    items = [_item(k) for (k, _t, _y) in pool]
    if search:
        q = search.lower()
        items = [i for i in items if q in i['title'].lower()]
    elif sort == 'addedAt':
        items.sort(key=lambda i: i['addedAt'] or '', reverse=True)
    else:
        items.sort(key=lambda i: i['title'].lower())
    total = len(items)
    offset = (page - 1) * size
    return jsonify({'items': items[offset:offset + size], 'totalSize': total,
                    'page': page, 'pageSize': size})


def get_library_collections(key):
    return jsonify({'collections': [_collection(cid) for cid in _order
                                    if _COLLECTIONS[cid]['lib'] == key]})


def get_collection_items(cid):
    if cid not in _COLLECTIONS:
        return jsonify({'error': 'Collection not found'}), 404
    return jsonify({'collection': _collection(cid),
                    'items': [_item(k) for k in _COLLECTIONS[cid]['items']]})


def create_collection(data):
    global _next_id
    lib = str(data.get('libraryKey') or '1')
    title = (data.get('title') or '').strip()
    item_keys = [k for k in (data.get('itemKeys') or []) if k in _BY_KEY]
    if not title or not item_keys:
        return jsonify({'error': 'title and itemKeys are required'}), 400
    cid = f'c{_next_id}'
    _next_id += 1
    _COLLECTIONS[cid] = {'lib': lib, 'title': title,
                         'summary': (data.get('summary') or '').strip(), 'items': item_keys}
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


def set_collection_cover(cid, item_key=None, url=None, data=None):
    """Set a collection's cover from a member item, a pasted URL, or an uploaded
    file (mimetype, bytes). Only one mode wins; the others are cleared."""
    if cid not in _COLLECTIONS:
        return jsonify({'error': 'Collection not found'}), 404
    c = _COLLECTIONS[cid]
    if data is not None:
        c['coverData'] = data
        c.pop('coverUrl', None)
        c.pop('cover', None)
    elif url:
        c['coverUrl'] = url
        c.pop('coverData', None)
        c.pop('cover', None)
    elif item_key and item_key in _BY_KEY:
        c['cover'] = item_key
        c.pop('coverUrl', None)
        c.pop('coverData', None)
    return jsonify({'success': True})


def delete_collection(cid):
    if cid in _COLLECTIONS:
        del _COLLECTIONS[cid]
        if cid in _order:
            _order.remove(cid)
    return jsonify({'success': True})


def reorder_collections(data):
    keys = data.get('collectionKeys') or []
    kept = [k for k in keys if k in _COLLECTIONS]
    _order[:] = kept + [k for k in _order if k not in kept]
    return jsonify({'success': True})


# --- real posters --------------------------------------------------------------
# Public TMDb poster paths for the demo's (real) film/TV titles, so the demo looks
# like an actual library instead of coloured placeholders. Music artists have no
# film poster and fall back to the gradient below. These paths are public, not
# secrets, and image.tmdb.org serves them with no API key.
TMDB_IMG = 'https://image.tmdb.org/t/p'
_POSTERS = {
    'Oppenheimer': '/8Gxv8gSFCU0XGDykEGv7zR1n2ua.jpg',
    'Past Lives': '/k3waqVXSnvCZWfJYNtdamTgTtTA.jpg',
    'Everything Everywhere All at Once': '/u68AjlvlutfEIcpmbYpKcdi09ut.jpg',
    'The Batman': '/74xTEgt7R36Fpooo50r9T25onhq.jpg',
    'Dune': '/gDzOcq0pfeCeqMBwKIJlSmQpjkZ.jpg',
    'Nomadland': '/dKT8rGDR55cM1vGn7QZLA9Tg9YC.jpg',
    'Soul': '/6jmppcaubzLF8wkXM36ganVISCo.jpg',
    'Tenet': '/aCIFMriQh8rvhxpN1IWGgvH0Tlg.jpg',
    'Parasite': '/7IiTTgloJzvGI1TAYymCfbfl3vT.jpg',
    'Knives Out': '/pThyQovXQrw2m0s9x82twj48Jq4.jpg',
    'Joker': '/udDclJoHjfjb8Ekgsd4FDteOkCU.jpg',
    '1917': '/iZf0KyrE25z1sage4SYFLCCrMi9.jpg',
    'Blade Runner 2049': '/gajva2L0rPYkEWjzgFlBXCAVBE5.jpg',
    'Get Out': '/mE24wUCfjK8AoBBjaMjho7Rczr7.jpg',
    'Arrival': '/x2FJsf1ElAgr63Y3PNPtJrcmpoe.jpg',
    'La La Land': '/uDO8zWDhfWwoFdKS4fzkUJt0Rf0.jpg',
    'Moonlight': '/qLnfEmPrDjJfPyyddLJPkXmshkp.jpg',
    'The Revenant': '/ji3ecJphATlVgWNY0B0RVXZizdf.jpg',
    'Sicario': '/lz8vNyXeidqqOdJW9ZjnDAMb5Vr.jpg',
    'Mad Max: Fury Road': '/hA2ple9q4qnwxp3hKVNhroipsir.jpg',
    'Ex Machina': '/dmJW8IAKHKxFNiUnoDR7JfsK7Rp.jpg',
    'Whiplash': '/7fn624j5lj3xTme2SgiLCeuedmO.jpg',
    'Birdman': '/rHUg2AuIuLSIYMYFgavVwqt1jtc.jpg',
    'Gone Girl': '/ts996lKsxvjkO2yiYG0ht4qAicO.jpg',
    'The Grand Budapest Hotel': '/eWdyYQreja6JGCzqHWXpWHDrrPo.jpg',
    'Her': '/eCOtqtfvn7mxGl6nfmq4b1exJRc.jpg',
    'Prisoners': '/jsS3a3ep2KyBVmmiwaz3LvK49b1.jpg',
    'Gravity': '/kZ2nZw8D681aphje8NJi8EfbL1U.jpg',
    'Drive': '/602vevIURmpDfzbnv5Ubi6wIkQm.jpg',
    'Inception': '/xlaY2zyzMfkhk0HSC5VUwzoZPU1.jpg',
    'The Social Network': '/n0ybibhJtQ5icDqTp8eRytcIHJx.jpg',
    'There Will Be Blood': '/fa0RDkAlCec0STeMNAhPaF89q6U.jpg',
    'No Country for Old Men': '/6d5XOczc226jECq0LIX0siKtgHR.jpg',
    'The Dark Knight': '/qJ2tW6WMUDux911r6m7haRef0WH.jpg',
    'Interstellar': '/yQvGrMoipbRoddT0ZR8tPoR7NfX.jpg',
    'The Matrix': '/aOIuZAjPaRIE6CMzbazvcHuHXDc.jpg',
    'Severance': '/pPHpeI2X1qEd1CS1SeyrdhZ4qnT.jpg',
    'The Bear': '/4fVddnbhcmzRZE14NJY03GKS6Fn.jpg',
    'Succession': '/z0XiwdrCQ9yVIr4O0pxzaAYRxdW.jpg',
    'Better Call Saul': '/zjg4jpK1Wp2kiRvtt5ND0kznako.jpg',
    'Chernobyl': '/hlLXt2tOPT6RRnjiUmoxyG1LTFi.jpg',
    'Fleabag': '/27vEYsRKa3eAniwmoccOoluEXQ1.jpg',
    'True Detective': '/zYqVTiHK5ZajYcNzAW7qWte5NWS.jpg',
    'Breaking Bad': '/ztkUQFLlC19CCMYHW9o1zWhJRNq.jpg',
    'The Wire': '/4lbclFySvugI51fwsyxBTOm4DqK.jpg',
    'The Sopranos': '/rTc7ZXdroqjkKivFPvCPX0Ru7uw.jpg',
    'Mad Men': '/7v8iCNzKFpdlrCMcqCoJyn74Nsa.jpg',
    'Band of Brothers': '/pGzV187ogXzgJrvPRy2YPi29ofH.jpg',
}


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


def _gradient(key):
    info = _BY_KEY.get(key)
    title = info[1] if info else 'Untitled'
    year = info[2] if info else ''
    c1, c2 = _GRADIENTS[sum(ord(ch) for ch in key) % len(_GRADIENTS)]
    lines = _wrap(title)
    start_y = 225 - (len(lines) - 1) * 18
    tspans = ''.join(
        f'<tspan x="150" y="{start_y + i * 36}">{_esc(ln)}</tspan>'
        for i, ln in enumerate(lines)
    )
    year_txt = f'<text x="150" y="410" fill="#ffffffcc" font-size="18">{year}</text>' if year else ''
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 450">'
        f'<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/>'
        f'</linearGradient></defs>'
        f'<rect width="300" height="450" fill="url(#g)"/>'
        f'<rect width="300" height="450" fill="#000" opacity="0.18"/>'
        f'<g font-family="-apple-system,Segoe UI,Roboto,sans-serif" text-anchor="middle">'
        f'<text fill="#fff" font-size="26" font-weight="700">{tspans}</text>'
        f'{year_txt}'
        f'</g></svg>'
    )
    return Response(svg, mimetype='image/svg+xml',
                    headers={'Cache-Control': 'public, max-age=86400'})


def get_poster(key):
    """Poster for a demo item or a custom collection cover.

    Real film/TV titles 302-redirect to the TMDb image CDN; a `col-<cid>` key
    serves a collection's uploaded file (bytes) or pasted URL; everything else
    (music artists, unknown keys) falls back to a generated gradient card.
    """
    if key.startswith('col-'):
        c = _COLLECTIONS.get(key[4:])
        if c and c.get('coverData'):
            mime, blob = c['coverData']
            return Response(blob, mimetype=mime, headers={'Cache-Control': 'no-store'})
        if c and c.get('coverUrl'):
            return redirect(c['coverUrl'], code=302)
        return _gradient(key)
    info = _BY_KEY.get(key)
    path = _POSTERS.get(info[1]) if info else None
    if path:
        try:
            w = int(request.args.get('w', 300))
        except (TypeError, ValueError):
            w = 300
        size = 'w185' if w <= 150 else ('w342' if w <= 342 else 'w500')
        return redirect(f'{TMDB_IMG}/{size}{path}', code=302)
    return _gradient(key)
