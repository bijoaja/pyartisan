---
name: pyartisan
description: Use when creating, scaffolding, developing, serving, building, configuring, or managing plugins for Python web applications using the PyArtisan CLI (FlaskIQ and FastIQ).
---

# PyArtisan Skill

## Overview
PyArtisan is a framework-agnostic Python web development toolkit driven by project manifests (`.pyartisan/manifest.yaml`). It unifies template-based project generation (FlaskIQ, FastIQ), automated component scaffolding with AST/marker registration, local development execution, and an extensible plugin marketplace.

## When to Use
- Initializing a new Python web project with modern structure and preconfigured toolchain (`uv`/`pip`, linters, tests).
- Scaffolding components (controllers, models, services, routes, middleware) using template stubs with automatic import and router registration.
- Running diagnostics on local Python virtual environments, Git, and project dependencies.
- Serving local development environments with automatic Docker Compose detection or virtualenv isolation.
- Building production artifacts defined in project manifests.
- Installing, authoring, and applying modular plugins from the PyArtisan plugin registry.

### When NOT to Use
- Legacy or unstructured Python scripts with no framework architecture.
- Projects without a `.pyartisan/manifest.yaml` where custom manual file generation is explicitly requested.
- Frameworks currently unsupported by registered templates (unless initializing a custom template via `pyartisan config`).

---

## Quick Reference

| Command | Usage | Description |
|---|---|---|
| `pyartisan --version` | `pyartisan --version` | Display current PyArtisan CLI version |
| `pyartisan doctor` | `pyartisan doctor` | Check Python, pip, Git, venv, and environment health |
| `pyartisan new` | `pyartisan new <framework> <project_name>` | Clone template (`fastapi` or `flask`), init venv & deps |
| `pyartisan make` | `pyartisan make <target> <Name> [--force]` | Scaffold component from stub with auto-registration |
| `pyartisan serve` | `pyartisan serve` | Launch dev server (Docker Compose fallback to venv script) |
| `pyartisan build` | `pyartisan build` | Run production build script specified in `manifest.yaml` |
| `pyartisan config show` | `pyartisan config show` | Print `~/.pyartisan/config.toml` |
| `pyartisan config set` | `pyartisan config set <key> <value>` | Set global configuration key (e.g. templates) |
| `pyartisan config reset`| `pyartisan config reset` | Reset global config to factory defaults |
| `pyartisan plugin init`| `pyartisan plugin init <id>` | Scaffold a new plugin skeleton and link to dev registry |
| `pyartisan plugin install`| `pyartisan plugin install <user/repo> [--local <dir>]` | Download/link plugin into `~/.pyartisan/plugins/` |
| `pyartisan plugin apply`| `pyartisan plugin apply <id> [--yes]` | Execute plugin hooks & inject dependencies into project |
| `pyartisan plugin list` | `pyartisan plugin list [--global] [--updates]` | List project or global registry plugins, check git updates |
| `pyartisan plugin status`| `pyartisan plugin status` | Show applied plugins and health status for project |
| `pyartisan plugin doctor`| `pyartisan plugin doctor` | Diagnose manifest, framework, and plugin dependencies |
| `pyartisan plugin info` | `pyartisan plugin info <id>` | Inspect plugin metadata, author, and usage |
| `pyartisan plugin update`| `pyartisan plugin update <id> [--yes]` | Pull latest git changes for plugin and re-apply |
| `pyartisan plugin remove`| `pyartisan plugin remove <id...> [--all] [--yes]` | Detach plugin from project & run remove hooks |
| `pyartisan plugin uninstall`| `pyartisan plugin uninstall <id...> [--all]` | Delete plugin from global registry (fails if still used) |

---

## Workflows & Implementation

### 1. Prerequisites & CLI Verification

Always verify CLI availability before invoking commands:

```bash
pyartisan --version
```

If the command fails or `pyartisan` is not found:
1. Ask the user for their preferred clone directory:
   > "PyArtisan CLI is not installed on this system. Please specify a directory path to clone https://github.com/bijoaja/pyartisan.git:"
2. Clone and install in editable mode:
   ```bash
   git clone https://github.com/bijoaja/pyartisan.git <target_path>
   cd <target_path>
   # Priority 1: Fast isolated tool install via uv
   uv tool install --editable .
   # Fallback: pip editable install
   pip install -e .
   ```
3. Confirm with `pyartisan --version`.

---

### 2. Project Initialization (`pyartisan new`)

PyArtisan clones official templates from `bijoaja/flaskiq` (Flask) and `bijoaja/fastiq` (FastAPI).

