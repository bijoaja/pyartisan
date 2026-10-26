# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Perintah Pengembangan

### Instalasi
Pasang dependencies secara lokal dalam mode editable:
```bash
uv tool install --editable .   # atau: pip3 install -e .
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


Menambah framework baru (mis. Django) cukup: buat sub-package baru `pyartisan/plugin/django/` dengan `plugin.py` yang mengimplementasi `FrameworkPlugin`, tambah 1 baris ke `_REGISTRY` di `plugin/registry.py` — tidak perlu ubah apa pun di `pyartisan/core/` atau `pyartisan/cli/`.
