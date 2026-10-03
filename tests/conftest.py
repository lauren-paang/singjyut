import httpx
import pytest
import syncedlyrics

from fake_lyrics import LyricsProvider
from lib import config


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    """Fresh cache dir and no API keys, whatever the developer's .env says."""
    monkeypatch.setattr(config, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(config, "YOUTUBE_API_KEY", "")
    monkeypatch.setattr(config, "GOOGLE_TTS_KEY", "")
    return config


@pytest.fixture(autouse=True)
def lyrics_provider(monkeypatch):
    """Tests never reach the real lyrics providers."""
    provider = LyricsProvider()
    monkeypatch.setattr(syncedlyrics, "search", provider)
    return provider


class HttpMock:
    """Routes httpx.AsyncClient traffic to `handler`; records requests."""

    def __init__(self):
        self.requests = []
        self.handler = lambda request: httpx.Response(500)

    def __call__(self, request):
        self.requests.append(request)
        return self.handler(request)


@pytest.fixture
def http_mock(monkeypatch):
    mock = HttpMock()
    real_client = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(mock)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", client_factory)
    return mock
