"""Assert-based self-check for the PyArtisan generic manifest-driven engine.

No pytest dependency required — run directly:
    PYTHONPATH=src python3 tests/smoke_test.py
"""
import shutil
import tempfile
import os
from pathlib import Path
import yaml

from click.testing import CliRunner

from pyartisan.utils.naming import name_parts
from pyartisan.core.exceptions import (
    ManifestNotFound,
    ManifestError,
    GeneratorNotSupported,
    TemplateNotFound,
)
from pyartisan.core.manifest import load_manifest
from pyartisan.renderer import render_stub
from pyartisan.core.registration import apply_registration
import pyartisan.config as config
from pyartisan.cli import cli


def test_name_parts():
    assert name_parts("blog") == ("blog", "Blog", "blog", "blogs")
    assert name_parts("blog_post") == ("blog_post", "BlogPost", "blog_post", "blog_posts")
    assert name_parts("blog-post") == ("blog_post", "BlogPost", "blog_post", "blog_posts")
    assert name_parts("category") == ("category", "Category", "category", "categories")
    print("OK  name_parts")


def test_manifest_load():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        try:
            load_manifest(root)
            raise AssertionError("Expected ManifestNotFound")
        except ManifestNotFound:
            pass

        manifest_dir = root / ".pyartisan"
        manifest_dir.mkdir()
        (manifest_dir / "manifest.yaml").write_text("invalid: - [")
        try:
            load_manifest(root)
            raise AssertionError("Expected ManifestError")
        except ManifestError:
            pass

        (manifest_dir / "manifest.yaml").write_text("id: flaskiq\nframework: flask\n")
        data = load_manifest(root)
        assert data["id"] == "flaskiq"
        assert data["framework"] == "flask"
    print("OK  manifest_load")


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


def test_registration_import_list():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        target = root / "app" / "model" / "__init__.py"
        context = {"name_lower": "post", "name_title": "Post"}

        apply_registration("import_list", target, context)
        assert target.exists()
        assert "from .post import Post" in target.read_text()
        assert '__all__ = ["Post"]' in target.read_text()

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
        context = {
            "name": "Post",
            "name_lower": "post",
            "name_title": "Post",
            "name_snake": "post",
            "name_plural": "posts",
        }

        apply_registration(
            "marker",
            target,
            context,
            marker="# pyartisan:routers",
            line_template="app.include_router({{name_lower}}_router)"
        )
        content = target.read_text()
        assert "app.include_router(post_router)" in content

        apply_registration(
            "marker",
            target,
            context,
            marker="# pyartisan:routers",
            line_template="app.include_router({{name_lower}}_router)"
        )
        assert content.count("app.include_router(post_router)") == 1
    print("OK  registration_marker")


def test_config_roundtrip():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        config.CONFIG_DIR = root / ".pyartisan"
        config.CONFIG_PATH = config.CONFIG_DIR / "config.toml"

        data = config.load()
        assert data["theme"] == "default"
        assert "templates" in data
        assert data["templates"]["flask"] == "https://github.com/bijoaja/flaskiq.git"

        config.save({**data, "theme": "dark"})
        reloaded = config.load()
        assert reloaded["theme"] == "dark"
    print("OK  config load/save")


