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
        "paths": {"model": "app/model"},
        "generators": {
            "model": {
                "stub": "stubs/model",
                "stub_subpath": "{{type}}",
                "path": "model",
                "dest": "nested_{{type}}",
                "registration": [
                    {"type": "import_list", "target": "{{path}}/nested_{{type}}/__init__.py"},
                    {
                        "type": "marker",
                        "target": "app/main.py",
                        "marker": "# pyartisan:models",
                        "line": "from app.model.nested_{{type}}.{{name_lower}} import {{name_title}}",
                    },
                ],
            }
        },
    }
    (manifest_dir / "manifest.yaml").write_text(yaml.dump(manifest_data), encoding="utf-8")

    stub_dir = manifest_dir / "stubs" / "model" / "api"
    stub_dir.mkdir(parents=True)
    (stub_dir / "{{name_lower}}.py.jinja").write_text(
        "class {{name_title}}:\n    pass\n", encoding="utf-8"
    )

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


def _project(root, generator=None):
    """Create <root>/proj with a manifest and one controller stub; return the project dir."""
    proj = root / "proj"
    manifest_dir = proj / ".pyartisan"
    (manifest_dir / "stubs" / "ctl").mkdir(parents=True)
    (manifest_dir / "stubs" / "ctl" / "{{name_lower}}.py.jinja").write_text(
        "class {{name_title}}: pass\n", encoding="utf-8"
    )
    gen = {"stub": "stubs/ctl", "path": "controller"}
    gen.update(generator or {})
    manifest = {
        "id": "testproj",
        "framework": "flask",
        "paths": {"controller": "app/controller"},
        "generators": {"controller": gen},
    }
    (manifest_dir / "manifest.yaml").write_text(yaml.dump(manifest), encoding="utf-8")
    return proj


def _files(root):
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())


def test_make_rejects_traversal_name(runner, tmp_path, monkeypatch):
    proj = _project(tmp_path)
    monkeypatch.chdir(proj)
    before = _files(tmp_path)

    result = runner.invoke(cli, ["make", "controller", "../../escaped"])

    assert result.exit_code == 1, result.output
    assert _files(tmp_path) == before


def test_make_rejects_nested_name(runner, tmp_path, monkeypatch):
    proj = _project(tmp_path)
    monkeypatch.chdir(proj)
    before = _files(tmp_path)

    result = runner.invoke(cli, ["make", "controller", "admin/user"])

    assert result.exit_code == 1, result.output
    assert _files(tmp_path) == before


def test_make_rejects_manifest_dest_escape(runner, tmp_path, monkeypatch):
    proj = _project(tmp_path, {"dest": "../../out"})
    monkeypatch.chdir(proj)
    before = _files(tmp_path)

    result = runner.invoke(cli, ["make", "controller", "Post"])

    assert result.exit_code == 1, result.output
    assert _files(tmp_path) == before


def test_new_rejects_bad_project_name(runner, in_tmp_cwd, isolated_config, monkeypatch):
    def _boom(*args, **kwargs):
        raise AssertionError("subprocess.run must not be called")

    monkeypatch.setattr("subprocess.run", _boom)

    result = runner.invoke(cli, ["new", "flask", "../x"])

    assert result.exit_code == 1, result.output
    assert "Invalid project name" in result.output
