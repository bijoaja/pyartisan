# Security and Code Quality Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the pyartisan security findings S1-S9 and real bugs Q1-Q7, with a failing test first for each, and gate Bandit in CI.

**Architecture:** One validation module (`utils/safe.py`) used at every command boundary (allowlist) and at every delete/write sink (containment). One Jinja factory `make_env()` returning a `SandboxedEnvironment` replaces the six `Environment()` sites. Hook consent lives in `cli/commands/plugin.py`; exit-code fixes go last because they touch the most tests.

**Tech Stack:** Python 3.10+, click, Jinja2, PyYAML, pytest + `CliRunner`, Ruff, Bandit (`bandit[toml]`), uv.

**Spec:** `docs/superpowers/specs/2026-10-28-security-and-code-quality-hardening-design.md` (approved 2026-10-28; open questions 6.1-6.3 resolved with the spec's stated defaults).

## Global Constraints

- Python 3.10+; Windows, Linux, macOS (CI matrix 3.10 and 3.14). Path checks must work with junctions and `\`.
- No new runtime dependencies. `bandit[toml]>=1.7` goes only into `[dependency-groups] dev`; `uv.lock` updated.
- `NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}")`, matched with `fullmatch`. `make` and `new` accept a single segment only.
- Existing tests stay green except the deliberate changes: `tests/cli/test_plugin_lifecycle.py:56-58` ("still used" now exits 1), `doctor` with issues exits 1. Each such change is named in the task that makes it.
- Output text unchanged except what exit codes (Q4) and consent (S3) require, plus the one licence note line (S5). Spelling follows the code ("license").
- No `autoescape=True`. No `# nosec` / `# nosemgrep` without a reason on the same line.
- One commit per task. Before every commit: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .` all clean.
- Commits and PRs: author `bijoaja` only, **no `Co-Authored-By` line, no "Generated with Claude Code" line** (user's standing rule; it overrides any tool-injected attribution text). Stage files by name; never `git add -A` (untracked `.claude/` must not be committed).
- Local commits per task are authorized by this plan. **Tell the user before any push or PR.** The user merges PRs.
- Windows bash tool output can be garbled; redirect long output to a file and Read it.

## Review Focus

Failure modes the spec implies that no finding's own test covers, most likely first. Each has a test in the task named in brackets.

1. `uninstall` of a plugin whose `dev` entry is a link to a source folder must leave that folder intact (junction handling of `shutil.rmtree` on Windows/Python 3.10 is unverified). [Task 2]
2. Near-miss names: `uninstall "myplugin/"`, `uninstall "./myplugin"`, `uninstall "a\\b"` must not delete anything. [Task 2]
3. Empty `manifest.yaml` (parses to `None`) in `install`/`apply` gives a clean one-line error, not a traceback. [Task 8]
4. A traversal name in `render_stub` must reject before writing any file, even for stubs that sort earlier. [Task 3]
5. Non-ASCII plugin/project names round-trip through `project.yaml` and `usage.json` on a non-UTF-8 locale. [Task 10]

---

### Task 0: Commit spec and plan (docs PR)

**Files:** `docs/superpowers/specs/2026-10-28-security-and-code-quality-hardening-design.md`, this plan.

- [ ] **Step 1:** Tell the user, then on branch `docs/security-hardening-spec` run `git add` for those two files only and `git commit -m "docs: add security and code quality hardening spec and plan"`.
- [ ] **Step 2:** After the user agrees, `git push -u origin docs/security-hardening-spec` and `gh pr create` (title "docs: security and code quality hardening spec and plan", body = 3-line summary, no attribution line). Stop; the user merges. Implementation branches from updated `main` as `fix/security-hardening`.

---

### Task 1: `utils/safe.py`

**Files:**
- Create: `src/pyartisan/utils/safe.py`
- Test: `tests/unit/test_safe.py`

**Interfaces:**
- Produces (all raise `pyartisan.core.exceptions.PyArtisanError`, message `Invalid {what}: {value!r}`):
  - `NAME_RE: re.Pattern[str]`
  - `validate_name(value: str, what: str = "name") -> str`
  - `safe_child(root: Path, *parts: str) -> Path`
  - `validate_clone_url(url: str, what: str = "URL") -> str`

- [ ] **Step 1: Write failing tests** in `tests/unit/test_safe.py`:
  - `test_validate_name_accepts`: parametrized `"blog"`, `"my.plugin"`, `"42-crud"`, `"a_b-c"`, `"x" * 100` return the value.
  - `test_validate_name_rejects`: parametrized `""`, `"."`, `".."`, `"a/b"`, `"a\\b"`, `"C:x"`, `"-x"`, `".x"`, `"x" * 101`, `"a b"`, `"a\n"` raise `PyArtisanError` (the `"a\n"` case proves `fullmatch`, not `match`/`$`).
  - `test_safe_child_inside`: `safe_child(tmp_path, "a", "b") == tmp_path / "a" / "b"`.
  - `test_safe_child_rejects`: parametrized `("..",)`, `("a", "..", "..")`, `(".",)`, `("",)`, `(str(tmp_path.parent),)` (absolute) raise `PyArtisanError`.
  - `test_safe_child_does_not_follow_links`: create `tmp_path/"reg"/"p"` as a symlink to `tmp_path/"outside"` (skip if `os.symlink` raises `OSError`); `safe_child(reg, "p")` returns `reg/"p"` without raising.
  - `test_validate_clone_url`: accepts `https://github.com/o/r.git`, `ssh://git@host/o/r.git`, `git@github.com:o/r.git`; rejects `-oProxyCommand=x`, `--upload-pack=x`, `http://h/r`, `file:///r`, `/local/path`, `C:\\r`, `https://h/r with space`, `""`.
