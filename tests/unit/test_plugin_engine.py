import yaml

from pyartisan.core.plugin_engine import (
    ProjectContext,
    load_plugin_yaml,
    load_project_yaml,
    load_template_yaml,
)


def test_metadata_parsers(tmp_path):
    project_content = {"project": {"name": "ecommerce"}, "framework": {"name": "fastapi"}}
    with open(tmp_path / "project.yaml", "w", encoding="utf-8") as f:
        yaml.dump(project_content, f)

    res = load_project_yaml(tmp_path)
    assert res["project"]["name"] == "ecommerce"

    template_file = tmp_path / "template.yaml"
    template_content = {"markers": {"routers": {"file": "app/main.py"}}}
    with open(template_file, "w", encoding="utf-8") as f:
        yaml.dump(template_content, f)
    res_t = load_template_yaml(template_file)
    assert res_t["markers"]["routers"]["file"] == "app/main.py"

    plugin_file = tmp_path / "manifest.yaml"
    plugin_content = {"id": "payment-midtrans"}
    with open(plugin_file, "w", encoding="utf-8") as f:
        yaml.dump(plugin_content, f)
    res_p = load_plugin_yaml(plugin_file)
    assert res_p["id"] == "payment-midtrans"


def test_project_context_ops(fake_home, tmp_path):
    root = tmp_path
    pyartisan_dir = root / ".pyartisan"
    pyartisan_dir.mkdir()

    project_yaml_content = {
        "project": {"name": "sandbox"},
        "framework": {"name": "fastapi"},
        "template": {"name": "fastiq", "version": "1.0.0"},
    }
    with open(pyartisan_dir / "project.yaml", "w", encoding="utf-8") as f:
        yaml.dump(project_yaml_content, f)

    home_dir = fake_home
    global_pyartisan = home_dir / ".pyartisan"
    global_pyartisan.mkdir(parents=True, exist_ok=True)
    template_yaml_dir = global_pyartisan / "templates" / "fastiq" / "1.0.0"
    template_yaml_dir.mkdir(parents=True, exist_ok=True)

    template_yaml_content = {
        "markers": {
            "routers": {
                "file": "app/main.py",
                "marker": "# pyartisan:routers",
            }
        },
        "paths": {
            "services": "app/modules/{module}/service.py",
        },
    }
    with open(template_yaml_dir / "template.yaml", "w", encoding="utf-8") as f:
        yaml.dump(template_yaml_content, f)

    main_py = root / "app" / "main.py"
    main_py.parent.mkdir(parents=True, exist_ok=True)
    main_py.write_text("app = FastAPI()\n# pyartisan:routers\n", encoding="utf-8")

    stub_file = root / "stub.py.jinja"
    stub_file.write_text("class {{name_title}}Service:\n    pass\n", encoding="utf-8")

    req_file = root / "requirements.txt"
    req_file.write_text("fastapi\n", encoding="utf-8")

    ctx = ProjectContext(root)
    ctx.create_service("payment", str(stub_file))
    ctx.register_router("payment")
    ctx.add_dependency("stripe")

    service_dest = root / "app" / "modules" / "payment" / "service.py"
    assert service_dest.exists()
    assert "class PaymentService:" in service_dest.read_text(encoding="utf-8")
    assert "app.include_router(payment_router" in main_py.read_text(encoding="utf-8")
    assert "stripe" in req_file.read_text(encoding="utf-8")


def test_has_requirement():
    from pyartisan.core.plugin_engine import has_requirement

    assert has_requirement("flask-cors==4\n", "flask") is False
    assert has_requirement("Flask>=2\n", "flask") is True
    assert has_requirement("my_pkg\n", "my-pkg") is True
    assert has_requirement("# flask\n", "flask") is False
    assert has_requirement("flask[async]\n", "flask>=2") is True


def test_add_dependency_not_fooled_by_substring(fake_home, tmp_path):
    pyartisan_dir = tmp_path / ".pyartisan"
    pyartisan_dir.mkdir()
    with open(pyartisan_dir / "project.yaml", "w", encoding="utf-8") as f:
        yaml.dump(
            {
                "project": {"name": "sub"},
                "framework": {"name": "fastapi"},
                "template": {"name": "fastiq", "version": "1.0.0"},
            },
            f,
        )
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("flask-cors\n", encoding="utf-8")

    ctx = ProjectContext(tmp_path)
    ctx.add_dependency("flask")
    lines = [
        line.strip() for line in req_file.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    assert "flask" in lines
    assert "flask-cors" in lines


def test_add_dependency_idempotent(fake_home, tmp_path):
    pyartisan_dir = tmp_path / ".pyartisan"
    pyartisan_dir.mkdir()
    with open(pyartisan_dir / "project.yaml", "w", encoding="utf-8") as f:
        yaml.dump(
            {
                "project": {"name": "idem"},
                "framework": {"name": "fastapi"},
                "template": {"name": "fastiq", "version": "1.0.0"},
            },
            f,
        )
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("", encoding="utf-8")

    ctx = ProjectContext(tmp_path)
    ctx.add_dependency("flask")
    ctx.add_dependency("flask")
    lines = [
        line.strip() for line in req_file.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    assert lines.count("flask") == 1


def test_create_service_missing_stub_raises(fake_home, tmp_path):
    import pytest

    from pyartisan.core.exceptions import ManifestError

    pyartisan_dir = tmp_path / ".pyartisan"
    pyartisan_dir.mkdir()
    with open(pyartisan_dir / "project.yaml", "w", encoding="utf-8") as f:
        yaml.dump(
            {
                "project": {"name": "stubtest"},
                "framework": {"name": "fastapi"},
                "template": {"name": "fastiq", "version": "1.0.0"},
            },
            f,
        )

    ctx = ProjectContext(tmp_path)
    with pytest.raises(ManifestError, match="Stub not found"):
        ctx.create_service("nonexistent", "missing/stub.py.jinja")

    dest = tmp_path / "app" / "services" / "nonexistent.py"
    assert not dest.exists()
