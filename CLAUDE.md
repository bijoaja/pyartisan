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

PyArtisan adalah CLI multi-framework dengan Core yang framework-agnostic dan implementasi spesifik framework sebagai plugin terpisah (lihat `PRD.md` untuk desain lengkap).

### Struktur Direktori

*   `src/pyartisan/` — **Core**, tidak tahu apa-apa soal Flask/FastAPI:
    *   `cli.py`: Entry point CLI (`pyartisan = "pyartisan.cli:cli"`). Berisi command `init`, `make:*`, `serve`, `build`, `config`, `doctor`, `version`. Command `make:*`/`serve`/`build` bersifat dispatcher generik — resolve framework lewat `context.py`, lalu forward eksekusi ke `click.Group` milik plugin framework terkait.
    *   `context.py`: `ProjectContext.resolve()` — deteksi framework otomatis (atau pakai `--framework` eksplisit) untuk direktori kerja saat ini.
    *   `core/detector.py`: `detect_framework()` — deteksi berbasis file marker + signature, prioritas Flask → FastAPI → Django.
    *   `core/plugin_base.py`: `FrameworkPlugin` (ABC) — kontrak yang wajib diimplementasi tiap plugin framework (`name`, `detect()`, `build_cli()`).
    *   `plugin_loader.py`: Static registry dict (`{"flask": ..., "fastapi": ...}`) + `importlib` untuk lazy-load plugin sesuai kebutuhan (bukan setuptools entry-points).
    *   `config.py`: Baca/tulis `~/.pyartisan/config.toml` (`theme`, `author`, `license`, `default_framework`).
    *   `utils/`: Helper lintas-framework — `naming.py` (`name_parts`), `fs.py` (`write_file`, `write_service_init`, `write_controller_init`), `console.py` (format output konsisten).
    *   `shared/doctor.py`: Cek kesehatan environment (Python, pip, Git, virtualenv).
    *   `templates/`: Placeholder untuk Jinja2 template engine — belum dipakai karena semua template masih f-string sederhana.

*   `src/flasktool/` — **Flask plugin**, behavior generator persis sama seperti versi FlaskArtisan lama, hanya dibungkus jadi plugin:
    *   `plugin.py`: `FlaskPlugin(FrameworkPlugin)` — mendaftarkan 10 command lama (`init:project`, `make:controller`, `make:model`, `make:repository`, `make:service`, `make:migrations`, `make:docker`, `make:env`, `serve`, `build`) ke dalam satu `click.Group`.
    *   `commands/`: Implementasi tiap command (logic generator tidak berubah dari versi lama).
    *   `utils.py`: Re-export helper generik dari `pyartisan.utils`, plus 2 template spesifik Flask (`_view_service_template`, `_api_service_template`).

*   `src/fastapitool/` — **FastAPI placeholder** (structure only, sesuai scope v1 di `PRD.md` §4): `FastAPIPlugin` bisa mendeteksi project FastAPI, tapi belum ada command generator — hanya `status` yang melapor belum tersedia.

### Alur Eksekusi

1. User jalankan `pyartisan make:model Post` (tanpa `--framework`).
2. `pyartisan/cli.py` panggil `ProjectContext.resolve()` → `core/detector.py` cek `app.py`/`main.py`/`manage.py` di direktori kerja.
3. Kalau terdeteksi (mis. `flask`), `plugin_loader.load_plugin("flask")` import `flasktool.plugin.FlaskPlugin` secara lazy dan instansiasi.
4. `FlaskPlugin.build_cli()` mengembalikan `click.Group` berisi command aslinya; `pyartisan/cli.py` forward argumen ke situ (`make:model Post`), semua di-generate persis seperti versi FlaskArtisan lama.
5. Kalau gagal deteksi, tampilkan pesan `Project framework cannot be detected.` dan minta `--framework` eksplisit.

Menambah framework baru (mis. Django) cukup: buat package baru dengan `plugin.py` yang mengimplementasi `FrameworkPlugin`, tambah 1 baris ke `_REGISTRY` di `plugin_loader.py` — tidak perlu ubah apa pun di `pyartisan/core/`.