- [ ] **Step 2:** Run `uv run pytest tests/unit/test_safe.py -v`. Expected: FAIL (module missing).
- [ ] **Step 3: Implement** `safe.py`. `safe_child`: build `candidate = os.path.normpath(os.path.join(root, *parts))` and `base = os.path.normpath(root)`; accept only when `candidate != base` and `Path(candidate).is_relative_to(base)`; return `Path(candidate)`. Never call `resolve()` (the `dev` link points outside the registry on purpose). `validate_clone_url`: `re.fullmatch(r"(https://|ssh://|git@[\w.-]+:)[^\s]+", url)`.
- [ ] **Step 4:** Run the file again. Expected: PASS.
- [ ] **Step 5:** Commit `feat: add name, path and clone URL validation helpers`.

---

### Task 2: Apply validation to plugin commands and registry sinks (S1)

**Files:**
- Modify: `src/pyartisan/cli/commands/plugin.py` (every command), `src/pyartisan/marketplace/core.py` (`_usage_file`, `_find_registry_dir`)
- Test: `tests/cli/test_plugin_remove_uninstall.py`, `tests/cli/test_plugin_install.py`, `tests/cli/test_plugin_init.py`, `tests/cli/test_plugin_inspect.py`, `tests/unit/test_marketplace.py` (new)

**Interfaces:**
- Consumes: Task 1 helpers.
- Produces in `plugin.py`: `_valid(value: str, what: str) -> str` (calls `validate_name`, converts `PyArtisanError` to `click.ClickException`, exit 1).
- `marketplace/core.py`: `_usage_file` and `_find_registry_dir` build paths with `safe_child(plugins_registry, plugin_id[, version])` and let `PyArtisanError` propagate.

- [ ] **Step 1: Write failing tests.** Fixture: `plugin_project` plus a registry plugin `myplugin` installed via `install myplugin --local <src>`; sentinel file `home/.pyartisan/config.toml`.
  - `test_uninstall_rejects_unsafe_names` (parametrized `".."`, `"../x"`, absolute path of `home`, `"myplugin/"`, `"./myplugin"`, `"a\\b"`): `exit_code != 0`; sentinel and `plugins/myplugin` still exist. *(Review Focus 2.)*
  - `test_uninstall_keeps_dev_source`: after `uninstall myplugin` (exit 0), the local source dir and its `manifest.yaml` still exist. *(Review Focus 1.)*
  - `test_uninstall_all_still_works`: `uninstall --all` removes two installed plugins.
  - `test_install_rejects_bad_names`: `install .. --local src`, `install ../x --local src`, `install owner/..`, `install owner/.`, `install ../x/y` all exit non-zero; `subprocess.run` monkeypatched to fail the test if called; nothing created outside `plugins/`.
  - `test_install_accepts_dotted_and_numeric_ids`: `install my.plugin --local src` and `install 42-crud --local src` exit 0.
  - `test_init_rejects_traversal_name`: `plugin init ../evil` exits non-zero, no directory created.
  - `test_tampered_project_entries`: project.yaml `plugins: ["../x@1"]`, with `home/.pyartisan/x/` as a sentinel dir: `status` exits 0 and prints `✖` plus `invalid`; `doctor` prints `✖`; `remove --all` leaves the sentinel intact and keeps the entry in project.yaml.
  - `tests/unit/test_marketplace.py`: `_usage_file(reg, "../x")` and `_find_registry_dir(reg, "..", "1")` raise `PyArtisanError`; `_find_registry_dir(reg, "ok", "../..")` raises.
