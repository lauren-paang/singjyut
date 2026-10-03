import httpx
import pytest
import syncedlyrics

from lib import config


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    """Fresh cache dir and no API keys, whatever the developer's .env says."""
    monkeypatch.setattr(config, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(config, "YOUTUBE_API_KEY", "")
    monkeypatch.setattr(config, "GOOGLE_TTS_KEY", "")
    return config


class LyricsProvider:
    """Stand-in for syncedlyrics.search; records every call."""

    def __init__(self):
        self.calls = []
        self.synced = None   # returned for synced-only searches
        self.plain = None    # returned when allow_plain_format=True
        self.error = None

    def __call__(self, term, allow_plain_format=False, **kwargs):
        self.calls.append((term, allow_plain_format))
        if self.error:
            raise self.error
        if allow_plain_format:
            return self.synced or self.plain
        return self.synced


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
