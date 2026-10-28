# PyArtisan Mypy Type Checking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement static type checking with Mypy in `pyartisan`, add type annotations to core, CLI, marketplace, renderer, and utility modules, and add Mypy verification to the CI workflow.

**Architecture:**
1. Add `mypy>=1.10.0` and `types-PyYAML` to `[dependency-groups] dev` in `pyproject.toml` and update `uv.lock`.
2. Configure `[tool.mypy]` in `pyproject.toml` with gradual typing strategy (strictness on `utils/`, `config/`, `core/manifest.py`, `core/registration.py`, `shared/`; targeted overrides for dynamic layers).
3. Add type annotations and resolve Mypy errors across `src/pyartisan/`.
4. Integrate `uv run mypy` into the `lint` job in `.github/workflows/ci.yml`.
5. Update documentation with developer type check commands.

**Tech Stack:** Python 3.10+, uv, Mypy.

---

### Task 1: Add Mypy & Type Stubs Configuration

**Files:**
- Modify: `pyproject.toml`
- Modify: `uv.lock`

- [ ] **Step 1: Add Mypy to dev dependencies and configure in `pyproject.toml`**
  ```toml
  [dependency-groups]
  dev = [
      "pytest>=8.2.0",
      "ruff>=0.4.0",
      "mypy>=1.10.0",
      "types-PyYAML",
  ]

  [tool.mypy]
  python_version = "3.10"
  files = ["src/pyartisan"]
  warn_unused_configs = true
  warn_redundant_casts = true
  warn_unused_ignores = true
  check_untyped_defs = true
  disallow_untyped_defs = false

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

  [[tool.mypy.overrides]]
  module = [
      "tomli.*",
  ]
  ignore_missing_imports = true
  ```

- [ ] **Step 2: Update lockfile**
  Run:
  ```bash
  uv lock
  ```

---

### Task 2: Add Type Annotations & Resolve Mypy Errors

**Files:**
- Modify: `src/pyartisan/utils/**/*.py`
- Modify: `src/pyartisan/config/**/*.py`
- Modify: `src/pyartisan/core/**/*.py`
- Modify: `src/pyartisan/marketplace/**/*.py`
- Modify: `src/pyartisan/renderer/**/*.py`
- Modify: `src/pyartisan/cli/**/*.py`

- [ ] **Step 1: Type `utils/` and `config/`**
  Add explicit type annotations to `naming.py`, `fs.py`, `console.py`, and `config/__init__.py`.

- [ ] **Step 2: Type `core/` modules**
  Type `manifest.py`, `registration.py`, `exceptions.py`, `plugin_engine.py`, and `engine.py`. Ensure dynamic parameters (`**extra_options: Any`) and return types are annotated.

- [ ] **Step 3: Type `marketplace/` and `renderer/`**
  Type hook loaders (`_load_hooks` returning `types.ModuleType | None`), usage tracking, and `render_stub`.

- [ ] **Step 4: Type `cli/` and command modules**
  Annotate Click command functions and `ctx: click.Context`.

- [ ] **Step 5: Run Mypy locally**
  Run:
  ```bash
  uv run mypy
  ```
  Ensure 0 type errors.

- [ ] **Step 6: Run pytest to verify all 24 tests pass**
  Run:
  ```bash
  uv run pytest -v
  ```
  Ensure all tests continue passing.

---

### Task 3: Integrate Mypy into CI Workflow

**Files:**
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Add Mypy step to `lint` job**
  In `.github/workflows/ci.yml`, add step under `lint`:
  ```yaml
        - name: Mypy Type Check
          run: uv run mypy
  ```

---

### Task 4: Documentation & PR Submission

**Files:**
- Modify: `CLAUDE.md`
- Modify: `CONTRIBUTING.md`
- Modify: `docs/en/CONTRIBUTING.md`
- Modify: `docs/id/CONTRIBUTING.md`

- [ ] **Step 1: Update documentation**
  Add `uv run mypy` to developer commands.

- [ ] **Step 2: Commit, push, and open PR**
  - Branch: `feat/mypy-type-checking`
  - Commit message: `feat: add Mypy static type checking across pyartisan modules`
  - Author only `bijoaja` (NO co-author).
  - Open PR to `main`.