- [ ] **Step 2:** Run those tests. Expected: FAIL (the `..` uninstall test also reproduces the deletion; run it only against a sandbox HOME, which `fake_home` provides).
- [ ] **Step 3: Implement.**
  - `init`, `install` (whole `name` for `--local`/`--license`; both `owner` and `repo` segments for community), `apply`, `update`, `info`: first line `_valid(name, "plugin id")`. `remove` names are only compared, not used as paths.
  - `uninstall`: build `installed = {d.name for d in registry.iterdir() if d.is_dir()}`; a name in `installed` proceeds through `safe_child` (legacy ids the regex rejects stay removable); a name not in it that fails `validate_name` raises `ClickException`; otherwise keep the existing "not found" warning.
  - `status`, `doctor`, `remove`: wrap `_find_registry_dir` per entry in `try/except PyArtisanError`; print `✖ {entry} (invalid plugin entry)`; `status`/`doctor` mark not-ok, `remove` skips the entry and keeps it in the list.
  - Replace every `plugins_registry / name` that feeds `rmtree`, `unlink`, `mkdir`, link creation with `safe_child`.
  - Leave exit codes of existing "not found"/"not a project" paths alone (Task 11).
- [ ] **Step 4:** Run `uv run pytest tests/cli tests/unit/test_marketplace.py -v`. Expected: PASS. If `test_uninstall_keeps_dev_source` fails on Windows, unlink every `_is_link` child of `plugin_root` with `_remove_link` before `rmtree`.
- [ ] **Step 5:** Commit `fix: validate plugin ids and contain registry paths (uninstall .. deleted ~/.pyartisan)`.

---

### Task 3: Contain rendered output; validate `make`/`new` names (S2)

**Files:**
- Modify: `src/pyartisan/renderer/__init__.py`, `src/pyartisan/core/engine.py` (`dispatch_make`, `dispatch_new`)
- Test: `tests/unit/test_renderer.py`, `tests/cli/test_make.py`

**Interfaces:**
- Consumes: `validate_name`, `safe_child`.
- `render_stub` signature unchanged; raises `PyArtisanError` when any rendered destination is outside `dest_dir`.

- [ ] **Step 1: Write failing tests.**
  - `test_render_stub_rejects_escape` (renderer): stub `{{name_lower}}_c.py.jinja`, `name_lower="../../../escaped"`; `pytest.raises(PyArtisanError)`; nothing exists outside `dest_dir`.
  - `test_render_stub_rejects_before_writing_anything` *(Review Focus 4)*: stubs `a_ok.py.jinja` and `{{evil}}.py.jinja` with `evil="../x"`; after the raise, `dest_dir` does not exist or is empty.
  - `test_make_rejects_traversal_name` (CLI, existing manifest fixture in `test_make.py`): `make controller ../../escaped` exits 1; no file outside the project.
  - `test_make_rejects_nested_name`: `make controller admin/user` exits 1.
  - `test_make_rejects_manifest_dest_escape`: manifest generator with `dest: "../../out"` exits 1, nothing written.
  - `test_new_rejects_bad_project_name`: `new flask ../x` exits 1 before any `subprocess.run` call.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3: Implement.** `render_stub`: first pass renders and collects `(dest_file_path, template_rel)`, checks `dest_file_path.resolve().is_relative_to(dest_dir.resolve())`, raises `PyArtisanError`; second pass writes. `dispatch_make`: `validate_name(name, "name")` first; build `stub_dir`, `dest_dir` and the registration `target_file` with `safe_child(cwd, ...)`. `dispatch_new`: `validate_name(project_name, "project name")` before the exists check.
- [ ] **Step 4:** Run `uv run pytest -v`. Expected: PASS.
- [ ] **Step 5: Smoke against real templates.** Write `smoke_templates.py` in the scratchpad (not committed): for each of `D:\my_project\template-pyartisan\flaskiq` and `fastiq`, copy to a temp dir, then for every generator in `.pyartisan/manifest.yaml` run `pyartisan make <target> Sample` in a fresh copy and record exit code, stderr and the file tree with contents. Run it on `main` (git worktree) and on this branch into two directories; `diff -r` must be empty. Any difference blocks the commit.
- [ ] **Step 6:** Commit `fix: reject names and manifest paths that escape the project`.

