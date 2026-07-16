# Unified Manifest-Driven CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mengubah pyartisan menjadi generic CLI engine murni berbasis `.pyartisan/manifest.yaml` + Jinja2 stub rendering, menghapus detector framework/plugin Python yang hardcode, dan menyamakan CLI commands (`new`, `make <target> <name>`, `serve`, `build`) di seluruh framework.

**Architecture:** 
1. Core CLI (`cli/__init__.py`) diubah menjadi parser tipis murni spasi (`pyartisan make <target> <name>`).
2. `core/engine.py` bertindak sebagai dispatcher generic tunggal: mencari manifest di cwd, memproses input nama, me-render template `.jinja` dari folder target stub project, menerapkan file registration target (`import_list` atau `marker`), dan menjalankan lifecycle scripts (`serve`/`build`) berdasar fallback docker/venv.
3. Seluruh template generator lama di `plugin/flask` & `plugin/fastapi` dihapus total dari engine.

**Tech Stack:** Python 3.10+, Click, Jinja2, PyYAML.

## Global Constraints
- Menggunakan standard library & native library Python sedapat mungkin.
- Seluruh path file harus absolute path jika memanggil file eksternal di luar cwd, namun relative path digunakan untuk file generated di dalam project target.
- Semua target file yang digenerate harus divalidasi keunikan namanya dan tidak dioverwrite kecuali dengan flag `--force`.
- Tidak ada runtime dependency eksternal saat hasil project di-run oleh developer target.

---

### Task 1: Konfigurasi Dependencies & Exceptions Baru

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/pyartisan/core/exceptions.py`
- Test: `tests/smoke_test.py`

**Interfaces:**
- Consumes: None
- Produces: `ManifestNotFound`, `ManifestError`, `GeneratorNotSupported`, `TemplateNotFound` exceptions

- [ ] **Step 1: Daftarkan dependencies baru**
Edit `pyproject.toml` untuk menambahkan `jinja2` dan `pyyaml` ke dalam dependency list.

```toml
dependencies = [
    "click",
    "flask",
    "sqlalchemy",
    "tomli; python_version < '3.11'",
    "jinja2",
    "pyyaml",
]
```

- [ ] **Step 2: Tambahkan Exception baru**
Edit `src/pyartisan/core/exceptions.py` untuk menambahkan Exception baru:

```python
class ManifestNotFound(PyArtisanError):
    """Raised when .pyartisan/manifest.yaml cannot be found in cwd."""

class ManifestError(PyArtisanError):
    """Raised when manifest.yaml is invalid or has structural errors."""

class GeneratorNotSupported(PyArtisanError):
    """Raised when the requested generator is not supported by the template."""

class TemplateNotFound(PyArtisanError):
    """Raised when no git repository URL is registered for the requested framework."""
```

- [ ] **Step 3: Edit import di smoke test**
Ubah import exceptions di `tests/smoke_test.py` untuk menguji exception baru nanti:
```python
from pyartisan.core.exceptions import (
    PluginNotFound,
    ManifestNotFound,
    ManifestError,
    GeneratorNotSupported,
    TemplateNotFound,
)
```

- [ ] **Step 4: Jalankan smoke test**
Jalankan: `PYTHONPATH=src python3 tests/smoke_test.py`
Expected: Smoke test lulus karena exception baru belum dipakai di runtime.

- [ ] **Step 5: Commit**
```bash
git add pyproject.toml src/pyartisan/core/exceptions.py tests/smoke_test.py
git commit -m "feat: add jinja2/pyyaml dependencies and new exception classes"
```

---

### Task 2: Implementasi Extended Naming & Manifest Loader

**Files:**
- Modify: `src/pyartisan/utils/naming.py`
- Create: `src/pyartisan/core/manifest.py`
- Test: `tests/smoke_test.py`

**Interfaces:**
- Consumes: None
- Produces: 
  - `naming.name_parts(name) -> tuple[str, str, str, str]` (name_lower, name_title, name_snake, name_plural)
  - `manifest.load_manifest() -> dict`

- [ ] **Step 1: Tulis extended naming helper**
Edit `src/pyartisan/utils/naming.py` untuk menghasilkan snake_case dan plural secara dinamis:

```python
def name_parts(name: str) -> tuple[str, str, str, str]:
    """Return (name_lower, name_title, name_snake, name_plural) from user input.

    Examples:
        'blog_post' -> ('blog_post', 'BlogPost', 'blog_post', 'blog_posts')
        'category'  -> ('category', 'Category', 'category', 'categories')
    """
    name_lower = name.lower().replace("-", "_")
    name_snake = name_lower
    name_title = "".join(w.capitalize() for w in name_lower.split("_"))
    
    # Pluralisasi sederhana
    if name_lower.endswith("y") and not name_lower.endswith(("ay", "ey", "oy", "uy")):
        name_plural = name_lower[:-1] + "ies"
    elif name_lower.endswith("s"):
        name_plural = name_lower
    else:
        name_plural = name_lower + "s"
        
    return name_lower, name_title, name_snake, name_plural
