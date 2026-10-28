# Security and Code Quality Hardening — Design Spec (pyartisan)

Date: 2026-10-28
Status: Draft, awaiting approval (no implementation yet)

Scope: `src/pyartisan/` only. Template repos (flaskiq, fastiq) get their own analysis later.
This spec covers security findings and real bugs. The Mypy rollout is a **separate** spec/plan
(`2026-10-28-mypy-implementation-plan.md`) and ships as a separate PR afterwards.

## 1. Summary

Four analyses were run on `src/pyartisan/` on 2026-10-28: Bandit 1.9.4, Semgrep (`p/python`,
`p/security-audit`), Mypy (two configs) and a manual review of every module except
`templates/plugin_init/`. They were not run in CI; there is no baseline in the repo yet.

| Tool | Result |
|---|---|
| Bandit | 40 issues: 6 High (all B701), 34 Low (B404/B603/B607/B110), 0 Medium |
| Semgrep | 6 findings, all `missing-autoescape-disabled` |
| Mypy `--check-untyped-defs` | 6 errors in 2 files |
| Mypy `--disallow-untyped-defs` | 31 errors in 8 files |

The tools mostly flag the wrong things. The two worst problems are **not** reported by any tool and
were found by review, then **reproduced in a sandbox** (fake `HOME`, temp dirs):

- `pyartisan plugin uninstall ..` deleted the whole `~/.pyartisan` of the sandbox HOME and exited 0.
- `render_stub` with name `../../../escaped` wrote a file outside the destination directory.

### 1.1 Findings by severity

Legend: **V** = reproduced by running it, **R** = established by reading code (the plan must write a
failing test first, which doubles as verification), **T** = reported by a tool.

| ID | Sev | Finding | Where | Evidence |
|---|---|---|---|---|
| S1 | High | Plugin id / name not validated; `uninstall ..` runs `rmtree` outside the registry | `cli/commands/plugin.py:160,374-386`, also `install --local`, `apply`, `info` | V |
| S2 | Medium | `make`/`plugin init` name not validated; stub renders outside `dest_dir` | `renderer/__init__.py:22-37`, `core/engine.py:190-217`, `utils/naming.py` | V |
| S3 | Medium | Plugin `hooks.py` executed on `apply`/`remove` with no consent, including `git clone`d community plugins | `marketplace/core.py:63-72`, `plugin.py:224,334` | R |
| S4 | Medium | Jinja `Environment()` is unsandboxed and renders strings from manifests/plugins/stubs (6 sites) | `engine.py:207,216,240`, `plugin_engine.py:84`, `registration.py:75`, `renderer:16` | T+R |
| S5 | Medium | `_verify_blockchain_license` accepts any key starting `valid-`; `install --license` writes a fake manifest | `marketplace/core.py:75`, `plugin.py:136-152` | R |
| S6 | Low | `git clone <url> <name>` without `--`; a value starting with `-` is parsed as an option (`project_name`, config `templates.*`, plugin repo) | `engine.py:81`, `plugin.py:168`, `cli/commands/config.py:38-42` | R |
| S7 | Low | `except Exception: pass` hides a broken manifest and silently uses defaults | `engine.py:105` | T |
| S8 | Low | 34 subprocess notices (B404/B603/B607): argv lists, no `shell=True`, constant executables | many | T |
| S9 | Low | `open()` without `encoding=` (Windows locale), mixed `Path.read_text()` | `plugin.py`, `fs.py`, `engine.py`, `plugin_engine.py`, `registration.py` | R |
| Q1 | Bug | `_version_key` mixes `int` and `str`; `1.0.0` vs `1.0.0-beta` raises `TypeError` | `marketplace/core.py:104` | R |
| Q2 | Bug | Dependency check is substring match: `flask` counts as present because of `flask-cors` | `plugin_engine.py:128`, `plugin.py:555` | R |
| Q3 | Bug | `create_service` never resolves relative `stub_path`; silently writes nothing; dead `if not absolute: pass` | `plugin_engine.py:75-86` | R |
| Q4 | Bug | Most plugin errors print and `return` → exit code 0; CI and scripts cannot detect failure | `plugin.py` (about 20 sites) | R |
| Q5 | Bug | `apply` runs hooks before persisting; a failing hook leaves partial state; `plugin_manifest['id']` can `KeyError` | `plugin.py:219-250` | R |
| Q6 | Type bug | Real Mypy errors: implicit `Optional` (2), `spec`/`loader` may be `None` (3), `-> str` returns `None` (1) | `registration.py:8`, `marketplace/core.py:70,71,87` | T |
| Q7 | Cleanup | Identical ternary branches; `os.chdir` mutates process state in `dispatch_new` | `plugin_engine.py:97`, `engine.py:124` | R |

