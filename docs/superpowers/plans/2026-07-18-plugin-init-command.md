# `pyartisan plugin init` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `pyartisan plugin init <name>` — a command that scaffolds an empty, ready-to-develop plugin skeleton and auto-registers it into the local dev registry, so community developers never hand-write plugin boilerplate from scratch.

**Architecture:** New subcommand on the existing `plugin_group` Click group in `src/pyartisan/marketplace/__init__.py`. Skeleton content is bundled as Jinja template package-data (`src/pyartisan/templates/plugin_init/`) and rendered with the already-existing `renderer.render_stub()` — the same mechanism `pyartisan make` uses. After rendering, the command creates empty `stubs/<framework>/` folders for whichever frameworks the user picks at an interactive prompt, then symlinks the new folder into `~/.pyartisan/plugins/<name>/dev/` using the same dev-symlink logic `plugin install --local` already uses.

**Tech Stack:** Python 3.10+, Click (CLI + prompts), Jinja2 (via existing `renderer.render_stub`), PyYAML (manifest parsing in tests).

## Global Constraints

- New command lives in the existing `plugin_group` (`src/pyartisan/marketplace/__init__.py`) — no new `setup` command group.
- Plugin skeleton renders into `./<name>/` in the current working directory; if that directory already exists, the command errors out and makes no filesystem changes.
- Skeleton is intentionally minimal/empty (no working CRUD example) — guidance comments only, matching the "skeleton kosong siap isi" decision from the design spec.
- `id` in the generated `manifest.yaml` and the registry symlink folder name must both equal the literal `<name>` argument exactly as typed (hyphenated, e.g. `crud-blogs`) — never the underscored `name_lower` form. This must match what `apply_cmd`/`install_cmd` look up (`src/pyartisan/marketplace/__init__.py:146`, `:220`).
- Template source files are bundled as package data inside `pyartisan` itself (`src/pyartisan/templates/plugin_init/`) — no network/GitHub access required to run `init`.
- Framework selection is a single-choice interactive prompt (`fastapi`/`flask`/`django`/`all`), default `all`.
- Command auto-registers the new plugin into the local dev registry (`~/.pyartisan/plugins/<name>/dev` symlink) — no separate `plugin install --local` step needed afterward.
- Reuse existing utilities only: `renderer.render_stub()` (`src/pyartisan/renderer/__init__.py:7`), `utils.naming.name_parts()` (`src/pyartisan/utils/naming.py:1`), `_plugins_registry()` (`src/pyartisan/marketplace/__init__.py:16`). Do not introduce new rendering/naming logic or extract new shared helpers.

---

### Task 1: Implement `pyartisan plugin init` command with tests

**Files:**
- Create: `src/pyartisan/templates/plugin_init/manifest.yaml.jinja`
- Create: `src/pyartisan/templates/plugin_init/hooks.py.jinja`
- Create: `src/pyartisan/templates/plugin_init/README.md.jinja`
- Create: `src/pyartisan/templates/plugin_init/LICENSE`
- Modify: `pyproject.toml`
- Modify: `src/pyartisan/marketplace/__init__.py`
- Test: `tests/smoke_test.py`

**Interfaces:**
- Consumes: `render_stub(stub_dir: Path, dest_dir: Path, context: dict, force: bool = False) -> list[Path]` from `pyartisan.renderer` (`src/pyartisan/renderer/__init__.py:7`); `name_parts(name: str) -> tuple[str, str, str, str]` from `pyartisan.utils.naming` (`src/pyartisan/utils/naming.py:1`); `_plugins_registry() -> Path` already defined in `src/pyartisan/marketplace/__init__.py:16`.
- Produces: new Click command `init_cmd` registered as `pyartisan plugin init <name>` on `plugin_group`. No other task depends on this — it's the full feature.

- [ ] **Step 1: Create the plugin skeleton template files**

Create `src/pyartisan/templates/plugin_init/manifest.yaml.jinja`:

