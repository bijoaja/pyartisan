# Product Requirements Document (PRD)

## PyArtisan v1.0

**Refactor FlaskArtisan menjadi Multi-Framework AI Development Toolkit**

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

Karena itu, FlaskArtisan akan direfactor menjadi **PyArtisan**.

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

---

# 4. Scope v1

## Included

* Refactor branding
* Core CLI
* Flask Module
* FastAPI Module (structure only) (SOON Template)
* Shared Core
* Shared Utilities
* Plugin Architecture

---

## Excluded

* MCP
* AI Agent
* Deployment
* Kubernetes
* VSCode Extension

Semua akan menjadi roadmap v2.

---

# 5. Arsitektur Baru

## Saat ini

```
FlaskArtisan

↓

Flask CLI
```

## Target

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

---

# 6. Struktur Project

```
pyartisan/

├── src/
│
└── pyartisan/
    │
    ├── cli/                  # thin click parser only
    │
    ├── core/                 # engine.py (dispatch), context.py, detector.py, exceptions.py
    │
    ├── plugin/                # base.py (kontrak), registry.py (loader)
    │   ├── flask/              # plugin bawaan Flask
    │   │   └── commands/
    │   └── fastapi/            # plugin bawaan FastAPI (structure only, v1)
    │       └── commands/
    │
    ├── project/               # Project API (placeholder v1)
    │
    ├── renderer/               # Jinja2 template engine (placeholder v1)
    │
    ├── marketplace/            # plugin marketplace (di luar scope v1)
    │
    ├── config/
    │
    ├── utils/
    │
    └── shared/
```

Tidak ada lagi package top-level terpisah per framework (`flasktool/`, `fastapitool/`) — semua plugin framework konkret hidup nested di dalam `pyartisan/plugin/`.

> **Catatan implementasi:** goal "tidak ada package top-level per
> framework" sudah tercapai, tapi caranya berbeda dari desain di atas.
> Tidak ada folder `pyartisan/plugin/flask/` atau `pyartisan/plugin/fastapi/`
> di `src/pyartisan/`. Sebagai gantinya, Flask/FastAPI diimplementasikan
> sebagai template repo eksternal (FlaskIQ, FastIQ) yang di-clone oleh
> `pyartisan new`, dan generator dibaca dari `.pyartisan/manifest.yaml`
> milik project — bukan built-in plugin nested di `core`. `detector.py`
> juga belum ada (lihat §10). Struktur nyata saat ini: `cli/`, `core/`,
> `project/` (placeholder), `renderer/`, `marketplace/`, `config/`, `utils/`,
> `shared/` — tanpa `plugin/`.

---

# 7. Core Responsibilities

Core tidak mengetahui detail Flask ataupun FastAPI.

Core hanya bertanggung jawab terhadap:

* CLI
* Plugin loading
* Config
* Template Engine
* Logging
* File Utilities
* Prompt
* Output
* Shared Helpers

---

# 8. Framework Responsibilities

Setiap framework bertanggung jawab terhadap implementasinya sendiri.

Contoh Flask:

* Create Project
* Generate CRUD
* Generate Blueprint
* Generate Model
* Generate Service
* Generate Repository
* Migration
* Flask CLI Integration

FastAPI memiliki implementasi sendiri.

Begitu pula framework lain.

---

# 9. CLI Design

> **Catatan implementasi (per repo saat ini):** command aktual memakai
> `new` (bukan `init`) dan `make <target> <name>` dengan spasi (bukan
> `make:target`) — lihat [CLI.md](CLI.md) untuk referensi command yang
> sudah sinkron dengan kode.

## Project Creation

```
pyartisan new flask myapp

pyartisan new fastapi api
```

---

## Generate

```
Baca CLI.md section '## 3. Generator Kode (make)'
```

Framework **tidak** dideteksi otomatis dari file (lihat catatan di §10) —
ditentukan sekali saat `pyartisan new` dan disimpan di
`.pyartisan/project.yaml` / `.pyartisan/manifest.yaml`.

---

## Explicit Framework

Rencana desain ini (memilih framework lewat `--framework` di `make`)
**belum diimplementasikan**. `make` tidak punya flag `--framework` — target
project selalu ditentukan oleh `.pyartisan/manifest.yaml` yang sudah ada
di dalam project aktif.