### 1.2 Decisions this spec makes

These are my calls unless marked "needs your answer" (section 6).

1. **One validation point, defense in depth.** A single `validate_name()` (allowlist) at every
   command boundary, plus a containment check (`resolved.is_relative_to(root)`) at every
   delete/write sink. Either alone is not enough.
2. **Jinja: sandbox, not autoescape.** Autoescape would corrupt generated code (`"` → `&#34;`).
   Keep one `make_env()` factory in `renderer/` returning a `SandboxedEnvironment`, and use it at
   all six sites. Bandit/Semgrep may still flag it; if so, suppress with a reason (see 3.4).
3. **Subprocess notices are configured away, not edited away** (B404/B603/B607 skipped in Bandit
   config with the reason written next to the setting).
4. **Hooks need consent for non-local plugins.** Local `dev` links are trusted (the developer wrote
   them). Everything else prompts once, with `--yes` to skip. Needs your answer, see 6.
5. **Mypy bug fixes (Q6) land here**, because they are bugs. The annotation-only work (about 25
   errors) stays in the Mypy PR.
6. **Bandit joins CI** (`dev` dependency group + one step in the existing `lint` job). Semgrep stays a
   documented local command; it needs registry access and is slower.

### 1.3 Goals, non-goals, anti-goals

Goals
- No CLI input can delete or write outside the intended directory.
- Tool noise is either fixed or suppressed with a written reason; the scan is then clean and gated.
- Every finding has a test that fails before the fix and passes after.

Non-goals
- Sandboxing or signing plugins (real marketplace trust model, commit pinning, checksums). S3 only adds consent.
- Replacing the license stub with a real blockchain check (S5 only stops it posing as real).
- Type annotations beyond Q6 (Mypy PR).
- Hardening flaskiq/fastiq.

Anti-goals
- Blanket `# nosec` / `# nosemgrep` without a reason on the same line or in config.
- Enabling Jinja `autoescape=True` to make the scanner quiet.
- Changing user-visible output text beyond what exit codes (Q4) and consent (S3) require.

## 2. Constraints

- Python 3.10+; Windows, Linux, macOS (CI matrix). Path checks must work with junctions and `\`.
- No new runtime dependencies. `bandit` goes only into `[dependency-groups] dev`.
- Existing 24 tests must stay green; behavior changes (Q4 exit codes, S3 prompt) update tests deliberately and are called out in the PR description.
- One commit per finding group so the diff can be reviewed finding by finding.
- Author `bijoaja` only; no co-author or generated-by lines.

## 3. Design

### 3.1 Name validation and containment (S1, S2, S6)

New `src/pyartisan/utils/safe.py`:

```python
# One path segment: starts alphanumeric, then letters, digits, '.', '_', '-'.
# GitHub repo names (my.plugin, 42-crud) pass; '', '.', '..', '/', '\\', ':' do not.
NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}")

def validate_name(value: str, what: str = "name") -> str:
    """Return value if it is a single plain path segment, else raise PyArtisanError."""

def safe_child(root: Path, *parts: str) -> Path:
    """root/parts, resolved; raise PyArtisanError if it is not inside root."""
