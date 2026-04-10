# FlaskArtisan

FlaskArtisan is a command-line tool inspired by Laravel Artisan,
designed to streamline development workflows in Flask applications. It
provides a convenient CLI interface to scaffold controllers, services,
repositories, and models; manage database migrations; and spin up dev
servers — all following the [FlaskIQ](https://github.com/bijoaja/flaskiq)
project conventions.

## Features

- Artisan-like CLI commands for Flask
- Full 5-layer scaffold: Routes → Controller → Service → Repository → Model
- Auto install dependencies on project init
- Database migrations via Flask-Migrate
- Docker support for dev and production environments
- Integrates with SQLAlchemy
- Git automation powered by GitPython
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
- GitPython

## Usage

FlaskArtisan registers the `flasktool` command. Run anywhere inside your project.

```bash
flasktool --help
```

### Initialize a new project

Clones the FlaskIQ template and optionally sets up a virtual environment:

```bash
flasktool init:project my_app
```

### Scaffold a controller

Generates a controller, service, and route file for the given feature.

```bash
# View controller (HTML responses)
flasktool make:controller Post --type view

# API controller (JSON responses, versioned)
flasktool make:controller Post --type api

# Fullstack (view + API in one command)
flasktool make:controller Post --type fullstack

# Specify API version (default: 1)
flasktool make:controller Post --type api --version 2
```

### Scaffold a standalone service

```bash
flasktool make:service Post --type view
flasktool make:service Post --type api
```

### Scaffold a model

Generates a separate model file with `to_dict()` and updates `app/model/__init__.py`:

```bash
flasktool make:model Post
```

### Scaffold a repository

Generates a data-access repository class and updates `app/repository/__init__.py`:

```bash
flasktool make:repository Post
```

### Database migrations

```bash
# Create a migration
flasktool make:migrations -m "add posts table"

# Create and immediately apply
flasktool make:migrations -m "add posts table" --upgrade
```

### Generate Docker files

Creates `Docker/Dockerfile` (prod), `Docker/Dockerfile.dev`, and `docker-compose.yml`:

```bash
flasktool make:docker
```

### Copy environment file

```bash
flasktool make:env
```

### Run the dev server

**Local** (requires active virtual environment and `server.py`):

```bash
flasktool serve
```

**Docker** (requires `Docker/Dockerfile.dev` and `docker-compose.yml`):

```bash
# Start containers
flasktool serve --docker

# Start and rebuild image
flasktool serve --docker --build
```

### Build production Docker image

```bash
flasktool build
```

## Generated Project Structure

Running FlaskArtisan commands inside a FlaskIQ project produces:

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

FlaskArtisan scaffolds code that follows the FlaskIQ 5-layer architecture:

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

`flasktool` is registered as a script entry point:

```
flasktool = "flasktool.cli:cli"
```

## Contributing

Contributions are welcome!
Feel free to submit issues, feature requests, or pull requests.

## License

This project is licensed under the MIT License.
