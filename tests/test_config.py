from lib import config


def test_placeholder_keys_count_as_unset(monkeypatch):
    monkeypatch.setenv("SOME_KEY", "your_google_tts_api_key_here")
    assert config._secret("SOME_KEY") == ""


def test_real_keys_are_stripped(monkeypatch):
    monkeypatch.setenv("SOME_KEY", "  AIza-real-key \n")
    assert config._secret("SOME_KEY") == "AIza-real-key"


def test_missing_key_is_empty(monkeypatch):
    monkeypatch.delenv("SOME_KEY", raising=False)
    assert config._secret("SOME_KEY") == ""


def test_paths_do_not_depend_on_working_directory():
    assert config.PUBLIC_DIR.is_absolute()
    assert (config.PUBLIC_DIR / "index.html").is_file()
