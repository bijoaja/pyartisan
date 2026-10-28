# PyArtisan Plugin Tutorial

> **Language:** [Indonesia](../id/HOW_TO_CREATE_PLUGIN.md) | English
> **Audience:** plugin developers
> **Last verified against the code:** commit `80b5acc` (2026-10-26)

---

# Overview

A PyArtisan plugin is a folder containing `manifest.yaml`, `hooks.py`, and (optionally) stub files. A plugin is installed into the global registry at `~/.pyartisan/plugins/`, then applied (`apply`) to a project. When applied, PyArtisan:

1. runs the `before_install(project)` hook if present,
2. adds the pip dependencies from `manifest.yaml` to the project's `requirements.txt`,
3. runs the `after_install(project)` hook if present,
4. records the plugin in `.pyartisan/project.yaml`.

All plugin logic lives in `hooks.py`. The `project` object received by hooks is a `ProjectContext` (the Project API) described below.

## Recognized frameworks

`ProjectContext` reads the framework name from `.pyartisan/project.yaml` (`framework.name`). The code only distinguishes `fastapi` from everything else:

| Framework | Behavior of `create_service` / `register_router` |
|---|---|
| `fastapi` | Fallback service path `app/services/{module}.py`; registration uses `app.include_router(...)` |
| `flask` and others (including `django`) | Fallback service path `app/service/{module}.py`; registration uses `app.register_blueprint(...)` |

`django` is only an option during `pyartisan plugin init`; there is no Django-specific behavior in the code yet.

---

# Limitations to be aware of

* **Hooks are plain Python code.** `hooks.py` is loaded through `importlib` and runs with the user's full privileges. PyArtisan does not restrict a plugin's file access. Using the Project API (instead of calling `open()` or `shutil` directly) is a recommended practice, not an enforced rule.
* **Plugins cannot add CLI commands.** There is no mechanism for it. Plugins only run through the `apply` and `remove` hooks.
* **Install and apply are two steps.** `install` only places the plugin in the registry; hooks and dependencies only run on `apply`.

---

# Development Workflow

The workflow available now:

```text
pyartisan plugin init <name>   (scaffold + automatically linked to the registry, dev mode)
      │
      ▼
Edit hooks.py and stubs/
      │
      ▼
pyartisan plugin apply <name>  (di project sandbox)
      │
      ▼
Manual test (run the project, check the result)
      │
      ▼
git push ke GitHub (publikasi manual)
```

