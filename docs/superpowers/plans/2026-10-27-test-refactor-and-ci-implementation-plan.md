# PyArtisan Test Refactor & CI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the monolithic `tests/smoke_test.py` (882 lines, 23 functions) into a modular Pytest test suite (`tests/unit/` and `tests/cli/`), commit `uv.lock`, and set up multi-OS CI testing on GitHub Actions.

**Architecture:**
1. Configure `pyproject.toml` with `[dependency-groups] dev = ["pytest"]` and `[tool.pytest.ini_options]` (`testpaths = ["tests"]`, `pythonpath = ["src"]`).
2. Implement clean pytest fixtures in `tests/conftest.py`:
   - `fake_home`: isolates user home directory (`os.path.expanduser("~")`) using `monkeypatch`.
   - `in_tmp_cwd`: isolates working directory via `monkeypatch.chdir(tmp_path)`.
   - `runner`: creates clean `click.testing.CliRunner`.
   - `plugin_project`: sets up temporary plugin test structure.
   - `isolated_config`: patches `config.CONFIG_DIR` and `CONFIG_PATH`.
3. Split existing 23 smoke tests into 24 modular tests (splitting `test_uv_support` into installer selection and doctor checks):
   - `tests/unit/`: `test_naming.py`, `test_manifest.py`, `test_renderer.py`, `test_registration.py`, `test_config.py`, `test_plugin_engine.py`, `test_installer_selection.py`, `test_doctor.py`, `test_serve_venv.py`, `test_console_encoding.py`.
   - `tests/cli/`: `test_make.py`, `test_plugin_lifecycle.py`, `test_plugin_install.py`, `test_plugin_remove_uninstall.py`, `test_plugin_inspect.py`, `test_plugin_init.py`.
4. Run tests via `uv run pytest`, verify 24 passed tests, then remove `tests/smoke_test.py`.
5. Update docs (`CLAUDE.md`, `CONTRIBUTING.md`, `PRD.md`) to reflect `uv run pytest`.
6. Add GitHub Actions CI workflow `.github/workflows/ci.yml` across Ubuntu, Windows, and macOS with Python 3.10 and 3.14.

**Tech Stack:** Python 3.10+, Pytest, uv, Click, Jinja2, PyYAML, GitHub Actions.

---

### Task 1: Pytest Setup & Lockfile Generation

**Files:**
- Modify: `pyproject.toml`
- Create: `uv.lock`

- [ ] **Step 1: Update `pyproject.toml`**
  Add dev dependency group and pytest configuration:
  ```toml
  [dependency-groups]
  dev = ["pytest"]

  [tool.pytest.ini_options]
  testpaths = ["tests"]
  pythonpath = ["src"]
  ```

- [ ] **Step 2: Generate `uv.lock`**
  Run `uv lock` and ensure lock covers both Python 3.10 (with `tomli`) and 3.14+.

---

### Task 2: Implement Shared Fixtures (`tests/conftest.py`)

**Files:**
- Create: `tests/conftest.py`

- [ ] **Step 1: Write `tests/conftest.py`**
  Implement fixtures:
  - `fake_home(monkeypatch, tmp_path)`: sets up isolated home directory and patches `os.path.expanduser`.
  - `in_tmp_cwd(monkeypatch, tmp_path)`: isolates current working directory.
  - `runner()`: returns `CliRunner()`.
  - `plugin_project(tmp_path)`: generates sample plugin sandbox project.
  - `isolated_config(monkeypatch, tmp_path)`: isolates `CONFIG_DIR` and `CONFIG_PATH`.

---

### Task 3: Migrate Unit Tests (`tests/unit/`)

**Files:**
- Create: `tests/unit/test_naming.py`
- Create: `tests/unit/test_manifest.py`
- Create: `tests/unit/test_renderer.py`
- Create: `tests/unit/test_registration.py`
- Create: `tests/unit/test_config.py`
- Create: `tests/unit/test_plugin_engine.py`
- Create: `tests/unit/test_installer_selection.py`
- Create: `tests/unit/test_doctor.py`
- Create: `tests/unit/test_serve_venv.py`
- Create: `tests/unit/test_console_encoding.py`

