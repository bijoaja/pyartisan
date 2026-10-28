import shutil
import pyartisan.shared.doctor as doctor


def test_doctor_uv_and_pip(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda n: None)
    assert doctor._check_uv()[0] is True
    assert doctor._check_pip()[0] is False

    monkeypatch.setattr(shutil, "which", lambda n: "/x/uv" if n == "uv" else None)
    assert doctor._check_pip()[0] is True
