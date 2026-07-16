# Unified Manifest-Driven CLI — Design Spec

Date: 2026-07-16
Status: Approved for planning

## Context

Saat ini `pyartisan` punya command generator yang framework-spesifik secara implisit:
CLI-nya sudah dispatch berdasar deteksi framework (`detector.py` sniff `app.py`/`main.py`),
tapi logic generator-nya sendiri (path tujuan file, isi template, cara registrasi) tertulis
hardcode dalam kode Python di `pyartisan/plugin/flask/commands/*.py` dan
`pyartisan/plugin/fastapi/`. Menambah framework baru (FastAPI penuh, Django, dst) berarti
menulis satu set command Python baru per framework — persis masalah yang PRD.md ingin
hindari ("Core tidak memiliki kode yang spesifik terhadap Flask, FastAPI, atau Django").

Referensi visi yang sudah ditulis user di `FastIQ.md` dan `FlaskIQ.md`: setiap template
project (FlaskIQ, FastIQ, dan framework masa depan) membawa metadata `.pyartisan/manifest.yaml`
+ folder stub `.pyartisan/stubs/` sendiri. PyArtisan menjadi *generic engine* yang membaca
manifest tersebut dan merender stub — engine sendiri tidak pernah tahu apa itu "Flask" atau
"FastAPI" secara struktural.

Tujuan sesi ini: mendesain command CLI yang benar-benar seragam
(`pyartisan make <target> <name>`, `pyartisan new <framework> <name>`) yang bekerja untuk
FlaskIQ dan FastIQ tanpa baris kode Python berbeda per framework, plus command lifecycle
(`serve`, `build`) yang smart-fallback antara Docker dan virtualenv.

## Arsitektur & Alur Eksekusi

```
User: pyartisan make controller users
        │
        ▼
cli/ (thin click parser — TIDAK tahu framework apa pun)
        │
        ▼
core/engine.py
        │  1. cari .pyartisan/manifest.yaml di cwd (persis, tidak walk-up parent dirs)
        │     tidak ketemu → ManifestNotFound
        ▼
core/manifest.py → load & parse manifest.yaml
        │  2. cek "controller" in manifest["generators"]
        │     tidak ada → GeneratorNotSupported (pesan sebut alternatif yang tersedia)
        ▼
utils/naming.py → compute context: name, name_lower, name_title, name_snake, name_plural
        ▼
renderer/ (Jinja2) → render_stub(stub_dir, dest_dir, context)
        │  3. walk semua file di stub dir, render nama file + isi via Jinja2, tulis via utils/fs.write_file
        ▼
core/registration.py → apply_registration(type, target, context)  [jika generator declare `registration:`]
        │  4a. type=import_list → reuse pola __all__ (mirror fs.write_service_init)
        │  4b. type=marker      → sisipkan baris di bawah marker comment di file target
        ▼
Selesai — echo hasil
```

**Prinsip kunci**: tidak ada lagi package Python per-framework (`pyartisan/plugin/flask/`,
`pyartisan/plugin/fastapi/`). Engine 100% generik. Framework baru cukup menyediakan
`.pyartisan/manifest.yaml` + stub di template project-nya sendiri — nol perubahan kode
`pyartisan`.

`detector.py` dan `core/context.py` (`ProjectContext`) **dihapus total**. Kehadiran
`.pyartisan/manifest.yaml` di cwd itu sendiri adalah sinyal "ini project pyartisan" — tidak
ada lagi signature-sniffing `app.py`/`Flask(`/`main.py`/`FastAPI(`. Flag `--framework` juga
dihapus dari semua command `make:*` lama karena manifest sudah menyediakan info itu.

## Struktur Kode

```
src/pyartisan/
  cli/
    __init__.py       — command: new, make (generic group), serve, build, config, doctor, version
  core/
    engine.py         — dispatch_new(), dispatch_make(), dispatch_serve(), dispatch_build()
    manifest.py        — ManifestLoader.load(root) -> dict; validasi key wajib
    registration.py    — apply_registration(kind, target, context) — dua strategi
    exceptions.py       — + ManifestNotFound, ManifestError, GeneratorNotSupported, TemplateNotFound
  renderer/
    __init__.py        — JinjaRenderer.render_stub(stub_dir, dest_dir, context, force=False)
  config/
    __init__.py        — + section [templates] (map framework -> git URL, default flask/fastapi)
  utils/
    naming.py          — name_parts() existing + name_snake(), name_plural()
    fs.py               — tidak berubah, dipakai renderer
  shared/
    doctor.py           — tidak berubah
```