```

- [ ] **Step 2: Tulis manifest loader**
Buat `src/pyartisan/core/manifest.py`:

```python
import os
import yaml
from pathlib import Path
from pyartisan.core.exceptions import ManifestNotFound, ManifestError

def load_manifest(cwd: Path | None = None) -> dict:
    """Load and validate .pyartisan/manifest.yaml from cwd root."""
    cwd = cwd or Path.cwd()
    manifest_path = cwd / ".pyartisan" / "manifest.yaml"
    
    if not manifest_path.exists():
        raise ManifestNotFound(
            "Not a pyartisan project. Run inside a project generated by `pyartisan new`, "
            "or add .pyartisan/manifest.yaml"
        )
        
    try:
        with open(manifest_path, "r") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        raise ManifestError(f"Invalid manifest at {manifest_path}: {e}")
        
    if not data or not isinstance(data, dict):
        raise ManifestError(f"Manifest at {manifest_path} must be a non-empty YAML object.")
        
    # Validasi basic keys
    if "id" not in data or "framework" not in data:
        raise ManifestError(f"Manifest at {manifest_path} is missing 'id' or 'framework' keys.")
        
    return data
```

- [ ] **Step 3: Tulis unit test di smoke test**
Tambahkan `test_naming_extended()` dan `test_manifest_load()` di `tests/smoke_test.py`:

```python
def test_naming_extended():
    assert name_parts("blog-post") == ("blog_post", "BlogPost", "blog_post", "blog_posts")
    assert name_parts("category") == ("category", "Category", "category", "categories")
    print("OK  name_parts_extended")

def test_manifest_load():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        # Test missing manifest
        try:
            load_manifest(root)
            raise AssertionError("Expected ManifestNotFound")
        except ManifestNotFound:
            pass
            
        # Test invalid yaml
        manifest_dir = root / ".pyartisan"
        manifest_dir.mkdir()
        (manifest_dir / "manifest.yaml").write_text("invalid: - [")
        try:
            load_manifest(root)
            raise AssertionError("Expected ManifestError")
        except ManifestError:
            pass

        # Test valid yaml
        (manifest_dir / "manifest.yaml").write_text("id: flaskiq\nframework: flask\n")
        data = load_manifest(root)
        assert data["id"] == "flaskiq"
    print("OK  manifest_load")
```
Ingat untuk mendaftarkan test function baru ini ke `main()` di `tests/smoke_test.py` dan import `load_manifest` di bagian atas file.

- [ ] **Step 4: Jalankan smoke test**
Jalankan: `PYTHONPATH=src python3 tests/smoke_test.py`
Expected: `OK  name_parts_extended` dan `OK  manifest_load` tercetak, test lulus.

- [ ] **Step 5: Commit**
```bash
git add src/pyartisan/utils/naming.py src/pyartisan/core/manifest.py tests/smoke_test.py
git commit -m "feat: add manifest loader and extended naming parts"
```

---

### Task 3: Implementasi Jinja2 Stub Renderer

**Files:**
- Create: `src/pyartisan/renderer/__init__.py`
- Test: `tests/smoke_test.py`

**Interfaces:**
- Consumes: `pyartisan.utils.fs.write_file`
- Produces: `renderer.render_stub(stub_dir: Path, dest_dir: Path, context: dict, force: bool = False)`

- [ ] **Step 1: Tulis Renderer dengan Jinja2**
Tulis isi `src/pyartisan/renderer/__init__.py`:

```python
import os
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from pyartisan.utils.fs import write_file

def render_stub(stub_dir: Path, dest_dir: Path, context: dict, force: bool = False) -> list[Path]:
    """Walk through stub_dir, render file names & contents via Jinja2, and write to dest_dir."""
    if not stub_dir.exists():
        raise FileNotFoundError(f"Stub directory not found: {stub_dir}")
        
    rendered_files = []
    # Setup Jinja environment
    env = Environment(loader=FileSystemLoader(str(stub_dir)))
    
    # Render file names and contents
    for root, _, files in os.walk(stub_dir):
        for file in files:
            # File name rendering (e.g. {{name_lower}}_controller.py.jinja -> users_controller.py)
            rel_path = Path(root).relative_to(stub_dir) / file
            rendered_rel_path_str = env.from_string(str(rel_path)).render(context)
            
            # Remove .jinja suffix if present
            if rendered_rel_path_str.endswith(".jinja"):
                rendered_rel_path_str = rendered_rel_path_str[:-6]
                
            dest_file_path = dest_dir / rendered_rel_path_str
            
            # Content rendering
            template = env.get_template(str(rel_path))
            content = template.render(context)
            
            write_file(str(dest_file_path), content, overwrite=force)
            rendered_files.append(dest_file_path)
            
    return rendered_files
