# PyArtisan

> **Bahasa:** [English](README.md) | Indonesia

PyArtisan adalah CLI pengembangan web Python multi-framework, terinspirasi Laravel Artisan. `pyartisan new` meng-clone template framework menjadi project baru; command berikutnya seperti `make` membaca `.pyartisan/manifest.yaml` milik project itu untuk menghasilkan kode. Core-nya tidak terikat framework: pengetahuan framework ada di repo template, [FlaskIQ](https://github.com/bijoaja/flaskiq) untuk Flask dan [FastIQ](https://github.com/bijoaja/fastiq) untuk FastAPI.

## Fitur

- `new`: clone template framework dan siapkan project (venv dan dependency, opsional)
- `make`: generate kode dari generator yang dideklarasikan di manifest project, tanpa generator hardcoded per framework
- `serve`: Docker dulu, lalu venv project
- `build`: jalankan build script dari manifest
- `plugin`: plugin bergaya package manager (`install`, `apply`, `remove`, ...), lihat [docs/id/CLI.md](docs/id/CLI.md#7-sistem-plugin)
- `config`: pengaturan permanen di `~/.pyartisan/config.toml`
- `doctor`: cek environment lokal
- Mendukung [uv](https://docs.astral.sh/uv/) (instalasi terisolasi, tanpa venv); pip juga bisa
- Python 3.10+

## Instalasi

Disarankan memakai [uv](https://docs.astral.sh/uv/). Terpasang di environment terisolasi, jadi tidak perlu membuat venv dan Python sistem tidak tersentuh:

```bash
uv tool install git+https://github.com/bijoaja/pyartisan
# atau jalankan tanpa install:
uvx --from git+https://github.com/bijoaja/pyartisan pyartisan --help
```

Dari source:

```bash
git clone https://github.com/bijoaja/pyartisan.git
cd pyartisan
uv tool install .      # atau: uv tool install --editable .   (untuk kontributor)
# tanpa uv: pip install -e .
```

Jika `pyartisan` tidak ditemukan setelahnya, jalankan `uv tool update-shell` lalu buka terminal baru.

Jika `uv` ada di `PATH`, `pyartisan new` juga membuat venv project dan memasang dependency dengan uv. Jika tidak, dipakai `python -m venv` dan pip.

## Kebutuhan

- Python ≥ 3.10 (uv bisa mengunduhnya untuk Anda)
- Git (`pyartisan new` dan instalasi plugin dari GitHub memakai `git clone`)
- Dependency runtime dideklarasikan di `pyproject.toml`: `click`, `flask`, `sqlalchemy`, `jinja2`, `pyyaml`, dan `tomli` untuk Python < 3.11. `flask` dan `sqlalchemy` tidak di-import oleh kode PyArtisan sendiri.

## Penggunaan

```bash
pyartisan --help
```

### Membuat project baru

```bash
pyartisan new flask myapp
pyartisan new fastapi myapi
```

Menjalankan `git clone` template (FlaskIQ untuk `flask`, FastIQ untuk `fastapi`; URL-nya lihat `pyartisan config show`), menulis `.pyartisan/project.yaml`, lalu menanyakan apakah `./venv` dan instalasi `requirements.txt` ingin dibuat. URL template bisa diubah dengan `pyartisan config set templates.<framework> <url>`.

### Dari mana framework diketahui

Tidak ada deteksi otomatis dari isi file. Framework dicatat sekali oleh `pyartisan new` di `.pyartisan/project.yaml`. `make` dan `serve` membaca `.pyartisan/manifest.yaml`, jadi jalankan keduanya dari dalam project hasil `pyartisan new`.

### Generate kode (`make`)

```bash
pyartisan make <target> <name> [--force] [--<opsi> <nilai> ...]
```

`<target>` harus berupa generator yang dideklarasikan di `.pyartisan/manifest.yaml` project. Pada FlaskIQ: `controller`, `service`, `repository`, `model`, dan `routes`; FastIQ mendeklarasikan `module` dan `model`. Pasangan `--opsi nilai` tambahan langsung masuk ke context render Jinja2 (bawaan: `type` = `view`, `version` = `1`).

```bash
pyartisan make model Post
pyartisan make repository Post
pyartisan make service Post --type view
pyartisan make controller Post --type api --version 2
```

Target tidak dikenal, atau dijalankan di luar project yang punya `.pyartisan/manifest.yaml`, menghasilkan pesan error dan kode keluar 1.

### Menjalankan dev server

```bash
pyartisan serve
```

Tanpa opsi. `serve` memilih strategi otomatis:

1. Docker (`docker compose up`) jika ada `docker-compose.yml` dan Docker berjalan.
2. Jika tidak, command `scripts.serve` dari manifest, dijalankan di dalam venv milik project (`./venv` atau `./.venv`). Ini juga berfungsi saat PyArtisan sendiri dipasang lewat `uv tool`.
3. Jika tidak ada keduanya, pesan error berisi petunjuk (kode keluar 1).

### Build

```bash
pyartisan build
```

Menjalankan `scripts.build` dari `.pyartisan/manifest.yaml`. Gagal dengan kode keluar 1 jika manifest tidak mendefinisikan build script.

### Konfigurasi

```bash
pyartisan config          # sama dengan: config show
pyartisan config show
pyartisan config set templates.flask https://github.com/anda/fork-flaskiq.git
pyartisan config reset
```

### Doctor dan versi

```bash
pyartisan doctor     # Python, uv, pip, Git, virtual environment
pyartisan version
```

### Plugin

```bash
pyartisan plugin init my-plugin               # buat skeleton plugin dan tautkan untuk development
pyartisan plugin install user/repo            # clone dari GitHub ke ~/.pyartisan/plugins
pyartisan plugin apply my-plugin              # terapkan ke project aktif
pyartisan plugin list --global
```

Semua command plugin ada di [docs/id/CLI.md](docs/id/CLI.md#7-sistem-plugin), dan cara menulis plugin di [docs/id/HOW_TO_CREATE_PLUGIN.md](docs/id/HOW_TO_CREATE_PLUGIN.md).

## Struktur project

Susunan folder project hasil generate ditentukan template-nya, bukan PyArtisan. Lihat repo template ([FlaskIQ](https://github.com/bijoaja/flaskiq), [FastIQ](https://github.com/bijoaja/fastiq)) untuk susunan terbaru.

PyArtisan sendiri adalah satu package, `src/pyartisan/`:

| Folder | Peran |
|---|---|
| `cli/commands/` | satu file per command, hanya mem-parse argumen |
| `core/` | `engine.py` (dispatch), pemuatan manifest, registrasi, `ProjectContext` untuk hook plugin |
| `marketplace/` | registry plugin global di `~/.pyartisan/plugins` |
| `renderer/`, `config/`, `shared/`, `utils/` | render Jinja2, `config.toml`, logika doctor, helper |
| `templates/plugin_init/` | skeleton yang dipakai `plugin init` |

## File konfigurasi

`~/.pyartisan/config.toml` dibuat saat pertama dipakai:

```toml
theme = "default"
author = ""
license = "MIT"
default_framework = "flask"

[templates]
flask = "https://github.com/bijoaja/flaskiq.git"
fastapi = "https://github.com/bijoaja/fastiq.git"
```

Saat ini hanya `templates.*` yang dibaca sebuah command (`new`); key lain tersimpan tetapi belum dipakai.

## Dokumentasi

| Dokumen | English | Indonesia |
|---|---|---|
| Referensi CLI | [docs/en/CLI.md](docs/en/CLI.md) | [docs/id/CLI.md](docs/id/CLI.md) |
| Menulis plugin | [docs/en/HOW_TO_CREATE_PLUGIN.md](docs/en/HOW_TO_CREATE_PLUGIN.md) | [docs/id/HOW_TO_CREATE_PLUGIN.md](docs/id/HOW_TO_CREATE_PLUGIN.md) |
| Kebutuhan produk dan status | [docs/en/PRD.md](docs/en/PRD.md) | [docs/id/PRD.md](docs/id/PRD.md) |
| Panduan kontributor | [docs/en/CONTRIBUTING.md](docs/en/CONTRIBUTING.md) | [docs/id/CONTRIBUTING.md](docs/id/CONTRIBUTING.md) |

## Berkontribusi

Kontribusi sangat diterima. Mulai dari [CONTRIBUTING.md](CONTRIBUTING.md).

## Lisensi

MIT, lihat [LICENSE](LICENSE).
