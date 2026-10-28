# Tutorial Plugin PyArtisan

> **Bahasa:** Indonesia | [English](../en/HOW_TO_CREATE_PLUGIN.md)
> **Target pembaca:** developer plugin
> **Terakhir diverifikasi terhadap kode:** commit `80b5acc` (2026-10-26)

---

# Gambaran Umum

Plugin PyArtisan adalah folder berisi `manifest.yaml`, `hooks.py`, dan (opsional) file stub. Plugin di-install ke registry global di `~/.pyartisan/plugins/`, lalu diterapkan (`apply`) ke sebuah project. Saat diterapkan, PyArtisan:

1. menjalankan hook `before_install(project)` bila ada,
2. menambahkan dependency pip dari `manifest.yaml` ke `requirements.txt` project,
3. menjalankan hook `after_install(project)` bila ada,
4. mencatat plugin di `.pyartisan/project.yaml`.

Semua logika plugin ada di `hooks.py`. Objek `project` yang diterima hook adalah `ProjectContext` (Project API) yang dijelaskan di bawah.

## Framework yang dikenali

`ProjectContext` membaca nama framework dari `.pyartisan/project.yaml` (`framework.name`). Kode hanya membedakan `fastapi` dan selain itu:

| Framework | Perilaku `create_service` / `register_router` |
|---|---|
| `fastapi` | Path service fallback `app/services/{module}.py`; registrasi memakai `app.include_router(...)` |
| `flask` dan lainnya (termasuk `django`) | Path service fallback `app/service/{module}.py`; registrasi memakai `app.register_blueprint(...)` |

`django` hanya menjadi pilihan saat `pyartisan plugin init`; belum ada perilaku khusus Django di kode.

---

# Batasan yang perlu diketahui

* **Hook adalah kode Python biasa.** `hooks.py` dimuat lewat `importlib` dan berjalan dengan hak penuh pengguna. PyArtisan tidak membatasi akses file dari plugin. Anjuran memakai Project API (bukan `open()` atau `shutil` langsung) adalah praktik yang disarankan, bukan aturan yang ditegakkan.
* **Plugin tidak bisa menambah command CLI.** Tidak ada mekanisme untuk itu. Plugin hanya berjalan lewat hook `apply` dan `remove`.
* **Instal dan apply adalah dua langkah.** `install` hanya menaruh plugin di registry; hook dan dependency baru berjalan saat `apply`.

---

# Alur Kerja Pengembangan

Alur yang tersedia sekarang:

```text
pyartisan plugin init <name>   (scaffold + otomatis ditautkan ke registry, mode dev)
      │
      ▼
Edit hooks.py dan stubs/
      │
      ▼
pyartisan plugin apply <name>  (di project sandbox)
      │
      ▼
Uji manual (jalankan project, periksa hasilnya)
      │
      ▼
git push ke GitHub (publikasi manual)
```

