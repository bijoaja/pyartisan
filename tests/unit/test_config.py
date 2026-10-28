import pyartisan.config as config


def test_config_roundtrip(isolated_config):
    data = config.load()
    assert data["theme"] == "default"
    assert "templates" in data
    assert data["templates"]["flask"] == "https://github.com/bijoaja/flaskiq.git"

    config.save({**data, "theme": "dark"})
    reloaded = config.load()
    assert reloaded["theme"] == "dark"
