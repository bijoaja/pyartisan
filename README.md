# PyArtisan

PyArtisan is an AI-powered, multi-framework Python web development toolkit,
inspired by Laravel Artisan. It provides a single CLI (`pyartisan`) that
detects your project's framework and dispatches to the right generator —
starting with full support for Flask (via the [FlaskIQ](https://github.com/bijoaja/flaskiq)
project conventions), with FastAPI wired in as a structural placeholder for
a future release.

## Features

- Artisan-like CLI, framework-agnostic core with per-framework plugins
- Automatic framework detection (Flask now, FastAPI/Django planned)
- Full 5-layer Flask scaffold: Routes → Controller → Service → Repository → Model
- Auto install dependencies on project init
- Database migrations via Flask-Migrate
- Docker support for dev and production environments
- Persistent config at `~/.pyartisan/config.toml`
- `doctor` command to check your local dev environment
- Python 3.10+ support

## Installation

Install directly from source:

```bash
git clone https://github.com/bijoaja/flaskartisan.git
cd flaskartisan
pip install -e .
```

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
pyartisan init flask myapp
```

Clones the FlaskIQ template and optionally sets up a virtual environment.

FastAPI isn't implemented yet (`pyartisan init fastapi api` will report it's
not supported); use `pyartisan fastapi status` to check its placeholder state.

### Framework detection

Most commands below auto-detect the framework from files in the current
directory (`app.py` + `Flask(`/`create_app(` for Flask, `main.py` + `FastAPI(`
for FastAPI). If detection fails, pass `--framework` explicitly:

```bash
pyartisan make:model Post --framework flask
```

If no framework can be detected and `--framework` isn't given:

```
Project framework cannot be detected.
Please specify:
  --framework flask
```

### Scaffold a controller

Generates a controller, service, and route file for the given feature.

```bash
# View controller (HTML responses)
pyartisan make:controller Post --type view

# API controller (JSON responses, versioned)
pyartisan make:controller Post --type api

# Fullstack (view + API in one command)
pyartisan make:controller Post --type fullstack

# Specify API version (default: 1)
pyartisan make:controller Post --type api --version 2
```

### Scaffold a standalone service

```bash
pyartisan make:service Post --type view
pyartisan make:service Post --type api
```

### Scaffold a model

Generates a separate model file with `to_dict()` and updates `app/model/__init__.py`:

```bash
pyartisan make:model Post
```

### Scaffold a repository

Generates a data-access repository class and updates `app/repository/__init__.py`:

```bash
pyartisan make:repository Post
```

### Database migrations

```bash
# Create a migration
pyartisan make:migrations -m "add posts table"

# Create and immediately apply
pyartisan make:migrations -m "add posts table" --upgrade
```

### Generate Docker files

Creates `Docker/Dockerfile` (prod), `Docker/Dockerfile.dev`, and `docker-compose.yml`:

```bash
pyartisan make:docker
```

### Copy environment file

```bash
pyartisan make:env
```

### Run the dev server

**Local** (requires active virtual environment and `server.py`):

```bash
pyartisan serve
```

**Docker** (requires `Docker/Dockerfile.dev` and `docker-compose.yml`):

```bash
# Start containers
pyartisan serve --docker

# Start and rebuild image
pyartisan serve --docker --build
```

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
│   │   ├── post.py               # Blueprint per feature (make:controller --type view)
│   │   └── api/
│   │       └── v1/
│   │           └── __init__.py   # API resource registrations (make:controller --type api)
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
│   │   └── post_repository.py    # make:repository Post
│   ├── model/
│   │   ├── __init__.py
│   │   └── post.py               # make:model Post
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

PyArtisan is a framework-agnostic core CLI that dispatches to per-framework
plugins. See `CLAUDE.md` for the full breakdown of `src/pyartisan/` (core),
`src/flasktool/` (Flask plugin), and `src/fastapitool/` (FastAPI placeholder).

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