---

### Task 4: Clone URL policy and `--` (S6)

**Files:**
- Modify: `src/pyartisan/cli/commands/config.py`, `src/pyartisan/core/engine.py` (`dispatch_new`), `src/pyartisan/cli/commands/plugin.py` (`install` clone)
- Test: `tests/unit/test_config.py`, `tests/cli/test_make.py` or a new `tests/unit/test_engine_new.py`

**Interfaces:** Consumes `validate_clone_url`, `validate_name`.

- [ ] **Step 1: Write failing tests.**
  - `test_config_set_rejects_bad_template_url`: `config set templates.flask -oProxyCommand=x`, `http://h/r`, `/local/dir` exit non-zero; config unchanged.
  - `test_config_set_accepts_good_urls`: `https://...`, `ssh://...`, `git@github.com:o/r.git` exit 0.
  - `test_config_set_rejects_bad_sub_key`: `config set templates.../x https://h/r` exits non-zero.
  - `test_dispatch_new_rejects_tampered_config`: write `templates.flask = "--upload-pack=x"` straight into `config.toml`; `new flask app` exits 1 and the monkeypatched `subprocess.run` is never called.
  - `test_clone_uses_double_dash`: monkeypatch `subprocess.run`, `new flask app` with a valid https URL; first call's argv ends with `["--", url, "app"]`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3: Implement.** `config set` for `templates.*`: `validate_name(sub)` and `validate_clone_url(value)`, errors as `click.ClickException`. `dispatch_new`: `validate_clone_url(repo_url, "template URL")` before cloning. Both `git clone` calls (engine, plugin install) get `"--"` before the positional arguments. Update any existing test fixtures that store non-URL template values.
- [ ] **Step 4:** Run `uv run pytest -v`. Expected: PASS.
- [ ] **Step 5:** Commit `fix: validate clone URLs and pass -- to git clone`.

---

### Task 5: Sandboxed Jinja factory (S4)

**Files:**
- Modify: `src/pyartisan/renderer/__init__.py`, `src/pyartisan/core/engine.py` (3 sites), `src/pyartisan/core/plugin_engine.py`, `src/pyartisan/core/registration.py`
- Test: `tests/unit/test_renderer.py`

**Interfaces:**
- Produces: `make_env(**kwargs: Any) -> jinja2.sandbox.SandboxedEnvironment` in `pyartisan.renderer`; `**kwargs` passes through (`loader=`, `keep_trailing_newline=`). No `autoescape`.

- [ ] **Step 1: Write failing tests.**
  - `test_make_env_blocks_dunder_access`: `make_env().from_string("{{ ''.__class__.__mro__ }}").render()` raises `jinja2.exceptions.SecurityError`.
  - `test_make_env_keeps_quotes_unescaped`: `make_env().from_string('{{ x }}').render(x='"a"') == '"a"'`.
  - `test_render_stub_output_unchanged`: existing two render tests stay as the golden compare.
- [ ] **Step 2:** Run. Expected: FAIL (`make_env` missing).
- [ ] **Step 3: Implement** `make_env` and replace all six `Environment(...)` sites (`engine.py` 3, `plugin_engine.py`, `registration.py`, `renderer`). Remove the now-unused `jinja2.Environment` imports.
- [ ] **Step 4:** Run `uv run pytest -v`. Expected: PASS.
- [ ] **Step 5:** Re-run the Task 3 step 5 smoke script against the branch and `diff -r` with the `main` output. Any difference blocks the commit: fix the stub or relax the sandbox with a written reason.
- [ ] **Step 6:** Commit `fix: render all templates through a sandboxed Jinja environment`.

---

### Task 6: Broken manifest warning (S7), Bandit config and CI (S8)

Folded S7 here so the Bandit gate is green: B110 at `engine.py:105` would otherwise fail it.

**Files:**
- Modify: `src/pyartisan/core/engine.py`, `pyproject.toml`, `uv.lock`, `.github/workflows/ci.yml`, `CLAUDE.md`, `docs/en/CONTRIBUTING.md`, `docs/id/CONTRIBUTING.md`
- Test: `tests/unit/test_engine_new.py` (new)

**Interfaces:**
- Produces in `engine.py`: `_template_meta(manifest_path: Path, default_name: str, default_version: str) -> tuple[str, str]`; returns defaults and `click.echo`s `⚠ Could not read template manifest: {reason}. Using defaults.` on `OSError`, `yaml.YAMLError`, or non-dict content. `dispatch_new` calls it.