**Dihapus**: `core/context.py`, `core/detector.py`, `plugin/` seluruhnya (`base.py`,
`registry.py`, `flask/`, `fastapi/`), `project/` dan `marketplace/` placeholder tetap ada
(di luar scope, tidak disentuh).

**Dependency baru**: `jinja2` (render stub), `pyyaml` (parse `manifest.yaml`) — ditambah ke
`pyproject.toml`.

## Skema `manifest.yaml`

Hidup di `.pyartisan/manifest.yaml` pada tiap project template (FlaskIQ, FastIQ), bukan di
repo `pyartisan`.

```yaml
id: flaskiq
framework: flask        # metadata informatif, BUKAN dispatch key
version: 1.0

paths:
  controller: app/controller
  service: app/service
  repository: app/repository
  model: app/model
  docker: Docker

generators:
  controller:
    stub: stubs/controller
    path: controller           # merujuk key di `paths:`
    registration:
      type: import_list         # reuse pola __all__ (fs.write_service_init)
      target: "{path}/__init__.py"
  model:
    stub: stubs/model
    path: model
    registration:
      type: import_list
      target: "{path}/__init__.py"
  router:
    stub: stubs/router
    path: modules
    registration:
      type: marker
      target: app/main.py
      marker: "# pyartisan:routers"
      line: "app.include_router({name_lower}_router)"
  docker:
    stub: stubs/docker
    path: docker
    # tanpa `registration` — generator ini cuma copy/render file, tidak ada import list

scripts:
  serve: "flask --app server run --reload"
  build: "gunicorn --bind 0.0.0.0:5000 --workers 4 run:app"
```

Struktur folder stub:

```
.pyartisan/
├── manifest.yaml
└── stubs/
    ├── controller/
    │   └── {{name_lower}}_controller.py.jinja   # nama file di-render Jinja2 juga
    ├── model/
    │   └── {{name_lower}}.py.jinja
    └── docker/
        ├── Dockerfile.jinja
        └── docker-compose.yml.jinja
```

Context variable standar yang selalu di-inject engine ke setiap render (nama file & isi):
`name` (raw input), `name_lower` (`post`), `name_title` (`Post`), `name_snake` (sama seperti
`name_lower` untuk single-word, `blog_post` untuk multi-word), `name_plural` (`posts`,
pluralisasi sederhana: tambah `s`, kecuali berakhiran `s`→tetap atau `y`→`ies`).

## Command CLI

Format spasi (bukan colon), sesuai `CLI-EXAMPLE.md`:

- `pyartisan new <framework> <name>` — clone template dari `config.toml [templates]` map,
  reuse logic clone existing (`git clone`, hapus remote, tanya venv+install deps), dipindah
  dari `plugin/flask/commands/init_project.py` ke `core/engine.py` sebagai fungsi generik
  (terima url+target apa saja, bukan Flask-spesifik). `config.toml` dapat section baru:
  ```toml
  [templates]
  flask = "https://github.com/bijoaja/flaskiq.git"
  fastapi = "https://github.com/bijoaja/fastiq.git"
  ```
- `pyartisan make <target> <name> [--force]` — generic generator, dispatch penuh ke manifest
  seperti dijelaskan di atas. `--force` override skip-if-exists.
- `pyartisan serve` — fallback chain:
  1. `docker-compose.yml` ada di root DAN `docker info` sukses → `docker compose up`
  2. else, venv aktif (`sys.prefix != sys.base_prefix`) → jalankan `manifest["scripts"]["serve"]`
     via `subprocess.run(shlex.split(cmd))`
  3. else → pesan saran: "No docker-compose.yml and no active venv. Run `pyartisan make docker`
     or activate a virtualenv."
- `pyartisan build` — jalankan `manifest["scripts"]["build"]` via subprocess (butuh manifest +
  scripts.build ada, else error jelas). Ini command lifecycle terpisah dari `make docker`:
  `make docker` (generator) menulis `Dockerfile`/`docker-compose.yml` ke disk dari stub;
  `build` (script) menjalankan `docker build`/`gunicorn` memakai file yang sudah ada. Keduanya
  tidak saling memanggil satu sama lain di engine — urutan pemakaian normal adalah
  `make docker` sekali lalu `build`/`serve` berkali-kali.
