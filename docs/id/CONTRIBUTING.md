# Panduan Kontributor

> **Bahasa:** Indonesia | [English](../en/CONTRIBUTING.md)
> **Terakhir diverifikasi terhadap kode:** commit `80b5acc` (2026-10-26)

Terima kasih sudah mau berkontribusi ke PyArtisan. Panduan ini hanya memuat hal yang benar-benar berlaku di repo ini. Jika ada yang tidak cocok dengan kenyataan, itu bug dokumentasi: silakan buka issue.

---

## 1. Menyiapkan lingkungan

Prasyarat: [uv](https://docs.astral.sh/uv/) dan Git. Python tidak wajib terpasang; uv bisa mengunduhnya (project butuh Python 3.10 ke atas).

```bash
git clone https://github.com/bijoaja/pyartisan.git
cd pyartisan
uv tool install --editable .
pyartisan --help
```

`uv tool install` membuat env terpisah, jadi tidak perlu membuat venv dan Python sistem tidak tersentuh. `--editable` membuat perubahan di `src/` langsung terpakai tanpa install ulang.

Tanpa uv, alternatifnya `pip install -e .` di dalam venv Anda sendiri.

Jika `pyartisan` tidak ditemukan, jalankan `uv tool update-shell` lalu buka terminal baru. Setelah selesai mencoba, hapus dengan `uv tool uninstall pyartisan`.

> **Windows:** jika keluaran berisi karakter aneh atau error encoding, set `PYTHONUTF8=1`. PyArtisan sudah memaksa UTF-8 untuk stdout/stderr-nya sendiri, tetapi program lain di terminal yang sama bisa tidak.

---

## 2. Struktur kode

```text
src/pyartisan/
├── cli/commands/     # satu file per command (new, make, serve, build, config, doctor, version, plugin)
├── core/
│   ├── engine.py         # dispatch_new / dispatch_make / dispatch_serve / dispatch_build
│   ├── manifest.py       # baca .pyartisan/manifest.yaml
│   ├── registration.py   # sisip import / baris ke file yang sudah ada
│   ├── plugin_engine.py  # ProjectContext (Project API untuk hooks plugin)
│   └── exceptions.py
├── marketplace/      # registry plugin global ~/.pyartisan/plugins
├── project/          # placeholder Project API (belum berisi kode)
├── renderer/         # render_stub (Jinja2)
├── config/           # ~/.pyartisan/config.toml
├── shared/           # logika doctor
├── utils/            # console, fs, naming
└── templates/plugin_init/   # skeleton untuk `plugin init`
tests/smoke_test.py   # satu-satunya test
docs/                 # dokumentasi (id/ dan en/); docs/superpowers/ berisi spec dan plan
```

Prinsip: `cli/` hanya mem-parse argumen lalu memanggil fungsi di `core/engine.py`. `core/` tidak boleh memuat kode khusus satu framework. Pengetahuan framework ada di template repo (FlaskIQ, FastIQ) lewat `.pyartisan/manifest.yaml`. Lihat [PRD.md](PRD.md) untuk rancangan dan status tiap fitur.

---

## 3. Menjalankan test

Tidak ada framework test. Satu-satunya pemeriksaan adalah `tests/smoke_test.py` (assert biasa). Dari root repo:

```bash
PYTHONPATH=src uv run --no-project --with click --with jinja2 --with pyyaml --with flask --with sqlalchemy python tests/smoke_test.py
```

Jika `python` sudah ada di venv Anda yang berisi dependency project, cukup:

```bash
PYTHONPATH=src python tests/smoke_test.py
```

Keluaran yang benar berakhir dengan `ALL SMOKE TESTS PASSED`. Perintah pertama tidak meninggalkan file di repo; jangan memakai `uv run --with-editable .` karena itu membuat `uv.lock` yang tak terlacak.

Tidak ada CI, linter, atau formatter. Sebelum membuka PR, jalankan smoke test dan, bila perubahan Anda menyentuh perilaku CLI, jalankan perintahnya sendiri secara manual.

Setiap perubahan logika non-trivial sebaiknya menambah satu fungsi `test_...` di `tests/smoke_test.py` dan mendaftarkannya di `main()`.

---

## 4. Alur kerja

1. Cari atau buka issue yang menjelaskan masalahnya.
2. Buat branch dari `main`, mis. `fix/serve-project-venv`, `feat/uv-support`, `docs/restructure`.
3. Buat perubahan kecil dan terfokus. Satu PR satu tujuan.
4. Jalankan smoke test.
5. Commit dengan pesan bergaya Conventional Commits, mis. `fix: ...`, `feat: ...`, `docs: ...`.
6. Buka PR ke `main`. Cantumkan `Closes #<nomor>` di deskripsi supaya issue tertutup otomatis saat PR di-merge.
7. Di deskripsi PR, tulis apa yang diubah, bagaimana diverifikasi, dan apa yang **belum** diverifikasi.

---

## 5. Menambah dukungan framework baru

Tidak perlu mengubah `core/` atau `cli/`.

1. Siapkan template repo untuk framework itu, berisi `.pyartisan/manifest.yaml` (daftar `generators`, `paths`, `scripts`) dan folder stub.
2. Daftarkan URL-nya di `DEFAULT_CONFIG["templates"]` pada `src/pyartisan/config/__init__.py`. Pengguna juga bisa menambahkannya sendiri: `pyartisan config set templates.<framework> <url>`.
3. Tambahkan nama framework ke `click.Choice` di `plugin init` bila ingin dipilih saat membuat plugin (`cli/commands/plugin.py`).

Jika `ProjectContext` (`core/plugin_engine.py`) perlu perilaku khusus framework, catat di issue: bagian itu saat ini masih memuat percabangan `fastapi` / selain itu.

---

## 6. Menulis dokumentasi

* Dokumentasi ada dalam dua bahasa: `docs/id/` dan `docs/en/`, dengan nama file yang sama. Ubah keduanya dalam PR yang sama.
* `README.md` (Inggris) dan `README.id.md` (Indonesia) ada di root.
* Tulis hanya yang sudah dicek ke kode atau ke keluaran `--help`. Fitur yang belum ada ditandai jelas sebagai rencana, bukan ditulis seolah sudah ada.
* Perintah, nama file, dan nama field (`apply`, `manifest.yaml`, `hooks.py`) tidak diterjemahkan.

---

## 7. Aturan commit dan PR

* Author commit adalah Anda sendiri. Jangan menambahkan baris `Co-Authored-By` untuk alat atau orang yang tidak ikut menulis commit.
* Jangan commit folder hasil build: `build/`, `dist/`, `*.egg-info/` (sudah di `.gitignore`), maupun `uv.lock` bila tidak sengaja dibuat.
* Merge dilakukan oleh maintainer lewat GitHub.

---

## 8. Melaporkan masalah

Buka issue di <https://github.com/bijoaja/pyartisan/issues>. Sertakan:

* versi (`pyartisan version`), OS, dan cara install (uv tool, pip, atau source),
* langkah mengulang masalah dan keluaran lengkap,
* hasil yang diharapkan.

Masalah pada template project (struktur folder, `requirements.txt` hasil `pyartisan new`) dilaporkan ke repo template: [flaskiq](https://github.com/bijoaja/flaskiq) atau [fastiq](https://github.com/bijoaja/fastiq).
