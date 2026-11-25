# doctor + serve multi-mode + analyze Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `pyartisan doctor` melapor paket outdated dan versi pyartisan baru, `serve` punya mode docker/venv/uv, `analyze` menjalankan ruff/bandit/mypy dari satu command.

**Architecture:** Logika baru di modul kecil `shared/` (updates, deps) dan `core/engine.py` (serve mode, analyze). `cli/commands/*` hanya parse argumen. Perintah dijalankan lewat `subprocess` dengan argv list (aturan bandit repo: tanpa `shell=True`).

**Tech Stack:** Python >=3.10, click, pyyaml, pytest, stdlib saja (tanpa dependency baru).

**Spec:** `docs/superpowers/specs/2026-11-25-doctor-serve-check-design.md` (akan di-rename ke `...-analyze-design.md`, isinya sudah memakai `analyze`).

## Global Constraints
- Bandit skip hanya `B404/B603/B607` (`pyproject.toml`). Tanpa `shell=True`. Setiap `# nosec` wajib disertai alasan di baris yang sama.
- Mypy `disallow_untyped_defs = true`, semua fungsi baru bertipe penuh.
- Ruff line-length 100, target py310.
- Output pakai `console.success/warn/error` (`utils/console.py`) atau `click.echo`.
- Test tanpa jaringan: subprocess dan `git ls-remote` di-mock. Gaya test: lihat `tests/unit/test_serve_venv.py`, fixture `fake_home`, `in_tmp_cwd`, `runner` di `tests/conftest.py`.
- URL repo: `https://github.com/bijoaja/pyartisan.git`, konstanta `REPO_URL` di `pyartisan/config/__init__.py`.
- Rilis: bump versi di `pyproject.toml` dan `src/pyartisan/__init__.py`, `git tag vX.Y.Z`, `git push --tags`. Rollback = `uv tool install --force git+<repo>@vX.Y.Z` lama.
- Cek versi: cache 24 jam di `~/.pyartisan/version-check.json`, timeout 5 detik, gagal = diam.
- Commit tanpa baris atribusi (memori user: tanpa co-author/generated-by, author bijoaja).

## Review Focus
- Tag `v1.10.0` vs `v1.9.0`: harus `1.10.0` lebih besar (bukan perbandingan string).
- Tag non-semver (`latest`, `v2`, `v1.0.0-rc1`): diabaikan, tidak crash.
- Offline / `git` tidak ada / `git ls-remote` timeout: doctor jalan normal tanpa pesan error.
- File cache korup atau bukan JSON: dianggap tidak ada cache.
- `serve --uv` tanpa `uv` di PATH, atau `--docker` saat docker mati: error jelas, exit 1, tanpa fallback diam-diam.
- Dua flag mode sekaligus (`--docker --uv`): ditolak.
- `analyze` saat satu langkah gagal: langkah lain tetap jalan, exit 1. Alat tidak terpasang: langkah gagal dengan pesan, bukan traceback.
- `analyze --only` dengan nama tidak dikenal: error menyebut nama yang valid.

---

### Task 1: Cek versi pyartisan (`shared/updates.py`)

**Files:**
- Create: `src/pyartisan/shared/updates.py`
- Modify: `src/pyartisan/config/__init__.py` (tambah `REPO_URL`)
- Test: `tests/unit/test_updates.py`

**Interfaces:**
- Produces:
  - `parse_semver(tag: str) -> tuple[int, int, int] | None` : menerima `v1.2.3` atau `1.2.3`, selain itu `None`.
  - `latest_version(tags: list[str]) -> str | None` : tag semver terbesar tanpa awalan `v`.
  - `fetch_tags(repo_url: str, timeout: float = 5.0) -> list[str]` : `git ls-remote --tags --refs`, `[]` jika gagal apa pun.
  - `check_update(current: str, cache_path: Path, now: float, fetch: Callable[[], list[str]], ttl: float = 86400.0) -> str | None` : versi lebih baru atau `None`. Pakai cache jika segar, tulis cache setelah fetch berhasil.
  - `install_hint(version: str) -> str` : `uv tool install --force git+<REPO_URL>@v<version>`.

