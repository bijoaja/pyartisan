# Project API Consolidation & Template Versioning — Design Spec

Date: 2026-07-22
Status: Approved for planning

## 1. Background

PyArtisan's PRD (`PRD.md` §"Struktur Project", layer `project/`) and the FastIQ/PyArtisan
architecture notes (`FastIQ.md` §10-13, `PyArtisan.md` Layer 4) both define a **Project API**:
a mediated interface that plugins and generators must use to touch project files, instead of
manipulating paths/files directly.

Investigation of the current codebase found this API already exists in practice, but split
across two divergent, undocumented implementations:

- `pyartisan/core/plugin_engine.py::ProjectContext` — a real, actively used class
  (`create_service`, `register_router`, `add_dependency`) consumed by `pyartisan plugin
  install/remove/doctor` and passed into plugin `hooks.py` as `project`. This *is* the Project
  API described in FastIQ.md, but it lives in `core/`, not in the `project/` package the PRD
  designates as its home.
- `pyartisan/core/engine.py::dispatch_make()` — the `pyartisan make:*` command path, which
  calls `render_stub()` and `apply_registration()` directly, bypassing `ProjectContext`
  entirely.
- `pyartisan/project/__init__.py` — the PRD-designated home for the Project API. Currently a
  placeholder with only a comment, unused anywhere.

Two additional gaps were found during design discussion:

- `template.yaml` (versioned per-template-release metadata read by `ProjectContext` from
  `~/.pyartisan/templates/<id>/<version>/template.yaml`) is **never written** anywhere in the
  codebase — only referenced by `smoke_test.py` via manual filesystem mocking. In real usage
  `template_config` is always `{}`.
- There is no version pinning when cloning a template (`pyartisan init` always clones the
  default branch HEAD), and no compatibility declaration/check between a plugin and the
  template version it's applied to. A plugin built against FastIQ v1 structure could silently
  corrupt a project already upgraded to FastIQ v2.

This spec addresses all of these as one consolidated change, since they are causally linked:
consolidating the Project API's location is not meaningful unless the config it reads
(`template.yaml`) is actually provisioned, and provisioning without a compatibility check
leaves the version-isolation problem (the whole reason `template.yaml` exists per FastIQ.md's
"Catatan Penting" section) unsolved.

## 2. Goals

1. One canonical Project API class, living in `pyartisan/project/`, used by **every** code
   path that writes to a project (`make:*`, `plugin install/apply/remove`).
2. `template.yaml` is actually provisioned into the global registry at `init` time, so
   `Project.template_config` reflects the real template version a project was created from.
3. Template versions are pinned via git tags, selectable at `init` time.
4. Plugins can declare which template version ranges they support; incompatible plugin/template
   pairs are rejected at `apply` time with a clear message.

## 3. Non-Goals

- Merging `manifest.yaml` (project-local, generator config) and `template.yaml` (global
  registry, versioned template metadata) into a single schema. They serve different purposes
  (see `FastIQ.md` "Catatan Penting") and both are kept.
- Full PEP 440 version specifier support. A minimal comma-separated constraint parser
  (`>=`, `<=`, `>`, `<`, `==`) is sufficient for now.
- Branch-per-version template maintenance. Tag-per-version is the chosen strategy (simpler,
  no parallel branch maintenance).
- Marketplace-side plugin signing/licensing changes — out of scope, unrelated to this work.

## 4. Design

### 4.1 Project API relocation

- `pyartisan/project/__init__.py` becomes the real home of the Project API:
  - `load_project_yaml`, `load_template_yaml` move here from `core/plugin_engine.py`.
  - `ProjectContext` is renamed to `Project` and moves here, keeping its existing methods
    (`create_service`, `register_router`, `add_dependency`) unchanged in behavior.
  - A new method `generate(target: str, name: str, force: bool = False, **opts) -> None` is
    added: it is the extracted body of today's `dispatch_make()` — reads
    `.pyartisan/manifest.yaml`, resolves the generator's stub/path/registration config, renders
    via `render_stub()`, and applies registration via `apply_registration()`. This makes
    `make:*` generation part of the Project API surface instead of a free function in
    `core/engine.py`.