```

- `validate_name` is called in: `plugin init|install|apply|update|remove|uninstall|info` (plugin id), `make` (name) and `new` (project name).
- `make` and `new` accept a single segment only. Nested names such as `admin/user` and project paths such as `sub/app` are rejected (my call; today they only half-work because `name_parts` passes `/` through into class names). Mention in PR notes.
- `install owner/repo` validates both segments separately; plugin id is the repo segment.
- Untrusted ids that do not come from the command line are checked at the sink instead: `manifest['id']` and the `plugins:` entries in `project.yaml` (used by `_record_usage`, `_find_registry_dir`, `status`, `doctor`, `remove`) go through `validate_name`/`safe_child` before building any registry path.
- `safe_child` replaces `plugins_registry / name` before every `rmtree`, `unlink`, `mkdir`, link creation. It checks the **lexical** path before any `resolve()`, so the `dev` link, which deliberately points outside the registry, is never rejected for where it points. Existing registry entries with names the regex rejects can still be removed with `uninstall` because `uninstall` only requires the name to be a single segment found by `iterdir()` of the registry.
- `render_stub` checks each `dest_file_path.resolve()` is inside `dest_dir.resolve()` before `write_file`. This covers values that arrive from manifest `dest`/`paths` and not only the name.
- Clone URLs: `git clone` gets `--` before positional args. `config set templates.*` and `dispatch_new` (which reads `config.toml`, editable by hand) share one `validate_clone_url()`. Allowed schemes are in section 6, item 3.

### 3.2 Hook consent (S3)

`_load_hooks` itself stays a pure loader (and gets `None` checks for Q6). The consent decision lives in
`plugin.py`: a small `_confirm_hooks(plugin_id, version, plugin_dir, assume_yes)` called before the
first hook of an `apply` or `remove` run.

- Prompt **once per command invocation per plugin** (`remove --all` asks per plugin that has a
  `hooks.py`). Nothing is remembered between runs; no state file.
- No `hooks.py` in the plugin: no prompt.
- `dev` links are trusted without a prompt (the developer owns them). `install --local <path>` creates
  a `dev` link, so a freshly cloned third-party repo installed that way is also trusted. Known
  limit, documented in `HOW_TO_CREATE_PLUGIN.md`; not solved here.
- `--yes` is added to `apply`, `update` and `remove`. `update` passes it through to its
  `ctx.invoke(apply_cmd, ...)` re-apply, so an update that pulls new hook code asks again.
- Non-interactive stdin without `--yes` aborts with a clear error and exit code 1.

### 3.3 Licence stub (S5)

`install --license` keeps its current output (including "License ownership successfully verified",
which `tests/cli/test_plugin_install.py:9` asserts) and gains one extra leading line: "Note: license
verification is an offline stub, no network check is performed." Documented as such in
`docs/*/CLI.md`. No change to the accepted-key rule. Spelling follows the code ("license").

### 3.4 Scanner configuration (S4, S8)

`pyproject.toml`:

```toml
[tool.bandit]
exclude_dirs = ["tests"]
# B404/B603/B607: every subprocess call passes an argv list, never shell=True,
# and runs fixed executables (git, uv, docker, python).
skips = ["B404", "B603", "B607"]
```

If `SandboxedEnvironment` is still reported as B701/Semgrep, suppress on that single factory line:
`# nosec B701  # sandboxed; autoescape would corrupt generated source`. Whether the scanners accept the
sandboxed class is **unverified**; the plan checks it first and chooses the suppression accordingly.
Bandit is installed as `bandit[toml]` so it can read `pyproject.toml` on Python 3.10.

**Sandbox compatibility gate.** `SandboxedEnvironment` blocks some attribute and method access
(for example `str.format` and underscore attributes). The golden compare on fixture stubs is not
enough, because the real stubs live in flaskiq and fastiq. Before the sandbox change is committed the
plan renders every generator of both template repos (`pyartisan new` into a temp dir, then every
`make <target> Sample`) with and without the sandbox and diffs the output. Any difference blocks the
change until the stub is fixed or the sandbox is relaxed with a documented reason.

### 3.5 Bugs (Q1-Q5, Q7)

| ID | Fix |
|---|---|
| Q1 | `_version_key` returns `(0, int)` / `(1, str)` tuples so mixed segments compare; pre-release sorts lower than release |
| Q2 | Parse requirement names with `re.split(r"[<>=!~\[; ]", line)[0].lower()`, compare normalized names (`_` ≡ `-`), in one shared helper used by `add_dependency` and `doctor` |
| Q3 | Delete the dead branch; `create_service` raises `ManifestError` when `stub_path` does not exist instead of silently doing nothing. Update `docs/en|id/HOW_TO_CREATE_PLUGIN.md`, which documents the silent no-op |
| Q4 | Rule per site, not blanket (see below) |
| Q5 | Order is already hooks, deps, then write `project.yaml`, so reordering is not the fix. The fix is small and explicit: check `id` is present and valid before running anything; wrap the hook calls so an exception prints the error, exits 1, and skips both the `project.yaml` write and `_record_usage`. **No rollback** of files a hook or `add_dependency` already wrote; the message says so. Real rollback is out of scope |

**Q4 rule.** The command fails (exit 1) when it could not do what was asked:
- "not found", "not a pyartisan project", "missing manifest.yaml", "no installed version", clone failure, invalid license: `raise click.ClickException(...)`.
- Loop commands (`remove`, `uninstall`, `update`) with several names: keep going, remember failures, exit 1 at the end if any item failed. "Still used by" in `uninstall` counts as a failure for that item.
- `doctor` exits 1 when it finds issues. `status` prints a report and stays 0 (it is a view; `doctor` is the check).
- "Nothing to do" messages (no plugins installed, only dev links to update) stay exit 0.
- Existing assertion `test_plugin_lifecycle.py:56-58` ("still used" with exit 0) is changed on purpose.
| Q7 | Collapse the ternary; replace `os.chdir` with `cwd=` on each subprocess |

### 3.6 Mypy real bugs (Q6)

`marker: str | None = None`, `line_template: str | None = None`; `_load_hooks` raises
`ImportError` if `spec` or `spec.loader` is `None`; `_resolve_plugin_version -> str | None` and its two
callers handle `None`. After this the Mypy baseline in the next PR drops from 6/31 to 0/about 25.

### 3.7 CI and docs

- `[dependency-groups] dev` += `bandit>=1.7`; `uv.lock` updated.
- `lint` job: add `uv run bandit -q -r src -c pyproject.toml`.
- `docs/en|id/CONTRIBUTING.md` and `CLAUDE.md`: Bandit command, Semgrep local command, rule for `# nosec` reasons.

## 4. Testing

Plan follows TDD: for each finding one test in the existing layout that fails first.

| Finding | Test (file) |
|---|---|
| S1 | `tests/cli/test_plugin_remove_uninstall.py`: `uninstall ..`, `uninstall ../x`, `uninstall /abs` leave registry intact and exit non-zero; `install --local ..` rejected |
| S2 | `tests/unit/test_renderer.py`: name with `../` raises, nothing written outside `dest_dir`; `tests/cli/test_make.py` same through CLI |
| S3 | `tests/cli/test_plugin_lifecycle.py`: git-sourced plugin without `--yes` and no TTY aborts; `dev` link runs hooks; `--yes` runs hooks |
| S4 | `tests/unit/test_renderer.py`: sandbox blocks `{{ ''.__class__ }}` style access; stub rendering output unchanged (golden compare) |
| S5 | `tests/cli/test_plugin_install.py`: warning text present |
| S6 | `tests/unit/test_config.py`: `templates.x` with leading `-` rejected |
| S7 | `tests/unit/test_manifest.py` / engine test: broken manifest during `new` warns and uses defaults |
| S9 | one test writing and reading a non-ASCII plugin name through a file under `LANG=C`-like encoding is not portable; covered by passing `encoding="utf-8"` and the existing Windows CI jobs |
| Q1 | `tests/unit/test_plugin_engine.py` (or new `test_versions.py`): `["1.0.0","1.0.0-beta","dev","2.0"]` |
| Q2 | `tests/unit/test_plugin_engine.py`: `flask` not satisfied by `flask-cors` |
| Q3, Q5 | `tests/unit/test_plugin_engine.py`, `tests/cli/test_plugin_lifecycle.py` |
| Q4 | assert `exit_code != 0` in the existing plugin CLI error tests |
| Q6 | covered by running Mypy with `--check-untyped-defs` in the PR description; not added to CI here |

Additional tests from review: `validate_name` accepts `my.plugin`, `42-crud`, rejects `.`, `..`, `a/b`, `a\b`, `C:x`, empty,
over-long; a tampered `project.yaml` plugin entry (`../x@1`) and a manifest with `id: ../x` are rejected by `status`,
`doctor`, `remove`, `apply`; `remove a b` with `a` failing still processes `b` and exits 1; a failing hook leaves
`project.yaml` unchanged and exits 1; `update` re-apply asks for consent again.

Gate before PR: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`,
`uv run bandit -q -r src -c pyproject.toml` all clean. Semgrep run locally and result pasted in the PR.

## 5. Order of work

1. `utils/safe.py` + S1 + S2 + S6 (the dangerous part; smallest reviewable commit first)
2. S4 `make_env()` factory + scanner config + Bandit in CI (S8)
3. Q6 type bugs
4. S3 consent, S5 warning
5. Q1, Q2, Q3, Q5, Q7, S7, S9
6. Q4 exit codes last, because it touches the most tests

Estimated size: about 15 files, mostly `plugin.py`; split into two PRs if the diff goes over about 600
changed lines (PR A = steps 1-3, PR B = steps 4-6).

## 6. Open questions (need your answer)

1. **Hook consent (S3).** Prompt for any non-`dev` plugin that has a `hooks.py` (my default), or only for plugins installed from GitHub?
2. **Exit codes (Q4).** The per-site rule in 3.5 changes behavior for anyone scripting `pyartisan plugin ...` (failures now exit 1, `doctor` exits 1 on issues). Accept as a bug fix in this PR (my default)?
3. **Clone URL policy (S6).** Allow `https://`, `ssh://` and `git@host:` URLs, reject `http://`, `file://`, local paths and anything starting with `-` (my default). A local template checkout would then need `https://` or a manual `config.toml` edit... which is also rejected by the same check in `dispatch_new`. Alternatively also allow existing local directories. Which?

## 7. Appendix: detail per finding

### S1 — reproduced

`plugin_root = plugins_registry / ".."` resolves to `~/.pyartisan`. `_all_usages` looks for
`plugin_root/usage.json`, which does not exist there, so the "still used" guard does not fire and
`shutil.rmtree(plugin_root)` runs. Sandbox run (fake `HOME`, real CLI via `CliRunner`): before →
`config.toml`, `plugins`; output `✔ Uninstalled '..' from registry.`, exit 0; after →
`.pyartisan` gone, sibling `outside.txt` untouched. Same root cause: `install owner/..` gives
`plugin_id == ".."` (`plugin.py:160`); `install --local ../x` / `init ../x` build
`plugins_registry / name / "dev"` and can `rmtree`/relink outside the registry.

### S2 — reproduced

`name_parts("../../../escaped")` returns `name_lower == "../../../escaped"` unchanged (it only lower-cases
and replaces `-`). A stub file named `{{name_lower}}_controller.py.jinja` rendered to
`<dest>/../../../escaped_controller.py`; the run wrote `escaped_controller.py` three levels above
`dest_dir`. `write_file` skips existing files unless `--force`, so the damage is write-new by default
and overwrite with `--force`.

### S3, S5

`hooks.py` runs with the user's full privileges. For `plugin install owner/repo` the code comes from
`https://github.com/owner/repo.git` at whatever HEAD is, and `plugin update` pulls new code that runs on
re-apply. Consent is the minimum; pinning/signing is out of scope. `_verify_blockchain_license`
returns `key.startswith("valid-")`; the "blockchain" messages in `install` read as real verification.

### S4

`autoescape` matters for HTML output and these templates generate Python/YAML/Markdown, so the
scanners' advice is wrong here. The real exposure is that manifest `stub_subpath`, `dest`, registration
`target` and stub bodies come from template repos and plugins; an unsandboxed template can reach
`__class__`/`__subclasses__`. `SandboxedEnvironment` blocks that class of access.

### Tool output reference

Bandit locations (all argv-list `subprocess.run`, no `shell=True`): `plugin.py:50,168,278`;
`engine.py:81,90,128,145,257,313,321,334,365`; `marketplace/core.py:128,134,140`; `doctor.py:20,33,53`.
B110 at `engine.py:105`. B701 at `engine.py:207,216,240`, `plugin_engine.py:84`, `registration.py:75`,
`renderer/__init__.py:16`.

Mypy `--check-untyped-defs`: `registration.py:8` (x2), `marketplace/core.py:70,71 (x2),87`.
Mypy `--disallow-untyped-defs` adds 25 missing-annotation errors in `cli/commands/plugin.py` (11),
`cli/commands/config.py` (4), `marketplace/core.py` (3), `core/plugin_engine.py` (3), `engine.py`,
`make.py`, `cli/__init__.py` — left to the Mypy PR.

### Not covered

`templates/plugin_init/` content, runtime behavior of generated projects, dependency CVEs (no
`pip-audit`/`uv audit` run yet), and the AWS Security Agent (MCP connection returned 401; it also
uploads source to AWS, so it needs an explicit decision).
