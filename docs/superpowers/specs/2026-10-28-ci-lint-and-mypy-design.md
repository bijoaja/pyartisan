# CI Enhancement (Linting & Formatting) and Mypy Type Checking — Design Spec (pyartisan)

Date: 2026-10-28
Status: Draft, awaiting approval (no implementation yet)

## 1. Background

PyArtisan recently migrated to a modular Pytest test suite (24 tests) and a multi-OS CI matrix across Ubuntu, Windows, and macOS with Python 3.10 and 3.14.

However:
- **No linter or code formatter** is active in the repository or in CI. Code style differences, unused imports, dead variables, and formatting inconsistencies can be merged undetected.
- **No static type checking** is performed. Although several functions in `core/`, `utils/`, and `shared/` have partial type hints, untyped or incorrectly typed code can pass tests if not explicitly exercised by an assertion.
- The CI workflow currently cancels all in-progress runs when a new commit is pushed, including pushes to `main`. Pushes to `main` should always run to completion to verify post-merge health.

A reference CI workflow provided from an external project demonstrates a robust pattern:
1. Concurrency configured to cancel obsolete runs only for pull requests:
   `cancel-in-progress: ${{ github.event_name == 'pull_request' }}`.
2. A fast, dedicated `lint` job running on `ubuntu-latest` before or parallel to tests:
   `ruff check .`, `ruff format --check .`, and `mypy <src_paths>`.
3. An aggregate status check (`ci-ok`) that requires the `lint` job to pass alongside test and build jobs.

## 2. Goals

- Add Ruff for fast, modern linting and code formatting (`ruff check` and `ruff format`).
- Add Mypy for static type checking across `src/pyartisan/` and `tests/`.
- Enhance the GitHub Actions CI workflow with:
  - PR-only run cancellation (`cancel-in-progress: ${{ github.event_name == 'pull_request' }}`).
  - A dedicated `lint` job running Ruff and Mypy on `ubuntu-latest`.
  - Integration of `lint` into the `ci-ok` required gate.
- Document local developer commands (`uv run ruff check .`, `uv run ruff format .`, `uv run mypy src`).

## 3. Non-goals and Anti-goals

Non-goals:
- Zero tolerance (`--strict`) across every single line on day one: dynamic features like Click command decorators, Jinja2 template loader internals, and `importlib`-based dynamic plugin hook loading require targeted type ignores or relaxed settings.
- Adding pre-commit hooks that block local git commits unless explicitly requested by the user.
- Enforcing docstring style rules (e.g. pydocstyle `D` rules).

Anti-goals:
- Silently skipping type errors with blanket `# type: ignore` without comments explaining why.
- Adding runtime overhead or new production dependencies (`ruff` and `mypy` belong strictly in `[dependency-groups] dev`).
- Enabling formatting checks in CI before formatting the existing codebase, which would instantly fail the build.

## 4. Linting & Formatting Specification (Ruff)

