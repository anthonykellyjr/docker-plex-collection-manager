# docker-plex-collection-manager

![License](https://img.shields.io/badge/license-MIT-blue)
![web image](https://img.shields.io/badge/ghcr.io-web-2496ed)
![api image](https://img.shields.io/badge/ghcr.io-api-2496ed)
![Vue](https://img.shields.io/badge/Vue-3-42b883)
![Flask](https://img.shields.io/badge/Flask-API-000000)

A Letterboxd-style web app for ranking and editing **Plex collections** by hand,
packaged as two small Docker images: an nginx-served Vue app and a Flask API that
talks to Plex with [python-plexapi](https://github.com/pkkid/python-plexapi).

It ships with a demo mode, so you can run the whole thing with no Plex server and
no tokens.

## Images

| Image | Description |
|-------|-------------|
| `ghcr.io/anthonykellyjr/plex-collection-manager-web` | nginx serving the built app, proxies `/capi` to the API |
| `ghcr.io/anthonykellyjr/plex-collection-manager-api` | Flask backend (python-plexapi) |

## Usage

```yaml
# docker-compose.yml
services:
  api:
    image: ghcr.io/anthonykellyjr/plex-collection-manager-api:latest
    environment:
      - DEMO_MODE=0
      - PLEX_URL=http://your-plex-host:32400
      - PLEX_TOKEN=your-plex-token
      - ADMIN_KEY=change-me
    volumes:
      - poster-cache:/cache
    restart: unless-stopped
  web:
    image: ghcr.io/anthonykellyjr/plex-collection-manager-web:latest
    ports:
      - 8080:80
    depends_on:
      - api
    restart: unless-stopped
volumes:
  poster-cache:
```

```bash
docker compose up -d
```

Then open `http://localhost:8080` and log in with your `ADMIN_KEY`.

### Try the demo (no Plex)

```bash
git clone https://github.com/anthonykellyjr/docker-plex-collection-manager
cd docker-plex-collection-manager
docker compose up --build
```

`DEMO_MODE` is on by default, so this works with no Plex. Open `http://localhost:8080`
and log in with the key `demo`. Make a collection, drag to reorder, switch list/grid.
It resets when you restart.

## Parameters

| Parameter | Function |
|-----------|----------|
| `-p 8080:80` | Web UI (the `web` container). |
| `-e DEMO_MODE=1` | Run with fake data and no Plex. Set `0` for a real server. |
| `-e PLEX_URL` | Plex base URL, e.g. `http://10.0.0.10:32400`. Needed when `DEMO_MODE=0`. |
| `-e PLEX_TOKEN` | Plex server token. Needed when `DEMO_MODE=0`. |
| `-e ADMIN_KEY` | The app's login, sent as `X-Admin-Key`. Needed when `DEMO_MODE=0`. |
| `-e GUNICORN_WORKERS=1` | API workers. Demo needs 1; raise it for real use. |
| `-v /cache` | Where the `api` container caches resized posters. |

Here's how to [find your Plex token](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/).

## What it does

- **Drag to reorder.** Poster grid or a ranked row list like a Letterboxd diary. The toggle remembers which you used.
- **Search or browse to add.** Type to find a film, or flip to a Recent tab and add from the newest in your library.
- **Saves in the background.** Add, remove, rename, reorder, it all autosaves. A small status and a toast confirm it, no modal blocking the page.
- **Fast posters.** The API caches resized posters on disk and only asks Plex for the size it needs, so it stays light on the server.
- **Kometa-aware.** Flags collections managed by [Kometa](https://kometa.wiki/) so you don't fight a tool that will overwrite you.
- **Smart collections are read-only**, so a rule-based one can't be broken by accident.

## Screenshots

Drop images in `docs/screenshots/` and link them here:

```
![Editor](docs/screenshots/editor.png)
![List view](docs/screenshots/list.png)
```

## How it works

```
browser ──>  web (nginx)  ──/────────>  built Vue app
                          ──/capi/──>   api (Flask)  ──>  Plex Media Server
```

No database. Collections live in Plex. In demo mode the API serves the fixtures in
`backend/demo.py` instead of talking to Plex.

## Build from source

The compose file above builds locally if you swap `image:` for `build:` (the repo's
own `docker-compose.yml` already does, for the demo). To build the images yourself:

```bash
docker build -t plex-collection-manager-web .
docker build -t plex-collection-manager-api ./backend
```

For frontend dev with hot reload, point Vite at a running API:

```bash
docker run --rm -it -v "$(pwd):/app" -w /app -p 5173:5173 \
  --add-host=host.docker.internal:host-gateway \
  -e VITE_API_TARGET=http://host.docker.internal:5060 \
  node:22-alpine sh -c "npm install && npm run dev -- --host 0.0.0.0 --port 5173"
```

## License

[MIT](LICENSE) © Anthony Kelly
