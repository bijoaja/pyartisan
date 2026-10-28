import sys

import pyartisan.core.engine as engine


def test_serve_project_venv(monkeypatch, tmp_path):
    cwd = tmp_path
    assert engine._find_project_venv(cwd) is None  # no venv in project

    venv = cwd / ".venv"
    py = engine._venv_python(venv)
    py.parent.mkdir(parents=True)
    py.write_text("", encoding="utf-8")
    assert engine._find_project_venv(cwd) is None  # no pyvenv.cfg: not a venv
    (venv / "pyvenv.cfg").write_text("", encoding="utf-8")
    assert engine._find_project_venv(cwd) == venv

    # the env pyartisan itself runs in must never be picked up
    monkeypatch.setattr(sys, "prefix", str(venv))
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    assert engine._find_project_venv(cwd) is None
    monkeypatch.setenv("VIRTUAL_ENV", str(venv))  # VIRTUAL_ENV == own prefix: still skipped
    assert engine._find_project_venv(cwd) is None

    argv, env = engine._venv_command(venv, ["python3", "server.py"])
    assert argv == [str(py), "server.py"]  # python3 mapped to venv python
    assert env["VIRTUAL_ENV"] == str(venv)
    assert env["PATH"].startswith(str(engine._venv_bin(venv)))
    assert engine._venv_command(venv, ["no-such-tool", "x"])[0] == ["no-such-tool", "x"]
