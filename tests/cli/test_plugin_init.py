import yaml

from pyartisan.cli import cli
from pyartisan.cli.commands.plugin import _is_link


def test_cli_plugin_init_all_frameworks(runner, in_tmp_cwd, fake_home):
    """`pyartisan plugin init <name>` scaffolds skeleton + registers dev symlink."""
    root = in_tmp_cwd
    home_dir = fake_home

    result = runner.invoke(cli, ["plugin", "init", "crud-blogs"], input="all\n")
    assert result.exit_code == 0, result.output
    assert "plugin skeleton created" in result.output.lower()

    plugin_dir = root / "crud-blogs"
    assert (plugin_dir / "manifest.yaml").exists()
    assert (plugin_dir / "hooks.py").exists()
    assert (plugin_dir / "README.md").exists()
    assert (plugin_dir / "LICENSE").exists()
    assert (plugin_dir / "stubs" / "fastapi" / ".gitkeep").exists()
    assert (plugin_dir / "stubs" / "flask" / ".gitkeep").exists()
    assert (plugin_dir / "stubs" / "django" / ".gitkeep").exists()

    manifest = yaml.safe_load((plugin_dir / "manifest.yaml").read_text(encoding="utf-8"))
    assert manifest["id"] == "crud-blogs"
    assert manifest["name"] == "CrudBlogs Plugin"
    assert manifest["version"] == "1.0.0"

    registry_link = home_dir / ".pyartisan" / "plugins" / "crud-blogs" / "dev"
    assert _is_link(registry_link)
    assert registry_link.resolve() == plugin_dir.resolve()


def test_cli_plugin_init_single_framework(runner, in_tmp_cwd, fake_home):
    """Only the chosen framework's stub folder is created."""
    root = in_tmp_cwd

    result = runner.invoke(cli, ["plugin", "init", "demo-plugin"], input="fastapi\n")
    assert result.exit_code == 0, result.output

    plugin_dir = root / "demo-plugin"
    assert (plugin_dir / "stubs" / "fastapi" / ".gitkeep").exists()
    assert not (plugin_dir / "stubs" / "flask").exists()
    assert not (plugin_dir / "stubs" / "django").exists()


def test_cli_plugin_init_existing_directory(runner, in_tmp_cwd, fake_home):
    """Command refuses to overwrite an existing directory."""
    root = in_tmp_cwd
    (root / "demo-plugin").mkdir()
    (root / "demo-plugin" / "keep-me.txt").write_text("do not touch", encoding="utf-8")

    result = runner.invoke(cli, ["plugin", "init", "demo-plugin"], input="all\n")
    assert result.exit_code == 1, result.output
    assert "already exists" in result.output.lower()

    assert not (root / "demo-plugin" / "manifest.yaml").exists()
    assert (root / "demo-plugin" / "keep-me.txt").exists()


def test_init_rejects_traversal_name(runner, in_tmp_cwd, fake_home):
    result = runner.invoke(cli, ["plugin", "init", "../evil"], input="all\n")
    assert result.exit_code != 0, result.output
    assert not (in_tmp_cwd.parent / "evil").exists()
    assert not (fake_home / ".pyartisan" / "evil").exists()