The `plugin validate`, `plugin test`, and `plugin publish` commands **do not exist yet**. See [Plans](#plans-not-yet-implemented).

---

# Scaffold a New Plugin (`pyartisan plugin init`)

```bash
pyartisan plugin init payment-midtrans
```

This command:

1. Refuses to run if the folder `./payment-midtrans/` already exists.
2. Asks for the target framework: `fastapi`, `flask`, `django`, or `all` (default `all`).
3. Creates `manifest.yaml`, `hooks.py`, `README.md`, and `LICENSE` from PyArtisan's built-in templates (no internet connection needed).
4. Creates an empty `stubs/<framework>/` folder (containing `.gitkeep`) for each selected framework.
5. Links the plugin into the registry as `~/.pyartisan/plugins/payment-midtrans/dev/` (equivalent to `pyartisan plugin install payment-midtrans --local ./payment-midtrans`).

---

# Plugin Structure

Result of `plugin init`:

```text
payment-midtrans/
├── manifest.yaml
├── hooks.py
├── README.md
├── LICENSE
└── stubs/
    ├── fastapi/
    ├── flask/
    └── django/
```

The contents of `stubs/` are your plugin's own Jinja2 template files, for example `service.py.jinja`. File names and sub-folders are up to you; only `hooks.py` decides which files are used.

---

# manifest.yaml

```yaml
id: payment-midtrans
name: Midtrans Payment Plugin
version: 1.0.0
description: Midtrans integration
author: Community
dependencies:
  pip:
    - midtrans-client
    - httpx
environment:
  - MIDTRANS_SERVER_KEY
```

| Field | Required | Used by |
|---|---|---|
| `id` | Yes | Plugin name in the registry and in `project.yaml` (`id@version`) |
| `name` | No | Messages during `apply`, `plugin info` |
| `version` | No | The `id@version` entry in `project.yaml`; if empty, the version folder name in the registry is used |
| `description`, `author` | No | `plugin info` |
| `dependencies.pip` | No | Added to `requirements.txt` during `apply` |
| `environment` | No | Only displayed by `plugin info`; no validation and nothing is written to `.env` |

---

# hooks.py

> **Security Note:** Plugin hooks execute arbitrary Python code with the user's system privileges. Commit only reviewed hooks. When users run `plugin apply`, `update`, or `remove`, PyArtisan prompts for explicit consent before running hooks unless `--yes` is passed. Local development links (`plugin install --local` or `plugin init`) are trusted without prompting.

Recognized hooks:

| Hook | Called |
|---|---|
| `before_install(project)` | During `apply`, before dependencies are added |
| `after_install(project)` | During `apply`, after dependencies are added |
| `before_remove(project)` | During `remove`, before the entry is removed from `project.yaml` |
| `after_remove(project)` | During `remove`, after `before_remove` |

All hooks are optional. The `plugin init` template only creates `after_install` and `before_remove`.

Example:

```python
from pathlib import Path


def after_install(project):
    stub = Path(__file__).parent / "stubs" / project.framework / "service.py.jinja"
    project.create_service(name="midtrans", stub_path=str(stub))
    project.register_router("midtrans")
```

> **Use an absolute path for `stub_path`**, such as `Path(__file__).parent / ...` above. See the note in the Create Service section.

---

# Project API

The `project` object is a `ProjectContext` (`src/pyartisan/core/plugin_engine.py`). Only the following members exist. Calling anything else raises `AttributeError`.

| Member | Description |
|---|---|
| `project.framework` | String from `.pyartisan/project.yaml` (`framework.name`) |
| `project.project_path` | `Path` to the project root |
| `project.project_config` | Dict of the contents of `.pyartisan/project.yaml` |
| `project.template_config` | Dict of the contents of `template.yaml`; almost always `{}` (see the note) |
| `project.create_service(name, stub_path)` | Render a Jinja2 stub into a service file |
| `project.register_router(name)` | Insert a router/blueprint registration line |
| `project.add_dependency(package_name)` | Add a package to `requirements.txt` |

## Create Service

```python
project.create_service(name="payment", stub_path="/absolute/path/to/service.py.jinja")
```

Renders the stub with the variables `name`, `name_lower`, `name_title`, `name_snake`, `name_plural`, then writes it to:

* `paths.services` from `template.yaml` if present, or
* the fallback `app/services/{module}.py` (fastapi) / `app/service/{module}.py` (others), with `{module}` = `name_lower`.

> **A relative `stub_path` is resolved from the current working directory (the project root), not from the plugin root.** If the stub file is not found, this method **raises `ManifestError`**. Always use an absolute path.

## Register Router

```python
project.register_router("payment")
```

Inserts the import and registration lines right after the marker, in the file specified by `template.yaml` (fallback: `app/main.py`, marker `# pyartisan:routers`). Rules:

* If the file does not exist, it is created containing the marker and those lines.
* If the marker is not in the file, the lines are appended at the end of the file.
* If the lines already exist, nothing changes (idempotent).

Lines inserted for FastAPI:

```python
from app.modules.payment.router import router as payment_router
app.include_router(payment_router, prefix="/payment")
```

And for anything other than FastAPI:

```python
from app.payment.routes import payment_bp
app.register_blueprint(payment_bp)
```

There is no separate `register_blueprint` method.

## Add Dependency

```python
project.add_dependency("midtrans-client")
```

Adds a line to the project's `requirements.txt` **only if that file exists**. The duplicate check uses a substring search: a name that already appears anywhere in the file (including as part of another package's name) is considered already present.

## Note: `template.yaml`

`ProjectContext` tries to read `~/.pyartisan/templates/<template>/<version>/template.yaml`, but **no command creates this file**. As a result `template_config` is empty and the hardcoded fallback is always used. Do not rely on `template.yaml` customization.

Another consequence: because no code writes `template.yaml`, `pyartisan plugin doctor` shows `✖ Template Metadata` on a project with a `project.yaml` like the one `pyartisan new` creates. Verified on projects created by `pyartisan new` from both the FlaskIQ and FastIQ templates: both show `✖ Template Metadata`.

## APIs that do not exist yet

The following **do not exist** in `ProjectContext`. Do not call them in `hooks.py`:

```python
project.create_model(...)
project.create_repository(...)
project.create_module(...)
project.add_env("MIDTRANS_KEY", "...")
project.update_config(...)
```

---

# Development Mode

`pyartisan plugin link` and `pyartisan plugin dev` do not exist. The dev-mode link is created by one of:

