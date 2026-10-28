import os

import pytest

from pyartisan.core.exceptions import PyArtisanError
from pyartisan.utils.safe import safe_child, validate_clone_url, validate_name


@pytest.mark.parametrize("value", ["blog", "my.plugin", "42-crud", "a_b-c", "x" * 100])
def test_validate_name_accepts(value):
    assert validate_name(value) == value


@pytest.mark.parametrize(
    "value",
    ["", ".", "..", "a/b", "a\\b", "C:x", "-x", ".x", "x" * 101, "a b", "a\n"],
)
def test_validate_name_rejects(value):
    with pytest.raises(PyArtisanError, match="Invalid name"):
        validate_name(value)


def test_validate_name_uses_what_in_message():
    with pytest.raises(PyArtisanError, match="Invalid plugin name: '..'"):
        validate_name("..", "plugin name")


def test_safe_child_inside(tmp_path):
    assert safe_child(tmp_path, "a", "b") == tmp_path / "a" / "b"


@pytest.mark.parametrize("parts", [("..",), ("a", "..", ".."), (".",), ("",)])
def test_safe_child_rejects(tmp_path, parts):
    with pytest.raises(PyArtisanError):
        safe_child(tmp_path, *parts)


def test_safe_child_rejects_absolute(tmp_path):
    with pytest.raises(PyArtisanError):
        safe_child(tmp_path, str(tmp_path.parent))


def test_safe_child_does_not_follow_links(tmp_path):
    reg = tmp_path / "reg"
    reg.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        os.symlink(outside, reg / "p", target_is_directory=True)
    except OSError:
        pytest.skip("symlinks not permitted")
    assert safe_child(reg, "p") == reg / "p"


@pytest.mark.parametrize(
    "url",
    [
        "https://github.com/o/r.git",
        "ssh://git@host/o/r.git",
        "git@github.com:o/r.git",
    ],
)
def test_validate_clone_url_accepts(url):
    assert validate_clone_url(url) == url


@pytest.mark.parametrize(
    "url",
    [
        "-oProxyCommand=x",
        "--upload-pack=x",
        "http://h/r",
        "file:///r",
        "/local/path",
        "C:\\r",
        "https://h/r with space",
        "",
    ],
)
def test_validate_clone_url_rejects(url):
    with pytest.raises(PyArtisanError, match="Invalid URL"):
        validate_clone_url(url)
