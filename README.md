# Plex Collection Manager

![Vue](https://img.shields.io/badge/Vue-3-42b883)
![Vite](https://img.shields.io/badge/Vite-5-646cff)
![Tailwind](https://img.shields.io/badge/Tailwind-3-38bdf8)
![Flask](https://img.shields.io/badge/Flask-API-000000)
![plexapi](https://img.shields.io/badge/plexapi-powered-e5a00d)
![License](https://img.shields.io/badge/license-MIT-blue)

A Letterboxd-style web app for building and ranking **Plex collections** by hand.
Search your library, drag posters (or rows) into the order you want, rename the
collection, and it saves straight to your Plex Media Server. The whole thing runs
in two small containers.

I built it because Plex's own collection editing is clunky, and I wanted to rank
movies by recommendation order, not alphabetically.

## Quickstart (no Plex needed)

There's a demo mode with fake libraries and collections, so you can try it without
a server or any tokens:

```bash
git clone https://github.com/anthonykellyjr/plex-collection-manager
cd plex-collection-manager
docker compose up --build
```

Open http://localhost:8080 and log in with the key `demo`. Make a collection, drag
things around, switch between list and grid. Nothing hits a real server, and it
resets when you restart.

## Point it at your Plex

Same two containers, real data:

1. Copy `.env.example` to `.env`.
2. Set `DEMO_MODE=0` and fill in `PLEX_URL`, `PLEX_TOKEN`, and an `ADMIN_KEY` you pick.
3. `docker compose up --build`, then open http://localhost:8080 and log in with your `ADMIN_KEY`.

`ADMIN_KEY` is just the app's login (sent as the `X-Admin-Key` header). Here's how to
[find your Plex token](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/).

## What it does

- **Drag to reorder.** Posters in a grid, or a ranked row list like a Letterboxd diary. The list makes ranking easy; the toggle remembers which you used.
- **Search or browse to add.** Type to find a film, or flip to a Recent tab and add from the newest in your library.
- **Saves in the background.** Add, remove, rename, reorder, it all autosaves. A small status and a toast tell you it synced, no modal blocking the page.
- **Fast posters.** The backend caches resized posters on disk and only ever asks Plex for the size it needs, so it stays light on the server.
- **Kometa-aware.** Flags collections managed by [Kometa](https://kometa.wiki/) so you don't fight a tool that's going to overwrite you.
- **Smart collections are read-only**, so you can't break a rule-based one by accident.

## Screenshots

Drop images in `docs/screenshots/` and link them here, for example:

```
![Editor](docs/screenshots/editor.png)
![List view](docs/screenshots/list.png)
```

## How it works

```
browser ──>  nginx  ──/────────>  built Vue app (static)
                    ──/capi/──>   Flask API  ──>  Plex Media Server
```

- **web**: builds the Vue app and serves it with nginx, which also proxies `/capi` to the API.
- **api**: a small Flask service using [python-plexapi](https://github.com/pkkid/python-plexapi). In demo mode it serves the fixtures in `backend/demo.py` instead.

Two containers, one `docker compose up`. No database, collections live in Plex.

## Project layout

```
.
├── docker-compose.yml      # web + api, demo mode by default
├── Dockerfile              # frontend: vite build -> nginx
├── nginx.conf              # serves the app, proxies /capi -> api
├── index.html
├── vite.config.js
├── src/
│   ├── App.vue
│   ├── components/         # AuthGate, CollectionDetail, AddItemsPanel, PosterCard, ...
│   ├── composables/        # useApi, useViewPreference
│   └── shared/             # vendored UI bits so the repo is self-contained
└── backend/
    ├── Dockerfile          # gunicorn
    ├── api.py              # the /capi endpoints
    ├── demo.py             # in-memory data for demo mode
    └── requirements.txt
```

## Configuration

The API reads everything from the environment. Nothing is hardcoded.

| Variable           | Default                              | What it's for                                              |
|--------------------|--------------------------------------|------------------------------------------------------------|
| `DEMO_MODE`        | `1`                                  | Run with fake data and no Plex. Set `0` for a real server. |
| `PLEX_URL`         | `http://host.docker.internal:32400`  | Your Plex base URL.                                        |
| `PLEX_TOKEN`       | (none)                               | Plex server token. Required when `DEMO_MODE=0`.            |
| `ADMIN_KEY`        | `demo` in demo mode                  | The app's login key. Required when `DEMO_MODE=0`.          |
| `WEB_PORT`         | `8080`                               | Host port for the web UI.                                  |
| `GUNICORN_WORKERS` | `1`                                  | API workers. Demo needs 1; raise it for real use.         |

## Development

Node isn't required on the host. Run the dev server in a container with hot reload,
pointed at a running backend:

```bash
# backend on :5060
docker run --rm -p 5060:5000 --env-file .env collection-api

# vite dev server on :5173
docker run --rm -it -v "$(pwd):/app" -w /app -p 5173:5173 \
  --add-host=host.docker.internal:host-gateway \
  -e VITE_API_TARGET=http://host.docker.internal:5060 \
  node:22-alpine sh -c "npm install && npm run dev -- --host 0.0.0.0 --port 5173"
```

Then open http://localhost:5173.

## License

[MIT](LICENSE) © Anthony Kelly
