# PyArtisan

> **Language:** English | [Indonesia](README.id.md)

PyArtisan is a multi-framework Python web development CLI, inspired by Laravel Artisan. `pyartisan new` clones a framework template into a new project; later commands such as `make` read that project's `.pyartisan/manifest.yaml` to generate code. The core is framework-agnostic: framework knowledge lives in the template repos, [FlaskIQ](https://github.com/bijoaja/flaskiq) for Flask and [FastIQ](https://github.com/bijoaja/fastiq) for FastAPI.

## Features

- `new`: clone a framework template and set up the project (venv and dependencies, optional)
- `make`: generate code from the generators declared in the project's manifest, with no hardcoded generator per framework
- `serve`: Docker first, then the project's venv
- `build`: run the build script from the manifest
- `plugin`: package-manager-style plugins (`install`, `apply`, `remove`, ...), see [docs/en/CLI.md](docs/en/CLI.md#7-plugin-system)
- `config`: persistent settings in `~/.pyartisan/config.toml`
- `doctor`: check your local environment
- Works with [uv](https://docs.astral.sh/uv/) (isolated install, no venv needed); pip also works
- Python 3.10+

## Installation

Recommended, with [uv](https://docs.astral.sh/uv/). It installs into an isolated environment, so you do not need to create a venv and your system Python is untouched:

```bash
uv tool install git+https://github.com/bijoaja/pyartisan
# or run without installing:
uvx --from git+https://github.com/bijoaja/pyartisan pyartisan --help
```

From source:

```bash
git clone https://github.com/bijoaja/pyartisan.git
cd pyartisan
uv tool install .      # or: uv tool install --editable .   (for contributors)
# without uv: pip install -e .
```

If `pyartisan` is not found afterwards, run `uv tool update-shell` and open a new terminal.

When `uv` is on `PATH`, `pyartisan new` also creates the project venv and installs dependencies with uv. Otherwise it falls back to `python -m venv` and pip.

## Requirements

- Python ≥ 3.10 (uv can download it for you)
- Git (`pyartisan new` and GitHub plugin installs use `git clone`)
- Runtime dependencies are declared in `pyproject.toml`: `click`, `flask`, `sqlalchemy`, `jinja2`, `pyyaml`, and `tomli` on Python < 3.11. `flask` and `sqlalchemy` are not imported by PyArtisan's own code.

## Usage

```bash
pyartisan --help
```

### Create a new project

```bash
pyartisan new flask myapp
pyartisan new fastapi myapi
```

Runs `git clone` of the template (FlaskIQ for `flask`, FastIQ for `fastapi`; see `pyartisan config show` for the URLs), writes `.pyartisan/project.yaml`, then asks whether to create `./venv` and install `requirements.txt`. Template URLs can be changed with `pyartisan config set templates.<framework> <url>`.

### How the framework is known

There is no auto-detection from files. The framework is recorded once, by `pyartisan new`, in `.pyartisan/project.yaml`. `make` and `serve` read `.pyartisan/manifest.yaml`, so run them from inside a project created by `pyartisan new`.

### Generate code (`make`)

```bash
pyartisan make <target> <name> [--force] [--<option> <value> ...]
```

`<target>` must be a generator declared in the project's `.pyartisan/manifest.yaml`. For FlaskIQ these are `controller`, `service`, `repository`, `model` and `routes`; FastIQ declares `module` and `model`. Extra `--option value` pairs go straight into the Jinja2 render context (defaults: `type` = `view`, `version` = `1`).

```bash
pyartisan make model Post
pyartisan make repository Post
pyartisan make service Post --type view
pyartisan make controller Post --type api --version 2
```

An unknown target, or running outside a project that has `.pyartisan/manifest.yaml`, fails with an error and exit code 1.

### Run the dev server

```bash
pyartisan serve
```

No flags. `serve` picks a strategy automatically:

1. Docker (`docker compose up`) if `docker-compose.yml` exists and Docker is running.
2. Otherwise, the `scripts.serve` command from the manifest, run inside the project's own venv (`./venv` or `./.venv`). This also works when PyArtisan itself was installed with `uv tool`.
3. Otherwise, an error with instructions (exit code 1).

### Build

```bash
pyartisan build
```

Runs `scripts.build` from `.pyartisan/manifest.yaml`. Fails with exit code 1 if the manifest defines no build script.

### Configuration

```bash
pyartisan config          # same as: config show
pyartisan config show
pyartisan config set templates.flask https://github.com/you/your-flaskiq-fork.git
pyartisan config reset
```

### Doctor and version

```bash
pyartisan doctor     # Python, uv, pip, Git, virtual environment
pyartisan version
```

### Plugins

```bash
pyartisan plugin init my-plugin               # scaffold a plugin and link it for development
pyartisan plugin install user/repo            # clone from GitHub into ~/.pyartisan/plugins
pyartisan plugin apply my-plugin              # apply it to the current project
pyartisan plugin list --global
```

See [docs/en/CLI.md](docs/en/CLI.md#7-plugin-system) for every plugin command and [docs/en/HOW_TO_CREATE_PLUGIN.md](docs/en/HOW_TO_CREATE_PLUGIN.md) to write one.

## Project structure

The folder layout of a generated project comes from its template, not from PyArtisan. Look at the template repo ([FlaskIQ](https://github.com/bijoaja/flaskiq), [FastIQ](https://github.com/bijoaja/fastiq)) for the current layout.

PyArtisan itself is one package, `src/pyartisan/`:

| Folder | Role |
|---|---|
| `cli/commands/` | one file per command, parses arguments only |
| `core/` | `engine.py` (dispatch), manifest loading, registration, `ProjectContext` for plugin hooks |
| `marketplace/` | global plugin registry in `~/.pyartisan/plugins` |
| `renderer/`, `config/`, `shared/`, `utils/` | Jinja2 rendering, `config.toml`, doctor logic, helpers |
| `templates/plugin_init/` | skeleton used by `plugin init` |

## Configuration file

`~/.pyartisan/config.toml` is created on first use:

```toml
theme = "default"
author = ""
license = "MIT"
default_framework = "flask"

[templates]
flask = "https://github.com/bijoaja/flaskiq.git"
fastapi = "https://github.com/bijoaja/fastiq.git"
```

Only `templates.*` is read by a command today (`new`); the other keys are stored but not used yet.

## Documentation

| Document | English | Indonesia |
|---|---|---|
| CLI reference | [docs/en/CLI.md](docs/en/CLI.md) | [docs/id/CLI.md](docs/id/CLI.md) |
| Writing a plugin | [docs/en/HOW_TO_CREATE_PLUGIN.md](docs/en/HOW_TO_CREATE_PLUGIN.md) | [docs/id/HOW_TO_CREATE_PLUGIN.md](docs/id/HOW_TO_CREATE_PLUGIN.md) |
| Product requirements and status | [docs/en/PRD.md](docs/en/PRD.md) | [docs/id/PRD.md](docs/id/PRD.md) |
| Contributor guide | [docs/en/CONTRIBUTING.md](docs/en/CONTRIBUTING.md) | [docs/id/CONTRIBUTING.md](docs/id/CONTRIBUTING.md) |

## Contributing

Contributions are welcome. Start with [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT, see [LICENSE](LICENSE).