- [ ] **Step 1: Tulis test gagal** di `tests/unit/test_updates.py`:
  - `test_parse_semver`: `"v1.10.0" -> (1,10,0)`, `"1.0.0" -> (1,0,0)`, `"latest"`, `"v2"`, `"v1.0.0-rc1"` -> `None`.
  - `test_latest_version_numeric`: `["v1.9.0","v1.10.0","junk"] -> "1.10.0"`; `[] -> None`.
  - `test_check_update_newer`: current `"1.0.0"`, fetch `["v1.1.0"]` -> `"1.1.0"`, dan cache tertulis.
  - `test_check_update_uses_fresh_cache`: cache `now-100` berisi `latest="1.2.0"`, fetch yang raise -> `"1.2.0"` tanpa memanggil fetch.
  - `test_check_update_expired_cache_refetches`: cache `now-90000`.
  - `test_check_update_corrupt_cache`: isi `"{not json"` -> refetch.
  - `test_check_update_offline`: fetch `[]` -> `None`, tanpa cache ditulis.
  - `test_check_update_not_newer`: current sama atau lebih baru -> `None`.
  - `test_fetch_tags_failure`: `subprocess.run` di-patch raise `FileNotFoundError`/`TimeoutExpired`/`returncode=1` -> `[]`.
- [ ] **Step 2: Jalankan, pastikan gagal:** `uv run pytest tests/unit/test_updates.py -v` -> FAIL (modul tidak ada).
- [ ] **Step 3: Implementasi** sesuai Interfaces. Tag diambil dari kolom kedua `refs/tags/<tag>`. Cache JSON `{"checked_at": float, "latest": str|null}`.
- [ ] **Step 4: Jalankan:** `uv run pytest tests/unit/test_updates.py -v` -> PASS.
- [ ] **Step 5: Commit** `git add src/pyartisan/shared/updates.py src/pyartisan/config/__init__.py tests/unit/test_updates.py && git commit -m "feat(doctor): detect newer pyartisan release via git tags"`

### Task 2: Cek paket outdated (`shared/deps.py`)

**Files:**
- Create: `src/pyartisan/shared/deps.py`
- Test: `tests/unit/test_deps.py`

**Interfaces:**
- Consumes: `_find_project_venv(cwd) -> Path | None`, `_venv_python(venv) -> Path` dari `core/engine.py`.
- Produces:
  - `Outdated = tuple[str, str, str]` (nama, terpasang, terbaru).
  - `parse_uv_updates(output: str) -> list[Outdated]` : baris `Update <pkg> v<a> -> v<b>` (stdout/stderr uv).
  - `parse_pip_outdated(json_text: str) -> list[Outdated]` : JSON `pip list --outdated --format=json`; JSON rusak -> `[]`.
  - `find_outdated(cwd: Path) -> list[Outdated] | None` : `None` bila cek tidak bisa dilakukan (tidak ada `uv.lock`/`requirements*.txt`, uv/venv tidak ada). Prioritas: `uv.lock` + `uv` -> `uv lock --upgrade --dry-run`; selain itu `requirements*.txt` + venv -> pip.
  - `upgrade(cwd: Path) -> bool` : uv: `uv lock --upgrade` lalu `uv sync`; pip: `<venv python> -m pip install -U -r requirements.txt`. `True` jika sukses.

- [ ] **Step 1: Tulis test gagal:**
  - `test_parse_uv_updates`: `"Update flask v3.0.0 -> v3.1.0\nResolved 40 packages"` -> `[("flask","3.0.0","3.1.0")]`.
  - `test_parse_uv_updates_none`: `"Resolved 40 packages"` -> `[]`.
  - `test_parse_pip_outdated`: `'[{"name":"flask","version":"3.0.0","latest_version":"3.1.0"}]'`; `"not json"` -> `[]`.
  - `test_find_outdated_none_without_files`: cwd kosong -> `None`.
  - `test_find_outdated_uv`: `uv.lock` ada, `shutil.which`/`subprocess.run` di-patch -> hasil parse.
  - `test_find_outdated_pip_needs_venv`: hanya `requirements.txt`, tanpa venv -> `None`.
  - `test_upgrade_uv_runs_lock_then_sync`: urutan argv terekam.
- [ ] **Step 2: Jalankan -> FAIL:** `uv run pytest tests/unit/test_deps.py -v`
- [ ] **Step 3: Implementasi.** Subprocess dengan argv list, `capture_output=True, text=True`, tangkap `OSError`.
- [ ] **Step 4: Jalankan -> PASS.**
- [ ] **Step 5: Commit** `git commit -m "feat(doctor): detect outdated project dependencies"` (add kedua file).

