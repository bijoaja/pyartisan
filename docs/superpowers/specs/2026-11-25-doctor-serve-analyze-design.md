# Desain: doctor (deps + versi), serve multi-mode, `pyartisan analyze`

> Tanggal: 2026-11-25. Status: menunggu review. Plan: `../plans/2026-11-25-doctor-serve-analyze.md`.
> Spec terkait di template: `flaskiq` dan `fastiq`, `docs/superpowers/specs/2026-11-25-manifest-analyze-serve-design.md`.

## Tujuan
1. `pyartisan doctor` di dalam project melaporkan paket outdated (`pyproject.toml` atau `requirements*.txt`).
2. `pyartisan doctor` memberi tahu ada versi pyartisan baru dan perintah install-nya.
3. `pyartisan serve` bisa jalan lewat docker, venv, atau uv.
4. Bandit ada di CI pyartisan dan tiap template.
5. Satu command `pyartisan analyze` menjalankan ruff check, ruff format --check, bandit, mypy.

## Bukan tujuan
- Update versi template, atau merge perubahan template upstream.
- Menggantikan Dependabot. Dependabot tetap jalur update otomatis di template.
- Publish ke PyPI atau GitHub Release workflow.

## Pendekatan yang dipilih

### 1. Doctor: paket outdated
- Hanya aktif jika cwd project (ada `.pyartisan/manifest.yaml`). Di luar project, cek dilewati.
- Project uv (ada `uv.lock`): `uv lock --upgrade --dry-run`, parse baris `Update <pkg> vA -> vB`.
- Project pip (ada `requirements*.txt`): `<venv python> -m pip list --outdated --format=json`. Venv dicari lewat `_find_project_venv` (`core/engine.py`). Tanpa venv: cek dilewati dengan pesan.
- Hanya melapor. `doctor --upgrade` menjalankan upgrade setelah konfirmasi: `uv lock --upgrade && uv sync`, atau `pip install -U -r requirements.txt`. Opt-in, jadi doctor tetap aman.
- Paket outdated bukan kegagalan: tidak mengubah exit code.

### 2. Doctor: versi pyartisan (git tags)
- `git ls-remote --tags --refs https://github.com/bijoaja/pyartisan.git`. Ambil tag `vMAJOR.MINOR.PATCH`, tag lain diabaikan. Bandingkan dengan `__version__` secara numerik, bukan string.
- Cache 24 jam di `~/.pyartisan/version-check.json` (`checked_at`, `latest`). Offline, timeout (5 detik), git tidak ada: skip diam-diam, tidak gagal.
- Output: `pyartisan 1.0.0 -> 1.1.0 tersedia` dan `uv tool install --force git+https://github.com/bijoaja/pyartisan@v1.1.0`.
- URL repo konstanta di `config`, bukan hardcode tersebar.

Alur rilis fix: commit, naikkan versi di `pyproject.toml` dan `src/pyartisan/__init__.py`, `git tag vX.Y.Z`, `git push --tags`. Install dari tag dibangun lokal oleh uv, jadi tidak ada langkah build.
- Fix tanpa tag tidak terdeteksi. Untuk uji: `@main`.
- Tag lama tidak boleh dipindah (doctor tidak melihat perubahan, cache uv bisa pakai commit lama).
- Test menjamin versi `pyproject.toml` == `__version__`.

### 3. Serve multi-mode
- Tanpa flag: docker (jika `docker-compose.yml` dan docker jalan), lalu venv (+ `scripts.serve`), lalu uv.
- Flag `--docker | --venv | --uv` (saling eksklusif) memaksa satu mode. Mode tidak tersedia: error jelas, exit 1, tanpa fallback diam-diam.
- Mode uv: butuh `uv` di PATH dan `scripts.serve`. Jika `scripts.serve` sudah diawali `uv run`, jalankan apa adanya. Jika tidak, template mendeklarasikan perintahnya di `scripts.serve_uv` (lihat spec template). Tanpa `serve_uv`: error menyebut key itu.
- Refaktor `dispatch_serve` jadi pemilih mode kecil + runner per mode. `_find_project_venv`, `_venv_command` dipakai ulang.

### 4. Bandit di CI
- Sudah ada di `ci.yml` (`bandit -q -r src -c pyproject.toml`) dan `[tool.bandit]`. Verifikasi saja, tambahkan hanya jika hilang. Tidak ada perubahan fungsional yang diharapkan.

### 5. `pyartisan analyze`
- File baru `cli/commands/analyze.py`, logika `core/engine.py` (`dispatch_analyze`), terdaftar di `cli/__init__.py`.
- Langkah dari manifest `scripts.analyze`: list `{name, cmd, fix?}`. `fix` opsional: perintah pengganti saat `--fix`. Tidak ada: default ruff check ., ruff format --check ., bandit -q -r <paths> -c pyproject.toml, mypy.
- Semua langkah dijalankan, ringkasan pass/fail per langkah, exit 1 jika ada yang gagal. Perintah lewat venv/uv project, bukan env pyartisan.
- Flag: `--only <nama>` (boleh berulang), `--fix` (`ruff check --fix` dan `ruff format`).
- Alat tidak terpasang di project: langkah ditandai gagal dengan pesan jelas.

## Alternatif yang ditolak
- Release workflow/GitHub API: rate limit anonim, workflow baru, tanpa kebutuhan release notes.
- PyPI: butuh publik dan nama paket bebas. Install saat ini dari git.
- Serve ditentukan manifest saja: mengubah kedua template untuk hal yang bisa otomatis.

## Pengujian
- pytest: parser output uv dan pip, perbandingan semver (termasuk `1.10.0 > 1.9.0`), cache version-check (segar, kedaluwarsa, offline), pemilih mode serve per kombinasi flag, `analyze` (semua lulus, satu gagal, `--only`, tanpa manifest, default).
- Subprocess dan `git ls-remote` di-mock. Tidak ada akses jaringan di test.
- Manual: `pyartisan doctor`, `serve --docker|--venv|--uv`, `analyze` di flaskiq dan fastiq.

## Diserahkan ke implementer
Format teks output, nama berkas cache, timeout tepat, pembagian modul.
