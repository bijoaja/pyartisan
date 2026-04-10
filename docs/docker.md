# Docker & Makefile

## Development

The dev setup uses a **bind-mounted** container — your local source code is mounted directly into the container, so changes are reflected immediately without rebuilding.

```bash
# Start dev server
make dev

# View logs
make logs

# Open a shell in the container
make shell

# Stop the server
make stop
```

Dev stack: `docker-compose.yml` → `Docker/Dockerfile.dev`

- Flask built-in dev server (`python server.py`)
- `FLASK_DEBUG=TRUE` — auto-reload on file changes
- MySQL + Ollama services included

## Production

The prod setup uses a **multi-stage Docker build** — no source bind mount, leaner image, Gunicorn WSGI server.

```bash
# Start prod server
make prod

# Stop prod server
make prod-stop
```

Prod stack: `docker-compose.prod.yml` → `Docker/Dockerfile.prod`

- Multi-stage build: `builder` installs deps, `runtime` copies only what's needed
- Gunicorn with 4 workers (`--workers 4`)
- Non-root user (`appuser`) for container security
- Ollama is excluded — use `AI_PROVIDER=openai` in production

## Database

```bash
# First time setup (initialise + first migration + upgrade)
make db-setup

# After changing models
make db-migrate MESSAGE="add user roles"
make db-upgrade
```

## Image Management

```bash
# Build dev image
make build-dev

# Build prod image (tagged latest + VERSION)
make build-prod VERSION=2.1.0

# Push to Docker Hub
make push VERSION=2.1.0

# Full release: build + tag + push + git commit
make all VERSION=2.1.0 MESSAGE="Release 2.1.0"
```

## Environment Variables

Copy `.env.example` to `.env` and fill in the values:

| Variable              | Required | Description                                    |
|-----------------------|----------|------------------------------------------------|
| `SECRET_KEY`          | Yes      | Flask secret key (any long random string)      |
| `JWT_KEY`             | Yes      | JWT signing secret                             |
| `DATABASE_URL`        | No       | Defaults to `sqlite:///flaskiq.db`             |
| `AI_PROVIDER`         | No       | `ollama` (default) or `openai`                 |
| `OLLAMA_HOST`         | No       | Ollama server URL (default: localhost:11434)   |
| `OLLAMA_MODEL`        | No       | Model name (default: `mistral`)                |
| `AI_KEY`              | Openai   | OpenAI API key                                 |
| `OPENAI_MODEL`        | No       | OpenAI model (default: `gpt-4o-mini`)          |
| `FLASK_RUN_PORT`      | No       | Port to expose (default: `8080`)               |
| `JWT_EXPIRY_MINUTES`  | No       | Token lifetime (default: `60`)                 |

## Tailwind CSS Note

The templates use Tailwind's **Play CDN** (`cdn.tailwindcss.com`) for zero-configuration setup.  
For a production deployment where CDN latency matters, replace it with a compiled CSS file:

```bash
# Install Tailwind CLI
npm install -D tailwindcss
npx tailwindcss init

# Build CSS
npx tailwindcss -i ./app/static/css/app.css -o ./app/static/css/tailwind.min.css --minify
```

Then replace the CDN `<script>` tag in `base.html` with:
```html
<link rel="stylesheet" href="{{ url_for('static', filename='css/tailwind.min.css') }}">
```