```

- [ ] **Step 2: Tulis unit test di smoke test**
Tambahkan `test_render_stub()` di `tests/smoke_test.py`:

```python
from pyartisan.renderer import render_stub

def test_render_stub():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        stub_dir = root / "stubs"
        stub_dir.mkdir()
        (stub_dir / "{{name_lower}}_service.py.jinja").write_text(
            "class {{name_title}}Service:\n    pass\n"
        )
        
        dest_dir = root / "app" / "service"
        context = {
            "name_lower": "blog_post",
            "name_title": "BlogPost",
        }
        
        rendered = render_stub(stub_dir, dest_dir, context)
        assert len(rendered) == 1
        service_file = dest_dir / "blog_post_service.py"
        assert service_file.exists()
        assert service_file.read_text() == "class BlogPostService:\n    pass\n"
    print("OK  render_stub")
```
Daftarkan `test_render_stub()` ke `main()`.

- [ ] **Step 3: Jalankan smoke test**
Jalankan: `PYTHONPATH=src python3 tests/smoke_test.py`
Expected: `OK  render_stub` tercetak, test lulus.

- [ ] **Step 4: Commit**
```bash
git add src/pyartisan/renderer/__init__.py tests/smoke_test.py
git commit -m "feat: implement jinja2 stub renderer"
```

---

### Task 4: Implementasi Registration Engine (Import & Marker)

**Files:**
- Create: `src/pyartisan/core/registration.py`
- Test: `tests/smoke_test.py`

**Interfaces:**
- Consumes: None
- Produces: `registration.apply_registration(reg_type: str, target_file: Path, context: dict, marker: str = None, line: str = None)`

- [ ] **Step 1: Tulis Registration Engine**
Buat `src/pyartisan/core/registration.py`:

```python
import os
from pathlib import Path
from pyartisan.utils import console

def apply_registration(
    reg_type: str,
    target_file: Path,
    context: dict,
    marker: str = None,
    line_template: str = None
) -> None:
    """Apply import list or marker-based registration into target_file."""
    os.makedirs(target_file.parent, exist_ok=True)
    
    # Variable context unpack
    name_lower = context["name_lower"]
    name_title = context["name_title"]
    
    if reg_type == "import_list":
        # Strategy 1: import_list (mirror pyartisan.utils.fs.write_service_init)
        file_stem = f"{name_lower}_controller" if "controller" in str(target_file) else name_lower
        # Jika service, bedakan view/api
        if "service" in str(target_file):
            file_stem = f"{name_lower}_service"
            class_name = f"{name_title}ApiService" if "api" in str(target_file) else f"{name_title}Service"
        elif "repository" in str(target_file):
            file_stem = f"{name_lower}_repository"
            class_name = f"{name_title}Repository"
        elif "model" in str(target_file):
            class_name = name_title
        else:
            class_name = name_title
            
        import_line = f"from .{file_stem} import {class_name}"
        all_entry = f'"{class_name}"'
        
        if not target_file.exists():
            target_file.write_text(f"{import_line}\n\n__all__ = [{all_entry}]\n")
            console.success(f"created: {target_file}")
            return
            
        content = target_file.read_text()
        if import_line in content:
            return # already registered
            
        lines = content.splitlines()
        new_lines = []
        all_updated = False
        insert_at = 0
        
        for i, line in enumerate(lines):
            if line.strip().startswith("__all__") and not all_updated:
                insert_at = i
                stripped = line.rstrip()
                if stripped.endswith("]"):
                    line = stripped[:-1].rstrip() + f", {all_entry}]"
                all_updated = True
            new_lines.append(line)
            
        new_lines.insert(insert_at, import_line)
        if not all_updated:
            new_lines.append(f'\n__all__ = [{all_entry}]')
            
        target_file.write_text("\n".join(new_lines) + "\n")
        console.success(f"updated: {target_file}")
        
    elif reg_type == "marker":
        # Strategy 2: marker comment insertion
        if not marker or not line_template:
            return
            
        # Render target line (e.g. app.include_router({{name_lower}}_router) -> app.include_router(users_router))
        from jinja2 import Environment
        target_line = Environment().from_string(line_template).render(context)
        
        if not target_file.exists():
            # Create file with marker
            target_file.write_text(f"{marker}\n{target_line}\n")
            console.success(f"created: {target_file}")
            return
            
        content = target_file.read_text()
        if target_line in content:
            return # already registered
            
        if marker not in content:
            # Fallback append if marker is missing
            target_file.write_text(content + f"\n{target_line}\n")
            console.success(f"updated: {target_file}")
            return
            
        lines = content.splitlines()
        new_lines = []
        for line in lines:
            new_lines.append(line)
            if marker in line:
                new_lines.append(target_line)
                
        target_file.write_text("\n".join(new_lines) + "\n")
        console.success(f"updated: {target_file}")
