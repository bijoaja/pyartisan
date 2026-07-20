# Tutorial Plugin PyArtisan (Multi-Framework)

> **Version:** 1.0
> **Target Audience:** Plugin Developer

---

# Overview

PyArtisan menyediakan **Plugin System** yang memungkinkan developer menambahkan fitur baru tanpa mengubah source code PyArtisan.

Plugin dapat digunakan untuk:

* Menambahkan generator
* Menambahkan service
* Menambahkan module
* Integrasi third-party (Midtrans, Xendit, Firebase, dll)
* Menambahkan command CLI
* Menambahkan Docker configuration
* Menambahkan CI/CD
* Menambahkan authentication
* Menambahkan observability
* dan fitur lainnya.

Plugin dirancang agar **tidak bergantung pada struktur project framework tertentu**.

Framework yang didukung:

* FastAPI
* Flask
* Django

PyArtisan Engine akan menerjemahkan abstraksi plugin menjadi implementasi yang sesuai dengan framework target.

---

# Plugin Architecture

Plugin **tidak boleh** mengakses file project secara langsung.

Contoh yang **tidak diperbolehkan**:

```python
open("app/services/payment.py")
```

atau

```python
shutil.copy(
    "service.py",
    "app/services/service.py"
)
```

Karena struktur project setiap framework berbeda.

Sebagai gantinya gunakan **Project API**.

```python
project.create_service(...)
```

PyArtisan Engine yang menentukan lokasi file berdasarkan framework.

---

# Plugin Development Workflow

Pengembangan plugin terdiri dari beberapa tahap:

```text
Create Plugin
      │
      ▼
Validate Plugin
      │
      ▼
Link Plugin (Development Mode)
      │
      ▼
Apply Plugin
      │
      ▼
Run Tests
      │
      ▼
Publish to GitHub / Marketplace
```

---

# Scaffold Plugin Baru (`pyartisan plugin init`)

Daripada membuat struktur folder di atas secara manual, jalankan:

```bash
pyartisan plugin init payment-midtrans
```

CLI akan menanyakan framework target (`fastapi`/`flask`/`django`/`all`),
lalu langsung membuat `manifest.yaml`, `hooks.py` (skeleton kosong dengan
komentar panduan Project API), `README.md`, `LICENSE`, dan folder
`stubs/<framework>/` kosong untuk tiap framework yang dipilih — plus
langsung mendaftarkan plugin ke registry lokal dalam mode dev (setara
`pyartisan plugin install --local`). Tinggal isi `hooks.py` dan `stubs/`,
lalu langsung uji dengan `pyartisan plugin apply payment-midtrans` di
project sandbox.

---

# Project Structure

Struktur plugin yang direkomendasikan

```text
payment-midtrans/

├── manifest.yaml
├── README.md
├── LICENSE
├── hooks.py
│
├── stubs/
│   ├── fastapi/
│   │   ├── service.py.jinja
│   │   └── router.py.jinja
│   │
│   ├── flask/
│   │   ├── service.py.jinja
│   │   └── blueprint.py.jinja
│   │
│   └── django/
│       ├── service.py.jinja
│       └── views.py.jinja
│
├── assets/
│
└── tests/
```

---

# manifest.yaml

Contoh

```yaml
id: payment-midtrans

name: Midtrans Payment Plugin

version: 1.0.0

description: Midtrans integration

author: Community

dependencies:

  pip:

    - midtrans-client

    - httpx
```

---

# hooks.py

Semua logika plugin berada di sini.

Contoh

```python
def after_install(project):

    framework = project.framework

    if framework == "fastapi":

        project.create_service(
            name="midtrans",
            stub_path="stubs/fastapi/service.py.jinja"
        )

        project.register_router("midtrans")
```

---

# Project API

Plugin menggunakan API berikut.

## Framework

```python
project.framework
```

Return

```
fastapi

flask

django
```

---

## Create Service

```python
project.create_service(
    name="payment",
    stub_path="..."
)
```

---

## Create Model

```python
project.create_model(...)
```

---

## Create Repository

```python
project.create_repository(...)
```

---

## Create Module

```python
project.create_module(...)
```

---

## Register Router

```python
project.register_router(...)
```

---

## Register Blueprint

```python
project.register_blueprint(...)
```

---

## Add Environment Variable

```python
project.add_env(
    "MIDTRANS_KEY",
    "..."
)
```

---

## Add Dependency

```python
project.add_dependency(
    "midtrans-client"
)
```

---

## Add Configuration

```python
project.update_config(...)
```

---

# Development Mode

Saat mengembangkan plugin, **tidak disarankan** menginstal plugin dari GitHub setiap kali melakukan perubahan.

Gunakan **Development Mode**.

Misalnya plugin berada di

```text
~/Projects/payment-midtrans
```

Jalankan

```bash
pyartisan plugin link ~/Projects/payment-midtrans
```

atau

```bash
pyartisan plugin dev ~/Projects/payment-midtrans
```

PyArtisan akan membuat symbolic link ke direktori plugin.

Contoh

```text
~/.pyartisan/plugins/

payment-midtrans
    ─────────────►
~/Projects/payment-midtrans
```

Keuntungan:

* Tidak perlu install ulang
* Perubahan langsung digunakan
* Cocok untuk proses development

---

# Membuat Project Sandbox

Untuk menguji plugin, buat project kosong.

Contoh

```bash
pyartisan new sandbox --framework fastapi
```

Masuk ke project

```bash
cd sandbox
```

Apply plugin

