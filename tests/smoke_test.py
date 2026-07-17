"""Assert-based self-check for the PyArtisan generic manifest-driven engine.

No pytest dependency required — run directly:
    PYTHONPATH=src python3 tests/smoke_test.py
"""
import shutil
import tempfile
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


def main():
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
    print("\nALL SMOKE TESTS PASSED")


if __name__ == "__main__":
    main()