- [ ] **Step 1: Extract core unit tests**
  - `test_naming.py`: from `test_name_parts`
  - `test_manifest.py`: from `test_manifest_load`
  - `test_renderer.py`: from `test_render_stub` and `test_render_stub_nested`
  - `test_registration.py`: from `test_registration_import_list` and `test_registration_marker`
  - `test_config.py`: from `test_config_roundtrip` (using `isolated_config` fixture)
  - `test_plugin_engine.py`: from `test_metadata_parsers` and `test_project_context_ops`
  - `test_installer_selection.py`: from `test_uv_support` (command construction assertions)
  - `test_doctor.py`: from `test_uv_support` (doctor uv & pip check assertions)
  - `test_serve_venv.py`: from `test_serve_project_venv`
  - `test_console_encoding.py`: from `test_force_utf8`

---

### Task 4: Migrate CLI Tests (`tests/cli/`)

**Files:**
- Create: `tests/cli/test_make.py`
- Create: `tests/cli/test_plugin_lifecycle.py`
- Create: `tests/cli/test_plugin_install.py`
- Create: `tests/cli/test_plugin_remove_uninstall.py`
- Create: `tests/cli/test_plugin_inspect.py`
- Create: `tests/cli/test_plugin_init.py`

- [ ] **Step 1: Extract CLI tests**
  - `test_make.py`: `test_cli_generic_make`, `test_cli_make_not_supported`, `test_cli_make_no_manifest`
  - `test_plugin_lifecycle.py`: `test_cli_plugin_lifecycle`
  - `test_plugin_install.py`: `test_cli_plugin_install_blockchain_license`
  - `test_plugin_remove_uninstall.py`: `test_cli_plugin_remove_multi_and_all`
  - `test_plugin_inspect.py`: `test_cli_plugin_info_status_doctor`, `test_cli_plugin_list_updates`
  - `test_plugin_init.py`: `test_cli_plugin_init_all_frameworks`, `test_cli_plugin_init_single_framework`, `test_cli_plugin_init_existing_directory`

---

### Task 5: Verify Suite & Remove Legacy `tests/smoke_test.py`

**Files:**
- Delete: `tests/smoke_test.py`

- [ ] **Step 1: Run full pytest suite**
  Run `uv run pytest -v`. Assert 24 passed tests.
- [ ] **Step 2: Delete legacy smoke test file**
  Remove `tests/smoke_test.py`.

---

### Task 6: Update Documentation

**Files:**
- Modify: `CLAUDE.md`
- Modify: `CONTRIBUTING.md`
- Modify: `docs/en/CONTRIBUTING.md`
- Modify: `docs/id/CONTRIBUTING.md`
- Modify: `docs/en/PRD.md`
- Modify: `docs/id/PRD.md`

- [ ] **Step 1: Replace test commands**
  Update all mentions of `tests/smoke_test.py` to `uv run pytest`.

---

### Task 7: Implement CI Workflow (`.github/workflows/ci.yml`)

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Write `.github/workflows/ci.yml`**
  - Triggers: `pull_request`, `push: branches: [main]`, `workflow_dispatch`
  - Job `test`:
    - Matrix: `os: [ubuntu-latest, windows-latest, macos-latest]`, `python: ["3.10", "3.14"]`, `fail-fast: false`
    - Steps: checkout, setup uv, `uv sync --frozen --python ${{ matrix.python }}`, `uv run pytest -v`
  - Job `build`:
    - Ubuntu-latest, Python 3.14: `uv build`, verify wheel contains `templates/plugin_init/` and `entry_points.txt`.
  - Job `install`:
    - Ubuntu-latest & Windows-latest: install wheel via `uv tool install`, verify `pyartisan --version`, `pyartisan --help`, and `printf 'all\n' | pyartisan plugin init ci-check`.
  - Job `ci-ok`:
    - `needs: [test, build, install]`, `if: always()`, verifies all jobs succeeded.

- [ ] **Step 2: Submit PR & Ruleset instructions**
  Commit, push, and create PR.
