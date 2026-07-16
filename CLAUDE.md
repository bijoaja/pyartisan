# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Perintah Pengembangan

### Instalasi
Pasang dependencies secara lokal dalam mode editable:
```bash
pip3 install -e .
```

### Menjalankan CLI secara Lokal
```bash
pyartisan --help
```

### Pengujian & Linting
Tidak ada framework test (pytest/unittest) sebagai dependency — self-check assert-based ada di `tests/smoke_test.py`. Jalankan:
```bash
PYTHONPATH=src python3 tests/smoke_test.py
```
Cover: `name_parts`, `detect_framework`, `config` load/save/reset, `plugin_loader`, dan alur CLI end-to-end (`version`, `doctor`, `config show`, `make:model` dengan deteksi otomatis maupun `--framework` eksplisit).

## Arsitektur Codebase

PyArtisan adalah **satu package** (`src/pyartisan/`) — sebuah engine CLI multi-framework, murni framework-agnostic di intinya. Tidak ada lagi package top-level terpisah per framework (`flasktool`, `fastapitool`); setiap dukungan framework konkret adalah **built-in plugin** yang hidup di dalam `pyartisan.plugin.<nama_framework>` (lihat `PRD.md` untuk desain lengkap).

### Struktur Direktori

`src/pyartisan/` dipecah per tanggung jawab (skeleton engine):

*   `cli/`: Entry point CLI (`pyartisan = "pyartisan.cli:cli"`). Hanya berisi definisi command `click` (`init`, `make:*`, `serve`, `build`, `config`, `doctor`, `version`) — parser tipis, tidak tahu cara eksekusi framework. Setiap command langsung memanggil `core.engine`.
*   `core/`: Jantung engine, framework-agnostic.
    *   `engine.py`: `dispatch()` / `dispatch_init()` — resolve framework (lewat `context.py`, opsional override `--framework`), lalu forward eksekusi ke `click.Group` milik plugin framework terkait. Satu-satunya tempat yang menjembatani CLI ↔ plugin.
    *   `context.py`: `ProjectContext.resolve()` — deteksi framework otomatis untuk direktori kerja saat ini.
    *   `detector.py`: `detect_framework()` — deteksi berbasis file marker + signature, prioritas Flask → FastAPI → Django.
    *   `exceptions.py`: `PyArtisanError` dan turunannya (`FrameworkNotDetected`, `PluginNotFound`, `ConfigError`).
*   `plugin/`: Kontrak & registry plugin, plus plugin bawaan itu sendiri.
    *   `base.py`: `FrameworkPlugin` (ABC) — kontrak wajib tiap plugin (`name`, `detect()`, `build_cli()`).
    *   `registry.py`: Static registry dict (`{"flask": ..., "fastapi": ...}`) + `importlib` untuk lazy-load plugin sesuai kebutuhan (bukan setuptools entry-points).
    *   `flask/`: **Plugin Flask bawaan**, behavior generator persis sama seperti versi FlaskArtisan lama. `plugin.py` mendaftarkan 10 command (`init:project`, `make:controller`, `make:model`, `make:repository`, `make:service`, `make:migrations`, `make:docker`, `make:env`, `serve`, `build`) ke satu `click.Group`; `commands/` berisi implementasi tiap command; `utils.py` berisi helper + template spesifik Flask (`_view_service_template`, `_api_service_template`).
    *   `fastapi/`: **Plugin FastAPI bawaan** (structure only, sesuai scope v1 di `PRD.md` §4) — `FastAPIPlugin` bisa mendeteksi project FastAPI, tapi belum ada command generator, hanya `status` yang melapor belum tersedia.
*   `project/`: Placeholder Project API (mediated file-write layer untuk plugin) — belum diimplementasi, lihat komentar `ponytail:` di `__init__.py`.
*   `renderer/`: Placeholder Jinja2 template engine — belum dipakai, semua template plugin masih f-string sederhana. Lihat komentar `ponytail:`.
*   `marketplace/`: Placeholder plugin marketplace (install/manifest/hooks) — eksplisit di luar scope v1 (`PRD.md` §4/§18).
*   `config/`: Baca/tulis `~/.pyartisan/config.toml` (`theme`, `author`, `license`, `default_framework`).
*   `utils/`: Helper lintas-framework — `naming.py` (`name_parts`), `fs.py` (`write_file`, `copy_file`, `write_service_init`, `write_controller_init`), `console.py` (format output konsisten).
*   `shared/doctor.py`: Cek kesehatan environment (Python, pip, Git, virtualenv).

### Alur Eksekusi

1. User jalankan `pyartisan make:model Post` (tanpa `--framework`).
2. `cli/__init__.py` panggil `core.engine.dispatch("make:model", framework=None, args=[...])`.
3. `engine.dispatch()` panggil `core.context.ProjectContext.resolve()` → `core/detector.py` cek `app.py`/`main.py`/`manage.py` di direktori kerja.
4. Kalau terdeteksi (mis. `flask`), `plugin.registry.load_plugin("flask")` import `pyartisan.plugin.flask.plugin.FlaskPlugin` secara lazy dan instansiasi.
5. `FlaskPlugin.build_cli()` mengembalikan `click.Group` berisi command aslinya; `engine.dispatch()` forward argumen ke situ (`make:model Post`), semua di-generate persis seperti versi FlaskArtisan lama.
6. Kalau gagal deteksi, tampilkan pesan `Project framework cannot be detected.` dan minta `--framework` eksplisit.

Menambah framework baru (mis. Django) cukup: buat sub-package baru `pyartisan/plugin/django/` dengan `plugin.py` yang mengimplementasi `FrameworkPlugin`, tambah 1 baris ke `_REGISTRY` di `plugin/registry.py` — tidak perlu ubah apa pun di `pyartisan/core/` atau `pyartisan/cli/`.