def test_cli_generic_make():
    runner = CliRunner()
    with runner.isolated_filesystem() as tmp_dir:
        root = Path(tmp_dir)
        manifest_dir = root / ".pyartisan"
        manifest_dir.mkdir()

        # Create main.py with model registration marker
        main_py = root / "app" / "main.py"
        main_py.parent.mkdir(parents=True, exist_ok=True)
        main_py.write_text("# pyartisan:models\n")

        manifest_data = {
            "id": "testproj",
            "framework": "flask",
            "paths": {
                "model": "app/model"
            },
            "generators": {
                "model": {
                    "stub": "stubs/model",
                    "stub_subpath": "{{type}}",
                    "path": "model",
                    "dest": "nested_{{type}}",
                    "registration": [
                        {
                            "type": "import_list",
                            "target": "{{path}}/nested_{{type}}/__init__.py"
                        },
                        {
                            "type": "marker",
                            "target": "app/main.py",
                            "marker": "# pyartisan:models",
                            "line": "from app.model.nested_{{type}}.{{name_lower}} import {{name_title}}"
                        }
                    ]
                }
            }
        }
        (manifest_dir / "manifest.yaml").write_text(yaml.dump(manifest_data))

        stub_dir = manifest_dir / "stubs" / "model" / "api"
        stub_dir.mkdir(parents=True)
        (stub_dir / "{{name_lower}}.py.jinja").write_text("class {{name_title}}:\n    pass\n")

        result = runner.invoke(cli, ["make", "model", "Post", "--type", "api"])
        assert result.exit_code == 0, result.output
        assert "Scaffolding" in result.output

        model_file = root / "app" / "model" / "nested_api" / "post.py"
        init_file = root / "app" / "model" / "nested_api" / "__init__.py"
        assert model_file.exists()
        assert model_file.read_text() == "class Post:\n    pass\n"
        assert init_file.exists()
        assert "from .post import Post" in init_file.read_text()

        # Verify marker registration in main.py
        main_content = main_py.read_text()
        assert "from app.model.nested_api.post import Post" in main_content
    print("OK  cli_generic_make")


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
    print("OK  cli_make_not_supported")


def test_cli_make_no_manifest():
    runner = CliRunner()
    with runner.isolated_filesystem() as tmp_dir:
        result = runner.invoke(cli, ["make", "model", "Post"])
        assert result.exit_code != 0
        assert "Not a pyartisan project" in result.output
    print("OK  cli_make_no_manifest")


def test_metadata_parsers():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        # test project.yaml
        project_content = {"project": {"name": "ecommerce"}, "framework": {"name": "fastapi"}}
        with open(root / "project.yaml", "w") as f:
            yaml.dump(project_content, f)

        from pyartisan.core.plugin_engine import load_project_yaml, load_template_yaml, load_plugin_yaml
        res = load_project_yaml(root)
        assert res["project"]["name"] == "ecommerce"

        # test template.yaml
        template_file = root / "template.yaml"
        template_content = {"markers": {"routers": {"file": "app/main.py"}}}
        with open(template_file, "w") as f:
            yaml.dump(template_content, f)
        res_t = load_template_yaml(template_file)
        assert res_t["markers"]["routers"]["file"] == "app/main.py"

        # test plugin manifest.yaml
        plugin_file = root / "manifest.yaml"
        plugin_content = {"id": "payment-midtrans"}
        with open(plugin_file, "w") as f:
            yaml.dump(plugin_content, f)
        res_p = load_plugin_yaml(plugin_file)
        assert res_p["id"] == "payment-midtrans"
    print("OK  metadata_parsers")


def test_project_context_ops():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        pyartisan_dir = root / ".pyartisan"
        pyartisan_dir.mkdir()

        project_yaml_content = {
            "project": {"name": "sandbox"},
            "framework": {"name": "fastapi"},
            "template": {"name": "fastiq", "version": "1.0.0"}
        }
        with open(pyartisan_dir / "project.yaml", "w") as f:
            yaml.dump(project_yaml_content, f)

        # Mock global registry
        home_dir = root / "home"
        home_dir.mkdir()
        global_pyartisan = home_dir / ".pyartisan"
        global_pyartisan.mkdir()
        template_yaml_dir = global_pyartisan / "templates" / "fastiq" / "1.0.0"
        template_yaml_dir.mkdir(parents=True)

        template_yaml_content = {
            "markers": {
                "routers": {
                    "file": "app/main.py",
                    "marker": "# pyartisan:routers"
                }
            },
            "paths": {
                "services": "app/modules/{module}/service.py"
            }
        }
        with open(template_yaml_dir / "template.yaml", "w") as f:
            yaml.dump(template_yaml_content, f)

        # Mock app/main.py
        main_py = root / "app" / "main.py"
        main_py.parent.mkdir(parents=True)
        main_py.write_text("app = FastAPI()\n# pyartisan:routers\n")

        # Mock plugin stub
        stub_file = root / "stub.py.jinja"
        stub_file.write_text("class {{name_title}}Service:\n    pass\n")

        # Mock requirements.txt
        req_file = root / "requirements.txt"
        req_file.write_text("fastapi\n")

        # Patch expanduser to use our temp home
        import os
        orig_expanduser = os.path.expanduser
        os.path.expanduser = lambda path: str(home_dir) if path == "~" else orig_expanduser(path)

        try:
            from pyartisan.core.plugin_engine import ProjectContext
            ctx = ProjectContext(root)
            ctx.create_service("payment", str(stub_file))
            ctx.register_router("payment")
            ctx.add_dependency("stripe")

            # Assert service created
            service_dest = root / "app" / "modules" / "payment" / "service.py"
            assert service_dest.exists()
            assert "class PaymentService:" in service_dest.read_text()

            # Assert router registered
            assert "app.include_router(payment_router" in main_py.read_text()

            # Assert dependency added
            assert "stripe" in req_file.read_text()

        finally:
            os.path.expanduser = orig_expanduser

    print("OK  project_context_ops")


