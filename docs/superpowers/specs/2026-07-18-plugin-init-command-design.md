# `pyartisan plugin init` — Design Spec

Date: 2026-07-18
Status: Approved for planning

## Context

Membuat plugin PyArtisan dari nol saat ini berarti membuat manual seluruh struktur
(`manifest.yaml`, `hooks.py`, folder `stubs/`, `README.md`, `LICENSE`) dan menghafal
skema tiap file — mengacu ke `HOW_TO_CREATE_PLUGIN.md` sebagai satu-satunya referensi.
`HOW_TO_CREATE_PLUGIN.md` sendiri sudah mencatat kebutuhan ini di bagian
"Rekomendasi Tambahan" sebagai `pyartisan plugin init <name>` — generator skeleton
plugin agar developer komunitas langsung masuk ke tahap pengembangan logic, bukan
setup boilerplate.

Tujuan: tambah command `pyartisan plugin init <name>` yang men-scaffold skeleton
plugin siap pakai (bukan contoh CRUD jadi — murni starting point kosong dengan
komentar panduan), lalu langsung mendaftarkannya ke local plugin registry
(`~/.pyartisan/plugins/<name>/dev/`, symlink dev mode) sehingga developer bisa
langsung `pyartisan plugin apply <name>` di project sandbox tanpa langkah
`plugin install --local` terpisah.

## Command

```bash
pyartisan plugin init <name>
```

Ditambahkan sebagai subcommand baru pada `plugin_group` yang sudah ada di
`src/pyartisan/marketplace/__init__.py:125` (grup sama dengan `install`, `apply`,
`update`, `remove`, `uninstall`, `list`, `info`, `status`, `doctor`) — bukan group
`setup` baru. Konsisten dengan struktur command existing dan dengan rekomendasi di
`HOW_TO_CREATE_PLUGIN.md`.

## Alur Eksekusi

```
User: pyartisan plugin init crud-blogs
        │
        ▼
1. Validasi ./crud-blogs/ belum ada di cwd
   sudah ada → "❌ Directory already exists: <path>", exit tanpa mengubah apa pun
        │
        ▼
2. Prompt interaktif:
   "Target framework? [fastapi/flask/django/all] (all):"
   single-choice (click.Choice), default "all"
        │
        ▼
3. Render skeleton dari template package (src/pyartisan/templates/plugin_init/)
   ke ./crud-blogs/ via renderer.render_stub() — mekanisme sama yang dipakai
   `pyartisan make`
        │
        ▼
4. Buat folder stubs/<framework>/ kosong (+ .gitkeep) untuk tiap framework
   yang dipilih di langkah 2 (skip yang tidak dipilih)
        │
        ▼
5. Auto-register ke registry lokal: symlink
   ~/.pyartisan/plugins/crud-blogs/dev/ -> ./crud-blogs/
   (logic sama dengan plugin_group install --local, direuse)
        │
        ▼
6. Cetak next-steps: edit hooks.py, isi stubs/, lalu
   `pyartisan plugin apply crud-blogs` di project sandbox
```

## Struktur Skeleton yang Dihasilkan

```
crud-blogs/
├── manifest.yaml
├── hooks.py
├── README.md
├── LICENSE
└── stubs/
    ├── fastapi/.gitkeep   # hanya jika dipilih saat prompt
    ├── flask/.gitkeep     # hanya jika dipilih saat prompt
    └── django/.gitkeep    # hanya jika dipilih saat prompt
```

### `manifest.yaml` (rendered)

```yaml
id: {{name_lower}}
name: {{name_title}} Plugin
version: 1.0.0
description: ""
author: ""
dependencies:
  pip: []
```

### `hooks.py` (rendered — skeleton, bukan contoh CRUD jadi)

```python
def after_install(project):
    """Called after plugin dependencies are installed into the target project.

    Use the Project API to scaffold files without hardcoding paths:
      project.framework        -> "fastapi" | "flask" | "django"
      project.project_path     -> Path to the target project root
      project.create_service(name, stub_path)
      project.register_router(name)
      project.add_dependency(package_name)

    Example:
        if project.framework == "fastapi":
            project.create_service(
                name="{{name_lower}}",
                stub_path=str(Path(__file__).parent / "stubs" / "fastapi" / "service.py.jinja"),
            )
    """
    pass


def before_remove(project):
    """Called before the plugin is removed from a project. Optional — delete if unused."""
    pass
```

### `README.md` (rendered)

Template dokumentasi standar plugin: judul, deskripsi kosong untuk diisi, section
"Installation" (`pyartisan plugin install`/`apply`), section "Configuration"
(environment variables jika ada).

### `LICENSE`

Teks MIT License placeholder (tahun & nama author kosong untuk diisi).

## Implementasi

### File baru

- `src/pyartisan/templates/plugin_init/manifest.yaml.jinja`
- `src/pyartisan/templates/plugin_init/hooks.py.jinja`
- `src/pyartisan/templates/plugin_init/README.md.jinja`
- `src/pyartisan/templates/plugin_init/LICENSE` (statis, tanpa Jinja)