### 4.1 Tool Selection
[Ruff](https://docs.astral.sh/ruff/) is selected as the unified linter and code formatter. It replaces Flake8, Black, isort, and pyupgrade with 10-100x faster execution.

### 4.2 Configuration
Configured in `pyproject.toml`:

```toml
[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # Pyflakes
    "I",    # isort (import sorting)
    "B",    # flake8-bugbear (common bug patterns)
    "UP",   # pyupgrade (modernize Python syntax)
]
ignore = [
    "E501", # line too long (handled by formatter)
]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

### 4.3 Baseline Formatting Step
Existing files in `src/` and `tests/` will be cleanly formatted with `uv run ruff format .` and autofixed with `uv run ruff check --fix .` before the CI gate is introduced.

## 5. Type Checking Specification (Mypy)

### 5.1 Architecture & Strategy
PyArtisan is a framework-agnostic CLI toolkit written in modern Python (>=3.10).
A **gradual typing strategy** is used:
1. Global configuration checks untyped definitions and catches common type mismatches.
2. Core utilities and data structures (`utils/`, `config/`, `core/manifest.py`, `core/exceptions.py`) enforce full type annotations.
3. Dynamic layers (Click command wrappers in `cli/`, Jinja2 loader in `renderer/`, plugin hooks in `marketplace/`) use targeted overrides or annotations.

### 5.2 Dependencies
Added to `[dependency-groups] dev` in `pyproject.toml`:
- `mypy>=1.10.0`
- `types-PyYAML` (type stubs for PyYAML)

### 5.3 Mypy Configuration
In `pyproject.toml`:

```toml
[tool.mypy]
python_version = "3.10"
files = ["src/pyartisan"]
warn_unused_configs = true
warn_redundant_casts = true
warn_unused_ignores = true
check_untyped_defs = true
disallow_untyped_defs = false  # will be enabled per module below

# Modules with strict typing requirements:
[[tool.mypy.overrides]]
module = [
    "pyartisan.utils.*",
    "pyartisan.config.*",
    "pyartisan.core.exceptions",
    "pyartisan.core.manifest",
    "pyartisan.core.registration",
    "pyartisan.shared.*",
]
disallow_untyped_defs = true
disallow_incomplete_defs = true

# Third-party packages without bundled stubs:
[[tool.mypy.overrides]]
module = [
    "tomli.*",
]
ignore_missing_imports = true
```

### 5.4 Handling Dynamic Patterns
- **Click Context:** Click commands (`make_cmd`, `config_group`, etc.) use `@click.pass_context`. Type `ctx: click.Context`.
- **Dynamic Plugin Hooks:** `marketplace/core.py::_load_hooks` uses `importlib.util.spec_from_file_location`. Annotate the return type as `types.ModuleType | None`.
- **Dynamic Generator Kwargs:** `engine.py::dispatch_make` accepts `**extra_options: Any`. Annotate explicitly as `Any`.

## 6. CI Workflow Updates (`.github/workflows/ci.yml`)

### 6.1 Concurrency Adjustment
Update the concurrency block so PR runs are canceled when superseded, but pushes to `main` run to completion:

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}
```

### 6.2 New `lint` Job
Add a fast `lint` job running on `ubuntu-latest`:

```yaml
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
          python-version: "3.10"
      - name: Sync dependencies
        run: uv sync --frozen --python 3.10
      - name: Ruff Check
        run: uv run ruff check .
      - name: Ruff Format Check
        run: uv run ruff format --check .
      - name: Mypy Type Check
        run: uv run mypy
```

### 6.3 Update `ci-ok` Aggregate Gate
Add `lint` to `needs`:

```yaml
  ci-ok:
    runs-on: ubuntu-latest
    needs: [lint, test, build, install]
    if: always()
    steps:
      - name: Check all jobs succeeded
        run: |
          results="${{ join(needs.*.result, ' ') }}"
          echo "Job results: $results"
          for res in $results; do
            if [ "$res" != "success" ]; then
              echo "Error: Job failed with status: $res"
              exit 1
            fi
          done
          echo "All required jobs succeeded"
```

## 7. Developer Workflow

Developers can run checks locally before pushing:
```bash
# Check code style and common bugs
uv run ruff check .

# Automatically fix fixable lint issues
uv run ruff check --fix .

# Check formatting
uv run ruff format --check .

# Automatically format code
uv run ruff format .

# Run static type checking
uv run mypy
```

## 8. Acceptance Criteria

1. `uv run ruff check .` passes locally with 0 errors.
2. `uv run ruff format --check .` passes locally with 0 modifications needed.
3. `uv run mypy` passes locally with 0 type errors.
4. `.github/workflows/ci.yml` contains the `lint` job and updated concurrency settings.
5. In CI, `lint` job runs and passes on GitHub Actions.
6. `ci-ok` requires `lint` and turns red if linting or type-checking fails.