### Task 3: Integrasi ke `doctor`

**Files:**
- Modify: `src/pyartisan/shared/doctor.py` (`run_checks(upgrade: bool = False) -> bool`), `src/pyartisan/cli/commands/doctor.py` (opsi `--upgrade`)
- Test: `tests/unit/test_doctor.py` (tambah)

**Interfaces:**
- Consumes: `check_update`, `fetch_tags`, `install_hint` (Task 1); `find_outdated`, `upgrade` (Task 2); `load_manifest` untuk deteksi project (`ManifestNotFound` = bukan project).
- Produces: `run_checks(upgrade=False)`: setelah cek lama, cetak bagian informasi. Bagian ini tidak mengubah exit code.

- [ ] **Step 1: Tulis test gagal** (patch `check_update`/`find_outdated`):
  - `test_doctor_reports_new_version`: output memuat `1.0.0 -> 1.1.0` dan `install_hint("1.1.0")`.
  - `test_doctor_skips_deps_outside_project`: `find_outdated` tidak dipanggil tanpa manifest.
  - `test_doctor_lists_outdated_in_project`: output memuat `flask 3.0.0 -> 3.1.0`.
  - `test_doctor_outdated_does_not_fail`: exit code 0 walau ada outdated.
  - `test_doctor_upgrade_confirms`: `--upgrade` + input `n` -> `upgrade` tidak dipanggil; input `y` -> dipanggil.
- [ ] **Step 2: Jalankan -> FAIL.**
- [ ] **Step 3: Implementasi.** `run_checks` memanggil bagian update/deps; `--upgrade` memakai `click.confirm`. Cache path `config.CONFIG_DIR / "version-check.json"`.
- [ ] **Step 4: Jalankan** `uv run pytest tests/unit/test_doctor.py -v` -> PASS (test lama tetap hijau).
- [ ] **Step 5: Commit** `git commit -m "feat(doctor): report new pyartisan version and outdated deps"`

### Task 4: Mode serve

**Files:**
- Modify: `src/pyartisan/core/engine.py` (`dispatch_serve(mode: str | None = None) -> None`, `select_serve_mode`), `src/pyartisan/cli/commands/serve.py`
- Test: `tests/unit/test_serve_mode.py`

**Interfaces:**
- Produces: `select_serve_mode(cwd: Path, manifest: dict, forced: str | None) -> str` mengembalikan `"docker" | "venv" | "uv"` atau raise `PyArtisanError` (pakai tipe di `core/exceptions.py`; lihat file itu untuk pilihan kelas). Tanpa flag: docker jika `docker-compose.yml` dan `_docker_available()`; venv jika `_find_project_venv(cwd)` dan `scripts.serve`; uv jika `shutil.which("uv")` dan perintah uv ada; selain itu error (pesan lama dipertahankan).
- Perintah uv: `scripts.serve` jika diawali `uv run`, selain itu `scripts.serve_uv`; tidak ada -> error menyebut key `serve_uv`.
- Click: `--docker`, `--venv`, `--uv` lewat satu `click.Choice`-setara (tiga flag boolean + validasi: lebih dari satu -> `click.UsageError`).

- [ ] **Step 1: Tulis test gagal** (monkeypatch `_docker_available`, `shutil.which`, `_find_project_venv`, `subprocess.run`):
  - `test_auto_prefers_docker`, `test_auto_falls_to_venv`, `test_auto_falls_to_uv`, `test_auto_none_available_errors`.
  - `test_forced_docker_unavailable_errors` (tanpa fallback), `test_forced_uv_without_uv_errors`, `test_forced_venv_without_venv_errors`.
  - `test_uv_mode_uses_serve_when_prefixed`, `test_uv_mode_uses_serve_uv_key`, `test_uv_mode_missing_command_errors`.
  - `test_cli_rejects_two_mode_flags` lewat `runner.invoke(serve_cmd, ["--docker","--uv"])` -> exit code != 0.
- [ ] **Step 2: Jalankan -> FAIL.**
- [ ] **Step 3: Implementasi.** Pecah `dispatch_serve` menjadi pemilih + `_run_docker`, `_run_venv`, `_run_uv`. Pakai ulang `_venv_command`. `test_serve_venv.py` harus tetap hijau.
- [ ] **Step 4: Jalankan** `uv run pytest tests/unit -v` -> PASS.
- [ ] **Step 5: Commit** `git commit -m "feat(serve): add docker/venv/uv modes with force flags"`