```yaml
id: {{name}}
name: {{name_title}} Plugin
version: 1.0.0
description: ""
author: ""
dependencies:
  pip: []
```

Create `src/pyartisan/templates/plugin_init/hooks.py.jinja`:

```python
def after_install(project):
    """Called after plugin dependencies are installed into the target project.

    Use the Project API to scaffold files without hardcoding paths:
      project.framework        -> "fastapi" | "flask" | "django"
      project.project_path     -> Path to the target project root
      project.create_service(name, stub_path)
      project.register_router(name)
      project.add_dependency(package_name)

    Example:
        if project.framework == "fastapi":
            project.create_service(
                name="{{name}}",
                stub_path=str(Path(__file__).parent / "stubs" / "fastapi" / "service.py.jinja"),
            )
    """
    pass


def before_remove(project):
    """Called before the plugin is removed from a project. Optional — delete if unused."""
    pass
```

Create `src/pyartisan/templates/plugin_init/README.md.jinja`:

`````markdown
# {{name_title}} Plugin

<!-- Describe what this plugin does here. -->

## Installation

```bash
pyartisan plugin install {{name}} --local /path/to/{{name}}
pyartisan plugin apply {{name}}
```

## Configuration

<!-- List any environment variables this plugin requires, if any. -->

None yet.
`````

Create `src/pyartisan/templates/plugin_init/LICENSE`:

```
MIT License

Copyright (c) <year> <author>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 2: Register template files as package data in `pyproject.toml`**

Open `pyproject.toml`. It currently ends with:

```toml
[tool.setuptools.packages.find]
where = ["src"]
```

Append a new section after it:

```toml
[tool.setuptools.package-data]
pyartisan = ["templates/plugin_init/**/*"]
```

Full resulting file:

```toml
[project]
name = "pyartisan"
version = "1.0.0"
description = "AI-powered Python Web Development Toolkit — Artisan-like CLI for Flask, FastAPI, and beyond"
requires-python = ">=3.10"
dependencies = [
    "click",
    "flask",
    "sqlalchemy",
    "tomli; python_version < '3.11'",
    "jinja2",
    "pyyaml",
]

[project.scripts]
pyartisan = "pyartisan.cli:cli"

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
pyartisan = ["templates/plugin_init/**/*"]
```

- [ ] **Step 3: Write the failing tests**

Open `tests/smoke_test.py`. Add three new test functions right after `test_cli_plugin_list_updates` (before `def main():`):

```python
def _patch_home(root: Path):
    """Helper: point os.path.expanduser('~') at an isolated home dir under root."""
    home_dir = root / "home"
    home_dir.mkdir()
    orig_expanduser = os.path.expanduser
    os.path.expanduser = lambda path: str(home_dir) if path == "~" else orig_expanduser(path)
    return home_dir, orig_expanduser


def test_cli_plugin_init_all_frameworks():
    """`pyartisan plugin init <name>` scaffolds skeleton + registers dev symlink."""
    import os
    runner = CliRunner()
    with runner.isolated_filesystem() as tmp_dir:
        root = Path(tmp_dir)
        home_dir, orig_expanduser = _patch_home(root)
        orig_cwd = os.getcwd()

        try:
            os.chdir(root)

            result = runner.invoke(cli, ["plugin", "init", "crud-blogs"], input="all\n")
            assert result.exit_code == 0, result.output
            assert "plugin skeleton created" in result.output.lower()

            plugin_dir = root / "crud-blogs"
            assert (plugin_dir / "manifest.yaml").exists()
            assert (plugin_dir / "hooks.py").exists()
            assert (plugin_dir / "README.md").exists()
            assert (plugin_dir / "LICENSE").exists()
            assert (plugin_dir / "stubs" / "fastapi" / ".gitkeep").exists()
            assert (plugin_dir / "stubs" / "flask" / ".gitkeep").exists()
            assert (plugin_dir / "stubs" / "django" / ".gitkeep").exists()

            manifest = yaml.safe_load((plugin_dir / "manifest.yaml").read_text())
            assert manifest["id"] == "crud-blogs"
            assert manifest["name"] == "CrudBlogs Plugin"
            assert manifest["version"] == "1.0.0"

            registry_link = home_dir / ".pyartisan" / "plugins" / "crud-blogs" / "dev"
            assert registry_link.is_symlink()
            assert registry_link.resolve() == plugin_dir.resolve()
        finally:
            os.path.expanduser = orig_expanduser
            os.chdir(orig_cwd)

    print("OK  cli_plugin_init_all_frameworks")


