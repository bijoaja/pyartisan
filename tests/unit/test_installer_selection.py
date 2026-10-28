from pyartisan.core.engine import _detect_install_plan, _install_cmd, _venv_cmd


def test_installer_selection(tmp_path):
    assert _venv_cmd("/x/uv") == ["/x/uv", "venv", "venv"]
    assert _venv_cmd(None)[1:] == ["-m", "venv", "venv"]
    assert _install_cmd("/x/uv", "py", "r.txt") == [
        "/x/uv",
        "pip",
        "install",
        "--python",
        "py",
        "-r",
        "r.txt",
    ]
    assert _install_cmd(None, "py", "r.txt") == ["py", "-m", "pip", "install", "-r", "r.txt"]

    assert _detect_install_plan(tmp_path, "/x/uv", "py") is None

    (tmp_path / "requirements.txt").write_text("flask\n", encoding="utf-8")
    desc, cmd = _detect_install_plan(tmp_path, "/x/uv", "py")
    assert "requirements.txt" in desc
    assert cmd == ["/x/uv", "pip", "install", "--python", "py", "-r", "requirements.txt"]

    (tmp_path / "pyproject.toml").write_text("[project]\nname='test'\n", encoding="utf-8")
    desc, cmd = _detect_install_plan(tmp_path, "/x/uv", "py")
    assert "uv sync" in desc
    assert cmd == ["/x/uv", "sync"]

    desc_no_uv, cmd_no_uv = _detect_install_plan(tmp_path, None, "py")
    assert "pyproject.toml" in desc_no_uv
    assert cmd_no_uv == ["py", "-m", "pip", "install", "-e", "."]
