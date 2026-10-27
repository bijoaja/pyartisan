# Test Structure — Design Spec (pyartisan)

Date: 2026-10-27
Status: Draft, awaiting approval (no implementation yet)

## 1. Background

All tests live in one file, `tests/smoke_test.py` (882 lines, 23 `test_*` functions). It is run as a
script: `main()` calls every test in a hand-kept order and prints `OK ...` lines. Problems that
follow from this:

- Finding the test for one area means scrolling an 880-line file.
- Global state is changed and restored by hand in every test: `os.chdir` plus `orig_cwd` (8 tests),
  a patched `os.path.expanduser` plus `orig_expanduser` (5 inline copies plus the `_patch_home`
  helper), and monkeypatching of `shutil.which`, `sys.prefix` and `os.environ`. A failing assertion before the `finally` block
  leaves later tests running with the wrong home or cwd.
- Two private helpers (`_setup_plugin_project`, `_patch_home`) are shared only by living in the
  same file.
- `main()` order can drift from the file order (it already did: three tests are called first but
  defined last), and a new test is silently not run until someone adds it to `main()`.
- A run stops at the first failure, so one broken test hides the status of the rest.

The template repo `fastiq` already uses the structure this spec moves to: one `test_<module>.py` per
area, shared fixtures in `conftest.py`, pytest, `uv run pytest`.

## 2. Goals

- One test file per area, named `test_<area>.py`, grouped into `tests/unit/` and `tests/cli/`.
- Shared setup in `tests/conftest.py` as pytest fixtures, replacing the two private helpers and the
  hand-written try/finally state restoration.
- Tests are discovered automatically; no list to maintain.
- A failing test does not stop the others.
- Same coverage as today: every one of the 23 existing tests appears exactly once in the new layout.

## 3. Non-goals and anti-goals

Non-goals:
- No behavior change in `src/`. This work only moves and re-expresses tests.
- No new tests beyond what moving requires (a split of one test into two is allowed, see the table).
- No coverage tooling, linting, or test-time dependencies other than pytest.
- CI is a separate spec: `2026-10-27-ci-design.md`.

Anti-goals (this work failed even if it looks green):
- An assertion was weakened, deleted, or wrapped in skip/xfail to make a test pass.
- The test count after the change is lower than before without a recorded reason.
- Tests pass only because state leaked from an earlier test (they must pass in any order and one at a time).

## 4. Decisions

Made by the user:
- Framework is **pytest**, added as a dev dependency. This replaces the "no test framework" rule
  currently written in `CLAUDE.md`, `CONTRIBUTING.md` and `docs/{id,en}/CONTRIBUTING.md`.
- The specs for this work live in each repo's own `docs/superpowers/specs/`.

My calls (the user can overrule any of them):
- Dev dependency goes in `[dependency-groups] dev = ["pytest"]` in `pyproject.toml`, the same form
  `fastiq` uses, run with `uv run pytest`.
- `uv.lock` is committed (currently it is not tracked and `.gitignore` leaves it commented out), so CI
  can use `--frozen` and local runs match CI.
- The two directories are `tests/unit/` (calls Python functions directly) and `tests/cli/` (drives
  `pyartisan.cli.cli` through `click.testing.CliRunner`).

## 5. Target layout and mapping

```
tests/
  conftest.py
  unit/
    test_naming.py
    test_manifest.py
    test_renderer.py
    test_registration.py
    test_config.py
    test_plugin_engine.py
    test_installer_selection.py
    test_doctor.py
    test_serve_venv.py
    test_console_encoding.py
  cli/
    test_make.py
    test_plugin_lifecycle.py
    test_plugin_install.py
    test_plugin_remove_uninstall.py
    test_plugin_inspect.py
    test_plugin_init.py
```

Every current test, and where it goes:

| Current function (line) | New file | Notes |
|---|---|---|
| `test_name_parts` (28) | `unit/test_naming.py` | |
| `test_manifest_load` (36) | `unit/test_manifest.py` | |
| `test_render_stub` (61) | `unit/test_renderer.py` | |
| `test_render_stub_nested` (84) | `unit/test_renderer.py` | Regression test for the Windows path bug (issue #6). |
| `test_registration_import_list` (102) | `unit/test_registration.py` | |
| `test_registration_marker` (121) | `unit/test_registration.py` | |
| `test_config_roundtrip` (155) | `unit/test_config.py` | Currently assigns `config.CONFIG_DIR` and `CONFIG_PATH` and never restores them; use `monkeypatch`. |
| `test_metadata_parsers` (258) | `unit/test_plugin_engine.py` | Tests `load_project_yaml`, `load_template_yaml`, `load_plugin_yaml` from `core/plugin_engine.py`. |
| `test_project_context_ops` (288) | `unit/test_plugin_engine.py` | `ProjectContext`. |
| `test_uv_support` (775) | `unit/test_installer_selection.py` and `unit/test_doctor.py` | Split in two: the first half checks `doctor._check_uv` / `_check_pip` with `shutil.which` patched; the second checks `engine._venv_cmd` / `_install_cmd`. This is the one allowed split, so the new count is 24. |
| `test_serve_project_venv` (817) | `unit/test_serve_venv.py` | Currently mutates `sys.prefix` and `VIRTUAL_ENV`; use `monkeypatch`. |
| `test_force_utf8` (798) | `unit/test_console_encoding.py` | |
| `test_cli_generic_make` (172) | `cli/test_make.py` | |
| `test_cli_make_not_supported` (234) | `cli/test_make.py` | |
| `test_cli_make_no_manifest` (249) | `cli/test_make.py` | |
| `test_cli_plugin_lifecycle` (405) | `cli/test_plugin_lifecycle.py` | Uses `_setup_plugin_project` (line 366). |
| `test_cli_plugin_install_blockchain_license` (492) | `cli/test_plugin_install.py` | |
| `test_cli_plugin_remove_multi_and_all` (519) | `cli/test_plugin_remove_uninstall.py` | |
| `test_cli_plugin_info_status_doctor` (571) | `cli/test_plugin_inspect.py` | |
| `test_cli_plugin_list_updates` (646) | `cli/test_plugin_inspect.py` | |
| `test_cli_plugin_init_all_frameworks` (681) | `cli/test_plugin_init.py` | Uses `_patch_home` (line 672). |
| `test_cli_plugin_init_single_framework` (722) | `cli/test_plugin_init.py` | |
| `test_cli_plugin_init_existing_directory` (748) | `cli/test_plugin_init.py` | |

Total: 23 functions today, 24 after the one split.

## 6. Shared fixtures (`tests/conftest.py`)

Replace the hand-written setup with fixtures. Names are the contract; bodies are the builder's call.

| Fixture | Replaces | Behavior |
|---|---|---|
| `fake_home` | `_patch_home` and the 5 inline `os.path.expanduser` patches | Creates `tmp_path/"home"` and points `os.path.expanduser("~")` at it using `monkeypatch`. Plugin code builds the registry from `os.path.expanduser("~")` (`marketplace/core.py`), so patching `HOME`/`USERPROFILE` alone is not enough. |
| `in_tmp_cwd` | the inline `os.chdir(root)` / `orig_cwd` pairs | `monkeypatch.chdir(tmp_path)` and returns the path. |
| `runner` | `CliRunner()` created per test | A `CliRunner` instance. |
| `plugin_project` | `_setup_plugin_project` (366) | Builds the sample project and plugin tree under `tmp_path`, returns the paths. |
| `isolated_config` | the `config.CONFIG_DIR` / `CONFIG_PATH` assignments | Points the config module at `tmp_path` via `monkeypatch.setattr`. |

Rules for all tests: state is changed only through `monkeypatch` and `tmp_path`; no test calls
`os.chdir` or assigns to a module global directly; no test depends on another test having run.

## 7. Config

In `pyproject.toml`:

```toml
[dependency-groups]
dev = ["pytest"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

Commands: `uv run pytest` (all), `uv run pytest tests/unit` (one folder), `uv run pytest tests/cli/test_make.py -k not_supported` (one test). The runtime dependencies `click`, `jinja2`,
`pyyaml`, `flask`, `sqlalchemy` already come from `[project] dependencies`, so `uv run` needs nothing else.

## 8. Migration

1. Add pytest, `pyproject.toml` settings and commit `uv.lock`.
2. Record the baseline: the old suite passes, 23 functions.
3. Create `conftest.py`, then move tests area by area. Do not delete `smoke_test.py` yet.
4. When `uv run pytest` shows 24 passed and every row in section 5 is accounted for, delete `tests/smoke_test.py`.
5. Update the docs that describe the old command: `CLAUDE.md`, `CONTRIBUTING.md`, `docs/en/CONTRIBUTING.md`, `docs/id/CONTRIBUTING.md`, and the Testability row in `docs/en/PRD.md` / `docs/id/PRD.md`. The "do not use `uv run --with-editable .`" warning goes away once tests run with `uv run pytest`.

## 9. Acceptance

- `uv run pytest` passes, 24 tests, on the maintainer's Windows machine.
- Every file under `tests/` is named `test_*.py` or `conftest.py`, and each test appears once in section 5.
- Each test file passes when run alone (`uv run pytest tests/cli/test_make.py`), and `uv run pytest tests/cli tests/unit` (folders in the opposite order) passes too. This checks for leaked state.
- No assertion was removed or weakened (reviewed in the diff).
- `git grep -n "os.chdir\|orig_expanduser\|smoke_test"` in `tests/`, `CLAUDE.md` and the contributor docs finds nothing.

## 10. Risks

- Three tests depend on OS behavior: the junction fallback in `plugin init` and `plugin install --local`, `os.name` branches in the serve venv tests, and the UTF-8 test. They pass on Windows today; they have never been run on Linux or macOS. The first CI run may expose failures that are real portability bugs, not test bugs. See the CI spec for how to treat that.
- Adding pytest changes the documented rule "no test framework". This is a decision by the user, recorded in section 4.

## 11. Left to the builder

Fixture bodies, whether `tests/unit` and `tests/cli` get an `__init__.py` (pytest's default import mode needs unique basenames or package markers; choose one and keep names unique), and the exact wording of the doc updates.