- [ ] **Step 1: Write failing tests.** `test_template_meta_reads_id_and_version`; `test_template_meta_warns_on_broken_yaml` (content `": ["`: returns defaults, captured output contains `Using defaults`); `test_template_meta_warns_on_non_mapping` (content `"- a\n"`); `test_template_meta_missing_file_returns_defaults`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3: Implement** `_template_meta` and use it in `dispatch_new` (opens with `encoding="utf-8"`). Add `bandit[toml]>=1.7` to the dev group via `uv add --dev "bandit[toml]>=1.7"`. Add to `pyproject.toml` exactly the `[tool.bandit]` block from spec 3.4 (`exclude_dirs = ["tests"]`, `skips = ["B404", "B603", "B607"]`, with the written reason as a comment). Add to the `lint` job after the Ruff steps: `- name: Bandit` / `run: uv run bandit -q -r src -c pyproject.toml`.
- [ ] **Step 4:** Run `uv run bandit -q -r src -c pyproject.toml`. Expected: only B701 on the `make_env` line, or nothing. If B701 remains, add `# nosec B701  # sandboxed; autoescape would corrupt generated source` on that one line and rerun until clean. Run `uvx semgrep --config p/python --config p/security-audit src`; record the result for the PR body (Semgrep stays local).
- [ ] **Step 5:** Document in `CLAUDE.md` and `docs/en|id/CONTRIBUTING.md`: the Bandit command, the Semgrep command, and the rule that every `# nosec` carries a reason.
- [ ] **Step 6:** Run the full gate. Commit `ci: add Bandit to lint job; warn on unreadable template manifest`.

---

### Task 7: Mypy real bugs (Q6)

**Files:**
- Modify: `src/pyartisan/core/registration.py:8`, `src/pyartisan/marketplace/core.py` (`_load_hooks`, `_resolve_plugin_version`)
- Test: `tests/unit/test_marketplace.py`, `tests/unit/test_registration.py`

**Interfaces:**
- `apply_registration(..., marker: str | None = None, line_template: str | None = None)`.
- `_load_hooks` raises `ImportError(f"Cannot load hooks from {hooks_file}")` when `spec` or `spec.loader` is `None`.
- `_resolve_plugin_version(plugin_root: Path) -> str | None` (callers in `plugin.py` already test `not version`).

- [ ] **Step 1: Write failing tests.** `test_load_hooks_raises_when_spec_missing` (monkeypatch `importlib.util.spec_from_file_location` to return `None`; `pytest.raises(ImportError)`); `test_resolve_plugin_version_empty_dir_returns_none`; `test_marker_registration_without_marker_is_noop` (`marker=None` returns without writing).
- [ ] **Step 2:** Run. Expected: the first FAIL (`AttributeError`), others PASS.
- [ ] **Step 3: Implement** the signatures above.
- [ ] **Step 4:** Run `uvx mypy --check-untyped-defs src`. Expected: 0 errors (was 6). Run `uv run pytest -v`.
- [ ] **Step 5:** Commit `fix: handle None spec, None version and implicit Optional (Mypy baseline)`.
- [ ] **Step 6: PR A checkpoint.** Run the full gate and `git diff --stat main`. Report the changed-line count to the user. If the total plan will exceed about 600 lines, tell the user, then push `fix/security-hardening` and open PR A (Tasks 1-7); after the user merges, branch PR B from updated `main`. PR body lists the behavior changes: nested names rejected by `make`/`new`; clone URL schemes restricted; Bandit added to CI. No attribution line.

---

### Task 8: Hook consent (S3) and failing-hook handling (Q5)

**Files:**
- Modify: `src/pyartisan/cli/commands/plugin.py` (`apply`, `update`, `remove`), `docs/en/HOW_TO_CREATE_PLUGIN.md`, `docs/id/HOW_TO_CREATE_PLUGIN.md`, `docs/en/CLI.md`, `docs/id/CLI.md`
- Test: `tests/cli/test_plugin_lifecycle.py`

**Interfaces:**
- Produces: `_confirm_hooks(plugin_id: str, version: str, plugin_dir: Path, assume_yes: bool) -> None`. Returns silently when `plugin_dir / "hooks.py"` is absent, `plugin_dir.name == "dev"`, or `assume_yes`. Otherwise `click.confirm` (default `False`) showing id, version and the hooks.py path with the text that it runs Python with the user's privileges; refusal, EOF (`click.Abort`) or non-interactive stdin raises `click.ClickException("Plugin hooks were not approved. Re-run with --yes to allow them.")`.
- `apply`, `update`, `remove` gain `--yes` (parameter `yes`). `update` forwards it to `ctx.invoke(apply_cmd, name=name, yes=yes)`.