def test_cli_plugin_init_single_framework():
    """Only the chosen framework's stub folder is created."""
    import os
    runner = CliRunner()
    with runner.isolated_filesystem() as tmp_dir:
        root = Path(tmp_dir)
        _home_dir, orig_expanduser = _patch_home(root)
        orig_cwd = os.getcwd()

        try:
            os.chdir(root)

            result = runner.invoke(cli, ["plugin", "init", "demo-plugin"], input="fastapi\n")
            assert result.exit_code == 0, result.output

            plugin_dir = root / "demo-plugin"
            assert (plugin_dir / "stubs" / "fastapi" / ".gitkeep").exists()
            assert not (plugin_dir / "stubs" / "flask").exists()
            assert not (plugin_dir / "stubs" / "django").exists()
        finally:
            os.path.expanduser = orig_expanduser
            os.chdir(orig_cwd)

    print("OK  cli_plugin_init_single_framework")


def test_cli_plugin_init_existing_directory():
    """Command refuses to overwrite an existing directory."""
    import os
    runner = CliRunner()
    with runner.isolated_filesystem() as tmp_dir:
        root = Path(tmp_dir)
        _home_dir, orig_expanduser = _patch_home(root)
        orig_cwd = os.getcwd()

        try:
            os.chdir(root)
            (root / "demo-plugin").mkdir()
            (root / "demo-plugin" / "keep-me.txt").write_text("do not touch")

            result = runner.invoke(cli, ["plugin", "init", "demo-plugin"], input="all\n")
            assert result.exit_code == 0, result.output
            assert "already exists" in result.output.lower()

            assert not (root / "demo-plugin" / "manifest.yaml").exists()
            assert (root / "demo-plugin" / "keep-me.txt").exists()
        finally:
            os.path.expanduser = orig_expanduser
            os.chdir(orig_cwd)

    print("OK  cli_plugin_init_existing_directory")
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `PYTHONPATH=src python3 tests/smoke_test.py`

Expected: `FAIL` — the run raises `AssertionError` (or Click reports "No such command 'init'") because `init_cmd` does not exist yet. Since `main()` doesn't call the new tests yet, run them directly instead:

Run: `PYTHONPATH=src python3 -c "
import sys; sys.path.insert(0, 'tests')
from smoke_test import test_cli_plugin_init_all_frameworks
test_cli_plugin_init_all_frameworks()
"`

Expected: Click reports the `init` subcommand is unknown (non-zero exit code inside the assert on `result.exit_code == 0`), causing an `AssertionError`.

- [ ] **Step 5: Implement `init_cmd`**

Open `src/pyartisan/marketplace/__init__.py`. Update the import block at the top of the file (currently):

```python
import os
import shutil
import subprocess
import json
from pathlib import Path
import click
import yaml

from pyartisan.core.plugin_engine import ProjectContext, load_plugin_yaml
```

to:

```python
import os
import shutil
import subprocess
import json
from pathlib import Path
import click
import yaml

from pyartisan.core.plugin_engine import ProjectContext, load_plugin_yaml
from pyartisan.renderer import render_stub
from pyartisan.utils.naming import name_parts
```

Then add `init_cmd` immediately after the `plugin_group` definition and before `install_cmd` (i.e. right after this existing block):

