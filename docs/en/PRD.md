# Product Requirements Document (PRD)

## PyArtisan v1.0

**Refactoring FlaskArtisan into a Multi-Framework AI Development Toolkit**

> **Language:** [Indonesia](../id/PRD.md) | English
> **Last verified against the code:** commit `80b5acc` (2026-10-26)

This PRD is a **design** document. Not everything that is designed exists in the code yet, so every feature is given a status:

| Status | Meaning |
|---|---|
| **Done** | Exists in the code and has been checked |
| **Partial** | Exists, but differs from the design or is incomplete |
| **Not started** | Design only, no code yet |

---

# 1. Summary

## Background

Currently **FlaskArtisan** is a CLI focused on developing Flask applications.

As the project has grown, there is a need to:

* Support more than one Python framework.
* Turn the project into a platform, not just a Flask generator.
* Provide a foundation for AI Agents and MCP (Model Context Protocol).
* Reduce code duplication between frameworks.
* Have a more general and professional brand.

For these reasons, FlaskArtisan is being refactored into **PyArtisan**.

---

# 2. Goals

Build a modern CLI that can be used for various Python frameworks.

Initial target frameworks:

* Flask
* FastAPI

Future:

* Django
* Quart
* Litestar
* Sanic
* Starlette

---

# 3. Product Vision

> **PyArtisan is an AI-powered Python Web Development Toolkit that helps developers build, manage, and grow Python applications faster through a CLI, generators, AI, and MCP.**

Vision status: the CLI and generators are **Done**; AI and MCP are **Not started** (v2 roadmap).

---

# 4. Scope v1

## Included

| Item | Status | Notes |
|---|---|---|
| Branding refactor | Done | Package `pyartisan`, command `pyartisan` |
| Core CLI | Done | `cli/` (click parser) and `core/engine.py` (dispatch) |
| Flask Module | Partial | Through the external FlaskIQ template cloned by `pyartisan new`, not a module inside pyartisan |
| FastAPI Module (structure only) | Partial | Only the FastIQ template URL is registered in the config; there is no FastAPI code in pyartisan |
| Shared Core | Done | `core/`, `shared/` |
| Shared Utilities | Done | `utils/` (`console.py`, `fs.py`, `naming.py`) |
| Plugin Architecture | Partial | The plugin lifecycle (`install`, `apply`, `remove`, etc.) works; the per-framework `FrameworkPlugin` contract does not exist yet (see §11) |

## Excluded

* MCP
* AI Agent
* Deployment
* Kubernetes
* VSCode Extension

All of these will be on the v2 roadmap.

---

# 5. Architecture

## Before the refactor

```
FlaskArtisan

↓

Flask CLI
```

## Original design (target)

```
PyArtisan

↓

Core CLI

↓

Framework Module

↓

Flask
FastAPI
Django
```

## Current actual state

```
pyartisan (cli/ -> core/engine.py)

↓

.pyartisan/manifest.yaml owned by the project  (list of generators + stubs)

↓

Cloned project template: FlaskIQ / FastIQ
```

Frameworks are not implemented as modules inside pyartisan. Framework knowledge lives in the cloned template repos, and the engine only reads their manifest.

---

# 6. Project Structure

Actual structure of `src/pyartisan/`:

```
src/pyartisan/
│
├── cli/                  # thin click parser
│   └── commands/         # new, make, serve, build, config, doctor, version, plugin
│
├── core/
│   ├── engine.py         # dispatch_new / dispatch_make / dispatch_serve / dispatch_build
│   ├── manifest.py       # load_manifest (.pyartisan/manifest.yaml)
│   ├── registration.py   # apply_registration (import_list, marker)
│   ├── plugin_engine.py  # ProjectContext (Project API for plugin hooks)
│   └── exceptions.py
│
├── marketplace/          # global plugin registry (~/.pyartisan/plugins), usage tracking, hooks loader
├── project/              # Project API (placeholder, contains no code yet)
├── renderer/             # render_stub (Jinja2)
├── config/               # ~/.pyartisan/config.toml
├── shared/               # doctor
├── utils/                # console, fs, naming
└── templates/
    └── plugin_init/      # skeleton for `pyartisan plugin init`
```

Differences from the original design:

| Original design | Reality |
|---|---|
| `plugin/base.py`, `plugin/registry.py` | There is no `plugin/` folder |
| `plugin/flask/`, `plugin/fastapi/` | Do not exist; replaced by external templates |
| `core/context.py`, `core/detector.py` | Do not exist |

The goal of "no separate top-level package per framework" (`flasktool/`, `fastapitool/`) is **met**, but in a different way from the design.

> **Do not confuse the two:** the `plugin/` folder in the table above is a code module for built-in framework plugins (an old design, it does not exist). That is different from the **user-facing plugin system** (`pyartisan plugin ...`) and the **global registry** `~/.pyartisan/plugins/`, which do exist and are handled by `cli/commands/plugin.py` and `marketplace/core.py`.