Fixture for these tests: a helper that writes `home/.pyartisan/plugins/<id>/1.0.0/{manifest.yaml,hooks.py}` directly (a non-`dev` dir, no git needed); `hooks.py` appends a line to a marker file at **module level** and defines `before_install`.

- [ ] **Step 1: Write failing tests.**
  - `test_apply_without_yes_and_no_input_aborts`: exit 1, marker file absent (module-level code did not run, so consent happens before `_load_hooks`), `project.yaml` has no plugin entry, no `usage.json`.
  - `test_apply_declined_prompt_aborts`: `input="n\n"`, same assertions.
  - `test_apply_accepts_prompt`: `input="y\n"`, exit 0, marker file written.
  - `test_apply_yes_flag_skips_prompt`.
  - `test_dev_link_runs_hooks_without_prompt`: `install --local` plugin with hooks, `apply` with no input, exit 0.
  - `test_plugin_without_hooks_no_prompt`.
  - `test_remove_asks_per_plugin`: two registry plugins with hooks, `remove --all` with `input="y\nn\n"`: first removed, second aborts exit 1 and its entry stays.
  - `test_update_reapply_asks_again`: git-less variant: monkeypatch `subprocess.run`, plugin dir contains `.git`; `update` with no `--yes` and no input exits 1; with `--yes` re-applies.
  - `test_failing_hook_leaves_project_unchanged`: `hooks.py` `before_install` raises `RuntimeError("boom")`, `apply --yes`: exit 1, output contains `boom` and `not rolled back`, `project.yaml` unchanged, no `usage.json`.
  - `test_apply_bad_manifest_id`: manifest `id: ../x` and a manifest missing `id`: exit 1, no hook run, no file outside registry.
  - `test_empty_manifest_is_clean_error` *(Review Focus 3)*: empty `manifest.yaml` for `install --local` and for `apply`: exit 1, output has no `Traceback`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3: Implement.** Call `_confirm_hooks` before `_load_hooks` in `apply` and per plugin in `remove`. In `apply`: after loading the manifest, treat `None`/non-dict as an error, require a present valid `id` (`_valid(str(...), "manifest id")`) and use that value for the `project.yaml` entry and `_record_usage`; wrap hook calls and `add_dependency` in `try/except Exception as e` raising `ClickException(f"Plugin failed: {e}. Files already written were not rolled back.")` so neither `project.yaml` nor `usage.json` is written. Apply the empty-manifest check to `install` too.
- [ ] **Step 4:** Update the four docs: `--yes` on `apply|update|remove`, consent behavior, `install --local`/`dev` links are trusted (known limit), `docs/*/HOW_TO_CREATE_PLUGIN.md` advice to commit only reviewed hooks.
- [ ] **Step 5:** Run `uv run pytest -v`. Expected: PASS.
- [ ] **Step 6:** Commit `feat: ask before running plugin hooks; fail cleanly when a hook raises`.

---

### Task 9: Version ordering (Q1), dependency matching (Q2), missing stub (Q3)

**Files:**
- Modify: `src/pyartisan/marketplace/core.py`, `src/pyartisan/core/plugin_engine.py`, `src/pyartisan/cli/commands/plugin.py` (`doctor`), `docs/en/HOW_TO_CREATE_PLUGIN.md`, `docs/id/HOW_TO_CREATE_PLUGIN.md`
- Test: `tests/unit/test_marketplace.py`, `tests/unit/test_plugin_engine.py`

**Interfaces:**
- `_version_key(version: str) -> tuple` returning `(core, is_release, pre)` where `core` is a tuple of `(0, int)` / `(1, str)` per dot segment, `is_release` is `1` when there is no `-` suffix and `0` otherwise, `pre` is the suffix text.
- In `plugin_engine.py`: `requirement_name(spec: str) -> str` (text before the first of `<>=!~[; ` , lower-cased, `_` and `.` mapped to `-`); `has_requirement(content: str, spec: str) -> bool` (compares `requirement_name` of `spec` with that of every non-blank, non-comment, non-`-` line of `content`). `add_dependency` and `doctor` both use it.
- `create_service` raises `ManifestError(f"Stub not found: {stub_path}")` when the file does not exist; a relative `stub_path` still resolves from the current directory; the dead `is_absolute` branch is deleted.

