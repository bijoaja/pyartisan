# PyArtisan CLI — Dokumentasi Penggunaan

> **Bahasa:** Indonesia | [English](../en/CLI.md)
> **Terakhir diverifikasi terhadap kode:** commit `80b5acc` (2026-10-26)

Dokumen ini merangkum seluruh perintah `pyartisan`: pembuatan project, generator kode, manajemen konfigurasi, dan sistem plugin (komunitas & marketplace).

---

## 1. Instalasi

Dengan [uv](https://docs.astral.sh/uv/) (terisolasi, tanpa venv manual, Python sistem tidak tersentuh):

```bash
uv tool install git+https://github.com/bijoaja/pyartisan
```

Dari source:

```bash
git clone https://github.com/bijoaja/pyartisan.git
cd pyartisan
uv tool install .              # atau: uv tool install --editable .
# alternatif tanpa uv: pip install -e .
```

`--editable` adalah flag bawaan `uv tool install` (bukan milik pyartisan): kode di `src/` langsung dipakai tanpa install ulang, cocok untuk kontributor.

Tanpa install: `uvx --from git+https://github.com/bijoaja/pyartisan pyartisan --help`.

Jika `pyartisan` tidak ditemukan setelah install, jalankan `uv tool update-shell` lalu buka terminal baru.

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
1. Memeriksa bahwa folder `<name>` belum ada (jika sudah, perintah berhenti).
2. `git clone` template resmi (`FastIQ` untuk FastAPI, `FlaskIQ` untuk Flask) ke folder `<name>`, lalu menghapus remote `origin`. **Git harus terpasang.**
3. Menulis `.pyartisan/project.yaml` (nama project, framework, nama dan versi template, daftar plugin kosong).
4. Menanyakan apakah virtual environment dan dependency ingin dibuat sekarang (default: ya). Jika ya, membuat `./venv` dan memasang `requirements.txt`:
   * Jika `uv` ada di PATH: `uv venv venv` lalu `uv pip install --python <venv> -r requirements.txt`.
   * Jika tidak: `python -m venv venv` lalu `pip install -r requirements.txt`.

Framework yang tidak terdaftar di config menghasilkan error `No template registered for framework ...` beserta daftar yang tersedia.

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
- `--<nama opsi> <nilai>` — argumen dinamis apa pun yang dipakai stub template, diteruskan ke context rendering Jinja2. Tanda hubung diubah menjadi garis bawah (`--my-opt` menjadi `my_opt`). Opsi tanpa nilai di akhir menjadi `True`. Bawaan: `type` = `view`, `version` = `1`.

Jika target tidak dikenal atau project tidak memiliki `.pyartisan/manifest.yaml`, perintah gagal dengan pesan error dan kode keluar 1. Pesan untuk target tidak dikenal menyertakan daftar generator yang tersedia.

---

## 4. Menjalankan & Build Project

```bash
pyartisan serve
```
Menjalankan dev server. Tanpa opsi; strategi dipilih otomatis, berurutan:

1. **Docker**: jika ada `docker-compose.yml` dan Docker berjalan, menjalankan `docker compose up` (atau `docker-compose up`).
2. **Venv project**: jika ada `./venv` atau `./.venv` (atau `VIRTUAL_ENV` yang menunjuk venv lain, bukan env tempat pyartisan berjalan) dan manifest punya `scripts.serve`, menjalankan script itu dengan venv tersebut. Folder `Scripts`/`bin` venv dipasang di depan `PATH`, `VIRTUAL_ENV` di-set, dan `python` / `python3` di awal script diganti dengan interpreter venv (di Windows tidak ada `python3` di dalam venv).
3. **Error**: jika keduanya tidak ada, menampilkan petunjuk dan keluar dengan kode 1.

Venv yang dicari adalah venv **project**, jadi `serve` tetap benar saat pyartisan dipasang lewat `uv tool` (env tool tidak pernah dipilih).

```bash
pyartisan build
```
Menjalankan `scripts.build` dari `.pyartisan/manifest.yaml`. Jika tidak didefinisikan, perintah gagal dengan kode keluar 1.

---

## 5. Konfigurasi

```bash
pyartisan config show
pyartisan config set <key> <value>
pyartisan config reset
```

Key yang tersedia secara default: `theme`, `author`, `license`, `default_framework`, `templates.flask`, `templates.fastapi`. `config set` menolak key yang tidak dikenal, kecuali berawalan `templates.` (framework baru boleh ditambahkan di sana). Perintah `pyartisan config` tanpa subcommand sama dengan `config show`.

Saat ini hanya `templates.*` yang dibaca command lain (oleh `new`). Key `theme`, `author`, `license`, dan `default_framework` tersimpan tetapi belum dipakai.

Contoh mengganti URL template:

```bash
pyartisan config set templates.fastapi https://github.com/org/my-fastiq-fork.git
```

Konfigurasi disimpan di `~/.pyartisan/config.toml`.

---

## 6. Doctor & Version

```bash
pyartisan doctor    # Cek Python, uv, pip, Git, virtualenv
pyartisan version   # Cetak versi pyartisan
```

Catatan `doctor`: Python minimal 3.10. `uv` opsional (tidak ada uv tidak menggagalkan doctor). `pip` tidak dianggap gagal jika tidak ada tetapi `uv` tersedia, karena env `uv tool` memang tanpa pip.

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
Membuat symlink ke `~/.pyartisan/plugins/myplugin/dev/` — perubahan pada source lokal langsung terlihat tanpa install ulang. Di Windows tanpa hak membuat symlink, otomatis dipakai junction (`mklink /J`). Cocok untuk mengembangkan plugin sebelum di-publish ke GitHub/marketplace.

**c. Marketplace Premium (berbayar, verifikasi Blockchain)**
```bash
pyartisan plugin install payment-midtrans --license valid-xxxxxx
```
> **Masih tiruan (mock).** Verifikasi lisensi menerima kunci apa pun yang berawalan `valid-` tanpa memanggil Blockchain API, dan tidak ada plugin yang diunduh: yang ditulis ke registry hanya `manifest.yaml` kosong (versi `1.0.0`).

> `install` **tidak** mengubah project mana pun — plugin baru sekadar tersedia di registry lokal.

### 7.2 Apply — Terapkan ke Project Aktif

```bash
pyartisan plugin apply <name> [--yes]
```

Dijalankan di dalam folder project (harus ada `.pyartisan/project.yaml`). Prosesnya:
1. Meminta persetujuan pengguna sebelum mengeksekusi hook jika `hooks.py` ada (dilewati dengan `--yes`, atau untuk link `dev` via `install --local`). Sesi non-interaktif tanpa `--yes` dibatalkan dengan exit 1.
2. Menjalankan hook `before_install(project_context)` dari `hooks.py` plugin (jika ada).
3. Menambahkan dependency pip plugin (`manifest.yaml` → `dependencies.pip`) ke `requirements.txt` project, hanya jika file itu ada.
4. Menjalankan hook `after_install(project_context)` — di sinilah plugin memanggil Project API (`create_service`, `register_router`, dll).
5. Mencatat entri `<plugin-id>@<version>` ke `project.yaml` key `plugins`.
6. Mencatat penggunaan (usage tracking) plugin+versi ini oleh path project saat ini di registry global — dasar validasi `uninstall`.

### 7.3 Update — Perbarui Plugin di Registry

```bash
pyartisan plugin update <name> [--yes]
```

`git pull` semua versi git-based plugin tersebut di registry (symlink `dev` dilewati, karena sudah live dari source lokal). Jika plugin sedang dipakai project aktif, otomatis re-`apply` setelah update dengan meneruskan flag `--yes` jika ada.

### 7.4 Remove — Cabut dari Project

```bash
pyartisan plugin remove <name> [--yes]            # satu plugin
pyartisan plugin remove <name1> <name2> [--yes]   # banyak plugin sekaligus
pyartisan plugin remove --all [--yes]             # semua plugin di project ini
```

Meminta persetujuan pengguna sebelum mengeksekusi hook (kecuali opsi `--yes` diberikan). Menjalankan hook `before_remove` / `after_remove` (jika plugin menyediakannya), menghapus entri dari `project.yaml`, dan membatalkan pencatatan usage tracking. Salinan plugin di registry global **tidak dihapus** — project lain yang masih memakainya tidak terpengaruh.

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
- **Template Metadata** — `template.yaml` template project ditemukan di `~/.pyartisan/templates/<template>/<versi>/`. Belum ada command yang mengisi folder ini, jadi pemeriksaan ini gagal selama folder itu kosong (lihat [HOW_TO_CREATE_PLUGIN.md](HOW_TO_CREATE_PLUGIN.md)).
- **Dependencies** — tiap plugin aktif dicek: dependency pip di `manifest.yaml` sudah ada di `requirements.txt` project.
- **Marker** — marker registrasi router (mis. `# pyartisan:routers`) masih ada di file target. Hanya diperiksa jika `template.yaml` mendefinisikannya.

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
5. Langsung mendaftarkan plugin ke registry lokal sebagai symlink (atau junction di Windows tanpa hak symlink) dev-mode
   (`~/.pyartisan/plugins/<name>/dev/`) — setara efeknya dengan
   `pyartisan plugin install <name> --local ./<name>`, jadi tidak perlu
   dijalankan terpisah.

Setelah `init`, langsung bisa `pyartisan plugin apply <name>` di dalam
project sandbox mana pun untuk mulai menguji hook yang sedang dikembangkan.

---

## 8. Membuat Plugin Sendiri

Lihat [Tutorial Plugin](HOW_TO_CREATE_PLUGIN.md) untuk struktur plugin (`manifest.yaml`, `hooks.py`, `stubs/`), Project API (`project.framework`, `create_service`, `register_router`, `add_dependency`), dan cara publikasi lewat GitHub. Rancangan produk ada di [PRD.md](PRD.md); cara berkontribusi ada di [CONTRIBUTING.md](CONTRIBUTING.md).

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