---

# 7. Core Responsibilities

The core does not know the details of Flask or FastAPI. The core is responsible for:

| Responsibility | Status | Notes |
|---|---|---|
| CLI | Done | `cli/` |
| Plugin loading | Partial | `marketplace/core.py` loads a plugin's `hooks.py` through `importlib`; there is no per-framework loader |
| Config | Done | `config/__init__.py` |
| Template Engine | Done | `renderer.render_stub` (Jinja2) |
| Logging | Not started | There is no logging module |
| File Utilities | Done | `utils/fs.py` |
| Prompt | Partial | Uses `click.prompt` / `click.confirm` |
| Output | Partial | `utils/console.py` uses `click.echo`, not Rich |
| Shared Helpers | Done | `utils/naming.py` |

---

# 8. Framework Responsibilities

Each framework is responsible for its own implementation. In the actual state, this responsibility is held by the **template** (FlaskIQ, FastIQ) through `.pyartisan/manifest.yaml`.

Flask example:

| Function | Status |
|---|---|
| Create Project | Done (`pyartisan new flask <name>`) |
| Generate Model | Done (tested: `make model` creates the file and updates `__init__.py`) |
| Generate Service, Repository, Controller, Routes | Tested on FlaskIQ created by `pyartisan new`: `service`, `repository`, `routes` and `controller --type api` work. `controller --type view` fails on Windows with `TemplateNotFound` (issue [pyartisan#6](https://github.com/bijoaja/pyartisan/issues/6)); once that is fixed it creates a duplicate copy because the template keeps two identical stubs (issue [flaskiq#2](https://github.com/bijoaja/flaskiq/issues/2)) |
| Migration | Not started in pyartisan |
| Flask CLI Integration | Not started in pyartisan |

FastAPI has its own template. So do the other frameworks.

---

# 9. CLI Design

> The actual commands use `new` (not `init`) and `make <target> <name>` with a space (not `make:target`). The full reference is in [CLI.md](CLI.md).

## Project Creation

```
pyartisan new flask myapp

pyartisan new fastapi api
```

---

## Generate

```
pyartisan make model Post
pyartisan make controller Post --type api
```

See [Code Generators (`make`)](CLI.md#3-code-generators-make). The framework is **not** auto-detected from files (see §10); the framework is set once at `pyartisan new` and stored in `.pyartisan/project.yaml` and `.pyartisan/manifest.yaml`.

---

## Explicit Framework

The design selects the framework through `--framework` on `make`: **Not started**. `make` has no such flag; the target is determined by `.pyartisan/manifest.yaml` in the active project.

---

## Config

```
pyartisan config

pyartisan config show

pyartisan config set <key> <value>

pyartisan config reset
```

---

## Doctor

```
pyartisan doctor
```

Checks:

* Python (minimum 3.10)
* uv (optional; its absence does not make doctor fail)
* Pip (its absence does not make doctor fail if uv is available)
* Git
* Virtual Environment

---

## Version

```
pyartisan version
```

---

## Other commands that exist in the code but not in the original design

`pyartisan serve`, `pyartisan build`, and the `pyartisan plugin` group. See [CLI.md](CLI.md).

---

# 10. Framework Detection

> **Not started.** There is no `detector.py` or file-content-based detection in the current code. The framework is set explicitly once in `pyartisan new <framework> <name>` and read back from `.pyartisan/project.yaml` / `.pyartisan/manifest.yaml`. The section below is a design that has not been implemented.

When this command is run:

```
pyartisan make controller Post
```

The core performs detection.

Priority:

## Flask

```
app.py

create_app()

Flask(
```

---

## FastAPI

```
main.py

FastAPI(
```

---

## Django

```
manage.py

settings.py
```

---

If detection fails:

```
Project framework cannot be detected.

Please specify:

--framework flask
```

---

# 11. Plugin Loader

> **Not started** in its designed form. There is no `load_plugin(framework)`, `FlaskPlugin`, `FastAPIPlugin`, or `DjangoPlugin`.

Design:

```
framework = detect()

↓

load_plugin(framework)

↓

execute()
```

Actual state: the only thing loaded is the `hooks.py` of the applied plugin (`marketplace/core.py::_load_hooks`), through `importlib`. See [HOW_TO_CREATE_PLUGIN.md](HOW_TO_CREATE_PLUGIN.md).

---

# 12. Shared Components

All frameworks use:

## File Generator

Status: **Done** (`utils/fs.py`, `renderer.render_stub`).

* mkdir
* copy
* render template

---

## Jinja Template Engine

Status: **Done.** All templates use the same engine.

---

## Console Output

Status: **Partial.** The design mentions Rich; the code uses `click.echo` through `utils/console.py`.

---

## Prompt

Status: **Partial.** Uses `click.prompt` and `click.confirm`.

---

## Config Reader

Status: **Done.** Shared.

---

## Logging

Status: **Not started.**

---

# 13. Template Management

Design: templates are cloned from a GitHub repository; a framework only reads its own template.

Actual state (**Done**): `dispatch_new()` in `core/engine.py` clones the template through `git clone`. The template URL is stored in `~/.pyartisan/config.toml` (`templates.flask`, `templates.fastapi`) and changed with `pyartisan config set templates.<framework> <url>`.

Note: `~/.pyartisan/templates/<template>/<version>/template.yaml` is read by `ProjectContext`, but **no code populates it**. See [HOW_TO_CREATE_PLUGIN.md](HOW_TO_CREATE_PLUGIN.md).

---

# 14. Configuration

Location:

```
~/.pyartisan/config.toml
```

Example

```
theme = "default"

author = ""

license = "MIT"

default_framework = "flask"

[templates]
flask = "https://github.com/bijoaja/flaskiq.git"
fastapi = "https://github.com/bijoaja/fastiq.git"
```

Status: **Done.** Only `templates.*` is read by other commands (`new`). `theme`, `author`, `license`, and `default_framework` are stored but not yet read by any command.

---

# 15. Coding Standard

All frameworks must follow the template that has been cloned.

So that developers can easily switch between frameworks.

---

# 16. Migration Strategy

| Stage | Plan | Status |
|---|---|---|
| 1 | Rename the FlaskArtisan repository to PyArtisan | Done |
| 2 | Add the `pyartisan/` Core | Done |
| 3 | Move the CLI into the Core | Done |
| 4 | FlaskTool becomes the Flask plugin, with no behavior change | Partial: Flask became the FlaskIQ template + manifest, not a plugin inside pyartisan |
| 5 | Add the FastAPI structure, no implementation needed yet | Partial: only the FastIQ template URL in the config |

---

# 17. Non Functional Requirements

## Maintainability

Frameworks do not depend on each other. Status: **Partial.** `core/plugin_engine.py` (`ProjectContext`) still contains `fastapi` / `flask` branching and their respective fallback paths.

---

## Extensibility

A new framework only needs a new module. Status: **Partial.** A new framework is added through a template repo + a URL in the config, without changing `core/`. However, `ProjectContext` is not generic yet.

---

## Testability

Each framework can be tested independently. Status: **Partial.** There is a `tests/smoke_test.py` self-check (no test framework). There is no CI.

---

## Performance

CLI startup < 500 ms (target for lightweight commands). Status: **Not met on Windows.** `pyartisan version` was measured at about 1.0 seconds (989, 982, 1032 ms) on Windows 11 with a `uv tool` installation. Measurements on Linux/macOS have not been done.

---

## Compatibility

* Python 3.10+: declared in `pyproject.toml` (`requires-python`)
* Windows: in use and tested (the UTF-8 encoding fix and the plugin junction fix are merged)
* Linux, macOS: not verified manually; there is no CI

---

# 18. Roadmap

## v1

| Item | Status |
|---|---|
| Refactor into PyArtisan | Done |
| Core CLI | Done |
| Flask Module | Partial (FlaskIQ template) |
| FastAPI structure | Partial (FastIQ template URL) |
| Django structure | Not started. Django is only an option in `plugin init` |
| Shared Components | Partial (see §12) |
| uv support | Done (`uv tool install`, `uvx`, `new` uses uv when available) |

---

## v2

* AI Generator
* MCP Server
* AI Code Review
* AI Refactoring
* AI Project Analysis

---

## v3

* VS Code Extension
* JetBrains Plugin
* Interactive Wizard
* Marketplace Template

---

## v4

* Multi-language Support
* Remote Project Management
* Cloud Sync
* Team Collaboration

---

# 19. Success Criteria

The refactor is considered successful if:

| Criterion | Status |
|---|---|
| All FlaskArtisan features still work through the new CLI (`pyartisan`) | Cannot be verified from this repo (the old FlaskArtisan code is not here) |
| The Core CLI contains no code specific to Flask, FastAPI, or Django | Partial: `engine.py` is generic, but `plugin_engine.py` still has `fastapi` / `flask` branching |
| Adding a new framework can be done without changing the core architecture | Partial: possible through a template + config |
| The code structure supports developing AI and MCP features | Not started |
| Documentation and project structure are clear enough that contributors can add support for a new framework | Partial: see [CONTRIBUTING.md](CONTRIBUTING.md) |

---

# Appendix: Design Principles

1. **The core is framework-agnostic.**
2. **All framework-specific implementations live in separate modules.**
3. **Common code is centralized in `pyartisan/core` or `pyartisan/shared`.**
4. **The CLI is consistent across all frameworks.**
5. **The architecture is prepared from the start to support AI Agents and MCP without requiring a major refactor in the future.**
