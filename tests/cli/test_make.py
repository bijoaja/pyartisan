from pathlib import Path
import yaml
from pyartisan.cli import cli


def test_cli_generic_make(runner, in_tmp_cwd):
    root = in_tmp_cwd
    manifest_dir = root / ".pyartisan"
    manifest_dir.mkdir()

    # Create main.py with model registration marker
    main_py = root / "app" / "main.py"
    main_py.parent.mkdir(parents=True, exist_ok=True)
    main_py.write_text("# pyartisan:models\n", encoding="utf-8")

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
    (manifest_dir / "manifest.yaml").write_text(yaml.dump(manifest_data), encoding="utf-8")

    stub_dir = manifest_dir / "stubs" / "model" / "api"
    stub_dir.mkdir(parents=True)
    (stub_dir / "{{name_lower}}.py.jinja").write_text("class {{name_title}}:\n    pass\n", encoding="utf-8")

    result = runner.invoke(cli, ["make", "model", "Post", "--type", "api"])
    assert result.exit_code == 0, result.output
    assert "Scaffolding" in result.output

    model_file = root / "app" / "model" / "nested_api" / "post.py"
    init_file = root / "app" / "model" / "nested_api" / "__init__.py"
    assert model_file.exists()
    assert model_file.read_text(encoding="utf-8") == "class Post:\n    pass\n"
    assert init_file.exists()
    assert "from .post import Post" in init_file.read_text(encoding="utf-8")

    # Verify marker registration in main.py
    main_content = main_py.read_text(encoding="utf-8")
    assert "from app.model.nested_api.post import Post" in main_content


def test_cli_make_not_supported(runner, in_tmp_cwd):
    root = in_tmp_cwd
    manifest_dir = root / ".pyartisan"
    manifest_dir.mkdir()
    manifest_data = {"id": "testproj", "framework": "flask", "generators": {}}
    (manifest_dir / "manifest.yaml").write_text(yaml.dump(manifest_data), encoding="utf-8")

    result = runner.invoke(cli, ["make", "router", "payment"])
    assert result.exit_code != 0
    assert "does not support generator 'router'" in result.output


def test_cli_make_no_manifest(runner, in_tmp_cwd):
    result = runner.invoke(cli, ["make", "model", "Post"])
    assert result.exit_code != 0
    assert "Not a pyartisan project" in result.output