- `pyartisan config`, `pyartisan doctor`, `pyartisan version` — tidak berubah.

**Di luar scope sesi ini** (didesain terpisah nanti): `pyartisan make docker`/`make env`/
`make migrations` sebagai *generator* biasa (via manifest `generators.docker`) sudah tercakup
desain di atas, tapi isi stub Docker/migration-nya sendiri belum ditulis di sesi ini — itu
task implementasi terpisah untuk mengisi `.pyartisan/stubs/` di repo `flaskiq`/`fastiq`.
Command `plugin`, `market`, `ai`, `crud`, `auth` dari `CLI-EXAMPLE.md` — sesi brainstorming
terpisah.

## Error Handling

| Situasi | Exception | Pesan |
|---|---|---|
| `.pyartisan/manifest.yaml` tidak ada di cwd | `ManifestNotFound` | "Not a pyartisan project. Run inside a project generated by `pyartisan new`, or add .pyartisan/manifest.yaml" |
| `manifest.yaml` invalid YAML | `ManifestError` | "Invalid manifest at {path}: {yaml error}" |
| Target generator tidak dideklarasikan | `GeneratorNotSupported` | "{manifest.id} does not support '{target}'. Available: {list generators}" |
| Stub dir tidak ketemu walau dideklarasikan | `ManifestError` | "Stub not found: {stub_path} (declared in manifest but missing on disk)" |
| `new <framework>` tanpa entry di config `[templates]` | `TemplateNotFound` | "No template registered for '{framework}'. Available: {list config templates}" |

Semua exception baru mewarisi `PyArtisanError` (pola existing di `core/exceptions.py`).

## Idempotency

- File generator baru: skip-if-exists via `utils/fs.write_file` (existing behavior),
  bisa dioverride dengan `--force`.
- `registration.apply(type=import_list)`: reuse cek "already registered" dari
  `fs.write_service_init` — aman dijalankan berulang.
- `registration.apply(type=marker)`: cek baris target sudah ada persis di bawah marker
  sebelum insert — idempotent juga.

## Testing Plan

Extend `tests/smoke_test.py` (assert-based, tanpa pytest dependency, konsisten pola existing):

1. `test_naming_extended()` — `name_snake`, `name_plural` untuk kasus single-word, multi-word,
   kata berakhiran `y`/`s`.
2. `test_manifest_load()` — buat `manifest.yaml` sementara di tempdir, load, assert struktur
   ter-parse benar; assert `ManifestError` untuk YAML invalid.
3. `test_render_stub()` — buat stub `.jinja` sementara berisi `{{ name_title }}`, render ke
   tempdir, assert isi & nama file benar.
4. `test_registration_import_list()` — reuse skenario `write_service_init` lama, pastikan
   masih idempotent lewat `registration.apply`.
5. `test_registration_marker()` — file target dengan marker comment, assert baris ter-insert
   sekali dan idempotent saat dipanggil ulang.
6. `test_cli_make_end_to_end()` — fixture project tempdir dengan `.pyartisan/manifest.yaml` +
   stub controller minimal, jalankan `pyartisan make controller users`, assert file
   ter-generate di path benar.
7. `test_cli_make_not_supported()` — manifest tanpa generator `router`, assert pesan error
   sesuai format di atas.
8. `test_cli_make_no_manifest()` — cwd tanpa `.pyartisan/`, assert `ManifestNotFound` message.

`pyartisan new` **tidak** masuk smoke test otomatis (butuh network git clone) — didokumentasikan
sebagai manual verification step di plan implementasi.

## Out of Scope (didesain di sesi terpisah)

- Isi stub `.jinja` konkret untuk semua generator FlaskIQ/FastIQ (controller, service,
  repository, model, router, schema, docker, migration) — task implementasi tersendiri
  setelah engine ini jadi.
- Command `plugin`, `market`, `ai` dari `CLI-EXAMPLE.md`.
- `pyartisan make crud <name>` (composite generator yang panggil beberapa generator sekaligus).
- `pyartisan make auth` (composite generator kompleks).
- Lifecycle hooks Python (`hooks.py` di `.pyartisan/`) untuk logic custom di luar
  template+registration — disebutkan di `FastIQ.md` §6 tapi belum didesain detail di sini.