```python
@click.group(name="plugin")
def plugin_group():
    """Manage PyArtisan plugins (community & marketplace)"""
    pass
```

Insert:

```python
@plugin_group.command(name="init")
@click.argument("name")
def init_cmd(name: str):
    """Scaffold a new plugin skeleton, ready for development."""
    dest = Path.cwd() / name
    if dest.exists():
        click.echo(f"❌ Directory already exists: {dest}")
        return

    framework_choice = click.prompt(
        "Target framework?",
        type=click.Choice(["fastapi", "flask", "django", "all"]),
        default="all",
    )
    frameworks = (
        ["fastapi", "flask", "django"] if framework_choice == "all" else [framework_choice]
    )

    _, name_title, _, _ = name_parts(name)
    context = {"name": name, "name_title": name_title}

    template_dir = Path(__file__).parent.parent / "templates" / "plugin_init"
    render_stub(template_dir, dest, context)

    for fw in frameworks:
        fw_dir = dest / "stubs" / fw
        fw_dir.mkdir(parents=True, exist_ok=True)
        (fw_dir / ".gitkeep").touch()

    # Auto-register into the local registry (dev symlink) — same mechanism
    # `plugin install --local` uses. Registry key = `name` literal (e.g.
    # "crud-blogs"), matching manifest.yaml's `id` and what apply_cmd/
    # install_cmd look up.
    plugins_registry = _plugins_registry()
    plugin_dir = plugins_registry / name / "dev"
    plugin_dir.parent.mkdir(parents=True, exist_ok=True)
    if plugin_dir.exists() or plugin_dir.is_symlink():
        if plugin_dir.is_symlink():
            os.unlink(plugin_dir)
        else:
            shutil.rmtree(plugin_dir)
    os.symlink(dest.resolve(), plugin_dir, target_is_directory=True)

    click.echo(f"✔ Plugin skeleton created at {dest}")
    click.echo(f"✔ Linked to registry -> ~/.pyartisan/plugins/{name}/dev")
    click.echo(
        f"👉 Edit hooks.py and stubs/, then test with "
        f"`pyartisan plugin apply {name}` inside a sandbox project."
    )
```

- [ ] **Step 6: Register the new tests in `main()`**

In `tests/smoke_test.py`, update the `main()` function from:

```python
def main():
    test_name_parts()
    test_manifest_load()
    test_render_stub()
    test_registration_import_list()
    test_registration_marker()
    test_config_roundtrip()
    test_cli_generic_make()
    test_cli_make_not_supported()
    test_cli_make_no_manifest()
    test_metadata_parsers()
    test_project_context_ops()
    test_cli_plugin_lifecycle()
    test_cli_plugin_install_blockchain_license()
    test_cli_plugin_remove_multi_and_all()
    test_cli_plugin_info_status_doctor()
    test_cli_plugin_list_updates()
    print("\nALL SMOKE TESTS PASSED")
```

to:

```python
def main():
    test_name_parts()
    test_manifest_load()
    test_render_stub()
    test_registration_import_list()
    test_registration_marker()
    test_config_roundtrip()
    test_cli_generic_make()
    test_cli_make_not_supported()
    test_cli_make_no_manifest()
    test_metadata_parsers()
    test_project_context_ops()
    test_cli_plugin_lifecycle()
    test_cli_plugin_install_blockchain_license()
    test_cli_plugin_remove_multi_and_all()
    test_cli_plugin_info_status_doctor()
    test_cli_plugin_list_updates()
    test_cli_plugin_init_all_frameworks()
    test_cli_plugin_init_single_framework()
    test_cli_plugin_init_existing_directory()
    print("\nALL SMOKE TESTS PASSED")
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `PYTHONPATH=src python3 tests/smoke_test.py`

Expected output ends with:

```
OK  cli_plugin_init_all_frameworks
OK  cli_plugin_init_single_framework
OK  cli_plugin_init_existing_directory