def _setup_plugin_project(root: Path):
    """Helper: bangun struktur project + home + template.yaml + main.py untuk test plugin CLI."""
    pyartisan_dir = root / ".pyartisan"
    pyartisan_dir.mkdir()
    project_yaml_content = {
        "project": {"name": "sandbox"},
        "framework": {"name": "fastapi"},
        "template": {"name": "fastiq", "version": "1.0.0"}
    }
    with open(pyartisan_dir / "project.yaml", "w") as f:
        yaml.dump(project_yaml_content, f)

    home_dir = root / "home"
    home_dir.mkdir()
    global_pyartisan = home_dir / ".pyartisan"
    global_pyartisan.mkdir()
    template_yaml_dir = global_pyartisan / "templates" / "fastiq" / "1.0.0"
    template_yaml_dir.mkdir(parents=True)
    template_yaml_content = {
        "markers": {
            "routers": {
                "file": "app/main.py",
                "marker": "# pyartisan:routers"
            }
        }
    }
    with open(template_yaml_dir / "template.yaml", "w") as f:
        yaml.dump(template_yaml_content, f)

    main_py = root / "app" / "main.py"
    main_py.parent.mkdir()
    main_py.write_text("# pyartisan:routers\n")

    req_file = root / "requirements.txt"
    req_file.write_text("fastapi\n")

    return pyartisan_dir, home_dir


def test_cli_plugin_lifecycle():
    """Test alur lengkap: install (registry) -> apply (project) -> remove (project) -> uninstall (registry)."""
    runner = CliRunner()
    with runner.isolated_filesystem() as tmp_dir:
        root = Path(tmp_dir)
        pyartisan_dir, home_dir = _setup_plugin_project(root)

        # Mock local plugin directory
        plugin_src_dir = root / "my-plugin"
        plugin_src_dir.mkdir()
        manifest_content = {
            "id": "myplugin",
            "name": "My Local Plugin",
            "version": "1.0.0",
            "dependencies": {"pip": ["httpx"]}
        }
        with open(plugin_src_dir / "manifest.yaml", "w") as f:
            yaml.dump(manifest_content, f)

        import os
        orig_expanduser = os.path.expanduser
        os.path.expanduser = lambda path: str(home_dir) if path == "~" else orig_expanduser(path)
        orig_cwd = os.getcwd()

        try:
            os.chdir(root)

            # 1. install: download ke registry saja, project.yaml belum berubah
            result = runner.invoke(cli, ["plugin", "install", "myplugin", "--local", str(plugin_src_dir)])
            assert result.exit_code == 0, result.output
            assert "linked local plugin" in result.output.lower()
            assert "downloaded to registry" in result.output.lower()

            project_config = yaml.safe_load((pyartisan_dir / "project.yaml").read_text())
            assert "plugins" not in project_config or project_config["plugins"] == []

            # plugin list (project) masih kosong sebelum apply
            result = runner.invoke(cli, ["plugin", "list"])
            assert result.exit_code == 0, result.output
            assert "no plugins installed" in result.output.lower()

            # plugin list --global menunjukkan plugin yang sudah di-download
            result = runner.invoke(cli, ["plugin", "list", "--global"])
            assert result.exit_code == 0, result.output
            assert "myplugin@dev" in result.output

            # 2. apply: terapkan ke project
            result = runner.invoke(cli, ["plugin", "apply", "myplugin"])
            assert result.exit_code == 0, result.output
            assert "successfully applied" in result.output.lower()

            project_config = yaml.safe_load((pyartisan_dir / "project.yaml").read_text())
            assert "myplugin@1.0.0" in project_config["plugins"]
            assert "httpx" in (root / "requirements.txt").read_text()

            # plugin list (project) sekarang menunjukkan plugin aktif
            result = runner.invoke(cli, ["plugin", "list"])
            assert "myplugin@1.0.0" in result.output

            # 3. uninstall langsung gagal karena masih dipakai project ini
            result = runner.invoke(cli, ["plugin", "uninstall", "myplugin"])
            assert result.exit_code == 0, result.output
            assert "still used by" in result.output.lower()

            # 4. remove dari project dulu
            result = runner.invoke(cli, ["plugin", "remove", "myplugin"])
            assert result.exit_code == 0, result.output
            assert "removed myplugin@1.0.0" in result.output.lower()

            project_config = yaml.safe_load((pyartisan_dir / "project.yaml").read_text())
            assert "myplugin@1.0.0" not in project_config["plugins"]

            # 5. baru sekarang uninstall dari registry berhasil
            result = runner.invoke(cli, ["plugin", "uninstall", "myplugin"])
            assert result.exit_code == 0, result.output
            assert "uninstalled 'myplugin'" in result.output.lower()

            result = runner.invoke(cli, ["plugin", "list", "--global"])
            assert "no plugins installed in registry" in result.output.lower()

        finally:
            os.path.expanduser = orig_expanduser
            os.chdir(orig_cwd)

    print("OK  cli_plugin_lifecycle")


