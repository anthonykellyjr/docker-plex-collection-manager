# Collection Manager — Drag-and-Drop Plex Collections

![Vue](https://img.shields.io/badge/Vue-3-42b883)
![Vite](https://img.shields.io/badge/Vite-5-646cff)
![Tailwind](https://img.shields.io/badge/Tailwind-3-38bdf8)
![Flask](https://img.shields.io/badge/Flask-API-000000)
![plexapi](https://img.shields.io/badge/plexapi-powered-e5a00d)
![License](https://img.shields.io/badge/license-MIT-blue)

A fast, Letterboxd-style web app for building and curating **Plex collections** by hand.
Search your library, drag posters into the order you want, rename and describe the
collection, and push it straight to your Plex Media Server — all from the browser.

Built as a Vue 3 single-page app backed by a small Flask + [`python-plexapi`](https://github.com/pkkid/python-plexapi)
service. Designed to run behind nginx on a home media server.

---

## Features

- **Drag-and-drop ordering** — reorder a collection's posters with a live, animated grid.
- **Inline search & add** — an always-visible library search panel; click to add a film.
- **Auto-save with confirmation** — title, description, and add/remove changes save
  automatically (debounced) and surface a clear "Synced to Plex" modal; reordering is a
  deliberate **Save** so you can arrange freely first.
- **Unsaved-changes guard** — leaving (back, logo, library switch, logout, reload, or tab
  close) with pending changes prompts a custom Save / Discard / Cancel dialog.
- **Reload** — refetch the collection from Plex on demand, with a success/error toast.
- **Kometa-aware** — flags collections managed by [Kometa](https://kometa.wiki/) so you
  know when changes may be overwritten on the next run.
- **Smart-collection safe** — read-only handling for smart collections (no accidental edits).
- **Per-save Plex stats** — the save modal reports API calls, reorder ops, and throughput.

---

## Screenshots

> _Add screenshots to `docs/` and reference them here, e.g._
>
> `![Collection editor](docs/editor.png)`

---

## Architecture

```
┌──────────────────────────┐        /collections/ (static)        ┌───────────────┐
│  Vue 3 SPA (this repo)    │  ───────────────────────────────▶   │     nginx     │
│  Vite build → dist/       │                                      │  (web-router) │
└──────────────────────────┘                                      └──────┬────────┘
                                                                          │ /capi/* proxy
                                                                          ▼
                                                       ┌──────────────────────────────┐
                                                       │  collection-api (Flask)        │
                                                       │  backend/api.py + python-plexapi│
                                                       │  → Plex Media Server            │
                                                       └──────────────────────────────┘
```

- **Frontend** (`src/`): Vue 3 + Vite + Tailwind. Served as static files at `/collections/`.
- **Backend** (`backend/`): Flask API proxied at `/capi/`. Talks to Plex via `python-plexapi`.
- **Vendored shared UI** (`src/shared/`): `PageHeader`, `HubButton`, `PasswordInput`,
  the `useApi` fetch wrapper, and shared styles — copied in so this repo is self-contained.

---

## Project structure

```
collection-manager/
├── index.html
├── package.json            # standalone (no monorepo workspace)
├── vite.config.js          # base: /collections/, /capi dev proxy, idle-shutdown
├── tailwind.config.js
├── postcss.config.js
├── vite/
│   └── idle-shutdown.js     # auto-stops the dev server after 30 min idle
├── src/
│   ├── main.js
│   ├── style.css
│   ├── App.vue
│   ├── components/          # AuthGate, CollectionDetail, CollectionsGrid, PosterCard, …
│   ├── composables/
│   │   └── useApi.js         # X-Admin-Key fetch wrapper
│   └── shared/              # vendored reusable UI (PageHeader, PasswordInput, …)
└── backend/
    ├── api.py               # Flask collection API (proxied at /capi)
    ├── Dockerfile
    └── requirements.txt
```

---

## Configuration

The backend reads all secrets from the environment (nothing is hardcoded). Copy
[`.env.example`](.env.example) to `.env` and fill in:

| Variable     | Required | Description                                            |
|--------------|----------|--------------------------------------------------------|
| `PLEX_URL`   | no       | Plex base URL. Defaults to `http://10.0.0.222:32400`.  |
| `PLEX_TOKEN` | yes      | Plex server token (`X-Plex-Token`).                    |
| `ADMIN_KEY`  | yes      | Key required by every `/capi` endpoint (`X-Admin-Key`).|
| `KELLY_KEY`  | yes      | Access code for the Kelly Collection endpoints.        |

---

## Development

Node is not required on the host — develop inside Docker with hot-reload:

```bash
docker run --rm -it \
  -v "$(pwd):/app" -w /app \
  -p 5173:5173 \
  --add-host=host.docker.internal:host-gateway \
  node:22-alpine \
  sh -c "npm install && npm run dev -- --host 0.0.0.0 --port 5173"
```

Then open `http://localhost:5173/collections/`. The dev server proxies `/capi/*` to a
running `collection-api` on the host at `:5060` (via `host.docker.internal`), and
auto-shuts down after 30 minutes of inactivity.

---

## Build

```bash
docker run --rm -v "$(pwd):/app" -w /app node:22-alpine \
  sh -c "npm install && npm run build"
```

Outputs static files to `dist/`, ready to serve at `/collections/`.

### Backend

```bash
docker build -t collection-api ./backend
docker run --rm -p 5060:5000 --env-file .env collection-api
```

---

## Deployment notes

On the home server this runs as two pieces:

- **nginx** serves `dist/` at `/collections/` and proxies `/capi/*` to the backend.
- **collection-api** (the `backend/` image) runs on `:5060`, with `plex.tv` /
  `app.plex.tv` pinned to `127.0.0.1` so `python-plexapi` can't re-register the
  server's identity on plex.tv.

---

## License

[MIT](LICENSE) © 2026 Anthony Kelly
