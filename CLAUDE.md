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
PYTHONPATH=src uv run --no-project --with click --with jinja2 --with pyyaml --with flask --with sqlalchemy python tests/smoke_test.py
```
(Jika `python` sudah ada di venv yang berisi dependency project, cukup `PYTHONPATH=src python tests/smoke_test.py`. Jangan pakai `uv run --with-editable .`: itu membuat `uv.lock` yang tak terlacak.)

Cover: `name_parts`, `load_manifest`, `render_stub`, registrasi (`import_list`, `marker`), `config` load/save/reset, `make` generik (termasuk target tidak dikenal dan tanpa manifest), `ProjectContext`, seluruh siklus `plugin` (`init`, `install`, `apply`, `remove`, `uninstall`, `list`, `info`, `status`, `doctor`), pemilihan installer uv vs pip, pemaksaan UTF-8, dan pemilihan venv project untuk `serve`. Keluaran yang benar berakhir `ALL SMOKE TESTS PASSED`.

## Arsitektur Codebase

PyArtisan adalah **satu package** (`src/pyartisan/`) — sebuah engine CLI multi-framework, murni framework-agnostic di intinya. Tidak ada package top-level terpisah per framework, dan **tidak ada** modul `pyartisan/plugin/` maupun `FrameworkPlugin` (itu rancangan lama di `docs/id/PRD.md`, bukan kode). Pengetahuan framework ada di template repo (FlaskIQ, FastIQ) yang di-clone oleh `pyartisan new`, lewat `.pyartisan/manifest.yaml` milik project.

Peta `src/pyartisan/`:
- `cli/commands/` — satu file per command; hanya mem-parse argumen lalu memanggil `core/engine.py`.
- `core/` — `engine.py` (`dispatch_new/make/serve/build`), `manifest.py`, `registration.py`, `plugin_engine.py` (`ProjectContext`, Project API untuk hook plugin), `exceptions.py`.
- `marketplace/` — registry plugin global `~/.pyartisan/plugins/` (usage tracking, pemuat `hooks.py`). Ini sistem plugin untuk pengguna (`pyartisan plugin ...`) dan **sudah ada**, berbeda dari modul `plugin/` rancangan lama.
- `project/` — placeholder Project API, belum berisi kode.
- `renderer/`, `config/`, `shared/`, `utils/`, `templates/plugin_init/` — render Jinja2, `config.toml`, logika doctor, helper, skeleton `plugin init`.

Menambah framework baru (mis. Django) cukup: siapkan template repo dengan `.pyartisan/manifest.yaml`, lalu daftarkan URL-nya di `DEFAULT_CONFIG["templates"]` pada `src/pyartisan/config/__init__.py` — tidak perlu ubah `pyartisan/core/` atau `pyartisan/cli/`. Panduan lengkap ada di `docs/id/CONTRIBUTING.md`.