def test_cli_plugin_install_blockchain_license():
    runner = CliRunner()
    with runner.isolated_filesystem() as tmp_dir:
        root = Path(tmp_dir)
        _pyartisan_dir, home_dir = _setup_plugin_project(root)

        import os
        orig_expanduser = os.path.expanduser
        os.path.expanduser = lambda path: str(home_dir) if path == "~" else orig_expanduser(path)
        orig_cwd = os.getcwd()

        try:
            os.chdir(root)

            result_premium = runner.invoke(cli, ["plugin", "install", "premium-plugin", "--license", "valid-12345"])
            assert result_premium.exit_code == 0, result_premium.output
            assert "license ownership successfully verified" in result_premium.output.lower()

            result_invalid = runner.invoke(cli, ["plugin", "install", "premium-plugin", "--license", "invalid-key"])
            assert "invalid license key" in result_invalid.output.lower()
        finally:
            os.path.expanduser = orig_expanduser
            os.chdir(orig_cwd)

    print("OK  cli_plugin_install_blockchain_license")


def test_cli_plugin_remove_multi_and_all():
    runner = CliRunner()
    with runner.isolated_filesystem() as tmp_dir:
        root = Path(tmp_dir)
        pyartisan_dir, home_dir = _setup_plugin_project(root)

        project_yaml_content = yaml.safe_load((pyartisan_dir / "project.yaml").read_text())
        project_yaml_content["plugins"] = ["payment-midtrans@1.0.0", "auth-jwt@2.0.0", "docker-tools@1.2.1"]
        with open(pyartisan_dir / "project.yaml", "w") as f:
            yaml.dump(project_yaml_content, f)

        import os
        orig_cwd = os.getcwd()
        os.chdir(root)
        try:
            # Test list
            result = runner.invoke(cli, ["plugin", "list"])
            assert result.exit_code == 0, result.output
            assert "payment-midtrans@1.0.0" in result.output
            assert "auth-jwt@2.0.0" in result.output
            assert "docker-tools@1.2.1" in result.output

            # Test remove satu plugin dari project
            result = runner.invoke(cli, ["plugin", "remove", "payment-midtrans"])
            assert result.exit_code == 0, result.output
            assert "removed payment-midtrans@1.0.0" in result.output.lower()

            updated_config = yaml.safe_load((pyartisan_dir / "project.yaml").read_text())
            assert "payment-midtrans@1.0.0" not in updated_config["plugins"]
            assert "auth-jwt@2.0.0" in updated_config["plugins"]

            # Test remove banyak plugin sekaligus
            result = runner.invoke(cli, ["plugin", "remove", "auth-jwt", "docker-tools"])
            assert result.exit_code == 0, result.output
            updated_config2 = yaml.safe_load((pyartisan_dir / "project.yaml").read_text())
            assert updated_config2["plugins"] == []

            # Re-populate untuk test --all
            project_yaml_content["plugins"] = ["payment-midtrans@1.0.0", "auth-jwt@2.0.0"]
            with open(pyartisan_dir / "project.yaml", "w") as f:
                yaml.dump(project_yaml_content, f)

            result = runner.invoke(cli, ["plugin", "remove", "--all"])
            assert result.exit_code == 0, result.output
            updated_config3 = yaml.safe_load((pyartisan_dir / "project.yaml").read_text())
            assert updated_config3["plugins"] == []
        finally:
            os.chdir(orig_cwd)

    print("OK  cli_plugin_remove_multi_and_all")


