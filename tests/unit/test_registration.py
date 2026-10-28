from pyartisan.core.registration import apply_registration


def test_registration_import_list(tmp_path):
    target = tmp_path / "app" / "model" / "__init__.py"
    context = {"name_lower": "post", "name_title": "Post"}

    apply_registration("import_list", target, context)
    assert target.exists()
    assert "from .post import Post" in target.read_text(encoding="utf-8")
    assert '__all__ = ["Post"]' in target.read_text(encoding="utf-8")

    context2 = {"name_lower": "comment", "name_title": "Comment"}
    apply_registration("import_list", target, context2)
    content = target.read_text(encoding="utf-8")
    assert "from .comment import Comment" in content
    assert '__all__ = ["Post", "Comment"]' in content


def test_registration_marker(tmp_path):
    target = tmp_path / "main.py"
    target.write_text("app = FastAPI()\n# pyartisan:routers\n", encoding="utf-8")
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
        line_template="app.include_router({{name_lower}}_router)",
    )
    content = target.read_text(encoding="utf-8")
    assert "app.include_router(post_router)" in content

    apply_registration(
        "marker",
        target,
        context,
        marker="# pyartisan:routers",
        line_template="app.include_router({{name_lower}}_router)",
    )
    assert content.count("app.include_router(post_router)") == 1


def test_marker_registration_without_marker_is_noop(tmp_path):
    target = tmp_path / "main.py"
    target.write_text("initial content\n", encoding="utf-8")
    apply_registration("marker", target, {}, marker=None, line_template=None)
    assert target.read_text(encoding="utf-8") == "initial content\n"