```bash
pyartisan plugin apply payment-midtrans
```

Kemudian jalankan project.

Misalnya

```bash
uvicorn app.main:app --reload
```

---

# Validasi Plugin

Sebelum plugin dijalankan, lakukan validasi.

```bash
pyartisan plugin validate
```

PyArtisan akan memeriksa:

* manifest.yaml
* hooks.py
* folder stubs
* dependency
* semantic version
* plugin id
* framework support
* hook function
* syntax template

Output

```text
✔ Manifest

✔ Hooks

✔ Templates

✔ Version

✔ Dependencies

Plugin is valid
```

Jika terdapat error

```text
✖ Missing stub

stubs/fastapi/service.py.jinja
```

---

# Testing Plugin

Untuk memastikan plugin bekerja dengan baik.

```bash
pyartisan plugin test
```

PyArtisan akan

1. Membuat temporary project
2. Install plugin
3. Apply plugin
4. Generate source code
5. Menjalankan migration (jika ada)
6. Menjalankan test
7. Menjalankan server
8. Menghapus temporary project

Contoh output

```text
Creating temporary project...

Installing plugin...

Applying plugin...

Running tests...

✔ Tests passed

Running server...

✔ Health endpoint OK

Plugin successfully tested.
```

---

# Multi Framework Test

Plugin dapat diuji terhadap semua framework.

```bash
pyartisan plugin test --all
```

atau

```bash
pyartisan plugin test \
    --framework fastapi \
    --framework flask \
    --framework django
```

Output

```text
FastAPI

✔ PASS

Flask

✔ PASS

Django

✔ PASS
```

Jika ada kegagalan

```text
FastAPI

✔ PASS

Flask

✖ Missing Blueprint Registration

Django

✔ PASS
```

Developer dapat mengetahui framework mana yang belum kompatibel.

---

# Plugin Doctor

Untuk analisis lengkap plugin.

```bash
pyartisan plugin doctor
```

Contoh

```text
Plugin

✔ Manifest

✔ Hooks

✔ Dependencies

✔ Assets

✔ Templates

Framework Support

✔ FastAPI

✔ Flask

✖ Django

Reason

Missing:

stubs/django/
```

---

# Local Installation

Untuk mensimulasikan instalasi seperti pengguna akhir.

```bash
pyartisan plugin install ~/Projects/payment-midtrans
```

Plugin akan disalin ke direktori plugin PyArtisan.

Contoh

```text
~/.pyartisan/plugins/
```

Mode ini berguna untuk memastikan proses instalasi berjalan dengan benar.

---

# Install from GitHub

```bash
pyartisan plugin install https://github.com/username/payment-midtrans
```

PyArtisan akan:

1. Clone repository
2. Validasi `manifest.yaml`
3. Install dependency
4. Registrasi plugin
5. Menjalankan hook `after_install`

---

# Install from Marketplace

```bash
pyartisan plugin install payment-midtrans
```

Marketplace akan mencari plugin berdasarkan `id` pada `manifest.yaml`.

---

# Publish Plugin

Setelah plugin selesai dikembangkan.

Push ke GitHub

```bash
git push origin main
```

Kemudian publish

```bash
pyartisan plugin publish
```

PyArtisan akan

* memvalidasi plugin
* membuat package
* upload metadata
* submit ke Marketplace

---

# Marketplace Validation

Marketplace secara otomatis melakukan validasi sebelum plugin dipublikasikan.

Checklist:

* Valid manifest
* Semantic Version
* README tersedia
* LICENSE tersedia
* Hook valid
* Stub tersedia
* Tidak ada file berbahaya
* Dependency valid
* Kompatibel dengan versi PyArtisan

Plugin yang gagal validasi tidak akan dipublikasikan.

---

# Best Practices

* Jangan menulis path absolut ke project pengguna.
* Gunakan **Project API** untuk semua operasi file.
* Pisahkan stub berdasarkan framework.
* Pastikan plugin dapat dijalankan lebih dari satu kali (idempotent).
* Sertakan dokumentasi penggunaan dan konfigurasi.
* Tulis unit test untuk hook yang kompleks.
* Uji plugin minimal pada seluruh framework yang diklaim didukung.
* Gunakan Semantic Versioning (`MAJOR.MINOR.PATCH`).
* Hindari modifikasi langsung terhadap file yang bukan dikelola oleh Project API.

---

# Recommended Development Workflow

```text
Create Plugin
      │
      ▼
pyartisan plugin validate
      │
      ▼
pyartisan plugin link .
      │
      ▼
pyartisan plugin test --all
      │
      ▼
Fix Issues (if any)
      │
      ▼
Commit Changes
      │
      ▼
Push to GitHub
      │
      ▼
pyartisan plugin publish
      │
      ▼
Marketplace Validation
      │
      ▼
Available for Installation
```

## Rekomendasi Tambahan

Agar ekosistem plugin PyArtisan lebih kuat dan stabil, saya menyarankan menambahkan dua fitur lagi ke spesifikasi:

1. **Plugin SDK (`pyartisan.sdk`)**
   Sediakan package Python resmi yang berisi `ProjectContext`, decorator hook, exception, dan helper API. Dengan begitu developer plugin cukup melakukan:

   ```python
   from pyartisan.sdk import hook

   @hook.after_install
   def install(project):
       ...
   ```

   dibanding harus mengandalkan nama fungsi tertentu.

2. **`pyartisan plugin init`** — ✅ sudah diimplementasikan, lihat bagian
   "Scaffold Plugin Baru" di atas.