Disimpan sebagai package data di dalam `pyartisan` sendiri (bukan di-clone dari
GitHub) agar `plugin init` tidak butuh koneksi internet dan selalu konsisten
dengan versi CLI yang terinstall.

### File yang diubah

**`src/pyartisan/marketplace/__init__.py`** — tambah `init_cmd`:

```python
from pathlib import Path
from pyartisan.renderer import render_stub
from pyartisan.utils.naming import name_parts

@plugin_group.command(name="init")
@click.argument("name")
def init_cmd(name: str):
    """Scaffold a new plugin skeleton, ready for development."""
    dest = Path.cwd() / name
    if dest.exists():
        click.echo(f"❌ Directory already exists: {dest}")
        return

    framework_choice = click.prompt(
        "Target framework?",
        type=click.Choice(["fastapi", "flask", "django", "all"]),
        default="all",
    )
    frameworks = (
        ["fastapi", "flask", "django"] if framework_choice == "all" else [framework_choice]
    )

    name_lower, name_title, _, _ = name_parts(name)
    context = {"name": name, "name_lower": name_lower, "name_title": name_title}

    template_dir = Path(__file__).parent.parent / "templates" / "plugin_init"
    render_stub(template_dir, dest, context)

    for fw in frameworks:
        fw_dir = dest / "stubs" / fw
        fw_dir.mkdir(parents=True, exist_ok=True)
        (fw_dir / ".gitkeep").touch()

    # Auto-register ke registry lokal (dev symlink) — sama seperti install --local
    plugins_registry = _plugins_registry()
    plugin_dir = plugins_registry / name_lower / "dev"
    plugin_dir.parent.mkdir(parents=True, exist_ok=True)
    if plugin_dir.exists() or plugin_dir.is_symlink():
        if plugin_dir.is_symlink():
            os.unlink(plugin_dir)
        else:
            shutil.rmtree(plugin_dir)
    os.symlink(dest.resolve(), plugin_dir, target_is_directory=True)

    click.echo(f"✔ Plugin skeleton created at {dest}")
    click.echo(f"✔ Linked to registry -> ~/.pyartisan/plugins/{name_lower}/dev")
    click.echo(
        f"👉 Edit hooks.py and stubs/, then test with "
        f"`pyartisan plugin apply {name_lower}` inside a sandbox project."
    )
```

Reuse langsung: `renderer.render_stub()` (`src/pyartisan/renderer/__init__.py:7`),
`utils/naming.name_parts()` (`src/pyartisan/utils/naming.py:1`), dan
`_plugins_registry()` yang sudah ada di file yang sama
(`src/pyartisan/marketplace/__init__.py:16`). Logic symlink dev-mode
diduplikasi dari `install_cmd` (`marketplace/__init__.py:140-156`) — tidak
diekstrak jadi helper baru karena hanya dipakai 2 tempat dan menjaga
`install_cmd` tetap tidak berubah (mengurangi risiko regresi pada command
yang sudah ada).

**`pyproject.toml`** — pastikan `src/pyartisan/templates/` ikut ter-package saat
`pip install -e .` / build. Karena project sudah pakai package discovery
`where = ["src"]`, cukup tambah:

```toml
[tool.setuptools.package-data]
pyartisan = ["templates/plugin_init/**/*"]
```

### Error Handling

| Kondisi | Perilaku |
|---|---|
| `./<name>/` sudah ada | `❌ Directory already exists: <path>` — exit, tidak ada perubahan filesystem |
| Nama argumen kosong | Ditangani otomatis oleh Click (`missing argument` error) |
| Template package hilang/corrupt | Exception dari `render_stub()` di-propagate apa adanya (skenario ini seharusnya tidak terjadi karena template dibundle dalam package yang sama) |
| Symlink registry gagal dibuat (mis. permission) | Exception Python native di-propagate — konsisten dengan `install_cmd` yang juga tidak wrap `os.symlink` dalam try/except |

## Testing / Verifikasi

1. `pyartisan plugin init demo-plugin` di direktori kosong, pilih `all` saat prompt
   → folder `demo-plugin/` berisi `manifest.yaml`, `hooks.py`, `README.md`, `LICENSE`,
   `stubs/{fastapi,flask,django}/.gitkeep`
2. `manifest.yaml` berisi `id: demo_plugin`, `name: DemoPlugin Plugin`, `version: 1.0.0`
3. `~/.pyartisan/plugins/demo_plugin/dev` adalah symlink valid ke `demo-plugin/`
   (cek `readlink`)
4. `pyartisan plugin init demo-plugin` dijalankan lagi di folder yang sama
   → error "Directory already exists", tidak menimpa file
5. `pyartisan plugin init demo-plugin2`, pilih `fastapi` saja saat prompt
   → hanya `stubs/fastapi/` yang dibuat, `stubs/flask/` dan `stubs/django/`
   tidak ada
6. Update `tests/smoke_test.py` dengan test case baru untuk `init_cmd`
   (pola sama dengan test lifecycle plugin yang sudah ada di baris 387-624:
   buat di direktori tmp, jalankan `init`, assert file & symlink ter-buat)