Perintah `plugin validate`, `plugin test`, dan `plugin publish` **belum ada**. Lihat [Rencana](#rencana-belum-diimplementasikan).

---

# Scaffold Plugin Baru (`pyartisan plugin init`)

```bash
pyartisan plugin init payment-midtrans
```

Perintah ini:

1. Menolak berjalan jika folder `./payment-midtrans/` sudah ada.
2. Menanyakan framework target: `fastapi`, `flask`, `django`, atau `all` (default `all`).
3. Membuat `manifest.yaml`, `hooks.py`, `README.md`, dan `LICENSE` dari template bawaan PyArtisan (tanpa koneksi internet).
4. Membuat folder kosong `stubs/<framework>/` (berisi `.gitkeep`) untuk tiap framework yang dipilih.
5. Menautkan plugin ke registry sebagai `~/.pyartisan/plugins/payment-midtrans/dev/` (setara `pyartisan plugin install payment-midtrans --local ./payment-midtrans`).

---

# Struktur Plugin

Hasil `plugin init`:

```text
payment-midtrans/
├── manifest.yaml
├── hooks.py
├── README.md
├── LICENSE
└── stubs/
    ├── fastapi/
    ├── flask/
    └── django/
```

Isi `stubs/` adalah file template Jinja2 milik plugin Anda, misalnya `service.py.jinja`. Nama file dan sub-foldernya bebas; hanya `hooks.py` yang menentukan file mana yang dipakai.

---

# manifest.yaml

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
environment:
  - MIDTRANS_SERVER_KEY
```

| Field | Wajib | Dipakai oleh |
|---|---|---|
| `id` | Ya | Nama plugin di registry dan di `project.yaml` (`id@versi`) |
| `name` | Tidak | Pesan saat `apply`, `plugin info` |
| `version` | Tidak | Entri `id@versi` di `project.yaml`; bila kosong dipakai nama folder versi di registry |
| `description`, `author` | Tidak | `plugin info` |
| `dependencies.pip` | Tidak | Ditambahkan ke `requirements.txt` saat `apply` |
| `environment` | Tidak | Hanya ditampilkan oleh `plugin info`; tidak ada validasi atau penulisan `.env` |

---

# hooks.py

> **Catatan Keamanan:** Hook plugin mengeksekusi kode Python bebas dengan hak akses sistem pengguna. Pastikan hanya men-commit hook yang telah ditinjau keamanannya. Saat pengguna menjalankan `plugin apply`, `update`, atau `remove`, PyArtisan meminta persetujuan eksplisit sebelum menjalankan hook kecuali opsi `--yes` digunakan. Link pengembangan lokal (`plugin install --local` atau `plugin init`) dipercaya tanpa prompt konfirmasi.

Hook yang dikenali:

| Hook | Dipanggil |
|---|---|
| `before_install(project)` | Saat `apply`, sebelum dependency ditambahkan |
| `after_install(project)` | Saat `apply`, setelah dependency ditambahkan |
| `before_remove(project)` | Saat `remove`, sebelum entri dicabut dari `project.yaml` |
| `after_remove(project)` | Saat `remove`, setelah `before_remove` |

Semua hook opsional. Template `plugin init` hanya membuat `after_install` dan `before_remove`.

Contoh:

```python
from pathlib import Path


def after_install(project):
    stub = Path(__file__).parent / "stubs" / project.framework / "service.py.jinja"
    project.create_service(name="midtrans", stub_path=str(stub))
    project.register_router("midtrans")
```

> **Gunakan path absolut untuk `stub_path`**, seperti `Path(__file__).parent / ...` di atas. Lihat catatan di bagian Create Service.

---

# Project API

Objek `project` adalah `ProjectContext` (`src/pyartisan/core/plugin_engine.py`). Hanya anggota berikut yang ada. Memanggil yang lain menimbulkan `AttributeError`.

| Anggota | Keterangan |
|---|---|
| `project.framework` | String dari `.pyartisan/project.yaml` (`framework.name`) |
| `project.project_path` | `Path` ke root project |
| `project.project_config` | Dict isi `.pyartisan/project.yaml` |
| `project.template_config` | Dict isi `template.yaml`; hampir selalu `{}` (lihat catatan) |
| `project.create_service(name, stub_path)` | Render stub Jinja2 menjadi file service |
| `project.register_router(name)` | Sisipkan baris registrasi router/blueprint |
| `project.add_dependency(package_name)` | Tambahkan paket ke `requirements.txt` |

## Create Service

```python
project.create_service(name="payment", stub_path="/path/absolut/ke/service.py.jinja"  # path absolut ke file stub)
```

Merender stub dengan variabel `name`, `name_lower`, `name_title`, `name_snake`, `name_plural`, lalu menulis ke:

* `paths.services` dari `template.yaml` bila ada, atau
* fallback `app/services/{module}.py` (fastapi) / `app/service/{module}.py` (lainnya), dengan `{module}` = `name_lower`.

> **`stub_path` relatif dihitung dari direktori kerja saat ini (root project), bukan dari root plugin.** Jika file stub tidak ditemukan, method ini **tidak menulis apa pun dan tidak menampilkan error**. Terverifikasi: `stub_path="stubs/service.py.jinja"` tidak menghasilkan file, sedangkan path absolut berhasil. Selalu pakai path absolut.

## Register Router

```python
project.register_router("payment")
```

Menyisipkan baris import dan registrasi tepat setelah marker, di file yang ditentukan `template.yaml` (fallback: `app/main.py`, marker `# pyartisan:routers`). Aturan:

* Jika file belum ada, file dibuat berisi marker dan baris tersebut.
* Jika marker tidak ada di file, baris ditambahkan di akhir file.
* Jika baris sudah ada, tidak ada yang berubah (idempoten).

Baris yang disisipkan untuk FastAPI:

```python
from app.modules.payment.router import router as payment_router
app.include_router(payment_router, prefix="/payment")
```

Dan untuk selain FastAPI:

```python
from app.payment.routes import payment_bp
app.register_blueprint(payment_bp)
```

Tidak ada method `register_blueprint` terpisah.

## Add Dependency

```python
project.add_dependency("midtrans-client")
```

Menambahkan baris ke `requirements.txt` project **hanya jika file itu ada**. Pengecekan duplikat memakai pencarian substring: nama yang sudah muncul di mana pun dalam file (termasuk sebagai bagian nama paket lain) dianggap sudah ada.

## Catatan: `template.yaml`

`ProjectContext` mencoba membaca `~/.pyartisan/templates/<template>/<versi>/template.yaml`, tetapi **tidak ada command yang membuat file ini**. Akibatnya `template_config` kosong dan fallback hardcoded selalu dipakai. Jangan bergantung pada kustomisasi `template.yaml`.

Dampak lain: karena tidak ada kode yang menulis `template.yaml`, `pyartisan plugin doctor` menampilkan `✖ Template Metadata` pada project dengan `project.yaml` seperti yang dibuat `pyartisan new`. Terverifikasi pada project hasil `pyartisan new` dari template FlaskIQ maupun FastIQ: keduanya menampilkan `✖ Template Metadata`.

## API yang belum ada

Berikut **belum ada** di `ProjectContext`. Jangan dipanggil di `hooks.py`:

```python
project.create_model(...)
project.create_repository(...)
project.create_module(...)
project.add_env("MIDTRANS_KEY", "...")
project.update_config(...)
```

---

# Mode Development

`pyartisan plugin link` dan `pyartisan plugin dev` tidak ada. Tautan mode dev dibuat oleh salah satu dari:

```bash
# Plugin baru, di direktori kerja saat ini
pyartisan plugin init payment-midtrans

# Plugin yang sudah ada di path lain
pyartisan plugin install payment-midtrans --local ~/Projects/payment-midtrans
```

Hasilnya:

```text
~/.pyartisan/plugins/payment-midtrans/dev  ──►  ~/Projects/payment-midtrans
```

Di Windows tanpa hak membuat symlink, PyArtisan otomatis memakai **junction** (`mklink /J`) sehingga efeknya sama. Perubahan pada source langsung terlihat tanpa install ulang.

Jika sebuah plugin punya folder `dev`, folder itulah yang dipakai `apply` dan `info`, mengalahkan versi lain.

---

# Project Sandbox

Untuk menguji plugin, buat project terpisah:

```bash
pyartisan new flask sandbox
cd sandbox
pyartisan plugin apply payment-midtrans
```

Lalu jalankan project dengan cara yang disediakan template-nya (mis. `pyartisan serve`). Hasil akhir bergantung pada template FlaskIQ/FastIQ yang dipakai.

---

# Perintah Pemeriksaan: `plugin status` dan `plugin doctor`

Keduanya memeriksa **project aktif**, bukan struktur plugin. Dijalankan di folder yang punya `.pyartisan/project.yaml`.

`pyartisan plugin status` menampilkan nama project, framework, dan tiap plugin dengan tanda ✔ atau ✖ (hilang dari registry).

`pyartisan plugin doctor` memeriksa:

* **Manifest**: `project.yaml` punya `framework.name`.
* **Framework**: `ProjectContext` berhasil dibuat.
* **Template Metadata**: `template.yaml` ada di registry global. Lihat catatan di atas: selama tidak ada yang mengisinya, pemeriksaan ini gagal.
* **Dependencies**: tiap dependency pip plugin ada di `requirements.txt`.
* **Marker**: marker router masih ada di file target. Hanya dicek jika `template.yaml` mendefinisikannya.

Keluaran diakhiri `Plugin is valid` atau `Plugin has issues, see above.`

---

# Instalasi Plugin

## Dari path lokal

```bash
pyartisan plugin install payment-midtrans --local ~/Projects/payment-midtrans
```

Membuat tautan dev ke `~/.pyartisan/plugins/payment-midtrans/dev/`, bukan salinan.

## Dari GitHub

Format argumen `github-username/repo-name`, bukan URL penuh:

```bash
pyartisan plugin install username/payment-midtrans
```

PyArtisan melakukan `git clone https://github.com/username/payment-midtrans.git` ke `~/.pyartisan/plugins/payment-midtrans/1.0.0/`, lalu memastikan `manifest.yaml` ada. Versi folder selalu `1.0.0`, tidak diambil dari `manifest.yaml`. Dependency dan hook baru berjalan saat `apply`.

## Dari Marketplace

```bash
pyartisan plugin install payment-midtrans --license valid-xxxxxx
```

Fitur ini **masih tiruan (mock)**. `_verify_blockchain_license` di `marketplace/core.py` menerima kunci apa pun yang berawalan `valid-`, tanpa memanggil Blockchain API. Tidak ada plugin yang diunduh: PyArtisan hanya menulis `manifest.yaml` kosong lokal (`id`, `name`, `version 1.0.0`, dependency `stripe`) ke registry.

---

# Publikasi Plugin

`pyartisan plugin publish` **belum ada**, dan tidak ada pengiriman otomatis ke Marketplace. Publikasi saat ini berarti push manual ke GitHub:

```bash
git push origin main
```

Pengguna lain memasangnya dengan `pyartisan plugin install <github-user>/<repo-name>`.

---

# Praktik yang Disarankan

* Pakai Project API untuk operasi file yang didukungnya, jangan menulis path absolut ke project pengguna.
* Pakai path absolut (`Path(__file__).parent`) untuk `stub_path`.
* Pisahkan stub per framework di `stubs/<framework>/`.
* Buat hook idempoten; `apply` bisa dijalankan lebih dari sekali (`update` memanggil `apply` ulang).
* Sertakan dokumentasi penggunaan dan konfigurasi di `README.md` plugin.
* Gunakan Semantic Versioning (`MAJOR.MINOR.PATCH`) di `manifest.yaml`.

---

# Rencana (belum diimplementasikan)

Hal berikut **tidak ada** di kode saat ini:

* `pyartisan plugin validate`: validasi `manifest.yaml`, `hooks.py`, stub, dan versi.
* `pyartisan plugin test` dan `plugin test --all`: uji otomatis pada project sementara untuk semua framework.
* `pyartisan plugin publish`: pengemasan dan pengiriman ke Marketplace.
* Validasi otomatis Marketplace (manifest, versi, README, LICENSE, hook, stub, kompatibilitas versi PyArtisan).
* Pemeriksaan struktur plugin (cakupan stub per framework) di `plugin doctor`.
* Method Project API tambahan: `create_model`, `create_repository`, `create_module`, `add_env`, `update_config`.
* Gagasan: package `pyartisan.sdk` dengan dekorator hook, sehingga developer tidak bergantung pada nama fungsi tertentu:

  ```python
  from pyartisan.sdk import hook

  @hook.after_install
  def install(project):
      ...
  ```

Lihat juga [PRD.md](PRD.md) dan rancangan Project API di `docs/superpowers/specs/2026-07-22-project-api-consolidation-design.md`.
