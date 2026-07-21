# Design Spec: Refactoring CLI Commands Into Dedicated `commands/` Package

- **Date**: 2026-07-21
- **Status**: Draft
- **Target**: `src/pyartisan/cli/` & `src/pyartisan/marketplace/`

## 1. Background & Context

Saat ini seluruh logika command CLI PyArtisan terpusat dalam dua file monolitik:
1. `src/pyartisan/cli/__init__.py` (140 baris): Menampung command top-level (`new`, `make`, `serve`, `build`, `config` group, `doctor`, `version`).
2. `src/pyartisan/marketplace/__init__.py` (620 baris): Menampung grup command `plugin` berserta 9 subcommand dan helper function internal.

Kondisi ini membuat registrasi command dan implementasinya tercampur, sehingga sulit dipelihara dan di-extend.

## 2. Goals & Objectives

- Memecah setiap command CLI menjadi modul terpisah di dalam paket `src/pyartisan/cli/commands/`.
- Memastikan `src/pyartisan/cli/__init__.py` hanya bertugas meregistrasi command (thin registration layer).
- Memisahkan logika internal (helper) marketplace dari definisi command Click-nya.
- Memastikan seluruh fungsi sesuai dengan nama filenya.
- Menjaga 100% backward compatibility dan memastikan seluruh suite `tests/smoke_test.py` tetap LULUS.

## 3. Proposed Architecture

### Direktori Baru: `src/pyartisan/cli/commands/`

```text
src/pyartisan/cli/
├── __init__.py          # Entrypoint CLI & registrasi dari commands/
└── commands/
    ├── __init__.py      # Export / Loader otomatis untuk semua command
    ├── new.py           # Command 'new'
    ├── make.py          # Command 'make'
    ├── serve.py         # Command 'serve'
    ├── build.py         # Command 'build'
    ├── config.py        # Command group 'config' (show, reset, set)
    ├── doctor.py        # Command 'doctor'
    ├── version.py       # Command 'version'
    └── plugin.py        # Command group 'plugin' (install, apply, update, remove, uninstall, list, info, status, doctor)
```

### Struktur Modul Marketplace

Logika helper marketplace (seperti manajemen registri, licensi, hook) dipisahkan dari definisi Click Command:
```text
src/pyartisan/marketplace/
├── __init__.py          # Re-export helper atau entrypoint marketplace
└── core.py              # Logika utilitas/helper internal (registry, usage, updates, version resolve)
```

## 4. Detailed Component Mapping

| Old File / Location | New File / Location | Functional Responsibility |
|---|---|---|
| `cli/__init__.py` (`new_cmd`) | `cli/commands/new.py` | Command `pyartisan new <framework> <name>` |
| `cli/__init__.py` (`make_cmd`) | `cli/commands/make.py` | Command `pyartisan make <target> <name>` |
| `cli/__init__.py` (`serve_cmd`) | `cli/commands/serve.py` | Command `pyartisan serve` |
| `cli/__init__.py` (`build_cmd`) | `cli/commands/build.py` | Command `pyartisan build` |
| `cli/__init__.py` (`config_group`) | `cli/commands/config.py` | Command group `pyartisan config` (`show`, `reset`, `set`) |
| `cli/__init__.py` (`doctor`) | `cli/commands/doctor.py` | Command `pyartisan doctor` |
| `cli/__init__.py` (`version`) | `cli/commands/version.py` | Command `pyartisan version` |
| `marketplace/__init__.py` (`plugin_group`) | `cli/commands/plugin.py` | Command group `pyartisan plugin` |
| `marketplace/__init__.py` (helpers) | `marketplace/core.py` | Helper functions untuk marketplace registry & lifecycle |

## 5. Registration Pattern (`cli/__init__.py`)

`src/pyartisan/cli/__init__.py` akan menjadi sangat ringkas:

```python
import click
from pyartisan import __version__
from pyartisan.cli.commands import (
    new_cmd,
    make_cmd,
    serve_cmd,
    build_cmd,
    config_group,
    doctor_cmd,
    version_cmd,
    plugin_group,
)

@click.group()
@click.version_option(__version__, prog_name="pyartisan")
def cli():
    """pyartisan - AI-powered Python Web Development Toolkit"""
    pass

# Registration
cli.add_command(new_cmd)
cli.add_command(make_cmd)
cli.add_command(serve_cmd)
cli.add_command(build_cmd)
cli.add_command(config_group)
cli.add_command(doctor_cmd)
cli.add_command(version_cmd)
cli.add_command(plugin_group)

if __name__ == "__main__":
    cli()
```

## 6. Implementation Plan

1. **Buat direktori `src/pyartisan/cli/commands/`** dan `__init__.py`.
2. **Pindahkan helper marketplace** dari `src/pyartisan/marketplace/__init__.py` ke `src/pyartisan/marketplace/core.py`.
3. **Buat file command per file** di `src/pyartisan/cli/commands/`:
   - `new.py`
   - `make.py`
   - `serve.py`
   - `build.py`
   - `config.py`
   - `doctor.py`
   - `version.py`
   - `plugin.py`
4. **Update `src/pyartisan/cli/commands/__init__.py`** untuk mere-export semua command.
5. **Update `src/pyartisan/cli/__init__.py`** untuk meregistrasikan command-command tersebut.
6. **Update import** jika ada modul lain (seperti `tests/smoke_test.py`) yang mengimpor dari `marketplace`.

## 7. Verification Plan

1. Jalankan `PYTHONPATH=src python3 tests/smoke_test.py` untuk memastikan seluruh fitur CLI bekerja normal.
2. Jalankan perintah manual CLI (`pyartisan --help`, `pyartisan version`, dll).