### Task 5: `pyartisan analyze`

**Files:**
- Create: `src/pyartisan/cli/commands/analyze.py`
- Modify: `src/pyartisan/core/engine.py` (`dispatch_analyze`, `analyze_steps`), `src/pyartisan/cli/commands/__init__.py`, `src/pyartisan/cli/__init__.py`
- Test: `tests/unit/test_analyze.py`

**Interfaces:**
- Produces:
  - `analyze_steps(manifest: dict, fix: bool) -> list[tuple[str, str]]` (nama, cmd). Sumber `scripts.analyze`: list `{name, cmd, fix?}`. Mode `fix=True`: pakai `fix` jika ada, langkah tanpa `fix` tetap jalan sebagai cek. Tanpa `scripts.analyze`: default `ruff-check` (`ruff check .`, fix `ruff check --fix .`), `ruff-format` (`ruff format --check .`, fix `ruff format .`), `bandit` (`bandit -q -r . -c pyproject.toml`), `mypy` (`mypy .`).
  - `dispatch_analyze(only: tuple[str, ...] = (), fix: bool = False) -> None` : jalankan semua langkah terpilih, cetak `✔/❌ <nama>` dan ringkasan, `sys.exit(1)` jika ada gagal. Nama di `--only` tidak dikenal -> `PyArtisanError` yang menyebut nama valid.
- Eksekusi: `shlex.split(cmd)`; jika `_find_project_venv` ada, lewat `_venv_command`. `FileNotFoundError` = langkah gagal dengan pesan "tool not found".
- Click: `analyze` dengan `--only` (multiple) dan `--fix`.

- [ ] **Step 1: Tulis test gagal:**
  - `test_steps_from_manifest`, `test_steps_default_without_key`, `test_steps_fix_mode_swaps_cmd`.
  - `test_analyze_all_pass_exit_0`, `test_analyze_runs_all_even_if_one_fails` (exit 1, semua langkah dipanggil), `test_analyze_only_filters`, `test_analyze_unknown_only_lists_valid`, `test_analyze_missing_tool_reports_failure` (patch `subprocess.run` raise `FileNotFoundError`), `test_analyze_without_manifest_errors`.
  - `test_cli_registers_analyze`: `analyze` ada di `cli.commands`.
- [ ] **Step 2: Jalankan -> FAIL.**
- [ ] **Step 3: Implementasi** sesuai Interfaces, daftar command di dua `__init__`.
- [ ] **Step 4: Jalankan** `uv run pytest -v` -> PASS.
- [ ] **Step 5: Commit** `git commit -m "feat(cli): add analyze command"`

### Task 6: Bandit CI, versi, dokumentasi

**Files:**
- Modify: `.github/workflows/ci.yml` (hanya jika bandit hilang; saat ini sudah ada), `CLAUDE.md` (daftar command dan alur rilis tag), `docs/id/CONTRIBUTING.md` (alur rilis), `README` jika menyebut daftar command
- Test: `tests/unit/test_updates.py` (tambah `test_version_matches_pyproject`)

- [ ] **Step 1: Tulis test gagal** `test_version_matches_pyproject`: baca `pyproject.toml` (`tomllib`/`tomli`) dan bandingkan `project.version` dengan `pyartisan.__version__`.
- [ ] **Step 2: Jalankan** -> PASS atau FAIL. Saat ini keduanya `1.0.0`, jadi PASS; ini test pengaman rilis.
- [ ] **Step 3: Verifikasi bandit:** `uv run bandit -q -r src -c pyproject.toml` -> tanpa temuan. `grep -n bandit .github/workflows/ci.yml` -> step ada.
- [ ] **Step 4: Update dokumen:** tambah `analyze`, flag serve, `doctor --upgrade`, dan alur rilis tag di `CLAUDE.md` dan `docs/id/CONTRIBUTING.md`.
- [ ] **Step 5: Gerbang akhir:** `uv run pytest && uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run bandit -q -r src -c pyproject.toml` -> semua bersih.
- [ ] **Step 6: Commit** `git commit -m "docs: document analyze, serve modes, tag-based release"`