1. **Framework Selection**:
   - `fastapi`: Async REST API with automatic OpenAPI documentation.
   - `flask`: Modular MVC with Jinja2 templating.
2. **Execute Creation**:
   ```bash
   pyartisan new <framework> <project_name>
   ```
   **Important (Non-Interactive CLI Handling):**
   `pyartisan new` executes `click.confirm("Do you want to create a virtual environment and install dependencies now?", default=True)`. In an automated agent shell, send an empty newline / Enter so the default (`True`) is chosen, prompting PyArtisan to automatically initialize the venv (`uv venv` or `python -m venv`) and sync dependencies (`uv sync` or `pip install -e .`).
3. **Switch Directory**:
   ```bash
   cd <project_name>
   ```

---

### 3. Component Scaffolding (`pyartisan make`)

**The Golden Rule:** Never manually create files in `app/controllers`, `app/models`, or routes when working in a PyArtisan project. Manual file creation bypasses template stub logic and leaves out essential registration markers.

1. **Inspect Supported Generators**:
   Read `.pyartisan/manifest.yaml` in the project root. Examine `generators`:
   ```yaml
   generators:
     controller:
       stub: "stubs/controller.py.jinja"
       path: "controllers"
       registration:
         type: "import_list"
         target: "{{ path }}/__init__.py"
         line: "from .{{ name_lower }} import {{ name_title }}Controller"
   ```
2. **Run Generator**:
   ```bash
   pyartisan make <target> <Name>
   ```
   *Examples:*
   ```bash
   pyartisan make controller User
   pyartisan make model Order
   pyartisan make service Payment
   ```
3. **Overwrite Existing Files**:
   Pass `--force` if the file already exists and replacement is intended:
   ```bash
   pyartisan make controller User --force
   ```

---

### 4. Post-Scaffolding Code Quality & CI Standards (Ruff, Mypy, Bandit)

After scaffolding a component with `pyartisan make`, implement the business logic adhering strictly to the following standards so continuous integration (CI) jobs pass cleanly:

#### A. Static Type Annotations (Mypy)
- **Strict Typing**: All function/method parameters and return types must be fully annotated:
  ```python
  def find_by_id(user_id: int) -> User | None: ...
  def create(payload: dict[str, Any]) -> User: ...
  ```
- **Disallow Untyped Defs**: Never write unannotated functions (`def handler(req):`); CI enforces `disallow_untyped_defs = true` and `disallow_incomplete_defs = true`.
- **Avoid Bare `Any`**: Prefer specific types (`str`, `int`, `Path`, `dict[str, Any]`, `list[T]`) or modern union syntax (`str | None` instead of `Optional[str]`).

#### B. Linting & Formatting (Ruff)
- **Import Ordering (`isort`)**: Imports must be alphabetized and grouped in three sections separated by single blank lines:
  1. Python Standard Library (`os`, `sys`, `pathlib`)
  2. Third-party packages (`click`, `fastapi`, `pydantic`, `jinja2`)
  3. Local application imports (`app.models`, `app.controllers`)
- **No Unused or Wildcard Imports**: Never use `from module import *`. Remove any unused imports immediately (`F401`).
- **Formatting**: Maximum line length is 100 characters. Use double quotes (`"`) for strings and 4 spaces for indentation.
- **Exception Chaining**: Always preserve exception tracebacks using `raise NewError(...) from e` in error handling blocks (`B904`).

#### C. Security Hardening (Bandit & Semgrep)
- **Subprocess Safety**: Never invoke `subprocess` with `shell=True`. Always pass arguments as a list of strings (`["git", "clone", "--", url]`).
- **Safe Path Traversal**: Validate and constrain file paths using `Path.resolve()` or project safe-child utilities.
- **Audited Ignores**: Any `# nosec` or `# nosemgrep` must include an inline justification on the exact same line:
  ```python
  subprocess.run(argv, check=True)  # nosec: argv is an immutable list with fixed command
  ```

#### D. Encoding
- **UTF-8 Enforcement**: All file I/O operations (`open()`, `Path.read_text()`, `Path.write_text()`) must explicitly supply `encoding="utf-8"` to prevent Windows codepage drift.

#### E. Pre-flight CI Verification
Run the verification suite before committing or completing tasks:
```bash
uv run ruff check .          # Verify linting
uv run ruff check --fix .    # Auto-fix lint violations
uv run ruff format --check . # Verify formatting
uv run ruff format .         # Auto-format files
uv run mypy                  # Verify static type checks
uv run pytest                # Verify all tests pass
```

