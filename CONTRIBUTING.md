# Contributing to PyArtisan

Contributions are welcome: bug reports, fixes, docs, and new features.

**Full guide:** [English](docs/en/CONTRIBUTING.md) | [Indonesia](docs/id/CONTRIBUTING.md)

## Quick start

```bash
git clone https://github.com/bijoaja/pyartisan.git
cd pyartisan
uv tool install --editable .    # isolated env, no venv needed
```

Run the test suite (pytest):

```bash
uv run pytest
```

All 24 tests should pass.

## Pull requests

1. Open or pick an issue.
2. Branch from `main`, keep the change small, run `uv run pytest`.
3. Open a PR to `main` with `Closes #<number>` in the description, and say what was and was not verified.
4. Docs live in two languages (`docs/en/`, `docs/id/`): change both.

---

# Berkontribusi ke PyArtisan

Kontribusi sangat diterima: laporan bug, perbaikan, dokumentasi, dan fitur baru.

**Panduan lengkap:** [Indonesia](docs/id/CONTRIBUTING.md) | [English](docs/en/CONTRIBUTING.md)

Langkah singkat: clone repo, `uv tool install --editable .`, jalankan test suite (`uv run pytest`), buat branch dari `main`, lalu buka PR dengan `Closes #<nomor>`. Dokumentasi ada dalam dua bahasa (`docs/en/`, `docs/id/`): ubah keduanya.