def test_cli_plugin_info_status_doctor():
    runner = CliRunner()
    with runner.isolated_filesystem() as tmp_dir:
        root = Path(tmp_dir)
        pyartisan_dir, home_dir = _setup_plugin_project(root)

        plugin_src_dir = root / "my-plugin"
        plugin_src_dir.mkdir()
        manifest_content = {
            "id": "myplugin",
            "name": "My Local Plugin",
            "version": "1.0.0",
            "description": "Plugin uji coba",
            "author": "Tester",
            "dependencies": {"pip": ["httpx"]},
            "environment": ["MY_PLUGIN_KEY"]
        }
        with open(plugin_src_dir / "manifest.yaml", "w") as f:
            yaml.dump(manifest_content, f)

        import os
        orig_expanduser = os.path.expanduser
        os.path.expanduser = lambda path: str(home_dir) if path == "~" else orig_expanduser(path)
        orig_cwd = os.getcwd()

        try:
            os.chdir(root)

            # plugin belum di-install: info gagal
            result = runner.invoke(cli, ["plugin", "info", "myplugin"])
            assert "not found in registry" in result.output.lower()

            # install + apply
            result = runner.invoke(cli, ["plugin", "install", "myplugin", "--local", str(plugin_src_dir)])
            assert result.exit_code == 0, result.output

            # info sebelum apply: "Used by" kosong
            result = runner.invoke(cli, ["plugin", "info", "myplugin"])
            assert result.exit_code == 0, result.output
            assert "my local plugin" in result.output.lower()
            assert "httpx" in result.output
            assert "my_plugin_key" in result.output.lower()
            assert "not applied to any project" in result.output.lower()

            result = runner.invoke(cli, ["plugin", "apply", "myplugin"])
            assert result.exit_code == 0, result.output

            # info setelah apply: "Used by" berisi path project
            result = runner.invoke(cli, ["plugin", "info", "myplugin"])
            assert str(root) in result.output

            # status: project sehat karena plugin ada di registry
            result = runner.invoke(cli, ["plugin", "status"])
            assert result.exit_code == 0, result.output
            assert "myplugin@1.0.0" in result.output
            assert "health     : ok" in result.output.lower()

            # doctor: semua check lolos
            result = runner.invoke(cli, ["plugin", "doctor"])
            assert result.exit_code == 0, result.output
            assert "plugin is valid" in result.output.lower()

            # doctor mendeteksi dependency belum ditambahkan ke requirements.txt
            (root / "requirements.txt").write_text("fastapi\n")
            result = runner.invoke(cli, ["plugin", "doctor"])
            assert "missing httpx" in result.output.lower()
            assert "plugin has issues" in result.output.lower()

        finally:
            os.path.expanduser = orig_expanduser
            os.chdir(orig_cwd)

    print("OK  cli_plugin_info_status_doctor")


def test_cli_plugin_list_updates():
    runner = CliRunner()
    with runner.isolated_filesystem() as tmp_dir:
        root = Path(tmp_dir)
        _pyartisan_dir, home_dir = _setup_plugin_project(root)

        import os
        orig_expanduser = os.path.expanduser
        os.path.expanduser = lambda path: str(home_dir) if path == "~" else orig_expanduser(path)
        orig_cwd = os.getcwd()

        try:
            os.chdir(root)

            # Tidak ada plugin git-based di registry
            result = runner.invoke(cli, ["plugin", "list", "--updates"])
            assert result.exit_code == 0, result.output
            assert "no git-based plugins in registry" in result.output.lower()

        finally:
            os.path.expanduser = orig_expanduser
            os.chdir(orig_cwd)

    print("OK  cli_plugin_list_updates")


