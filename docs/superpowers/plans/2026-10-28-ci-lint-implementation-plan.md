# PyArtisan CI Linting & Formatting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Ruff linting and formatting in `pyartisan`, format the existing codebase cleanly, and add a dedicated `lint` job with PR-specific concurrency to the multi-OS GitHub Actions CI workflow.

**Architecture:**
1. Add `ruff>=0.4.0` to `[dependency-groups] dev` in `pyproject.toml` and update `uv.lock`.
2. Configure Ruff in `pyproject.toml` (`line-length = 100`, `target-version = "py310"`, select `E, W, F, I, B, UP`).
3. Format existing files in `src/pyartisan/` and `tests/` with `uv run ruff check --fix .` and `uv run ruff format .`.
4. Update `.github/workflows/ci.yml`:
   - Set concurrency to `cancel-in-progress: ${{ github.event_name == 'pull_request' }}`.
   - Add a fast `lint` job running on `ubuntu-latest` with `uv run ruff check .` and `uv run ruff format --check .`.
   - Update `ci-ok` to require `lint` alongside `test`, `build`, and `install`.
5. Update `CLAUDE.md`, `CONTRIBUTING.md`, and docs with developer commands.

**Tech Stack:** Python 3.10+, uv, Ruff, GitHub Actions.

---

### Task 1: Add Ruff & Configure in `pyproject.toml`

**Files:**
- Modify: `pyproject.toml`
- Modify: `uv.lock`

- [ ] **Step 1: Update `pyproject.toml`**
  Add Ruff to dev dependencies:
  ```toml
  [dependency-groups]
  dev = [
      "pytest>=8.2.0",
      "ruff>=0.4.0",
  ]

  [tool.ruff]
  line-length = 100
  target-version = "py310"

  [tool.ruff.lint]
  select = ["E", "W", "F", "I", "B", "UP"]
  ignore = ["E501"]

  [tool.ruff.format]
  quote-style = "double"
  indent-style = "space"
  ```

- [ ] **Step 2: Update lockfile**
  Run:
  ```bash
  uv lock
  ```

---

### Task 2: Format and Clean Codebase

**Files:**
- Modify: `src/pyartisan/**/*.py`, `tests/**/*.py`

- [ ] **Step 1: Run autofix and formatter**
  Run:
  ```bash
  uv run ruff check --fix .
  uv run ruff format .
  ```

- [ ] **Step 2: Verify zero lint and formatting errors**
  Run:
  ```bash
  uv run ruff check .
  uv run ruff format --check .
  ```
  Ensure both exit with 0.

- [ ] **Step 3: Run pytest to verify all 24 tests pass**
  Run:
  ```bash
  uv run pytest -v
  ```
  Ensure all 24 modular tests pass cleanly.

---

### Task 3: Update CI Workflow (`.github/workflows/ci.yml`)

**Files:**
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Update concurrency and add `lint` job**
  Update concurrency:
  ```yaml
  concurrency:
    group: ${{ github.workflow }}-${{ github.ref }}
    cancel-in-progress: ${{ github.event_name == 'pull_request' }}
  ```
  Add job `lint`:
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
  ```
  Update `ci-ok`:
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

- [ ] **Step 2: Validate workflow syntax**
  Verify YAML with `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"`.

---

### Task 4: Documentation & PR Submission

**Files:**
- Modify: `CLAUDE.md`
- Modify: `CONTRIBUTING.md`
- Modify: `docs/en/CONTRIBUTING.md`
- Modify: `docs/id/CONTRIBUTING.md`

- [ ] **Step 1: Update documentation**
  Add `uv run ruff check .` and `uv run ruff format .` instructions.

- [ ] **Step 2: Commit, push, and open PR**
  - Branch: `feat/ci-lint`
  - Commit message: `feat: add Ruff linting and formatting to CI workflow`
  - Author only `bijoaja` (NO co-author).
  - Open PR to `main`.