---

### 5. Development Server & Production Build

#### Dev Server (`pyartisan serve`)
Executes dev server through a 3-tier fallback strategy:
1. If `docker-compose.yml` exists and Docker daemon is running: runs `docker compose up`.
2. Otherwise, detects local virtual environment (`./venv`, `./.venv`, or `$VIRTUAL_ENV`) and executes the `manifest.scripts.serve` script (e.g. `uvicorn app.main:app --reload`).
3. If neither is available, provides clear troubleshooting steps.

```bash
pyartisan serve
```

#### Production Build (`pyartisan build`)
Executes the `manifest.scripts.build` defined in `.pyartisan/manifest.yaml` (e.g. wheel generation, container build, or static asset bundling):

```bash
pyartisan build
```

---

### 6. Diagnostics & Health (`pyartisan doctor`)

Always execute `pyartisan doctor` when encountering environment, dependency, or template issues:

```bash
pyartisan doctor
```

Verifies:
- Python 3.10+ runtime compatibility.
- Git installation and execution capability.
- Virtual environment detection and active state.
- Project manifest integrity (`.pyartisan/manifest.yaml`).

---

### 7. Plugin Management (`pyartisan plugin`)

Plugins extend PyArtisan projects with reusable hooks, dependencies, and code stubs.

#### Installing & Applying Plugins
1. **Download into Global Registry** (`~/.pyartisan/plugins/`):
   ```bash
   # Community GitHub repository
   pyartisan plugin install <github_user>/<repo_name>

   # Local directory link for local development
   pyartisan plugin install <plugin_id> --local /path/to/plugin
   ```
2. **Apply to Current Project**:
   ```bash
   pyartisan plugin apply <plugin_id> --yes
   ```
   *Note:* The `--yes` flag automatically confirms hook execution prompts without blocking terminal I/O.
3. **Inspect Plugin Status**:
   ```bash
   pyartisan plugin status
   pyartisan plugin doctor
   ```

#### Removing & Uninstalling Plugins
1. **Detach from Project**:
   ```bash
   pyartisan plugin remove <plugin_id> --yes
   ```
2. **Uninstall from Global Registry**:
   ```bash
   # Only succeeds if the plugin is no longer used by any local project
   pyartisan plugin uninstall <plugin_id>
   ```

#### Authoring a New Plugin
Scaffold a plugin skeleton with hook lifecycle functions (`before_install`, `after_install`, `before_remove`, `after_remove`):
```bash
pyartisan plugin init <plugin_id>
```

---

### 8. Global Configuration (`pyartisan config`)

Configuration file lives at `~/.pyartisan/config.toml`.

- Display settings:
  ```bash
  pyartisan config show
  ```
- Change default framework or add custom template repository:
  ```bash
  pyartisan config set default_framework fastapi
  pyartisan config set templates.django https://github.com/your-org/djangoiq.git
  ```
- Reset to factory defaults:
  ```bash
  pyartisan config reset
  ```

---

## Common Mistakes & Red Flags

| Mistake / Rationalization | Reality & Correct Action |
|---|---|
| "I'll create `controller.py` manually with the Write tool." | **Violates project convention.** Skips auto-import and marker registration in `__init__.py` or router tables. Always run `pyartisan make <target> <Name>`. |
| "I don't need type annotations for quick helper functions." | **Fails CI Mypy check.** Every function must have parameter and return type hints (`disallow_untyped_defs = true`). |
| "Imports can be placed anywhere in the file." | **Fails CI Ruff check.** Follow strict standard-library / third-party / local grouping with alphabetical order (`isort`). Never leave unused imports. |
| "Writing files without explicit encoding is fine on Windows." | Causes ANSI/Windows-1252 drift. Always pass `encoding="utf-8"` to all `open()`, `read_text()`, and `write_text()` calls. |
| "I don't need `pyartisan doctor` if dependencies fail." | `doctor` pinpoints whether issue is missing venv, bad python version, or broken manifest. Always run `pyartisan doctor` first on setup failures. |
| "I will run `python main.py` directly instead of `pyartisan serve`." | Bypasses Docker Compose fallback, environment variable loading, and manifest-configured runner arguments. Use `pyartisan serve`. |
| "I'll install dependencies using system pip." | Breaks environment isolation. PyArtisan is built around project venvs and `uv`. Always let PyArtisan create the venv or use project venv python. |
| "`pyartisan plugin apply` hangs on prompt." | Interactive prompt waiting for user confirmation on hook scripts. Always pass `--yes` in automated harness runs. |