def _patch_home(root: Path):
    """Helper: point os.path.expanduser('~') at an isolated home dir under root."""
    home_dir = root / "home"
    home_dir.mkdir()
    orig_expanduser = os.path.expanduser
    os.path.expanduser = lambda path: str(home_dir) if path == "~" else orig_expanduser(path)
    return home_dir, orig_expanduser


def test_cli_plugin_init_all_frameworks():
    """`pyartisan plugin init <name>` scaffolds skeleton + registers dev symlink."""
    import os
    runner = CliRunner()
    with runner.isolated_filesystem() as tmp_dir:
        root = Path(tmp_dir)
        home_dir, orig_expanduser = _patch_home(root)
        orig_cwd = os.getcwd()

        try:
            os.chdir(root)

            result = runner.invoke(cli, ["plugin", "init", "crud-blogs"], input="all\n")
            assert result.exit_code == 0, result.output
            assert "plugin skeleton created" in result.output.lower()

            plugin_dir = root / "crud-blogs"
            assert (plugin_dir / "manifest.yaml").exists()
            assert (plugin_dir / "hooks.py").exists()
            assert (plugin_dir / "README.md").exists()
            assert (plugin_dir / "LICENSE").exists()
            assert (plugin_dir / "stubs" / "fastapi" / ".gitkeep").exists()
            assert (plugin_dir / "stubs" / "flask" / ".gitkeep").exists()
            assert (plugin_dir / "stubs" / "django" / ".gitkeep").exists()

            manifest = yaml.safe_load((plugin_dir / "manifest.yaml").read_text())
            assert manifest["id"] == "crud-blogs"
            assert manifest["name"] == "CrudBlogs Plugin"
            assert manifest["version"] == "1.0.0"

            registry_link = home_dir / ".pyartisan" / "plugins" / "crud-blogs" / "dev"
            from pyartisan.cli.commands.plugin import _is_link
            assert _is_link(registry_link)  # symlink, or junction on Windows without privilege
            assert registry_link.resolve() == plugin_dir.resolve()
        finally:
            os.path.expanduser = orig_expanduser
            os.chdir(orig_cwd)

    print("OK  cli_plugin_init_all_frameworks")


def test_cli_plugin_init_single_framework():
    """Only the chosen framework's stub folder is created."""
    import os
    runner = CliRunner()
    with runner.isolated_filesystem() as tmp_dir:
        root = Path(tmp_dir)
        _home_dir, orig_expanduser = _patch_home(root)
        orig_cwd = os.getcwd()

        try:
            os.chdir(root)

            result = runner.invoke(cli, ["plugin", "init", "demo-plugin"], input="fastapi\n")
            assert result.exit_code == 0, result.output

            plugin_dir = root / "demo-plugin"
            assert (plugin_dir / "stubs" / "fastapi" / ".gitkeep").exists()
            assert not (plugin_dir / "stubs" / "flask").exists()
            assert not (plugin_dir / "stubs" / "django").exists()
        finally:
            os.path.expanduser = orig_expanduser
            os.chdir(orig_cwd)

    print("OK  cli_plugin_init_single_framework")


def test_cli_plugin_init_existing_directory():
    """Command refuses to overwrite an existing directory."""
    import os
    runner = CliRunner()
    with runner.isolated_filesystem() as tmp_dir:
        root = Path(tmp_dir)
        _home_dir, orig_expanduser = _patch_home(root)
        orig_cwd = os.getcwd()

        try:
            os.chdir(root)
            (root / "demo-plugin").mkdir()
            (root / "demo-plugin" / "keep-me.txt").write_text("do not touch")

            result = runner.invoke(cli, ["plugin", "init", "demo-plugin"], input="all\n")
            assert result.exit_code == 0, result.output
            assert "already exists" in result.output.lower()

            assert not (root / "demo-plugin" / "manifest.yaml").exists()
            assert (root / "demo-plugin" / "keep-me.txt").exists()
        finally:
            os.path.expanduser = orig_expanduser
            os.chdir(orig_cwd)

    print("OK  cli_plugin_init_existing_directory")


