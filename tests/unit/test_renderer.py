import pytest

from pyartisan.core.exceptions import PyArtisanError
from pyartisan.renderer import render_stub


def test_render_stub(tmp_path):
    stub_dir = tmp_path / "stubs"
    stub_dir.mkdir()
    (stub_dir / "{{name_lower}}_service.py.jinja").write_text(
        "class {{name_title}}Service:\n    pass\n", encoding="utf-8"
    )

    dest_dir = tmp_path / "app" / "service"
    context = {
        "name_lower": "blog_post",
        "name_title": "BlogPost",
    }

    rendered = render_stub(stub_dir, dest_dir, context)
    assert len(rendered) == 1
    service_file = dest_dir / "blog_post_service.py"
    assert service_file.exists()
    assert service_file.read_text(encoding="utf-8") == "class BlogPostService:\n    pass\n"


def test_render_stub_nested(tmp_path):
    """Stubs in sub-folders must render on every OS (Jinja needs '/' in template names)."""
    stub_dir = tmp_path / "stubs"
    nested = stub_dir / "{{name_lower}}"
    nested.mkdir(parents=True)
    (nested / "{{name_lower}}_controller.py.jinja").write_text(
        "class {{name_title}}Controller: pass\n", encoding="utf-8"
    )
    (stub_dir / "flat.py.jinja").write_text("x = '{{name_lower}}'\n", encoding="utf-8")

    dest_dir = tmp_path / "app"
    rendered = render_stub(stub_dir, dest_dir, {"name_lower": "post", "name_title": "Post"})
    assert len(rendered) == 2
    assert (dest_dir / "post" / "post_controller.py").read_text(
        encoding="utf-8"
    ) == "class PostController: pass\n"
    assert (dest_dir / "flat.py").read_text(encoding="utf-8") == "x = 'post'\n"


def test_render_stub_rejects_escape(tmp_path):
    stub_dir = tmp_path / "stubs"
    stub_dir.mkdir()
    (stub_dir / "{{name_lower}}_c.py.jinja").write_text("x\n", encoding="utf-8")
    dest_dir = tmp_path / "a" / "b" / "c"

    with pytest.raises(PyArtisanError):
        render_stub(stub_dir, dest_dir, {"name_lower": "../../../escaped"})

    assert not list(tmp_path.glob("escaped*"))
    assert not list(tmp_path.rglob("*_c.py"))


def test_render_stub_rejects_before_writing_anything(tmp_path):
    stub_dir = tmp_path / "stubs"
    stub_dir.mkdir()
    (stub_dir / "a_ok.py.jinja").write_text("ok\n", encoding="utf-8")
    (stub_dir / "{{evil}}.py.jinja").write_text("bad\n", encoding="utf-8")
    dest_dir = tmp_path / "out"

    with pytest.raises(PyArtisanError):
        render_stub(stub_dir, dest_dir, {"evil": "../x"})

    assert not dest_dir.exists() or not any(dest_dir.iterdir())
    assert not (tmp_path / "x.py").exists()
