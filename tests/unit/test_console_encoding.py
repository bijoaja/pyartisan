import io
import pytest
from pyartisan.cli import _force_utf8


def test_force_utf8():
    buf = io.BytesIO()
    s = io.TextIOWrapper(buf, encoding="cp1252")
    with pytest.raises(UnicodeEncodeError):
        s.write("✔")

    s = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
    _force_utf8(s, None, object())  # None and non-TextIOWrapper must not raise
    s.write("✔❌")
    s.flush()
    assert s.encoding == "utf-8"
