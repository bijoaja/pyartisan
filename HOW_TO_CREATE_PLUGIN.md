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

> **Catatan implementasi:** `create_service`/`register_router` mencoba
> membaca `template.yaml` dari `~/.pyartisan/templates/<template>/<version>/`
> (registry global) untuk path/marker kustom. File ini **belum pernah
> diisi/diprovisikan** oleh command mana pun saat ini, jadi selalu kosong
> (`{}`) dan kedua method jatuh ke path fallback hardcoded
> (`app/service/{module}.py` untuk Flask, marker `# pyartisan:routers` di
> `app/main.py`). Jangan bergantung pada kustomisasi `template.yaml` sampai
> fitur ini benar-benar tersambung.

---

# Plugin Development Workflow

Alur yang **sudah berjalan hari ini**:

```text
pyartisan plugin init <name>   (scaffold + auto-link ke registry dev mode)
      │
      ▼
Edit hooks.py & stubs/
      │
      ▼
pyartisan plugin apply <name>  (di project sandbox)
      │
      ▼
Uji manual (jalankan project, cek hasil)
      │
      ▼
git push (publish manual ke GitHub — `pyartisan plugin publish` belum ada)
```

> Tahap **Validate Plugin** dan **Run Tests** otomatis (`plugin validate`,
> `plugin test`) yang disebut di versi awal dokumen ini **belum
> diimplementasikan** — lihat catatan "Belum diimplementasikan" di
> masing-masing bagian di bawah.

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

`project` yang diterima hook adalah instance `ProjectContext`
(`src/pyartisan/core/plugin_engine.py`). Berikut method yang **benar-benar
ada saat ini** — jangan panggil selain ini di `hooks.py`.

## Framework

```python
project.framework
```

Return salah satu dari `"fastapi"`, `"flask"`, `"django"` (dibaca dari
`.pyartisan/project.yaml`).

---

## Create Service

```python
project.create_service(
    name="payment",
    stub_path="stubs/fastapi/service.py.jinja"   # path relatif ke root plugin
)
```

Merender file stub Jinja2 ke lokasi service sesuai `template.yaml` project
(atau fallback `app/service/{module}.py` / `app/services/{module}.py`).

---

## Register Router

```python
project.register_router("payment")
```

Menyisipkan baris import + registrasi router/blueprint di file & marker yang
ditentukan `template.yaml` (fallback: `app/main.py`,
marker `# pyartisan:routers`). Untuk Flask, method ini yang sama menulis
baris `register_blueprint(...)` — **tidak ada** method `register_blueprint`
terpisah.

---

## Add Dependency

```python
project.add_dependency("midtrans-client")
```

Menambahkan baris ke `requirements.txt` project jika file itu ada.

---

> ### Belum diimplementasikan (Planned API)
>
> Method di bawah ini **tidak ada** di `ProjectContext` saat ini. Jangan
> memanggilnya di `hooks.py` — akan gagal dengan `AttributeError`. Tercantum
> di sini sebagai rencana API ke depan:
>
> ```python
> project.create_model(...)
> project.create_repository(...)
> project.create_module(...)
> project.add_env("MIDTRANS_KEY", "...")
> project.update_config(...)
> ```

---

# Development Mode

Saat mengembangkan plugin, **tidak disarankan** menginstal plugin dari GitHub setiap kali melakukan perubahan.

`pyartisan plugin link` dan `pyartisan plugin dev` **tidak ada sebagai
command terpisah**. Dev-mode symlink dibuat otomatis oleh salah satu dari
dua command berikut:

```bash
# Kalau plugin baru dibuat di direktori kerja saat ini
pyartisan plugin init payment-midtrans

# Kalau plugin sudah ada di path lain
pyartisan plugin install payment-midtrans --local ~/Projects/payment-midtrans
```

Keduanya membuat symlink yang sama:

```text
~/.pyartisan/plugins/

payment-midtrans/dev
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
pyartisan new fastapi sandbox
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

> **Belum diimplementasikan.** `pyartisan plugin validate` tidak ada di CLI
> saat ini. Command yang tersedia sekarang untuk pemeriksaan kesehatan
> adalah `pyartisan plugin doctor` (lihat bagian "Plugin Doctor" di bawah,
> dan catatan perbedaan scope-nya). Bagian di bawah ini adalah rencana API
> validasi ke depan.

Rencana: sebelum plugin dijalankan, lakukan validasi.

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

> **Belum diimplementasikan.** `pyartisan plugin test` tidak ada di CLI
> saat ini. Untuk sekarang, uji plugin secara manual lewat alur "Membuat
> Project Sandbox" di atas (`plugin apply` lalu jalankan project-nya
> langsung). Bagian di bawah ini adalah rencana ke depan.

Rencana: untuk memastikan plugin bekerja dengan baik secara otomatis.

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

> **Belum diimplementasikan** — sama seperti `plugin test` di atas.

Rencana: plugin dapat diuji terhadap semua framework.

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

`pyartisan plugin doctor` **sudah ada**, tapi scope-nya berbeda dari
deskripsi rencana sebelumnya: perintah ini mendiagnosis kesehatan **project
aktif** (bukan struktur plugin itu sendiri) — dijalankan di dalam project
yang sudah punya `.pyartisan/project.yaml`.

```bash
pyartisan plugin doctor
```

Yang benar-benar diperiksa (lihat `cli/commands/plugin.py`):

* **Manifest** — `project.yaml` punya `framework.name`.
* **Framework** — `ProjectContext` berhasil dibuat.
* **Template Metadata** — `template.yaml` template project ditemukan di
  `~/.pyartisan/templates/<template>/<version>/template.yaml` (registry
  global — bukan di dalam plugin).
* **Dependencies** — tiap plugin yang `applied` ke project ini: dependency
  pip di `manifest.yaml`-nya sudah ada di `requirements.txt` project.
* **Marker** — marker registrasi router (mis. `# pyartisan:routers`) masih
  ada di file target sesuai `template.yaml`.

Diakhiri dengan `Plugin is valid` atau `Plugin has issues, see above.`.

Pemeriksaan struktur plugin itu sendiri (assets, per-framework stub
coverage seperti contoh di bawah) **belum diimplementasikan**:

```text
Framework Support

✔ FastAPI
✔ Flask
✖ Django

Reason
Missing: stubs/django/
```

---

# Local Installation

Untuk mensimulasikan instalasi seperti pengguna akhir, gunakan flag
`--local` (bukan path sebagai argumen langsung):

```bash
pyartisan plugin install payment-midtrans --local ~/Projects/payment-midtrans
```

Ini membuat symlink dev-mode ke `~/.pyartisan/plugins/payment-midtrans/dev/`
(mekanisme yang sama dijelaskan di "Development Mode" — bukan copy fisik).
Mode ini berguna untuk memastikan proses instalasi berjalan dengan benar.

---

# Install from GitHub

Format argumen harus `github-username/repo-name` (bukan URL penuh):

```bash
pyartisan plugin install username/payment-midtrans
```

PyArtisan akan:

1. Clone `https://github.com/username/payment-midtrans.git` ke
   `~/.pyartisan/plugins/payment-midtrans/1.0.0/`
2. Membaca `manifest.yaml` (gagal jika tidak ada)

Instalasi dependency, registrasi ke project, dan hook `after_install`
**baru dijalankan saat `pyartisan plugin apply <name>`** — bukan saat
`install`. `install` hanya menaruh plugin ke registry global, tidak
menyentuh project mana pun.

---

# Install from Marketplace

```bash
pyartisan plugin install payment-midtrans --license valid-xxxxxx
```

Verifikasi lisensi saat ini **mocked** — `_verify_blockchain_license` di
`marketplace/core.py` menerima kunci apa pun yang berawalan `valid-`.
Integrasi Blockchain API/smart contract nyata belum ada.

---

# Publish Plugin

> **Belum diimplementasikan.** `pyartisan plugin publish` tidak ada di CLI
> saat ini — tidak ada Marketplace submission otomatis.

Untuk sekarang, "publikasi" plugin cukup lewat push manual ke GitHub:

```bash
git push origin main
```

Pengguna lain menginstalnya dengan `pyartisan plugin install
<github-user>/<repo-name>`. Rencana ke depan (`plugin publish`) akan:

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

Alur nyata hari ini (command yang benar-benar ada):

```text
pyartisan plugin init <name>
      │
      ▼
Edit hooks.py & stubs/
      │
      ▼
pyartisan plugin apply <name>   (di project sandbox)
      │
      ▼
Uji manual, perbaiki jika ada masalah
      │
      ▼
Commit & push ke GitHub
      │
      ▼
Pengguna lain: pyartisan plugin install <user>/<repo>
```

Rencana ke depan (belum ada): `plugin validate`, `plugin test --all`,
`plugin publish`, dan Marketplace validation otomatis.

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