```

- [ ] **Step 2: Tulis unit test di smoke test**
Tambahkan `test_registration_import_list()` dan `test_registration_marker()` di `tests/smoke_test.py`:

```python
from pyartisan.core.registration import apply_registration

def test_registration_import_list():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        target = root / "app" / "model" / "__init__.py"
        context = {"name_lower": "post", "name_title": "Post"}
        
        # Test create new init
        apply_registration("import_list", target, context)
        assert target.exists()
        assert "from .post import Post" in target.read_text()
        assert '__all__ = ["Post"]' in target.read_text()
        
        # Test append to init
        context2 = {"name_lower": "comment", "name_title": "Comment"}
        apply_registration("import_list", target, context2)
        content = target.read_text()
        assert "from .comment import Comment" in content
        assert '__all__ = ["Post", "Comment"]' in content
    print("OK  registration_import_list")

def test_registration_marker():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        target = root / "main.py"
        target.write_text("app = FastAPI()\n# pyartisan:routers\n")
        context = {"name_lower": "post"}
        
        # Test insert under marker
        apply_registration(
            "marker",
            target,
            context,
            marker="# pyartisan:routers",
            line_template="app.include_router({{name_lower}}_router)"
        )
        content = target.read_text()
        assert "app.include_router(post_router)" in content
        
        # Test idempotency (no duplicate line)
        apply_registration(
            "marker",
            target,
            context,
            marker="# pyartisan:routers",
            line_template="app.include_router({{name_lower}}_router)"
        )
        assert content.count("app.include_router(post_router)") == 1
    print("OK  registration_marker")
```
Daftarkan kedua test function ke `main()`.

- [ ] **Step 3: Jalankan smoke test**
Jalankan: `PYTHONPATH=src python3 tests/smoke_test.py`
Expected: `OK  registration_import_list` dan `OK  registration_marker` tercetak, test lulus.

- [ ] **Step 4: Commit**
```bash
git add src/pyartisan/core/registration.py tests/smoke_test.py
git commit -m "feat: implement import_list and marker registration engine"
```

---

### Task 5: Implementasi CLI Parser & Engine Dispatcher Baru

**Files:**
- Create/Overwrite: `src/pyartisan/cli/__init__.py`
- Create/Overwrite: `src/pyartisan/core/engine.py`
- Delete: `src/pyartisan/core/detector.py`, `src/pyartisan/core/context.py`, `src/pyartisan/plugin_loader.py`
- Delete folders: `src/pyartisan/plugin/flask`, `src/pyartisan/plugin/fastapi`, `src/pyartisan/plugin/` (kecuali `base.py` & `registry.py` tapi karena generic engine murni, seluruh folder `plugin` termasuk `base.py` dan `registry.py` bisa kita hapus total).
- Test: `tests/smoke_test.py`

**Interfaces:**
- Consumes: `manifest.load_manifest`, `renderer.render_stub`, `registration.apply_registration`
- Produces: CLI commands `new`, `make`, `serve`, `build`

- [ ] **Step 1: Hapus file core & plugin lama**
```bash
rm -rf src/pyartisan/core/detector.py src/pyartisan/core/context.py src/pyartisan/plugin_loader.py src/pyartisan/plugin/
```

- [ ] **Step 2: Implementasi engine dispatcher generik**
Tulis ulang `src/pyartisan/core/engine.py`:

```python
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
import click

from pyartisan.core.manifest import load_manifest
from pyartisan.core.exceptions import GeneratorNotSupported, TemplateNotFound
from pyartisan.renderer import render_stub
from pyartisan.core.registration import apply_registration
from pyartisan.utils.naming import name_parts
from pyartisan import config as config_module