- `pyartisan/core/plugin_engine.py` keeps only `load_plugin_yaml` (plugin manifest loading —
  a distinct concern from project state) and re-exports nothing else. Existing imports of
  `ProjectContext` are updated to `from pyartisan.project import Project`.
- Call sites updated:
  - `cli/commands/plugin.py`: `install`, `apply` (formerly reached via `apply_cmd`), `remove`,
    `doctor` — construct `Project(cwd)` instead of `ProjectContext(cwd)`.
  - `core/engine.py::dispatch_make()` becomes a thin wrapper:
    `Project(Path.cwd()).generate(target, name, force, **extra_options)`.
  - `tests/smoke_test.py` updates its imports accordingly.

### 4.2 Template version pinning (git tags)

- Template repositories (FastIQ, FlaskIQ) are expected to tag releases as `v<semver>`
  (e.g. `v1.0.0`, `v2.0.0`).
- `pyartisan init <framework> <name>` gains an option:
  ```
  pyartisan init fastapi myapp                  # clone latest tag
  pyartisan init fastapi myapp --version 1.0.0  # clone a specific tag
  ```
- `dispatch_new()` changes:
  1. Run `git ls-remote --tags <repo_url>` to list available tags.
  2. If `--version` is given, resolve to `v<version>`; error clearly if that tag doesn't
     exist (list available versions in the error).
  3. If no tags exist at all (template repo hasn't adopted tagging yet), fall back to
     today's behavior: clone default branch HEAD, read `version` from the cloned
     `manifest.yaml` as-is. This keeps existing/untagged templates working unchanged.
  4. If tags exist and no `--version` given, pick the highest by semver comparison (simple
     tuple compare over `.`-split numeric segments — no new dependency).
  5. Clone with `git clone --branch v<version> --depth 1 <repo_url> <project_name>`.

### 4.3 `template.yaml` provisioning

- Immediately after a successful clone in `dispatch_new()`, in addition to writing
  `.pyartisan/project.yaml` (unchanged), copy the cloned `.pyartisan/manifest.yaml` content to:
  ```
  ~/.pyartisan/templates/<template_id>/<template_version>/template.yaml
  ```
  Only if that path doesn't already exist — different tags/versions never overwrite each
  other's registry entry, and re-running `init` against the same version is idempotent.
- This directly fixes the gap where `Project.template_config` was always empty in real usage:
  it now resolves to the exact template version a given project was generated from, read from
  `project.yaml`'s `template.version` field (already written today).
- Backward compatibility: projects created before this change (or from untagged templates)
  will have no corresponding `template.yaml` in the registry. `Project.template_config` falls
  back to `{}` as it does today, and `register_router()`/`create_service()` keep using their
  existing hardcoded per-framework defaults. No behavior change for existing projects.

### 4.4 Plugin compatibility declaration

- Plugin manifest template (`templates/plugin_init/manifest.yaml.jinja`) gains an optional
  field:
  ```yaml
  id: {{name}}
  name: {{name_title}} Plugin
  version: 1.0.0
  compatible_templates:
    fastiq: ">=1.0.0,<2.0.0"
    flaskiq: ">=1.0.0"
  dependencies:
    pip: []
  ```
  Keys are template IDs (`fastiq`, `flaskiq`, ...); values are comma-separated version
  constraints.
- `pyartisan plugin install` gains `--version`, mirroring the template pinning UX:
  ```
  pyartisan plugin install github-user/payment-midtrans --version 2.0.0
  ```
  Resolves/clones the matching tag into the existing versioned registry layout
  (`plugins_registry/<plugin_id>/<version>/`), reusing `_resolve_plugin_version` /
  `_find_registry_dir` machinery already in `marketplace/core.py`. `install` itself performs
  **no** compatibility check — it only downloads a specific plugin version, mirroring today's
  "install doesn't touch any project" contract.

### 4.5 Compatibility check at `apply`

- `apply_cmd()` in `cli/commands/plugin.py`, before running any hook or calling
  `add_dependency`:
  1. Read `template_id` + `template_version` from the project's `project.yaml` (via `Project`).
  2. Read `compatible_templates.get(template_id)` from the plugin manifest being applied.
  3. If the field is **absent** (older plugin, not yet updated): allow the apply to proceed,
     print a mild warning (`⚠ Plugin does not declare template compatibility; proceeding
     anyway.`). No breaking change for existing plugins.
  4. If present: parse the constraint string and check `template_version` against it. If it
     does not satisfy the constraint, **reject the apply entirely** (no hooks run, no
     dependencies added, no project.yaml mutation) with a clear message:
     ```
     ❌ Plugin 'payment-midtrans@2.0.0' requires fastiq >=1.0.0,<2.0.0, but project uses fastiq 2.1.0.
        Install a compatible plugin version: pyartisan plugin install <source> --version <x>
     ```

### 4.6 Version constraint parser

- New small helper, `pyartisan/utils/semver.py`:
  ```python
  def version_satisfies(version: str, spec: str) -> bool:
      """spec: comma-separated constraints, e.g. '>=1.0.0,<2.0.0'."""
  ```
  Pure stdlib, tuple-based numeric comparison. No new dependency (`packaging` is not installed
  and won't be added for this).
  - `ponytail:` skips full PEP 440 semantics (pre-releases, wildcards, `~=`); add real
    `packaging`-based parsing if constraints need to express anything beyond
    `>=`/`<=`/`>`/`<`/`==`.

## 5. Error Handling Summary

| Scenario | Behavior |
|---|---|
| `init --version X` but tag `vX` doesn't exist | Clear error, lists available tags |
| Template repo has no tags at all | Falls back to HEAD clone, unchanged today's behavior |
| `template.yaml` already provisioned for that version | No-op, not overwritten |
| Project has no `template.yaml` in registry (legacy) | `template_config` = `{}`, hardcoded fallback used, no error |
| Plugin manifest has no `compatible_templates` | Apply proceeds with a warning |
| Plugin manifest declares incompatible range | Apply rejected before any file/hook side effect |

## 6. Testing

Assert-based smoke tests added to `tests/smoke_test.py` (no new test framework, matching
existing convention):

1. `Project` import path — construct via `pyartisan.project.Project`, confirm existing
   `create_service`/`register_router`/`add_dependency` behavior is unchanged (port existing
   `test_project_context_ops` assertions to the new import).
2. `Project.generate()` — move the current `dispatch_make` CLI-runner smoke test to also
   verify calling `Project(cwd).generate(...)` directly produces identical output.
3. `template.yaml` provisioning — mock `dispatch_new` (or the git-clone step) and assert
   `~/.pyartisan/templates/<id>/<version>/template.yaml` is created with content matching the
   cloned template's `manifest.yaml`.
4. `version_satisfies()` — table-driven assert checks for `>=`, `<=`, `>`, `<`, `==`, and
   comma-combined constraints.
5. `apply_cmd` compatibility gate — one case where plugin has no `compatible_templates` (warns,
   proceeds), one where it's satisfied (proceeds silently), one where it's violated (rejected,
   no side effects on `project.yaml`/`requirements.txt`).

## 7. Migration / Rollout Notes

- No breaking change for existing projects or plugins: absence of `template.yaml` in registry
  or `compatible_templates` in a plugin manifest both degrade gracefully to today's behavior.
- Template repo maintainers (FastIQ, FlaskIQ) need to start tagging releases (`v1.0.0`, ...)
  for version pinning to take effect; until they do, `init` continues cloning HEAD as it does
  today.
