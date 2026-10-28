# Product Requirements Document (PRD)

## PyArtisan v1.0

**Refactor FlaskArtisan menjadi Multi-Framework AI Development Toolkit**

> **Bahasa:** Indonesia | [English](../en/PRD.md)
> **Terakhir diverifikasi terhadap kode:** commit `80b5acc` (2026-10-26)

PRD ini adalah dokumen **rancangan**. Tidak semua yang dirancang sudah ada di kode, jadi setiap fitur diberi status:

| Status | Arti |
|---|---|
| **Sudah ada** | Ada di kode dan sudah dicek |
| **Sebagian** | Ada, tetapi berbeda dari rancangan atau belum lengkap |
| **Belum ada** | Hanya rancangan, belum ada kodenya |

---

# 1. Ringkasan

## Latar Belakang

Saat ini **FlaskArtisan** merupakan CLI yang berfokus pada pengembangan aplikasi Flask.

Seiring berkembangnya project, muncul kebutuhan untuk:

* Mendukung lebih dari satu framework Python.
* Menjadikan project sebagai platform, bukan sekadar generator Flask.
* Menyediakan fondasi untuk AI Agent dan MCP (Model Context Protocol).
* Mengurangi duplikasi kode antar framework.
* Memiliki branding yang lebih umum dan profesional.

Karena itu, FlaskArtisan direfactor menjadi **PyArtisan**.

---

# 2. Tujuan

Membangun sebuah CLI modern yang dapat digunakan untuk berbagai framework Python.

Target framework awal:

* Flask
* FastAPI

Future:

* Django
* Quart
* Litestar
* Sanic
* Starlette

---

# 3. Visi Produk

> **PyArtisan adalah AI-powered Python Web Development Toolkit yang membantu developer membangun, mengelola, dan mengembangkan aplikasi Python secara lebih cepat melalui CLI, generator, AI, dan MCP.**

Status visi: CLI dan generator **sudah ada**; AI dan MCP **belum ada** (roadmap v2).

---

# 4. Scope v1

## Included

| Item | Status | Keterangan |
|---|---|---|
| Refactor branding | Sudah ada | Package `pyartisan`, command `pyartisan` |
| Core CLI | Sudah ada | `cli/` (parser click) dan `core/engine.py` (dispatch) |
| Flask Module | Sebagian | Lewat template eksternal FlaskIQ yang di-clone oleh `pyartisan new`, bukan modul di dalam pyartisan |
| FastAPI Module (structure only) | Sebagian | Hanya URL template FastIQ yang terdaftar di config; tidak ada kode FastAPI di pyartisan |
| Shared Core | Sudah ada | `core/`, `shared/` |
| Shared Utilities | Sudah ada | `utils/` (`console.py`, `fs.py`, `naming.py`) |
| Plugin Architecture | Sebagian | Siklus hidup plugin (`install`, `apply`, `remove`, dll) sudah jalan; kontrak `FrameworkPlugin` per framework belum ada (lihat §11) |

## Excluded

* MCP
* AI Agent
* Deployment
* Kubernetes
* VSCode Extension

Semua akan menjadi roadmap v2.

---

# 5. Arsitektur

## Sebelum refactor

```
FlaskArtisan

↓

Flask CLI
```

## Rancangan awal (target)

```
PyArtisan

↓

Core CLI

↓

Framework Module

↓

Flask
FastAPI
Django
```

## Kondisi nyata saat ini

```
pyartisan (cli/ -> core/engine.py)

↓

.pyartisan/manifest.yaml milik project  (daftar generator + stub)

↓

Template project hasil clone: FlaskIQ / FastIQ
```

Framework tidak diimplementasikan sebagai modul di dalam pyartisan. Pengetahuan framework ada di template repo yang di-clone, dan engine hanya membaca manifest-nya.

---

# 6. Struktur Project

Struktur nyata `src/pyartisan/`:

```
src/pyartisan/
│
├── cli/                  # parser click tipis
│   └── commands/         # new, make, serve, build, config, doctor, version, plugin
│
├── core/
│   ├── engine.py         # dispatch_new / dispatch_make / dispatch_serve / dispatch_build
│   ├── manifest.py       # load_manifest (.pyartisan/manifest.yaml)
│   ├── registration.py   # apply_registration (import_list, marker)
│   ├── plugin_engine.py  # ProjectContext (Project API untuk hooks plugin)
│   └── exceptions.py
│
├── marketplace/          # registry plugin global (~/.pyartisan/plugins), usage tracking, hooks loader
├── project/              # Project API (placeholder, belum berisi kode)
├── renderer/             # render_stub (Jinja2)
├── config/               # ~/.pyartisan/config.toml
├── shared/               # doctor
├── utils/                # console, fs, naming
└── templates/
    └── plugin_init/      # skeleton untuk `pyartisan plugin init`
```

Perbedaan dari rancangan awal:

| Rancangan awal | Kenyataan |
|---|---|
| `plugin/base.py`, `plugin/registry.py` | Tidak ada folder `plugin/` |
| `plugin/flask/`, `plugin/fastapi/` | Tidak ada; diganti template eksternal |
| `core/context.py`, `core/detector.py` | Tidak ada |

Tujuan "tidak ada package top-level terpisah per framework" (`flasktool/`, `fastapitool/`) **tercapai**, tetapi dengan cara berbeda dari rancangan.

> **Jangan tertukar:** folder `plugin/` di tabel di atas adalah modul kode untuk plugin framework bawaan (rancangan lama, tidak ada). Itu berbeda dari **sistem plugin untuk pengguna** (`pyartisan plugin ...`) dan **registry global** `~/.pyartisan/plugins/`, yang sudah ada dan dikelola oleh `cli/commands/plugin.py` dan `marketplace/core.py`.

---

# 7. Core Responsibilities

Core tidak mengetahui detail Flask ataupun FastAPI. Core bertanggung jawab terhadap:

| Tanggung jawab | Status | Keterangan |
|---|---|---|
| CLI | Sudah ada | `cli/` |
| Plugin loading | Sebagian | `marketplace/core.py` memuat `hooks.py` plugin lewat `importlib`; tidak ada loader per framework |
| Config | Sudah ada | `config/__init__.py` |
| Template Engine | Sudah ada | `renderer.render_stub` (Jinja2) |
| Logging | Belum ada | Tidak ada modul logging |
| File Utilities | Sudah ada | `utils/fs.py` |
| Prompt | Sebagian | Memakai `click.prompt` / `click.confirm` |
| Output | Sebagian | `utils/console.py` memakai `click.echo`, bukan Rich |
| Shared Helpers | Sudah ada | `utils/naming.py` |

---

# 8. Framework Responsibilities

Setiap framework bertanggung jawab terhadap implementasinya sendiri. Pada kondisi nyata, tanggung jawab ini dipegang oleh **template** (FlaskIQ, FastIQ) lewat `.pyartisan/manifest.yaml`.

Contoh Flask:

| Fungsi | Status |
|---|---|
| Create Project | Sudah ada (`pyartisan new flask <name>`) |
| Generate Model | Sudah ada (diuji: `make model` membuat file dan memperbarui `__init__.py`) |
| Generate Service, Repository, Controller, Routes | Diuji pada FlaskIQ hasil `pyartisan new`: `service`, `repository`, `routes`, dan `controller --type api` berhasil. `controller --type view` gagal di Windows dengan `TemplateNotFound` (issue [pyartisan#6](https://github.com/bijoaja/pyartisan/issues/6)); setelah itu diperbaiki, ia membuat salinan ganda karena template menyimpan dua stub identik (issue [flaskiq#2](https://github.com/bijoaja/flaskiq/issues/2)) |
| Migration | Belum ada di pyartisan |
| Flask CLI Integration | Belum ada di pyartisan |

FastAPI memiliki template sendiri. Begitu pula framework lain.

---

# 9. CLI Design

> Command aktual memakai `new` (bukan `init`) dan `make <target> <name>` dengan spasi (bukan `make:target`). Referensi lengkap ada di [CLI.md](CLI.md).

## Project Creation

```
pyartisan new flask myapp

pyartisan new fastapi api
```

---

## Generate

```
pyartisan make model Post
pyartisan make controller Post --type api
```

Lihat [Generator Kode (`make`)](CLI.md#3-generator-kode-make). Framework **tidak** dideteksi otomatis dari file (lihat §10); framework ditentukan sekali saat `pyartisan new` dan disimpan di `.pyartisan/project.yaml` dan `.pyartisan/manifest.yaml`.

---

## Explicit Framework

Rancangan memilih framework lewat `--framework` di `make`: **Belum ada**. `make` tidak punya flag itu; target ditentukan oleh `.pyartisan/manifest.yaml` di project aktif.

---

## Config

```
pyartisan config

pyartisan config show

pyartisan config set <key> <value>

pyartisan config reset
```

---

## Doctor

```
pyartisan doctor
```

Memeriksa:

* Python (minimal 3.10)
* uv (opsional; tidak membuat doctor gagal bila tidak ada)
* Pip (tidak membuat doctor gagal bila tidak ada tetapi uv tersedia)
* Git
* Virtual Environment

---

## Version

```
pyartisan version
```

---

## Command lain yang ada di kode tetapi tidak ada di rancangan awal

`pyartisan serve`, `pyartisan build`, dan grup `pyartisan plugin`. Lihat [CLI.md](CLI.md).

---

# 10. Framework Detection

> **Belum ada.** Tidak ada `detector.py` maupun deteksi berbasis isi file di kode saat ini. Framework ditentukan eksplisit sekali di `pyartisan new <framework> <name>` dan dibaca kembali dari `.pyartisan/project.yaml` / `.pyartisan/manifest.yaml`. Bagian di bawah adalah rancangan yang belum diimplementasikan.

Saat command dijalankan:

```
pyartisan make controller Post
```

Core melakukan deteksi.

Prioritas:

## Flask

```
app.py

create_app()

Flask(
```

---

## FastAPI

```
main.py

FastAPI(
```

---

## Django

```
manage.py

settings.py
```

---

Jika gagal:

```
Project framework cannot be detected.

Please specify:

--framework flask
```

---

# 11. Plugin Loader

> **Belum ada** dalam bentuk rancangan. Tidak ada `load_plugin(framework)`, `FlaskPlugin`, `FastAPIPlugin`, atau `DjangoPlugin`.

Rancangan:

```
framework = detect()

↓

load_plugin(framework)

↓

execute()
```

Kondisi nyata: yang dimuat hanyalah `hooks.py` milik plugin yang di-apply (`marketplace/core.py::_load_hooks`), lewat `importlib`. Lihat [HOW_TO_CREATE_PLUGIN.md](HOW_TO_CREATE_PLUGIN.md).

---

# 12. Shared Components

Semua framework menggunakan:

## File Generator

Status: **Sudah ada** (`utils/fs.py`, `renderer.render_stub`).

* mkdir
* copy
* render template

---

## Jinja Template Engine

Status: **Sudah ada.** Semua template menggunakan engine yang sama.

---

## Console Output

Status: **Sebagian.** Rancangan menyebut Rich; kode memakai `click.echo` lewat `utils/console.py`.

---

## Prompt

Status: **Sebagian.** Memakai `click.prompt` dan `click.confirm`.

---

## Config Reader

Status: **Sudah ada.** Shared.

---

## Logging

Status: **Belum ada.**

---

# 13. Template Management

Rancangan: template di-clone dari repository GitHub; framework hanya membaca template miliknya.

Kondisi nyata (**Sudah ada**): `dispatch_new()` di `core/engine.py` men-clone template lewat `git clone`. URL template disimpan di `~/.pyartisan/config.toml` (`templates.flask`, `templates.fastapi`) dan diubah dengan `pyartisan config set templates.<framework> <url>`.

Catatan: `~/.pyartisan/templates/<template>/<versi>/template.yaml` dibaca oleh `ProjectContext`, tetapi **tidak ada kode yang mengisinya**. Lihat [HOW_TO_CREATE_PLUGIN.md](HOW_TO_CREATE_PLUGIN.md).

---

# 14. Configuration

Lokasi:

```
~/.pyartisan/config.toml
```

Contoh

```
theme = "default"

author = ""

license = "MIT"

default_framework = "flask"

[templates]
flask = "https://github.com/bijoaja/flaskiq.git"
fastapi = "https://github.com/bijoaja/fastiq.git"
```

Status: **Sudah ada.** Hanya `templates.*` yang dibaca command lain (`new`). `theme`, `author`, `license`, dan `default_framework` tersimpan tetapi belum dibaca command mana pun.

---

# 15. Coding Standard

Semua framework wajib mengikuti template yang sudah di-clone.

Sehingga developer mudah berpindah framework.

---

# 16. Migration Strategy

| Tahap | Rencana | Status |
|---|---|---|
| 1 | Rename repository FlaskArtisan menjadi PyArtisan | Sudah ada |
| 2 | Tambahkan Core `pyartisan/` | Sudah ada |
| 3 | CLI dipindahkan ke Core | Sudah ada |
| 4 | FlaskTool menjadi plugin Flask, tanpa perubahan behavior | Sebagian: Flask menjadi template FlaskIQ + manifest, bukan plugin di dalam pyartisan |
| 5 | Tambahkan struktur FastAPI, belum perlu implementasi | Sebagian: hanya URL template FastIQ di config |

---

# 17. Non Functional Requirements

## Maintainability

Framework tidak saling bergantung. Status: **Sebagian.** `core/plugin_engine.py` (`ProjectContext`) masih memuat percabangan `fastapi` / `flask` dan path fallback masing-masing.

---

## Extensibility

Framework baru cukup menambah module. Status: **Sebagian.** Framework baru ditambahkan lewat template repo + URL di config, tanpa mengubah `core/`. Namun `ProjectContext` belum ikut generik.

---

## Testability

Setiap framework dapat diuji secara independen. Status: **Terimplementasi.** Test suite modular berbasis pytest di `tests/` (`uv run pytest`) dengan multi-OS CI.

---

## Performance

CLI startup < 500 ms (target untuk perintah ringan). Status: **Belum tercapai di Windows.** `pyartisan version` terukur sekitar 1,0 detik (989, 982, 1032 ms) pada Windows 11 dengan instalasi `uv tool`. Pengukuran di Linux/macOS belum dilakukan.

---

## Compatibility

* Python 3.10+: dideklarasikan di `pyproject.toml` (`requires-python`)
* Windows: sudah dipakai dan diuji (perbaikan encoding UTF-8 dan junction plugin sudah masuk)
* Linux, macOS: belum diverifikasi secara manual; tidak ada CI

---

# 18. Roadmap

## v1

| Item | Status |
|---|---|
| Refactor menjadi PyArtisan | Sudah ada |
| Core CLI | Sudah ada |
| Flask Module | Sebagian (template FlaskIQ) |
| Struktur FastAPI | Sebagian (URL template FastIQ) |
| Struktur Django | Belum ada. Django hanya menjadi pilihan di `plugin init` |
| Shared Components | Sebagian (lihat §12) |
| Dukungan uv | Sudah ada (`uv tool install`, `uvx`, `new` memakai uv bila tersedia) |

---

## v2

* AI Generator
* MCP Server
* AI Code Review
* AI Refactoring
* AI Project Analysis

---

## v3

* VS Code Extension
* JetBrains Plugin
* Interactive Wizard
* Marketplace Template

---

## v4

* Multi-language Support
* Remote Project Management
* Cloud Sync
* Team Collaboration

---

# 19. Success Criteria

Refactor dianggap berhasil apabila:

| Kriteria | Status |
|---|---|
| Seluruh fitur FlaskArtisan tetap berjalan melalui CLI baru (`pyartisan`) | Tidak dapat diverifikasi dari repo ini (kode FlaskArtisan lama tidak ada di sini) |
| Core CLI tidak memiliki kode yang spesifik terhadap Flask, FastAPI, atau Django | Sebagian: `engine.py` generik, tetapi `plugin_engine.py` masih punya percabangan `fastapi` / `flask` |
| Penambahan framework baru dapat dilakukan tanpa mengubah arsitektur inti | Sebagian: bisa lewat template + config |
| Struktur kode mendukung pengembangan fitur AI dan MCP | Belum ada |
| Dokumentasi dan struktur proyek cukup jelas sehingga kontributor dapat menambahkan dukungan framework baru | Sebagian: lihat [CONTRIBUTING.md](CONTRIBUTING.md) |

---

# Lampiran: Prinsip Desain

1. **Core bersifat framework-agnostic.**
2. **Semua implementasi spesifik framework berada pada modul terpisah.**
3. **Kode umum dipusatkan di `pyartisan/core` atau `pyartisan/shared`.**
4. **CLI bersifat konsisten di semua framework.**
5. **Arsitektur disiapkan sejak awal untuk mendukung AI Agent dan MCP tanpa memerlukan refactor besar di masa depan.**