ALL SMOKE TESTS PASSED
```

If any assertion fails, re-check that `render_stub`'s `context` dict includes every Jinja variable used in the template files (`name`, `name_title`) — a `jinja2.exceptions.UndefinedError` means a template references a variable not present in `context`.

- [ ] **Step 8: Manual end-to-end check**

Run in a scratch directory (adjust the `PYTHONPATH` if `pyartisan` isn't installed in your environment):

```bash
cd /tmp && rm -rf plugin-init-check && mkdir plugin-init-check && cd plugin-init-check
PYTHONPATH=/home/bijoaja/my_project/pyartisan/flaskartisan/src python3 -m pyartisan.cli plugin init sample-plugin <<< "all"
ls sample-plugin sample-plugin/stubs
cat sample-plugin/manifest.yaml
readlink ~/.pyartisan/plugins/sample-plugin/dev
```

Expected: `sample-plugin/` contains `manifest.yaml`, `hooks.py`, `README.md`, `LICENSE`, `stubs/{fastapi,flask,django}/`; `manifest.yaml` shows `id: sample-plugin`; `readlink` output resolves to the `sample-plugin` directory just created.

- [ ] **Step 9: Commit**

```bash
cd /home/bijoaja/my_project/pyartisan/flaskartisan
git add pyproject.toml src/pyartisan/marketplace/__init__.py src/pyartisan/templates/plugin_init tests/smoke_test.py
git commit -m "feat: add pyartisan plugin init command

Scaffolds an empty plugin skeleton (manifest.yaml, hooks.py, README.md,
LICENSE, stubs/<framework>/) from bundled package-data templates and
auto-registers it into the local dev registry, removing the need to
hand-write plugin boilerplate.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 2: Update documentation

**Files:**
- Modify: `CLI.md`
- Modify: `HOW_TO_CREATE_PLUGIN.md`

**Interfaces:**
- Consumes: nothing from Task 1's code — documents the command's behavior as specified in the design spec and implemented in Task 1.
- Produces: nothing consumed by other tasks — this is the last task.

- [ ] **Step 1: Add `init` to the plugin lifecycle diagram in `CLI.md`**

In `CLI.md`, find this block (inside section "## 7. Sistem Plugin"):

```text
install  → download ke registry (global, tidak mengubah project apa pun)
apply    → terapkan plugin registry ke project aktif (jalankan hooks, tulis project.yaml)
update   → tarik pembaruan git plugin di registry, re-apply otomatis jika dipakai project ini
remove   → cabut plugin dari project (registry tetap ada, project lain masih bisa pakai)
uninstall→ hapus plugin dari registry (ditolak jika masih dipakai project lain)
```

Replace with:

```text
init     → scaffold skeleton plugin baru + auto-register ke registry (dev mode)
install  → download ke registry (global, tidak mengubah project apa pun)
apply    → terapkan plugin registry ke project aktif (jalankan hooks, tulis project.yaml)
update   → tarik pembaruan git plugin di registry, re-apply otomatis jika dipakai project ini
remove   → cabut plugin dari project (registry tetap ada, project lain masih bisa pakai)
uninstall→ hapus plugin dari registry (ditolak jika masih dipakai project lain)
```

- [ ] **Step 2: Add a new "7.10 Init" subsection to `CLI.md`**

Find this block (end of section "### 7.9 Doctor — Diagnosis Detail"):

```text
Diakhiri dengan `Plugin is valid` atau `Plugin has issues, see above.`

---

## 8. Membuat Plugin Sendiri
```

Replace with:

`````text
Diakhiri dengan `Plugin is valid` atau `Plugin has issues, see above.`

### 7.10 Init — Scaffold Plugin Baru

```bash
pyartisan plugin init <name>
```

Membuat skeleton plugin baru di `./<name>/` — tidak perlu membuat struktur
folder secara manual lagi. Prosesnya:

1. Menolak jika direktori `./<name>/` sudah ada (tidak menimpa apa pun).
2. Menanyakan framework target secara interaktif: `fastapi` / `flask` /
   `django` / `all` (default `all`).
3. Merender skeleton dari template bawaan `pyartisan` sendiri (tidak butuh
   koneksi internet): `manifest.yaml`, `hooks.py` (fungsi `after_install`
   dan `before_remove` kosong berisi komentar panduan Project API),
   `README.md`, `LICENSE`.
4. Membuat folder `stubs/<framework>/` kosong untuk tiap framework yang
   dipilih di langkah 2.
5. Langsung mendaftarkan plugin ke registry lokal sebagai symlink dev-mode
   (`~/.pyartisan/plugins/<name>/dev/`) — setara efeknya dengan
   `pyartisan plugin install <name> --local ./<name>`, jadi tidak perlu
   dijalankan terpisah.

Setelah `init`, langsung bisa `pyartisan plugin apply <name>` di dalam
project sandbox mana pun untuk mulai menguji hook yang sedang dikembangkan.

---

## 8. Membuat Plugin Sendiri
`````

- [ ] **Step 3: Add a row to the command summary table in `CLI.md`**

Find this line (inside section "## 9. Ringkasan Perintah"):

```text
| `pyartisan plugin install <name>` | Download plugin ke registry global |
```

Replace with:

```text
| `pyartisan plugin init <name>` | Scaffold skeleton plugin baru + auto-register ke registry |
| `pyartisan plugin install <name>` | Download plugin ke registry global |
```

- [ ] **Step 4: Document real usage in `HOW_TO_CREATE_PLUGIN.md`**

Find this block (between the "Plugin Development Workflow" diagram and the
"Project Structure" section):

```text
Publish to GitHub / Marketplace
```

---

# Project Structure
```

Replace with:

`````text
Publish to GitHub / Marketplace
```

---

# Scaffold Plugin Baru (`pyartisan plugin init`)

Daripada membuat struktur folder di atas secara manual, jalankan:

```bash
pyartisan plugin init payment-midtrans
```

CLI akan menanyakan framework target (`fastapi`/`flask`/`django`/`all`),
lalu langsung membuat `manifest.yaml`, `hooks.py` (skeleton kosong dengan
komentar panduan Project API), `README.md`, `LICENSE`, dan folder
`stubs/<framework>/` kosong untuk tiap framework yang dipilih — plus
langsung mendaftarkan plugin ke registry lokal dalam mode dev (setara
`pyartisan plugin install --local`). Tinggal isi `hooks.py` dan `stubs/`,
lalu langsung uji dengan `pyartisan plugin apply payment-midtrans` di
project sandbox.

---

# Project Structure
`````

- [ ] **Step 5: Mark the "Rekomendasi Tambahan" item as implemented in `HOW_TO_CREATE_PLUGIN.md`**

Find this block (inside "## Rekomendasi Tambahan"):

`````text
2. **`pyartisan plugin init`**
   Sebuah generator untuk membuat skeleton plugin baru:

   ```bash
   pyartisan plugin init payment-midtrans
   ```

   Hasilnya langsung membuat struktur folder, `manifest.yaml`, `hooks.py`, stub framework, README, LICENSE, dan contoh test. Ini akan sangat meningkatkan pengalaman developer dan mendorong konsistensi antar plugin.
`````

Replace with:

```text
2. **`pyartisan plugin init`** — ✅ sudah diimplementasikan, lihat bagian
   "Scaffold Plugin Baru" di atas.
```

- [ ] **Step 6: Commit**

```bash
cd /home/bijoaja/my_project/pyartisan/flaskartisan
git add CLI.md HOW_TO_CREATE_PLUGIN.md
git commit -m "docs: document pyartisan plugin init command

Co-Authored-By: Claude <noreply@anthropic.com>"
```
