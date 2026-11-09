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


def test_registration_components(tmp_path):
    ctl_api = tmp_path / "app" / "controller" / "api" / "__init__.py"
    apply_registration("import_list", ctl_api, {"name_lower": "user", "name_title": "User"})
    assert "from .user_controller import UserApiController" in ctl_api.read_text(encoding="utf-8")
    assert '__all__ = ["UserApiController"]' in ctl_api.read_text(encoding="utf-8")

    ctl_view = tmp_path / "app" / "controller" / "__init__.py"
    apply_registration("import_list", ctl_view, {"name_lower": "user", "name_title": "User"})
    assert "from .user_controller import UserController" in ctl_view.read_text(encoding="utf-8")

    svc_api = tmp_path / "app" / "service" / "api" / "__init__.py"
    apply_registration("import_list", svc_api, {"name_lower": "user", "name_title": "User"})
    assert "from .user_service import UserApiService" in svc_api.read_text(encoding="utf-8")
    assert '__all__ = ["UserApiService"]' in svc_api.read_text(encoding="utf-8")

    svc_view = tmp_path / "app" / "service" / "__init__.py"
    apply_registration("import_list", svc_view, {"name_lower": "user", "name_title": "User"})
    assert "from .user_service import UserService" in svc_view.read_text(encoding="utf-8")

    repo = tmp_path / "app" / "repository" / "__init__.py"
    apply_registration("import_list", repo, {"name_lower": "user", "name_title": "User"})
    assert "from .user_repository import UserRepository" in repo.read_text(encoding="utf-8")
    assert '__all__ = ["UserRepository"]' in repo.read_text(encoding="utf-8")

    routes = tmp_path / "app" / "routes" / "__init__.py"
    apply_registration("import_list", routes, {"name_lower": "user", "name_title": "User"})
    assert "from .view.user import user_bp" in routes.read_text(encoding="utf-8")

    routes_view = tmp_path / "app" / "routes" / "view" / "__init__.py"
    apply_registration("import_list", routes_view, {"name_lower": "user", "name_title": "User"})
    assert "from .user import user_bp" in routes_view.read_text(encoding="utf-8")


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
