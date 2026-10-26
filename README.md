# PyArtisan

PyArtisan is a multi-framework Python web development toolkit, inspired by
Laravel Artisan. It provides a single CLI (`pyartisan`) that clones a
framework template into a new project and then reads that project's
`.pyartisan/manifest.yaml` to generate code — full support for Flask (via the
[FlaskIQ](https://github.com/bijoaja/flaskiq) project conventions), with
FastAPI (via [FastIQ](https://github.com/bijoaja/fastiq)) as a structural
placeholder for a future release.

## Features

- Artisan-like CLI, framework-agnostic core driven by per-project manifest
- Manifest-driven code generation (`make`) — no hardcoded generator per framework
- Full 5-layer Flask scaffold: Routes → Controller → Service → Repository → Model
- Auto install dependencies on project init
- Docker-first `serve` with local-venv fallback
- A package-manager-style plugin system (install/apply/remove, see [CLI.md](CLI.md#7-sistem-plugin))
- Persistent config at `~/.pyartisan/config.toml`
- `doctor` command to check your local dev environment
- Python 3.10+ support

## Installation

Recommended — with [uv](https://docs.astral.sh/uv/) (isolated; no venv, system Python untouched):

```bash
uv tool install git+https://github.com/bijoaja/pyartisan
# or run without installing:
uvx --from git+https://github.com/bijoaja/pyartisan pyartisan --help
```

From source:

```bash
git clone https://github.com/bijoaja/pyartisan.git
cd pyartisan
uv tool install .          # or: pip install -e .
```

When `uv` is on `PATH`, `pyartisan new` also creates the project venv and installs dependencies with uv (falls back to venv + pip otherwise).

## Requirements

- Python ≥ 3.10
- Flask
- SQLAlchemy
- Click

## Usage

PyArtisan registers the `pyartisan` command. Run anywhere inside your project.

```bash
pyartisan --help
```

### Initialize a new project

```bash
pyartisan new flask myapp
pyartisan new fastapi myapi
```

Clones the framework template (FlaskIQ for `flask`, FastIQ for `fastapi`, see
`pyartisan config show` for the URLs) and optionally sets up a virtual
environment plus `requirements.txt` install. Template URLs can be overridden
with `pyartisan config set templates.<framework> <url>`.

### Framework detection

There is no filesystem-based auto-detection. The framework is recorded once,
at `pyartisan new` time, in `.pyartisan/project.yaml` (and template metadata
in `.pyartisan/manifest.yaml`). Commands like `make` and `serve` read that
manifest — always run them from inside a project created by `pyartisan new`.

### Scaffold code (`make`)

```bash
pyartisan make <target> <name> [--force] [--<option> <value> ...]
```

`make` reads `.pyartisan/manifest.yaml` inside the project to know which
generators exist (`model`, `controller`, `service`, `repository`, etc. —
depends on the template). Extra `--option value` pairs are passed straight
into the Jinja2 render context (e.g. `--type`, `--version`).

```bash
# Controller (route + controller + service for the feature)
pyartisan make controller Post --type view
pyartisan make controller Post --type api
pyartisan make controller Post --type api --version 2

# Standalone service
pyartisan make service Post --type view

# Model — generates a model file and updates app/model/__init__.py
pyartisan make model Post

# Repository — generates a data-access class and updates app/repository/__init__.py
pyartisan make repository Post
```

Unknown targets, or running outside a project with `.pyartisan/manifest.yaml`,
fail with a clear error.

### Run the dev server

```bash
pyartisan serve
```

No flags — `serve` auto-detects the strategy: uses Docker (`docker compose up`)
if `docker-compose.yml` exists and Docker is running, otherwise falls back to
the `scripts.serve` command from `.pyartisan/manifest.yaml` inside an active
virtualenv, otherwise prints instructions to fix your setup.

### Build production Docker image

```bash
pyartisan build
```

### Configuration

```bash
pyartisan config          # same as config show
pyartisan config show
pyartisan config set default_framework fastapi
pyartisan config reset
```

### Doctor

Checks Python, pip, Git, and virtual environment health:

```bash
pyartisan doctor
```

### Version

```bash
pyartisan version
```

## Generated Project Structure

Running PyArtisan's Flask commands inside a FlaskIQ project produces:

```
project_name/
├── app/
│   ├── __init__.py
│   ├── routes/
│   │   ├── post.py               # Blueprint per feature (make controller --type view)
│   │   └── api/
│   │       └── v1/
│   │           └── __init__.py   # API resource registrations (make controller --type api)
│   ├── controller/
│   │   ├── view/
│   │   │   └── post/
│   │   │       ├── __init__.py
│   │   │       └── post_controller.py
│   │   └── api/
│   │       └── v1/
│   │           └── post/
│   │               ├── __init__.py
│   │               └── post_controller.py
│   ├── service/
│   │   ├── __init__.py
│   │   ├── post_service.py
│   │   └── api/
│   │       └── v1/
│   │           ├── __init__.py
│   │           └── post_service.py
│   ├── repository/
│   │   ├── __init__.py
│   │   └── post_repository.py    # make repository Post
│   ├── model/
│   │   ├── __init__.py
│   │   └── post.py               # make model Post
│   ├── templates/
│   └── static/
├── utils/
│   ├── response.py
│   └── middleware.py
├── Docker/
│   ├── Dockerfile                # Production
│   └── Dockerfile.dev            # Development
├── docker-compose.yml
├── server.py
├── requirements.txt
├── .env.example
├── Makefile
└── README.md
```

## Architecture

PyArtisan is a single package (`src/pyartisan/`) — a framework-agnostic
engine whose thin `cli/` parser dispatches, via `core/engine.py`, to
generators driven by each project's own `.pyartisan/manifest.yaml`. There is
no hardcoded Flask/FastAPI code in the core; framework support lives in the
FlaskIQ/FastIQ template repos themselves. A separate community/marketplace
plugin system exists on top of this (installed under `~/.pyartisan/plugins/`
and applied to a project via `pyartisan plugin apply`) — see
[CLI.md](CLI.md#7-sistem-plugin) and [HOW_TO_CREATE_PLUGIN.md](HOW_TO_CREATE_PLUGIN.md).
See `CLAUDE.md` for the full directory breakdown.

Generated Flask code follows the FlaskIQ 5-layer architecture:

```
HTTP Request → Routes → Controller → Service → Repository → Model
```

| Layer | Directory | Responsibility |
|-------|-----------|----------------|
| Routes | `app/routes/` | Map URLs to controllers via Blueprint |
| Controller | `app/controller/` | Parse request, validate input, call one service method |
| Service | `app/service/` | All business logic, raise `ValueError` for domain errors |
| Repository | `app/repository/` | Exclusive `db.session` access, return ORM instances |
| Model | `app/model/` | SQLAlchemy ORM definitions + `to_dict()` |

## Configuration

`pyartisan` is registered as a script entry point:

```
pyartisan = "pyartisan.cli:cli"
```

Persistent user config lives at `~/.pyartisan/config.toml`:

```toml
theme = "default"
author = ""
license = "MIT"
default_framework = "flask"
```

## Contributing

Contributions are welcome!
Feel free to submit issues, feature requests, or pull requests.

## License

This project is licensed under the MIT License.
