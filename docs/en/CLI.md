# PyArtisan CLI — Usage Documentation

> **Language:** [Indonesia](../id/CLI.md) | English
> **Last verified against the code:** commit `80b5acc` (2026-10-26)

This document covers all `pyartisan` commands: project creation, code generators, configuration management, and the plugin system (community & marketplace).

---

## 1. Installation

With [uv](https://docs.astral.sh/uv/) (isolated, no manual venv, system Python untouched):

```bash
uv tool install git+https://github.com/bijoaja/pyartisan
```

From source:

```bash
git clone https://github.com/bijoaja/pyartisan.git
cd pyartisan
uv tool install .              # or: uv tool install --editable .
# alternative without uv: pip install -e .
```

`--editable` is a built-in flag of `uv tool install` (not a pyartisan flag): the code in `src/` is used directly without reinstalling, which suits contributors.

Without installing: `uvx --from git+https://github.com/bijoaja/pyartisan pyartisan --help`.

If `pyartisan` is not found after installing, run `uv tool update-shell` and then open a new terminal.

Verify the installation:

```bash
pyartisan --help
pyartisan version
```

---

## 2. Creating a New Project

```bash
pyartisan new <framework> <name>
```

Examples:

```bash
pyartisan new fastapi ecommerce
pyartisan new flask blog
```

What happens:
1. Checks that the `<name>` folder does not exist yet (if it does, the command stops).
2. `git clone` of the official template (`FastIQ` for FastAPI, `FlaskIQ` for Flask) into the `<name>` folder, then removes the `origin` remote. **Git must be installed.**
3. Writes `.pyartisan/project.yaml` (project name, framework, template name and version, empty plugin list).
4. Asks whether to create the virtual environment and dependencies now (default: yes). If yes, creates `./venv` and installs `requirements.txt`:
   * If `uv` is on PATH: `uv venv venv` then `uv pip install --python <venv> -r requirements.txt`.
   * Otherwise: `python -m venv venv` then `pip install -r requirements.txt`.

A framework not registered in the config produces the error `No template registered for framework ...` along with the list of available ones.

The template URL can be changed with `pyartisan config set templates.<framework> <url>` (see [Configuration](#5-configuration)).

---

## 3. Code Generators (`make`)

```bash
pyartisan make <target> <name> [--force] [--<option> <value> ...]
```

This command reads `.pyartisan/manifest.yaml` inside the project to determine which generators are available (`model`, `controller`, `service`, `repository`, etc. — depending on the template).

Examples:

```bash
pyartisan make model Post
pyartisan make controller Post --type api
pyartisan make service Payment --version 2
```

Options:
- `--force` — overwrite existing files.
- `--<option name> <value>` — any dynamic argument used by the template stub, passed to the Jinja2 rendering context. Hyphens are converted to underscores (`--my-opt` becomes `my_opt`). A trailing option without a value becomes `True`. Defaults: `type` = `view`, `version` = `1`.

If the target is unknown or the project has no `.pyartisan/manifest.yaml`, the command fails with an error message and exit code 1. The message for an unknown target includes the list of available generators.

---

## 4. Running & Building the Project

```bash
pyartisan serve
```
Runs the dev server. No options; the strategy is chosen automatically, in order:

1. **Docker**: if `docker-compose.yml` exists and Docker is running, runs `docker compose up` (or `docker-compose up`).
2. **Project venv**: if `./venv` or `./.venv` exists (or a `VIRTUAL_ENV` that points to a different venv, not the env pyartisan itself runs in) and the manifest has `scripts.serve`, runs that script with that venv. The venv's `Scripts`/`bin` folder is prepended to `PATH`, `VIRTUAL_ENV` is set, and `python` / `python3` at the start of the script is replaced with the venv interpreter (on Windows there is no `python3` inside the venv).
3. **Error**: if neither exists, prints a hint and exits with code 1.

The venv searched for is the **project** venv, so `serve` stays correct when pyartisan is installed via `uv tool` (the tool env is never chosen).

```bash
pyartisan build
```
Runs `scripts.build` from `.pyartisan/manifest.yaml`. If it is not defined, the command fails with exit code 1.

---

## 5. Configuration

```bash
pyartisan config show
pyartisan config set <key> <value>
pyartisan config reset
```

Keys available by default: `theme`, `author`, `license`, `default_framework`, `templates.flask`, `templates.fastapi`. `config set` rejects unknown keys, except those prefixed with `templates.` (new frameworks may be added there). Running `pyartisan config` without a subcommand is the same as `config show`.

Currently only `templates.*` is read by other commands (by `new`). The keys `theme`, `author`, `license`, and `default_framework` are stored but not yet used.

Example of changing a template URL:

```bash
pyartisan config set templates.fastapi https://github.com/org/my-fastiq-fork.git
```

The configuration is stored in `~/.pyartisan/config.toml`.

---

## 6. Doctor & Version

```bash
pyartisan doctor    # Check Python, uv, pip, Git, virtualenv
pyartisan version   # Print the pyartisan version
```

Notes on `doctor`: Python minimum 3.10. `uv` is optional (a missing uv does not fail doctor). A missing `pip` is not counted as a failure if `uv` is available, because the `uv tool` env has no pip by design.

---

## 7. Plugin System

PyArtisan treats plugins like a **package manager** (similar to `npm`/`pip`), not just copy-pasting files. There are two storage levels:

- **Global Registry** (`~/.pyartisan/plugins/<plugin-id>/<version>/`) — plugins that have been downloaded, not necessarily used by any project.
- **Project Metadata** (`.pyartisan/project.yaml`) — the list of plugins actually **applied** to the active project, under the `plugins: [...]` key.

Plugin lifecycle:

```text
init     → scaffold a new plugin skeleton + auto-register to the registry (dev mode)
install  → download to the registry (global, does not change any project)
apply    → apply a registry plugin to the active project (run hooks, write project.yaml)
update   → pull git updates for the plugin in the registry, re-apply automatically if this project uses it
remove   → detach the plugin from the project (registry copy stays, other projects can still use it)
uninstall→ delete the plugin from the registry (refused if still used by another project)
```

### 7.1 Install — Download to Registry

```bash
pyartisan plugin install <name>
```

Three supported sources:

**a. Community (GitHub)**
```bash
pyartisan plugin install github-username/repo-name
```
Clones `https://github.com/<name>.git` into `~/.pyartisan/plugins/<repo-name>/1.0.0/`.

**b. Local (plugin development mode)**
```bash
pyartisan plugin install myplugin --local /path/to/my-plugin
```
Creates a symlink at `~/.pyartisan/plugins/myplugin/dev/` — changes to the local source are visible immediately without reinstalling. On Windows without the privilege to create symlinks, a junction (`mklink /J`) is used automatically. Suited for developing a plugin before publishing it to GitHub/marketplace.

**c. Premium Marketplace (paid, Blockchain verification)**
```bash
pyartisan plugin install payment-midtrans --license valid-xxxxxx
```
> **Offline stub.** License verification is an offline stub (prints `Note: license verification is an offline stub, no network check is performed.`), accepts any key prefixed with `valid-` without calling any network or blockchain API, and writes a mock `manifest.yaml` to the registry.

> `install` does **not** change any project — the new plugin is simply made available in the local registry.

### 7.2 Apply — Apply to the Active Project

```bash
pyartisan plugin apply <name> [--yes]
```

Run inside the project folder (`.pyartisan/project.yaml` must exist). The process:
1. Prompts for consent before executing hooks if `hooks.py` is present (skipped with `--yes`, or for `dev` links created via `install --local`). Non-interactive sessions without `--yes` abort with exit 1.
2. Runs the plugin's `before_install(project_context)` hook from `hooks.py` (if present).
3. Adds the plugin's pip dependencies (`manifest.yaml` → `dependencies.pip`) to the project's `requirements.txt`, only if that file exists.
4. Runs the `after_install(project_context)` hook — this is where the plugin calls the Project API (`create_service`, `register_router`, etc.).
5. Records an `<plugin-id>@<version>` entry in the `project.yaml` `plugins` key.
6. Records usage tracking of this plugin+version by the current project path in the global registry — the basis for `uninstall` validation.

### 7.3 Update — Update a Plugin in the Registry

```bash
pyartisan plugin update <name> [--yes]
```

`git pull` for all git-based versions of that plugin in the registry (the `dev` symlink is skipped, because it is already live from the local source). If the plugin is used by the active project, it is automatically re-`apply`-ed after the update, forwarding `--yes` if provided.

### 7.4 Remove — Detach from the Project

```bash
pyartisan plugin remove <name> [--yes]            # one plugin
pyartisan plugin remove <name1> <name2> [--yes]   # several plugins at once
pyartisan plugin remove --all [--yes]             # all plugins in this project
```

Prompts for consent before executing hooks (unless `--yes` is given). Runs the `before_remove` / `after_remove` hooks (if the plugin provides them), deletes the entry from `project.yaml`, and cancels the usage tracking record. The plugin copy in the global registry is **not deleted** — other projects that still use it are unaffected.

### 7.5 Uninstall — Remove from the Registry

```bash
pyartisan plugin uninstall <name>            # one plugin
pyartisan plugin uninstall <name1> <name2>   # several plugins at once
pyartisan plugin uninstall --all             # all plugins in the registry
```

Deleted permanently from `~/.pyartisan/plugins/`. If the plugin is still recorded as used by another project (usage tracking), the command is **refused** and shows the list of projects still using it:

```text
❌ Cannot uninstall 'payment-midtrans'. Still used by:
   - /home/user/projects/ecommerce
   - /home/user/projects/inventory
```

Run `plugin remove` in those projects first before `uninstall` can succeed.

### 7.6 List — View Installed Plugins

```bash
pyartisan plugin list             # active plugins in this project (from project.yaml)
pyartisan plugin list --global     # all plugins ever downloaded to the registry
pyartisan plugin list --updates    # check git-based plugins in the registry that have updates
```

### 7.7 Info — Plugin Details

```bash
pyartisan plugin info <name>
```

Shows full metadata from the registry: name, ID, version, description, author, dependencies, required environment variables, and the list of projects that use it (`Used by`).

### 7.8 Status — Project Health

```bash
pyartisan plugin status
```

Shows the project name, framework, the list of plugins marked ✔ (available in the registry) or ✖ (missing from the registry), and a conclusion of `Health: OK` / `Health: ISSUES FOUND`.

### 7.9 Doctor — Detailed Diagnosis

```bash
pyartisan plugin doctor
```

A deeper check than `status`:
- **Manifest** — `project.yaml` has `framework.name`.
- **Framework** — `ProjectContext` is created successfully (framework detection is valid).
- **Template Metadata** — the project template's `template.yaml` is found in `~/.pyartisan/templates/<template>/<version>/`. No command populates this folder yet, so this check fails while the folder is empty (see [HOW_TO_CREATE_PLUGIN.md](HOW_TO_CREATE_PLUGIN.md)).
- **Dependencies** — each active plugin is checked: the pip dependencies in `manifest.yaml` are already in the project's `requirements.txt`.
- **Marker** — the router registration marker (e.g. `# pyartisan:routers`) is still present in the target file. Only checked if `template.yaml` defines it.

Ends with `Plugin is valid` or `Plugin has issues, see above.`

### 7.10 Init — Scaffold a New Plugin

```bash
pyartisan plugin init <name>
```

Creates a new plugin skeleton in `./<name>/` — no need to create the folder
structure manually anymore. The process:

1. Refuses if the `./<name>/` directory already exists (overwrites nothing).
2. Interactively asks for the target framework: `fastapi` / `flask` /
   `django` / `all` (default `all`).
3. Renders the skeleton from `pyartisan`'s own built-in template (no internet
   connection needed): `manifest.yaml`, `hooks.py` (empty `after_install`
   and `before_remove` functions containing Project API guidance comments),
   `README.md`, `LICENSE`.
4. Creates an empty `stubs/<framework>/` folder for each framework
   chosen in step 2.
5. Immediately registers the plugin to the local registry as a dev-mode symlink (or junction on Windows without symlink privilege)
   (`~/.pyartisan/plugins/<name>/dev/`) — equivalent in effect to
   `pyartisan plugin install <name> --local ./<name>`, so it does not need
   to be run separately.

After `init`, you can immediately run `pyartisan plugin apply <name>` inside any
sandbox project to start testing the hooks under development.

---

## 8. Creating Your Own Plugin

See the [Plugin Tutorial](HOW_TO_CREATE_PLUGIN.md) for the plugin structure (`manifest.yaml`, `hooks.py`, `stubs/`), the Project API (`project.framework`, `create_service`, `register_router`, `add_dependency`), and how to publish via GitHub. The product design is in [PRD.md](PRD.md); how to contribute is in [CONTRIBUTING.md](CONTRIBUTING.md).

---

## 9. Command Summary

| Command | Purpose |
|---|---|
| `pyartisan new <framework> <name>` | Create a new project from a template |
| `pyartisan make <target> <name>` | Generate code from the project manifest stubs |
| `pyartisan serve` | Run the dev server |
| `pyartisan build` | Build the production artifact |
| `pyartisan config show\|set\|reset` | Manage global configuration |
| `pyartisan doctor` | Check environment health |
| `pyartisan version` | Show the CLI version |
| `pyartisan plugin init <name>` | Scaffold a new plugin skeleton + auto-register to the registry |
| `pyartisan plugin install <name>` | Download a plugin to the global registry |
| `pyartisan plugin apply <name>` | Apply a plugin to the active project |
| `pyartisan plugin update <name>` | Update a plugin in the registry (+ re-apply) |
| `pyartisan plugin remove <name...\|--all>` | Detach a plugin from the project |
| `pyartisan plugin uninstall <name...\|--all>` | Delete a plugin from the registry |
| `pyartisan plugin list [--global\|--updates]` | View project/registry plugins/available updates |
| `pyartisan plugin info <name>` | Plugin metadata details |
| `pyartisan plugin status` | Project plugin health |
| `pyartisan plugin doctor` | Detailed diagnosis of project plugins |