def dispatch_new(framework: str, project_name: str) -> None:
    """Initialize a new project by cloning the framework template."""
    config_data = config_module.load()
    templates = config_data.get("templates", {
        "flask": "https://github.com/bijoaja/flaskiq.git",
        "fastapi": "https://github.com/bijoaja/fastiq.git",
    })
    
    if framework not in templates:
        raise TemplateNotFound(
            f"No template registered for framework '{framework}'. "
            f"Available: {', '.join(templates.keys())}"
        )
        
    repo_url = templates[framework]
    
    if os.path.exists(project_name):
        click.echo(f"❌ Folder '{project_name}' already exists, choose a different name.")
        sys.exit(1)
        
    click.echo(f"⬇ Cloning {framework} template repository ...")
    try:
        result = subprocess.run(
            ["git", "clone", repo_url, project_name],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            click.echo("❌ Failed to clone project!")
            click.echo(result.stderr)
            sys.exit(1)
            
        click.echo(f"✔ Project cloned into: {project_name}")
        subprocess.run(["git", "remote", "rm", "origin"], cwd=project_name, capture_output=True)
    except FileNotFoundError:
        click.echo("❌ Git not found! Install Git first.")
        sys.exit(1)
        
    install_dependencies = click.confirm(
        "Do you want to create a virtual environment and install dependencies now?", default=True
    )
    if not install_dependencies:
        click.echo("⚠ Skipping virtual environment and dependency installation.")
        return
        
    os.chdir(project_name)
    click.echo("⚙ Creating virtual environment (venv)...")
    try:
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
        click.echo("✔ Virtual environment created successfully.")
    except Exception as e:
        click.echo(f"❌ Failed to create venv: {e}")
        sys.exit(1)
        
    venv_python = "venv\\Scripts\\python.exe" if os.name == "nt" else "venv/bin/python"
    req_file = "requirements.txt"
    if not os.path.exists(req_file):
        click.echo("⚠ requirements.txt not found, skipping dependency installation.")
        return
        
    click.echo("📦 Installing dependencies from requirements.txt ...")
    try:
        subprocess.run([venv_python, "-m", "pip", "install", "-r", req_file], check=True)
        click.echo("✔ Dependencies installed successfully.")
    except Exception as e:
        click.echo(f"❌ Failed to install dependencies: {e}")
        sys.exit(1)
        
    click.echo("\n🎉 Project initialization complete!")
    click.echo(f"   cd {project_name}")
    if os.name == "nt":
        click.echo("   venv\\Scripts\\activate")
    else:
        click.echo("   source venv/bin/activate")
    click.echo("   pyartisan serve\n")

def dispatch_make(target: str, name: str, force: bool = False) -> None:
    """Process file generation using manifest.yaml configuration."""
    cwd = Path.cwd()
    manifest = load_manifest(cwd)
    
    if "generators" not in manifest or target not in manifest["generators"]:
        avail = ", ".join(manifest.get("generators", {}).keys())
        raise GeneratorNotSupported(
            f"'{manifest['id']}' does not support generator '{target}'. "
            f"Available: {avail}"
        )
        
    gen_config = manifest["generators"][target]
    stub_rel = gen_config.get("stub")
    path_key = gen_config.get("path")
    
    if not stub_rel or not path_key:
        raise ManifestError(f"Generator '{target}' configuration must specify 'stub' and 'path' keys.")
        
    stub_dir = cwd / ".pyartisan" / stub_rel
    if not stub_dir.exists():
        raise ManifestError(f"Stub directory not found on disk: {stub_dir}")
        
    dest_path_rel = manifest.get("paths", {}).get(path_key)
    if not dest_path_rel:
        raise ManifestError(f"Path key '{path_key}' (used by '{target}') is not defined in manifest 'paths'.")
        
    dest_dir = cwd / dest_path_rel
    
    # Render context
    name_lower, name_title, name_snake, name_plural = name_parts(name)
    context = {
        "name": name,
        "name_lower": name_lower,
        "name_title": name_title,
        "name_snake": name_snake,
        "name_plural": name_plural,
    }
    
    click.echo(f"Scaffolding '{name_title}' ({target}) ...")
    render_stub(stub_dir, dest_dir, context, force=force)
    
    # Registration
    if "registration" in gen_config:
        reg = gen_config["registration"]
        reg_type = reg.get("type")
        target_template = reg.get("target")
        
        if not reg_type or not target_template:
            raise ManifestError(f"Registration configuration for '{target}' is missing 'type' or 'target'.")
            
        # Render target path
        from jinja2 import Environment
        target_file_rel = Environment().from_string(target_template).render(
            path=dest_path_rel, **context
        )
        target_file = cwd / target_file_rel
        
        apply_registration(
            reg_type=reg_type,
            target_file=target_file,
            context=context,
            marker=reg.get("marker"),
            line_template=reg.get("line")
        )
        
    click.echo(f"Done. '{name_title}' scaffolded successfully.")

def _docker_available() -> bool:
    try:
        subprocess.run(
            ["docker", "info"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
        return True
    except Exception:
        return False

def dispatch_serve() -> None:
    """Run dev server using the fallback docker -> venv -> warning strategy."""
    cwd = Path.cwd()
    manifest = load_manifest(cwd) # ensures it's a project
    
    # 1. Cek docker compose
    if (cwd / "docker-compose.yml").exists() and _docker_available():
        click.echo("Starting dev server with Docker (docker compose up) ...")
        try:
            # Cari docker compose binary
            cmd = ["docker", "compose", "up"]
            try:
                subprocess.run(["docker", "compose", "version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            except Exception:
                cmd = ["docker-compose", "up"]
            subprocess.run(cmd)
        except KeyboardInterrupt:
            click.echo("\nServer stopped.")
        return
        
    # 2. Cek venv + script serve
    is_venv = sys.prefix != sys.base_prefix or os.environ.get("VIRTUAL_ENV") is not None
    serve_script = manifest.get("scripts", {}).get("serve")
    
    if is_venv and serve_script:
        click.echo("Starting dev server locally ...")
        try:
            # Jalankan serve script
            subprocess.run(shlex.split(serve_script))
        except KeyboardInterrupt:
            click.echo("\nServer stopped.")
        except Exception as e:
            click.echo(f"❌ Serve script failed: {e}")
            sys.exit(1)
        return
        
    # 3. Fallback warning
    click.echo("Error: No docker-compose.yml active and no active virtual environment.")
    click.echo("  To resolve:")
    click.echo("    - Make sure Docker is running and run `pyartisan make docker` if needed.")
    if serve_script:
        click.echo("    - Activate your virtual environment first:")
        click.echo("        Mac/Linux: source venv/bin/activate")
        click.echo("        Windows:   venv\\Scripts\\activate")
    sys.exit(1)

def dispatch_build() -> None:
    """Run production build script."""
    cwd = Path.cwd()
    manifest = load_manifest(cwd)
    build_script = manifest.get("scripts", {}).get("build")
    
    if not build_script:
        click.echo("❌ No 'build' script defined in manifest.yaml.")
        sys.exit(1)
        
    click.echo(f"Running build script: {build_script} ...")
    try:
        subprocess.run(shlex.split(build_script), check=True)
        click.echo("✔ Build completed successfully.")
    except Exception as e:
        click.echo(f"❌ Build failed: {e}")
        sys.exit(1)
```

- [ ] **Step 3: Tulis ulang CLI parser tipis**
Tulis ulang `src/pyartisan/cli/__init__.py`:

```python
import sys
import click

from pyartisan import __version__
from pyartisan import config as config_module
from pyartisan.core import engine
from pyartisan.shared.doctor import run_checks

@click.group()
@click.version_option(__version__, prog_name="pyartisan")
def cli():
    """pyartisan - AI-powered Python Web Development Toolkit"""

@cli.command(name="new")
@click.argument("framework")
@click.argument("name")
def new_cmd(framework: str, name: str) -> None:
    """Create a new project using framework template."""
    engine.dispatch_new(framework, name)

@cli.command(name="make")
@click.argument("target")
@click.argument("name")
@click.option("--force", is_flag=True, default=False, help="Overwrite existing files")
def make_cmd(target: str, name: str, force: bool) -> None:
    """Scaffold files from template stubs (e.g. make controller Post)."""
    engine.dispatch_make(target, name, force=force)

@cli.command(name="serve")
def serve_cmd() -> None:
    """Run dev server (Docker fallback to local virtualenv)."""
    engine.dispatch_serve()

@cli.command(name="build")
def build_cmd() -> None:
    """Build production artifact using manifest build script."""
    engine.dispatch_build()

@cli.group(name="config", invoke_without_command=True)
@click.pass_context
def config_group(ctx):
    """Manage ~/.pyartisan/config.toml"""
    if ctx.invoked_subcommand is None:
        ctx.invoke(config_show)

@config_group.command(name="show")
def config_show():
    """Print current configuration."""
    data = config_module.load()
    for key, value in data.items():
        click.echo(f"{key} = {value!r}")

@config_group.command(name="reset")
def config_reset():
    """Reset configuration to defaults."""
    config_module.reset()
    click.echo("✔ Configuration reset to defaults.")

@config_group.command(name="set")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str):
    """Set a config key, e.g. pyartisan config set templates.flask <url>"""
    data = config_module.load()
    
    # Handle nested templates key
    if key.startswith("templates."):
        sub = key.split(".")[1]
        if "templates" not in data:
            data["templates"] = {}
        data["templates"][sub] = value
    else:
        if key not in data:
            click.echo(f"❌ Unknown config key: {key}")
            sys.exit(1)
        data[key] = value
        
    config_module.save(data)
    click.echo(f"✔ {key} = {value}")

@cli.command(name="doctor")
def doctor():
    """Check Python, pip, Git, and environment health."""
    ok = run_checks()
    if not ok:
        sys.exit(1)

@cli.command(name="version")
def version():
    """Show pyartisan version."""
    click.echo(f"pyartisan {__version__}")

if __name__ == "__main__":
    cli()
```

- [ ] **Step 4: Update config defaults untuk support templates map**
Edit `src/pyartisan/config/__init__.py` untuk mendaftarkan default templates:

```python
DEFAULT_CONFIG = {
    "theme": "default",
    "author": "",
    "license": "MIT",
    "default_framework": "flask",
    "templates": {
        "flask": "https://github.com/bijoaja/flaskiq.git",
        "fastapi": "https://github.com/bijoaja/fastiq.git",
    }
}
```

- [ ] **Step 5: Ganti test_detect_framework & test_plugin_loader di smoke test**
Ubah `tests/smoke_test.py` untuk menguji unit baru & CLI generik ini. Hapus test detector/plugin loader lama, dan tulis test baru:

```python
from click.testing import CliRunner
import yaml

def test_cli_generic_make():
    runner = CliRunner()
    with runner.isolated_filesystem() as tmp_dir:
        root = Path(tmp_dir)
        manifest_dir = root / ".pyartisan"
        manifest_dir.mkdir()
        
        # Buat manifest fixture
        manifest_data = {
            "id": "testproj",
            "framework": "flask",
            "paths": {
                "model": "app/model"
            },
            "generators": {
                "model": {
                    "stub": "stubs/model",
                    "path": "model",
                    "registration": {
                        "type": "import_list",
                        "target": "{path}/__init__.py"
                    }
                }
            }
        }
        (manifest_dir / "manifest.yaml").write_text(yaml.dump(manifest_data))
        
        # Buat stub fixture
        stub_dir = manifest_dir / "stubs" / "model"
        stub_dir.mkdir(parents=True)
        (stub_dir / "{{name_lower}}.py.jinja").write_text("class {{name_title}}:\n    pass\n")
        
        # Run make command
        result = runner.invoke(cli, ["make", "model", "Post"])
        assert result.exit_code == 0, result.output
        assert "Scaffolding" in result.output
        
        # Assert files created
        model_file = root / "app" / "model" / "post.py"
        init_file = root / "app" / "model" / "__init__.py"
        assert model_file.exists()
        assert model_file.read_text() == "class Post:\n    pass\n"
        assert init_file.exists()
        assert "from .post import Post" in init_file.read_text()

def test_cli_make_not_supported():
    runner = CliRunner()
    with runner.isolated_filesystem() as tmp_dir:
        root = Path(tmp_dir)
        manifest_dir = root / ".pyartisan"
        manifest_dir.mkdir()
        manifest_data = {"id": "testproj", "framework": "flask", "generators": {}}
        (manifest_dir / "manifest.yaml").write_text(yaml.dump(manifest_data))
        
        result = runner.invoke(cli, ["make", "router", "payment"])
        assert result.exit_code != 0
        assert "does not support generator 'router'" in result.output
```
Ubah `main()` di `tests/smoke_test.py` agar mengimpor & memanggil:
```python
def main():
    test_naming_extended()
    test_manifest_load()
    test_render_stub()
    test_registration_import_list()
    test_registration_marker()
    test_cli_generic_make()
    test_cli_make_not_supported()
    print("\nALL SMOKE TESTS PASSED")
```
Hapus `test_detect_framework`, `test_plugin_loader`, dan `test_cli_end_to_end` lama dari `tests/smoke_test.py` (karena behavior lamanya sudah berubah).

- [ ] **Step 6: Jalankan smoke test**
Jalankan: `PYTHONPATH=src python3 tests/smoke_test.py`
Expected: `ALL SMOKE TESTS PASSED` dengan seluruh tes generic engine baru lulus.

- [ ] **Step 7: Commit**
```bash
git add src/pyartisan/cli/ src/pyartisan/core/engine.py src/pyartisan/config/__init__.py tests/smoke_test.py
# Clean up deleted files from git
git rm src/pyartisan/core/detector.py src/pyartisan/core/context.py src/pyartisan/plugin_loader.py
git rm -r src/pyartisan/plugin/src/pyartisan/plugin/
git commit -m "feat: complete rewrite to unified manifest-driven CLI & delete old plugin system"
```

---

### Task 6: Migrasi Template Project (flaskiq & fastiq)

**Files:**
- Create: `/home/bijoaja/my_project/pyartisan/flaskiq/.pyartisan/manifest.yaml`
- Create: `/home/bijoaja/my_project/pyartisan/flaskiq/.pyartisan/stubs/` (controller, model, repository, service)
- Create: `/home/bijoaja/my_project/pyartisan/fastiq/.pyartisan/manifest.yaml`
- Create: `/home/bijoaja/my_project/pyartisan/fastiq/.pyartisan/stubs/` (router, service, repository, schemas)

*Catatan: Sesuai parameter "Termasuk Keduanya", kita harus melengkapi kedua folder local project agar siap di-generate oleh engine baru.*

- [ ] **Step 1: Inisialisasi folder manifest di flaskiq**
Jalankan:
```bash
mkdir -p /home/bijoaja/my_project/pyartisan/flaskiq/.pyartisan/stubs/controller
mkdir -p /home/bijoaja/my_project/pyartisan/flaskiq/.pyartisan/stubs/model
mkdir -p /home/bijoaja/my_project/pyartisan/flaskiq/.pyartisan/stubs/repository
mkdir -p /home/bijoaja/my_project/pyartisan/flaskiq/.pyartisan/stubs/service
```

- [ ] **Step 2: Buat manifest.yaml flaskiq**
Tulis `/home/bijoaja/my_project/pyartisan/flaskiq/.pyartisan/manifest.yaml`:

```yaml
id: flaskiq
framework: flask
version: 1.0

paths:
  controller: app/controller
  service: app/service
  repository: app/repository
  model: app/model

generators:
  controller:
    stub: stubs/controller
    path: controller
    registration:
      type: import_list
      target: "{path}/view/{name_lower}/__init__.py"
  service:
    stub: stubs/service
    path: service
    registration:
      type: import_list
      target: "{path}/__init__.py"
  repository:
    stub: stubs/repository
    path: repository
    registration:
      type: import_list
      target: "{path}/__init__.py"
  model:
    stub: stubs/model
    path: model
    registration:
      type: import_list
      target: "{path}/__init__.py"

scripts:
  serve: "python3 server.py"
```

- [ ] **Step 3: Tulis stub model flaskiq**
Tulis `/home/bijoaja/my_project/pyartisan/flaskiq/.pyartisan/stubs/model/{{name_lower}}.py.jinja`:

```python
from app import db


class {{name_title}}(db.Model):
    __tablename__ = "{{name_plural}}"

    id         = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=db.func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "created_at": str(self.created_at),
            "updated_at": str(self.updated_at),
        }
```

- [ ] **Step 4: Tulis stub controller, service, repository untuk flaskiq**
Gunakan f-string lama di `make_controller.py` dkk sebagai referensi isi template Jinja2 baru ini. Tulis stub di directory `.pyartisan/stubs/`.

- [ ] **Step 5: Inisialisasi folder manifest di fastiq**
Jalankan:
```bash
mkdir -p /home/bijoaja/my_project/pyartisan/fastiq/.pyartisan/stubs/router
mkdir -p /home/bijoaja/my_project/pyartisan/fastiq/.pyartisan/stubs/service
mkdir -p /home/bijoaja/my_project/pyartisan/fastiq/.pyartisan/stubs/repository
mkdir -p /home/bijoaja/my_project/pyartisan/fastiq/.pyartisan/stubs/schemas
```

- [ ] **Step 6: Buat manifest.yaml fastiq**
Tulis `/home/bijoaja/my_project/pyartisan/fastiq/.pyartisan/manifest.yaml`:

```yaml
id: fastiq
framework: fastapi
version: 1.0

paths:
  modules: app/modules

generators:
  feature:
    stub: stubs
    path: modules
    registration:
      type: marker
      target: app/main.py
      marker: "# pyartisan:routers"
      line: "from app.modules.{{name_lower}}.router import router as {{name_lower}}_router\napp.include_router({{name_lower}}_router)"
```
Note: module di FastAPI (FastIQ) meng-generate model, repository, router, service, schemas sekaligus di dalam folder modul tersebut. Cukup daftarkan `feature` generator yang mengarah ke `stubs/` (induk folder).

- [ ] **Step 7: Tulis stub router, service, repository, schemas untuk fastiq**
Gunakan codebase `fastiq/app/modules/auth/` sebagai referensi template. Tulis stub di folder stubs masing-masing di `.pyartisan/stubs/`.

- [ ] **Step 8: Verifikasi manual eksekusi generator**
Buka scratch dir baru, clone template lokal (e.g. `flaskiq`), jalankan generator baru `pyartisan make model Post`, dan pastikan file model + `__init__.py` update dengan benar.
