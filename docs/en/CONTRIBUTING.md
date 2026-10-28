# Contributor Guide

> **Language:** [Indonesia](../id/CONTRIBUTING.md) | English
> **Last verified against the code:** commit `80b5acc` (2026-10-26)

Thanks for wanting to contribute to PyArtisan. This guide only lists things that actually hold in this repo. If something does not match reality, that is a documentation bug: please open an issue.

---

## 1. Setting up your environment

Prerequisites: [uv](https://docs.astral.sh/uv/) and Git. Python does not have to be installed; uv can download it (the project needs Python 3.10 or newer).

```bash
git clone https://github.com/bijoaja/pyartisan.git
cd pyartisan
uv tool install --editable .
pyartisan --help
```

`uv tool install` creates a separate environment, so you do not need to create a venv and your system Python is untouched. `--editable` makes changes in `src/` take effect without reinstalling.

Without uv, the alternative is `pip install -e .` inside your own venv.

If `pyartisan` is not found, run `uv tool update-shell` and open a new terminal. When you are done experimenting, remove it with `uv tool uninstall pyartisan`.

> **Windows:** if the output contains garbled characters or encoding errors, set `PYTHONUTF8=1`. PyArtisan already forces UTF-8 for its own stdout/stderr, but other programs in the same terminal may not.

---

## 2. Code layout

```text
src/pyartisan/
├── cli/commands/     # one file per command (new, make, serve, build, config, doctor, version, plugin)
├── core/
│   ├── engine.py         # dispatch_new / dispatch_make / dispatch_serve / dispatch_build
│   ├── manifest.py       # reads .pyartisan/manifest.yaml
│   ├── registration.py   # inserts imports / lines into existing files
│   ├── plugin_engine.py  # ProjectContext (Project API for plugin hooks)
│   └── exceptions.py
├── marketplace/      # global plugin registry ~/.pyartisan/plugins
├── project/          # Project API placeholder (no code yet)
├── renderer/         # render_stub (Jinja2)
├── config/           # ~/.pyartisan/config.toml
├── shared/           # doctor logic
├── utils/            # console, fs, naming
└── templates/plugin_init/   # skeleton for `plugin init`
tests/                # modular pytest test suite (unit/ and cli/)
docs/                 # documentation (id/ and en/); docs/superpowers/ holds specs and plans
```

Principle: `cli/` only parses arguments and calls functions in `core/engine.py`. `core/` must not contain code specific to one framework. Framework knowledge lives in the template repos (FlaskIQ, FastIQ) through `.pyartisan/manifest.yaml`. See [PRD.md](PRD.md) for the design and the status of each feature.

---

## 3. Running tests and linters

Tests use pytest and are run via `uv`:

```bash
uv run pytest
```

To run a subset of tests:

```bash
uv run pytest tests/unit/
uv run pytest tests/cli/test_make.py
```

Linting and formatting use Ruff:

```bash
uv run ruff check .          # check lint
uv run ruff check --fix .    # autofix lint issues
uv run ruff format --check . # check formatting
uv run ruff format .         # format code
```

Security scanning uses Bandit (also runs in CI, `lint` job) and Semgrep (local only, needs registry access):

```bash
uv run bandit -q -r src -c pyproject.toml
uvx semgrep --config p/python --config p/security-audit src
```

Every `# nosec` / `# nosemgrep` suppression must carry a written reason on the same line.

CI runs on GitHub Actions on pull requests and pushes to `main` across Ubuntu, Windows, and macOS on Python 3.10 and 3.14.

Every non-trivial logic change should add test cases under `tests/unit/` or `tests/cli/`.

---

## 4. Workflow

1. Find or open an issue describing the problem.
2. Create a branch from `main`, e.g. `fix/serve-project-venv`, `feat/uv-support`, `docs/restructure`.
3. Keep the change small and focused. One PR, one purpose.
4. Run the test suite (`uv run pytest`).
5. Commit with Conventional Commits style messages, e.g. `fix: ...`, `feat: ...`, `docs: ...`.
6. Open a PR to `main`. Put `Closes #<number>` in the description so the issue closes automatically when the PR is merged.
7. In the PR description, write what changed, how it was verified, and what was **not** verified.

---

## 5. Adding support for a new framework

You do not need to change `core/` or `cli/`.

1. Prepare a template repo for the framework, containing `.pyartisan/manifest.yaml` (`generators`, `paths`, `scripts`) and a stubs folder.
2. Register its URL in `DEFAULT_CONFIG["templates"]` in `src/pyartisan/config/__init__.py`. Users can also add it themselves: `pyartisan config set templates.<framework> <url>`.
3. Add the framework name to the `click.Choice` in `plugin init` if you want it selectable when creating a plugin (`cli/commands/plugin.py`).

If `ProjectContext` (`core/plugin_engine.py`) needs framework-specific behavior, note it in an issue: that part currently still contains `fastapi` / everything-else branching.

---

## 6. Writing documentation

* Documentation exists in two languages: `docs/id/` and `docs/en/`, with the same file names. Change both in the same PR.
* `README.md` (English) and `README.id.md` (Indonesian) are in the root.
* Write only what has been checked against the code or against `--help` output. Features that do not exist yet are clearly marked as plans, not written as if they exist.
* Commands, file names and field names (`apply`, `manifest.yaml`, `hooks.py`) are not translated.

---

## 7. Commit and PR rules

* The commit author is you. Do not add `Co-Authored-By` lines for tools or people who did not take part in writing the commit.
* Do not commit build output folders: `build/`, `dist/`, `*.egg-info/` (already in `.gitignore`). Commit `uv.lock` when project dependencies change.
* Merging is done by the maintainer through GitHub.

---

## 8. Reporting problems

Open an issue at <https://github.com/bijoaja/pyartisan/issues>. Include:

* the version (`pyartisan version`), OS, and how you installed it (uv tool, pip, or source),
* the steps to reproduce and the full output,
* the expected result.

Problems with the project template (folder structure, the `requirements.txt` produced by `pyartisan new`) belong in the template repos: [flaskiq](https://github.com/bijoaja/flaskiq) or [fastiq](https://github.com/bijoaja/fastiq).