```bash
# New plugin, in the current working directory
pyartisan plugin init payment-midtrans

# Existing plugin at another path
pyartisan plugin install payment-midtrans --local ~/Projects/payment-midtrans
```

Result:

```text
~/.pyartisan/plugins/payment-midtrans/dev  ──►  ~/Projects/payment-midtrans
```

On Windows without the privilege to create symlinks, PyArtisan automatically uses a **junction** (`mklink /J`), so the effect is the same. Changes to the source are visible immediately without reinstalling.

If a plugin has a `dev` folder, that folder is what `apply` and `info` use, taking precedence over other versions.

---

# Project Sandbox

To test a plugin, create a separate project:

```bash
pyartisan new flask sandbox
cd sandbox
pyartisan plugin apply payment-midtrans
```

Then run the project the way its template provides (e.g. `pyartisan serve`). The final result depends on the FlaskIQ/FastIQ template used.

---

# Check Commands: `plugin status` and `plugin doctor`

Both check the **active project**, not the plugin structure. Run them in a folder that has `.pyartisan/project.yaml`.

`pyartisan plugin status` shows the project name, framework, and each plugin with a ✔ or ✖ mark (missing from the registry).

`pyartisan plugin doctor` checks:

* **Manifest**: `project.yaml` has `framework.name`.
* **Framework**: `ProjectContext` was created successfully.
* **Template Metadata**: `template.yaml` exists in the global registry. See the note above: as long as nothing populates it, this check fails.
* **Dependencies**: each of the plugin's pip dependencies is in `requirements.txt`.
* **Marker**: the router marker is still in the target file. Only checked if `template.yaml` defines it.

The output ends with `Plugin is valid` or `Plugin has issues, see above.`

---

# Installing Plugins

## From a local path

```bash
pyartisan plugin install payment-midtrans --local ~/Projects/payment-midtrans
```

Creates a dev link to `~/.pyartisan/plugins/payment-midtrans/dev/`, not a copy.

## From GitHub

The argument format is `github-username/repo-name`, not a full URL:

```bash
pyartisan plugin install username/payment-midtrans
```

PyArtisan runs `git clone https://github.com/username/payment-midtrans.git` into `~/.pyartisan/plugins/payment-midtrans/1.0.0/`, then makes sure `manifest.yaml` exists. The version folder is always `1.0.0`, not taken from `manifest.yaml`. Dependencies and hooks only run on `apply`.

## From the Marketplace

```bash
pyartisan plugin install payment-midtrans --license valid-xxxxxx
```

This feature is **still a mock**. `_verify_blockchain_license` in `marketplace/core.py` accepts any key that starts with `valid-`, without calling a Blockchain API. No plugin is downloaded: PyArtisan only writes a local empty `manifest.yaml` (`id`, `name`, `version 1.0.0`, dependency `stripe`) to the registry.

---

# Publishing Plugins

`pyartisan plugin publish` **does not exist yet**, and there is no automatic submission to the Marketplace. Publishing currently means a manual push to GitHub:

```bash
git push origin main
```

Other users install it with `pyartisan plugin install <github-user>/<repo-name>`.

---

# Recommended Practices

* Use the Project API for the file operations it supports; do not write absolute paths into the user's project.
* Use an absolute path (`Path(__file__).parent`) for `stub_path`.
* Separate stubs per framework in `stubs/<framework>/`.
* Make hooks idempotent; `apply` can run more than once (`update` calls `apply` again).
* Include usage and configuration documentation in the plugin's `README.md`.
* Use Semantic Versioning (`MAJOR.MINOR.PATCH`) in `manifest.yaml`.

---

# Plans (not yet implemented)

The following **do not exist** in the current code:

* `pyartisan plugin validate`: validation of `manifest.yaml`, `hooks.py`, stubs, and version.
* `pyartisan plugin test` and `plugin test --all`: automated tests on a temporary project for all frameworks.
* `pyartisan plugin publish`: packaging and submission to the Marketplace.
* Automatic Marketplace validation (manifest, version, README, LICENSE, hooks, stubs, PyArtisan version compatibility).
* Plugin structure checks (stub coverage per framework) in `plugin doctor`.
* Additional Project API methods: `create_model`, `create_repository`, `create_module`, `add_env`, `update_config`.
* Idea: a `pyartisan.sdk` package with hook decorators, so developers do not depend on specific function names:

  ```python
  from pyartisan.sdk import hook

  @hook.after_install
  def install(project):
      ...
  ```

See also [PRD.md](PRD.md) and the Project API design at `docs/superpowers/specs/2026-07-22-project-api-consolidation-design.md`.