- [ ] **Step 1: Write failing tests.**
  - `test_latest_version_mixed`: `_latest_version(["1.0.0", "1.0.0-beta", "dev", "2.0"]) == "2.0"` (no `TypeError`); `_latest_version(["1.0.0-beta", "1.0.0"]) == "1.0.0"`; `_latest_version(["1.2.0", "1.10.0"]) == "1.10.0"`.
  - `test_has_requirement`: `has_requirement("flask-cors==4\n", "flask")` is `False`; `("Flask>=2\n", "flask")` is `True`; `("my_pkg\n", "my-pkg")` is `True`; `("# flask\n", "flask")` is `False`; `("flask[async]\n", "flask>=2")` is `True`.
  - `test_add_dependency_not_fooled_by_substring`: requirements `flask-cors\n`; `add_dependency("flask")` appends `flask`.
  - `test_add_dependency_idempotent`: calling twice adds one line.
  - `test_doctor_flags_missing_dep_with_similar_name` (CLI, extend `test_plugin_inspect.py`): requirements has `httpx-extra`, plugin needs `httpx`: output shows `missing httpx`.
  - `test_create_service_missing_stub_raises`: `pytest.raises(ManifestError)`; no dest file created.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3: Implement** per the Interfaces block.
- [ ] **Step 4:** Update `docs/*/HOW_TO_CREATE_PLUGIN.md` line ~182 (and the matching tip near line 153): a missing `stub_path` now raises an error instead of writing nothing; a relative path is still resolved from the current directory.
- [ ] **Step 5:** Run `uv run pytest -v`. Expected: PASS.
- [ ] **Step 6:** Commit `fix: version ordering, exact dependency matching, error on missing stub`.

---

### Task 10: Cleanups (Q7), licence note (S5), explicit UTF-8 (S9)

**Files:**
- Modify: `src/pyartisan/core/plugin_engine.py`, `src/pyartisan/core/engine.py`, `src/pyartisan/cli/commands/plugin.py`, `src/pyartisan/marketplace/core.py`, `src/pyartisan/core/registration.py`, `src/pyartisan/utils/fs.py`, `docs/en/CLI.md`, `docs/id/CLI.md`
- Test: `tests/cli/test_plugin_install.py`, `tests/unit/test_installer_selection.py`, `tests/cli/test_plugin_init.py`

- [ ] **Step 1: Write failing tests.**
  - `test_install_license_prints_stub_note`: output contains `offline stub` and still contains `license ownership successfully verified` (existing assertion at `test_plugin_install.py:9`).
  - `test_new_does_not_change_cwd` (monkeypatch `subprocess.run`, `click.confirm` returning `True`): `os.getcwd()` is unchanged after `dispatch_new`, and every post-clone `subprocess.run` call received `cwd=project_name`.
  - `test_non_ascii_manifest_text_roundtrip` *(Review Focus 5)*: ids stay ASCII (`validate_name` rejects `café`), but a manifest with `name: "Café"` and `description: "naïve"` written as UTF-8 goes through `install --local`, `apply --yes`, `info`: output contains `Café` and `naïve`, `project.yaml` and `usage.json` decode as UTF-8. Run the sequence in a subprocess (`sys.executable -X warn_default_encoding -W error::EncodingWarning -c ...` driving `CliRunner`, `HOME` pointing at a temp dir): any `open()`, `read_text()` or `write_text()` without `encoding=` raises `EncodingWarning` and fails the test on every OS, which a monkeypatched locale cannot do.
  - Q7 ternary needs no test (identical branches).
- [ ] **Step 2:** Run. Expected: FAIL (the first two).
- [ ] **Step 3: Implement.** Q7: replace the identical ternary in `register_router` with the plain assignment; delete `os.chdir(project_name)` in `dispatch_new` and pass `cwd=project_name` to the venv, install-plan and install subprocess calls (use `Path(project_name)` for `_detect_install_plan`). S5: print the extra line `Note: license verification is an offline stub, no network check is performed.` before the existing "Verifying" line. S9: add `encoding="utf-8"` to every `open()`, `read_text()` and `write_text()` in `plugin.py`, `marketplace/core.py`, `plugin_engine.py`, `registration.py`, `engine.py`, `utils/fs.py`. Document the stub note in `docs/en|id/CLI.md`.
- [ ] **Step 4:** Run `uv run pytest -v`. Expected: PASS on Linux, macOS and Windows locally available.
- [ ] **Step 5:** Commit `fix: stop chdir in new, label the license stub, read and write files as UTF-8`.