def test_uv_support():
    import pyartisan.core.engine as engine
    import pyartisan.shared.doctor as doctor

    # doctor: uv optional, pip optional when uv present
    orig_which = shutil.which
    try:
        shutil.which = lambda n: None
        assert doctor._check_uv()[0] is True
        assert doctor._check_pip()[0] is False
        shutil.which = lambda n: "/x/uv" if n == "uv" else None
        assert doctor._check_pip()[0] is True
    finally:
        shutil.which = orig_which

    # installer command selection
    assert engine._venv_cmd("/x/uv") == ["/x/uv", "venv", "venv"]
    assert engine._venv_cmd(None)[1:] == ["-m", "venv", "venv"]
    assert engine._install_cmd("/x/uv", "py", "r.txt") == ["/x/uv", "pip", "install", "--python", "py", "-r", "r.txt"]
    assert engine._install_cmd(None, "py", "r.txt") == ["py", "-m", "pip", "install", "-r", "r.txt"]
    print("OK  uv_support")


def test_force_utf8():
    import io
    from pyartisan.cli import _force_utf8

    buf = io.BytesIO()
    s = io.TextIOWrapper(buf, encoding="cp1252")
    try:
        s.write("✔")
        raise AssertionError("cp1252 should not encode ✔")
    except UnicodeEncodeError:
        pass
    s = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
    _force_utf8(s, None, object())  # None and non-TextIOWrapper must not raise
    s.write("✔❌")
    s.flush()
    assert s.encoding == "utf-8"
    print("OK  force_utf8")


def test_serve_project_venv():
    import sys
    import pyartisan.core.engine as engine

    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        assert engine._find_project_venv(cwd) is None  # no venv in project

        venv = cwd / ".venv"
        py = engine._venv_python(venv)
        py.parent.mkdir(parents=True)
        py.write_text("")
        assert engine._find_project_venv(cwd) is None  # no pyvenv.cfg: not a venv
        (venv / "pyvenv.cfg").write_text("")
        assert engine._find_project_venv(cwd) == venv

        # the env pyartisan itself runs in must never be picked up
        orig_prefix, orig_ve = sys.prefix, os.environ.pop("VIRTUAL_ENV", None)
        try:
            sys.prefix = str(venv)
            assert engine._find_project_venv(cwd) is None
            os.environ["VIRTUAL_ENV"] = str(venv)  # VIRTUAL_ENV == own prefix: still skipped
            assert engine._find_project_venv(cwd) is None
        finally:
            sys.prefix = orig_prefix
            os.environ.pop("VIRTUAL_ENV", None)
            if orig_ve is not None:
                os.environ["VIRTUAL_ENV"] = orig_ve

        argv, env = engine._venv_command(venv, ["python3", "server.py"])
        assert argv == [str(py), "server.py"]  # python3 mapped to venv python
        assert env["VIRTUAL_ENV"] == str(venv)
        assert env["PATH"].startswith(str(engine._venv_bin(venv)))
        assert engine._venv_command(venv, ["no-such-tool", "x"])[0] == ["no-such-tool", "x"]
    print("OK  serve_project_venv")


def main():
    test_serve_project_venv()
    test_force_utf8()
    test_uv_support()
    test_name_parts()
    test_manifest_load()
    test_render_stub()
    test_registration_import_list()
    test_registration_marker()
    test_config_roundtrip()
    test_cli_generic_make()
    test_cli_make_not_supported()
    test_cli_make_no_manifest()
    test_metadata_parsers()
    test_project_context_ops()
    test_cli_plugin_lifecycle()
    test_cli_plugin_install_blockchain_license()
    test_cli_plugin_remove_multi_and_all()
    test_cli_plugin_info_status_doctor()
    test_cli_plugin_list_updates()
    test_cli_plugin_init_all_frameworks()
    test_cli_plugin_init_single_framework()
    test_cli_plugin_init_existing_directory()
    print("\nALL SMOKE TESTS PASSED")


if __name__ == "__main__":
    main()
