# PyArtisan CLI — Dokumentasi Penggunaan

Dokumen ini merangkum seluruh perintah `pyartisan`: pembuatan project, generator kode, manajemen konfigurasi, dan sistem plugin (komunitas & marketplace).

---

## 1. Instalasi

```bash
uv tool install .    # terisolasi, tanpa venv manual
# atau: pip3 install -e .
```

Tanpa install: `uvx --from . pyartisan --help`. Jika `uv` ada di PATH, `pyartisan new` memakai `uv venv` + `uv pip install`; jika tidak, fallback ke venv + pip.

Verifikasi instalasi:

```bash
pyartisan --help
pyartisan version
```

---

## 2. Membuat Project Baru

```bash
pyartisan new <framework> <name>
```

Contoh:

```bash
pyartisan new fastapi ecommerce
pyartisan new flask blog
```

Yang terjadi:
1. Meng-clone template resmi (`FastIQ` untuk FastAPI, `FlaskIQ` untuk Flask)
2. Menawarkan pembuatan virtual environment (`venv`) dan instalasi `requirements.txt`.

URL template dapat diubah lewat `pyartisan config set templates.<framework> <url>` (lihat [Konfigurasi](#5-konfigurasi)).

---

## 3. Generator Kode (`make`)

```bash
pyartisan make <target> <name> [--force] [--<opsi> <nilai> ...]
```

Perintah ini membaca `.pyartisan/manifest.yaml` di dalam project untuk menentukan generator yang tersedia (`model`, `controller`, `service`, `repository`, dst — tergantung template).

Contoh:

```bash
pyartisan make model Post
pyartisan make controller Post --type api
pyartisan make service Payment --version 2
```

Opsi:
- `--force` — timpa file yang sudah ada.
- `--<nama opsi> <nilai>` — argumen dinamis apa pun yang dipakai stub template (mis. `--type`, `--version`), diteruskan ke context rendering Jinja2.

Jika target tidak dikenal atau project tidak memiliki `.pyartisan/manifest.yaml`, perintah gagal dengan pesan error yang jelas.

---

## 4. Menjalankan & Build Project

```bash
pyartisan serve
```
Menjalankan dev server. Strategi fallback: Docker (jika tersedia) → virtualenv lokal → peringatan jika keduanya tidak ada.

```bash
pyartisan build
```
Menjalankan build script produksi sesuai definisi di manifest project.

---

## 5. Konfigurasi

```bash
pyartisan config show
pyartisan config set <key> <value>
pyartisan config reset
```

Key yang tersedia secara default: `theme`, `author`, `license`, `default_framework`, `templates.flask`, `templates.fastapi`.

Contoh mengganti URL template:

```bash
pyartisan config set templates.fastapi https://github.com/org/my-fastiq-fork.git
```

Konfigurasi disimpan di `~/.pyartisan/config.toml`.

---

## 6. Doctor & Version

```bash
pyartisan doctor    # Cek Python, pip, Git, virtualenv
pyartisan version   # Cetak versi pyartisan
```

---

## 7. Sistem Plugin

PyArtisan memperlakukan plugin seperti **package manager** (mirip `npm`/`pip`), bukan sekadar copy-paste file. Ada dua level penyimpanan:

- **Global Registry** (`~/.pyartisan/plugins/<plugin-id>/<version>/`) — plugin yang sudah di-download, belum tentu dipakai project mana pun.
- **Project Metadata** (`.pyartisan/project.yaml`) — daftar plugin yang benar-benar **diterapkan** ke project aktif, di key `plugins: [...]`.

Lifecycle plugin:

```text
init     → scaffold skeleton plugin baru + auto-register ke registry (dev mode)
install  → download ke registry (global, tidak mengubah project apa pun)
apply    → terapkan plugin registry ke project aktif (jalankan hooks, tulis project.yaml)
update   → tarik pembaruan git plugin di registry, re-apply otomatis jika dipakai project ini
remove   → cabut plugin dari project (registry tetap ada, project lain masih bisa pakai)
uninstall→ hapus plugin dari registry (ditolak jika masih dipakai project lain)
```

### 7.1 Install — Download ke Registry

```bash
pyartisan plugin install <name>
```

Tiga sumber yang didukung:

**a. Komunitas (GitHub)**
```bash
pyartisan plugin install github-username/repo-name
```
Meng-clone `https://github.com/<name>.git` ke `~/.pyartisan/plugins/<repo-name>/1.0.0/`.

**b. Lokal (mode pengembangan plugin)**
```bash
pyartisan plugin install myplugin --local /path/to/my-plugin
```
Membuat symlink ke `~/.pyartisan/plugins/myplugin/dev/` — perubahan pada source lokal langsung terlihat tanpa install ulang. Cocok untuk mengembangkan plugin sebelum di-publish ke GitHub/marketplace.

**c. Marketplace Premium (berbayar, verifikasi Blockchain)**
```bash
pyartisan plugin install payment-midtrans --license valid-xxxxxx
```
CLI memverifikasi kepemilikan lisensi ke Blockchain API node/smart contract sebelum mengunduh plugin premium secara aman.

> `install` **tidak** mengubah project mana pun — plugin baru sekadar tersedia di registry lokal.

### 7.2 Apply — Terapkan ke Project Aktif

```bash
pyartisan plugin apply <name>
```

Dijalankan di dalam folder project (harus ada `.pyartisan/project.yaml`). Prosesnya:
1. Menjalankan hook `before_install(project_context)` dari `hooks.py` plugin (jika ada).
2. Menambahkan dependency pip plugin (`manifest.yaml` → `dependencies.pip`) ke `requirements.txt` project.
3. Menjalankan hook `after_install(project_context)` — di sinilah plugin memanggil Project API (`create_service`, `register_router`, dll).
4. Mencatat entri `<plugin-id>@<version>` ke `project.yaml` key `plugins`.
5. Mencatat penggunaan (usage tracking) plugin+versi ini oleh path project saat ini di registry global — dasar validasi `uninstall`.

### 7.3 Update — Perbarui Plugin di Registry

```bash
pyartisan plugin update <name>
```

`git pull` semua versi git-based plugin tersebut di registry (symlink `dev` dilewati, karena sudah live dari source lokal). Jika plugin sedang dipakai project aktif, otomatis re-`apply` setelah update.

### 7.4 Remove — Cabut dari Project

```bash
pyartisan plugin remove <name>            # satu plugin
pyartisan plugin remove <name1> <name2>   # banyak plugin sekaligus
pyartisan plugin remove --all             # semua plugin di project ini
```

Menjalankan hook `before_remove` / `after_remove` (jika plugin menyediakannya), menghapus entri dari `project.yaml`, dan membatalkan pencatatan usage tracking. Salinan plugin di registry global **tidak dihapus** — project lain yang masih memakainya tidak terpengaruh.

### 7.5 Uninstall — Hapus dari Registry

```bash
pyartisan plugin uninstall <name>            # satu plugin
pyartisan plugin uninstall <name1> <name2>   # banyak plugin sekaligus
pyartisan plugin uninstall --all             # semua plugin di registry
```

Dihapus permanen dari `~/.pyartisan/plugins/`. Jika plugin masih tercatat dipakai oleh project lain (usage tracking), perintah **ditolak** dan menampilkan daftar project yang masih memakainya:

```text
❌ Cannot uninstall 'payment-midtrans'. Still used by:
   - /home/user/projects/ecommerce
   - /home/user/projects/inventory
```

Jalankan `plugin remove` di project-project tersebut terlebih dahulu sebelum `uninstall` bisa berhasil.

### 7.6 List — Lihat Plugin Terpasang

```bash
pyartisan plugin list             # plugin aktif di project ini (dari project.yaml)
pyartisan plugin list --global     # semua plugin yang pernah di-download ke registry
pyartisan plugin list --updates    # cek plugin git-based di registry yang punya update
```

### 7.7 Info — Detail Plugin

```bash
pyartisan plugin info <name>
```

Menampilkan metadata lengkap dari registry: nama, ID, versi, deskripsi, author, dependencies, environment variables yang dibutuhkan, dan daftar project yang memakainya (`Used by`).

### 7.8 Status — Kesehatan Project

```bash
pyartisan plugin status
```

Menampilkan nama project, framework, daftar plugin dengan tanda ✔ (tersedia di registry) atau ✖ (hilang dari registry), dan kesimpulan `Health: OK` / `Health: ISSUES FOUND`.

### 7.9 Doctor — Diagnosis Detail

```bash
pyartisan plugin doctor
```

Pemeriksaan lebih dalam dari `status`:
- **Manifest** — `project.yaml` punya `framework.name`.
- **Framework** — `ProjectContext` berhasil dibuat (deteksi framework valid).
- **Template Metadata** — `template.yaml` template project ditemukan di registry global.
- **Dependencies** — tiap plugin aktif dicek: dependency pip di `manifest.yaml` sudah ada di `requirements.txt` project.
- **Marker** — marker registrasi router (mis. `# pyartisan:routers`) masih ada di file target sesuai `template.yaml`.

Diakhiri dengan `Plugin is valid` atau `Plugin has issues, see above.`

### 7.10 Init — Scaffold Plugin Baru

```bash
pyartisan plugin init <name>
```

Membuat skeleton plugin baru di `./<name>/` — tidak perlu membuat struktur
folder secara manual lagi. Prosesnya:

1. Menolak jika direktori `./<name>/` sudah ada (tidak menimpa apa pun).
2. Menanyakan framework target secara interaktif: `fastapi` / `flask` /
   `django` / `all` (default `all`).
3. Merender skeleton dari template bawaan `pyartisan` sendiri (tidak butuh
   koneksi internet): `manifest.yaml`, `hooks.py` (fungsi `after_install`
   dan `before_remove` kosong berisi komentar panduan Project API),
   `README.md`, `LICENSE`.
4. Membuat folder `stubs/<framework>/` kosong untuk tiap framework yang
   dipilih di langkah 2.
5. Langsung mendaftarkan plugin ke registry lokal sebagai symlink dev-mode
   (`~/.pyartisan/plugins/<name>/dev/`) — setara efeknya dengan
   `pyartisan plugin install <name> --local ./<name>`, jadi tidak perlu
   dijalankan terpisah.

Setelah `init`, langsung bisa `pyartisan plugin apply <name>` di dalam
project sandbox mana pun untuk mulai menguji hook yang sedang dikembangkan.

---

## 8. Membuat Plugin Sendiri

Lihat [`Tutorial Create Plugin`](HOW_TO_CREATE_PLUGIN.md) untuk panduan lengkap struktur plugin (`manifest.yaml`, `hooks.py`, `stubs/`), penggunaan Project API (`project_context.framework`, `create_service`, `register_router`, dll), dan cara publikasi ke GitHub atau Marketplace.

---

## 9. Ringkasan Perintah

| Perintah | Fungsi |
|---|---|
| `pyartisan new <framework> <name>` | Buat project baru dari template |
| `pyartisan make <target> <name>` | Generate kode dari stub manifest project |
| `pyartisan serve` | Jalankan dev server |
| `pyartisan build` | Build artifact produksi |
| `pyartisan config show\|set\|reset` | Kelola konfigurasi global |
| `pyartisan doctor` | Cek kesehatan environment |
| `pyartisan version` | Tampilkan versi CLI |
| `pyartisan plugin init <name>` | Scaffold skeleton plugin baru + auto-register ke registry |
| `pyartisan plugin install <name>` | Download plugin ke registry global |
| `pyartisan plugin apply <name>` | Terapkan plugin ke project aktif |
| `pyartisan plugin update <name>` | Perbarui plugin di registry (+ re-apply) |
| `pyartisan plugin remove <name...\|--all>` | Cabut plugin dari project |
| `pyartisan plugin uninstall <name...\|--all>` | Hapus plugin dari registry |
| `pyartisan plugin list [--global\|--updates]` | Lihat plugin project/registry/update tersedia |
| `pyartisan plugin info <name>` | Detail metadata plugin |
| `pyartisan plugin status` | Kesehatan plugin project |
| `pyartisan plugin doctor` | Diagnosis detail plugin project |
