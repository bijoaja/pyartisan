from pyartisan.cli import cli


def test_cli_plugin_install_blockchain_license(runner, in_tmp_cwd, plugin_project):
    result_premium = runner.invoke(
        cli, ["plugin", "install", "premium-plugin", "--license", "valid-12345"]
    )
    assert result_premium.exit_code == 0, result_premium.output
    assert "license ownership successfully verified" in result_premium.output.lower()

    result_invalid = runner.invoke(
        cli, ["plugin", "install", "premium-plugin", "--license", "invalid-key"]
    )
    assert "invalid license key" in result_invalid.output.lower()