---

### Task 11: Exit codes (Q4)

**Files:**
- Modify: `src/pyartisan/cli/commands/plugin.py`
- Test: `tests/cli/test_plugin_lifecycle.py`, `tests/cli/test_plugin_inspect.py`, `tests/cli/test_plugin_remove_uninstall.py`, `tests/cli/test_plugin_install.py`, `tests/cli/test_plugin_init.py`

**Rule per site** (spec 3.5): the command exits 1 when it could not do what was asked.

| Site | Behavior |
|---|---|
| "Not a pyartisan project" in `apply`, `remove`, `list`, `status`, `doctor` | `raise click.ClickException(...)` |
| `init` directory exists; `install` local path missing, invalid license, bad GitHub path, clone failure, missing `manifest.yaml`; `apply`/`info` plugin not found, no installed version, missing manifest | `raise click.ClickException(...)` |
| `remove`, `uninstall` loops; `update` per version dir | keep going, remember a failure flag, `raise click.exceptions.Exit(1)` after the loop. "Still used by" and "not found" in `uninstall` count as failures |
| `update`, `info` single-plugin not found | `ClickException` |
| `doctor` with `all_ok` false | `raise click.exceptions.Exit(1)` after printing the summary |
| `status` with issues | stays 0 (a view) |
| "No plugins to remove", "No plugins specified", "No plugins installed", "No updatable plugin sources found" | stay 0 |

Keep each message text; the `❌` prefix may go because `ClickException` prints `Error: ...`.

- [ ] **Step 1: Write failing tests** (one per row group, asserting `exit_code` and a key substring of `result.output.lower()`):
  - `test_uninstall_in_use_exits_1`: change the existing lifecycle assertion at `test_plugin_lifecycle.py:57` to `exit_code == 1` while keeping `"still used by"`.
  - `test_uninstall_missing_exits_1`; `test_uninstall_multi_continues_and_exits_1`: `uninstall nope myplugin` removes `myplugin` and exits 1.
  - `test_remove_multi_continues_and_exits_1`: one entry with a tampered id, one valid: valid entry removed, exit 1.
  - `test_doctor_with_issues_exits_1` (extends the case at `test_plugin_inspect.py:62`); `test_doctor_ok_exits_0`.
  - `test_status_with_issues_exits_0`.
  - `test_not_a_project_exits_1` parametrized over `apply x`, `remove x`, `list`, `status`, `doctor`.
  - `test_install_failures_exit_1` parametrized over missing local path, bad license, bad GitHub path, missing manifest.
  - `test_init_existing_dir_exits_1`; `test_apply_unknown_plugin_exits_1`; `test_info_unknown_plugin_exits_1` (update the existing case near `test_plugin_inspect.py:26`).
  - `test_update_pull_failure_exits_1` and `test_update_only_dev_links_exits_0`.
  - `test_empty_states_exit_0`: `remove` with nothing matching, `uninstall` with no names, `list` with no plugins.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3: Implement** the table.
- [ ] **Step 4:** Run `uv run pytest -v`. Expected: PASS. Grep `tests/` for remaining `exit_code == 0` next to failure messages and fix any that now fail.
- [ ] **Step 5:** Commit `fix: plugin commands exit non-zero on failure`.

---

### Task 12: Final gate and PR

- [ ] **Step 1:** Run on a clean tree: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run bandit -q -r src -c pyproject.toml`, `uvx mypy --check-untyped-defs src` (0 errors), `uvx semgrep --config p/python --config p/security-audit src` (record output).
- [ ] **Step 2:** Re-run the smoke script from Task 3 step 5 once more; the diff against `main` must be empty.
- [ ] **Step 3:** Re-run the sandbox reproductions (`uninstall ..`, `make ../../../escaped`) against the branch: both must now fail with exit 1 and leave the sandbox intact.
- [ ] **Step 4:** Tell the user, then push and open the PR (PR B if Task 7 already shipped as PR A). Body: summary, finding → commit table, Bandit/Semgrep/Mypy results, a "Behavior changes" list (nested names rejected; clone URL schemes restricted; hook consent prompt and `--yes`; failures exit 1; `doctor` exits 1 on issues; `create_service` raises on a missing stub), and the smoke-diff result. No attribution line. The user merges.
- [ ] **Step 5:** Stop. The Mypy annotation PR (`2026-10-28-mypy-implementation-plan.md`) waits for the user's command; its baseline is now 0 real bugs and about 25 missing-annotation errors.
