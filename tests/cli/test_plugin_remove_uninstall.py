import yaml

from pyartisan.cli import cli


def test_cli_plugin_remove_multi_and_all(runner, in_tmp_cwd, plugin_project):
    pyartisan_dir, _home_dir = plugin_project

    project_yaml_content = yaml.safe_load(
        (pyartisan_dir / "project.yaml").read_text(encoding="utf-8")
    )
    project_yaml_content["plugins"] = [
        "payment-midtrans@1.0.0",
        "auth-jwt@2.0.0",
        "docker-tools@1.2.1",
    ]
    with open(pyartisan_dir / "project.yaml", "w", encoding="utf-8") as f:
        yaml.dump(project_yaml_content, f)

    # Test list
    result = runner.invoke(cli, ["plugin", "list"])
    assert result.exit_code == 0, result.output
    assert "payment-midtrans@1.0.0" in result.output
    assert "auth-jwt@2.0.0" in result.output
    assert "docker-tools@1.2.1" in result.output

    # Test remove satu plugin dari project
    result = runner.invoke(cli, ["plugin", "remove", "payment-midtrans"])
    assert result.exit_code == 0, result.output
    assert "removed payment-midtrans@1.0.0" in result.output.lower()

    updated_config = yaml.safe_load((pyartisan_dir / "project.yaml").read_text(encoding="utf-8"))
    assert "payment-midtrans@1.0.0" not in updated_config["plugins"]
    assert "auth-jwt@2.0.0" in updated_config["plugins"]

    # Test remove banyak plugin sekaligus
    result = runner.invoke(cli, ["plugin", "remove", "auth-jwt", "docker-tools"])
    assert result.exit_code == 0, result.output
    updated_config2 = yaml.safe_load((pyartisan_dir / "project.yaml").read_text(encoding="utf-8"))
    assert updated_config2["plugins"] == []

    # Re-populate untuk test --all
    project_yaml_content["plugins"] = ["payment-midtrans@1.0.0", "auth-jwt@2.0.0"]
    with open(pyartisan_dir / "project.yaml", "w", encoding="utf-8") as f:
        yaml.dump(project_yaml_content, f)

    result = runner.invoke(cli, ["plugin", "remove", "--all"])
    assert result.exit_code == 0, result.output
    updated_config3 = yaml.safe_load((pyartisan_dir / "project.yaml").read_text(encoding="utf-8"))
    assert updated_config3["plugins"] == []