---

## Config

```
pyartisan config

pyartisan config show

pyartisan config reset
```

---

## Doctor

```
pyartisan doctor
```

Memeriksa:

* Python
* Pip
* Git
* Virtual Environment

---

## Version

```
pyartisan version
```

---

# 10. Framework Detection

> **Belum diimplementasikan.** Tidak ada `detector.py` maupun deteksi
> berbasis isi file (`Flask(`, `FastAPI(`, dst.) di kode saat ini. Framework
> project ditentukan secara eksplisit sekali di `pyartisan new <framework>
> <name>` dan dibaca kembali dari `.pyartisan/project.yaml` /
> `.pyartisan/manifest.yaml` oleh command lain. Bagian di bawah adalah
> desain yang direncanakan.

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

Core memanggil module berdasarkan framework.

Contoh

```
framework = detect()

↓

load_plugin(framework)

↓

execute()
```

Misalnya

```
FlaskPlugin

FastAPIPlugin

DjangoPlugin
```

---

# 12. Shared Components

Semua framework menggunakan:

## File Generator

* mkdir
* copy
* render template

---

## Jinja Template Engine

Semua template menggunakan engine yang sama.

---

## Console Output

Misalnya Rich.

Semua framework menggunakan formatter yang sama.

---

## Prompt

Semua menggunakan prompt yang sama.

---

## Config Reader

Shared.

---

## Logging

Shared.

---

# 13. Template Management

```
Template di clone dari repository github (seperti konsep pada pyartisan/plugin/flask/commands/init_project)
```

Framework hanya membaca template miliknya.

> **Catatan implementasi:** clone dari GitHub sudah berjalan, tapi lewat
> `dispatch_new()` di `core/engine.py` (bukan modul
> `pyartisan/plugin/flask/commands/init_project` — path itu tidak ada).
> URL template disimpan di `~/.pyartisan/config.toml` (`templates.flask`,
> `templates.fastapi`), diubah lewat `pyartisan config set templates.<fw>
> <url>`.

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
```

---

# 15. Coding Standard

Semua framework wajib mengikuti template yang sudah di clone.

Sehingga developer mudah berpindah framework.
---

# 16. Migration Strategy

## Tahap 1

Rename repository

```
FlaskArtisan

↓

PyArtisan
```

---

## Tahap 2

Tambahkan Core

```
pyartisan/
```

---

## Tahap 3

CLI dipindahkan ke Core.

---

## Tahap 4

FlaskTool menjadi plugin Flask.

Tidak ada perubahan behavior.

---

## Tahap 5

Tambahkan struktur FastAPI.

Belum perlu implementasi.


---

# 17. Non Functional Requirements

## Maintainability

Framework tidak saling bergantung.

---

## Extensibility

Framework baru cukup menambah module.

---

## Testability

Setiap framework dapat diuji secara independen.

---

## Performance

CLI startup < 500 ms (target untuk perintah ringan).

---

## Compatibility

* Python 3.10+
* Linux
* macOS
* Windows

---

# 18. Roadmap

## v1

* ✅ Refactor menjadi PyArtisan
* ✅ Core CLI
* ✅ Flask Module
* ✅ Struktur FastAPI
* ✅ Struktur Django
* ✅ Shared Components

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

* Seluruh fitur FlaskArtisan tetap berjalan melalui CLI baru (`pyartisan`).
* Core CLI tidak memiliki kode yang spesifik terhadap Flask, FastAPI, atau Django.
* Penambahan framework baru dapat dilakukan tanpa mengubah arsitektur inti.
* Struktur kode mendukung pengembangan fitur AI dan MCP pada versi berikutnya.
* Dokumentasi dan struktur proyek cukup jelas sehingga kontributor dapat menambahkan dukungan framework baru dengan mudah.

---

# Lampiran: Prinsip Desain

1. **Core bersifat framework-agnostic.**
2. **Semua implementasi spesifik framework berada pada modul terpisah.**
3. **Kode umum dipusatkan di `pyartisan/core` atau `pyartisan/shared`.**
4. **CLI bersifat konsisten di semua framework.**
5. **Arsitektur disiapkan sejak awal untuk mendukung AI Agent dan MCP tanpa memerlukan refactor besar di masa depan.**
