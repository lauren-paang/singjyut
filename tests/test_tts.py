import asyncio
import json

import httpx

from lib import tts


def synthesize(*args):
    return asyncio.run(tts.synthesize(*args))


def test_returns_none_without_key(http_mock):
    assert synthesize("你好") is None
    assert http_mock.requests == []


def test_success_returns_audio_and_sends_voice(http_mock, isolated_config, monkeypatch):
    monkeypatch.setattr(isolated_config, "GOOGLE_TTS_KEY", "test-key")
    http_mock.handler = lambda request: httpx.Response(200, json={"audioContent": "QUJD"})

    assert synthesize("你好", "yue-HK-Standard-B") == "QUJD"

    (request,) = http_mock.requests
    assert request.url.params["key"] == "test-key"
    body = json.loads(request.content)
    assert body["input"] == {"text": "你好"}
    assert body["voice"] == {"languageCode": "yue-HK", "name": "yue-HK-Standard-B"}
    assert body["audioConfig"]["audioEncoding"] == "MP3"


def test_audio_is_cached_per_text_and_voice(http_mock, isolated_config, monkeypatch):
    monkeypatch.setattr(isolated_config, "GOOGLE_TTS_KEY", "test-key")
    http_mock.handler = lambda request: httpx.Response(200, json={"audioContent": "QUJD"})

    assert synthesize("你好") == "QUJD"
    assert synthesize("你好") == "QUJD"
    assert len(http_mock.requests) == 1

    synthesize("你好", "yue-HK-Standard-B")
    synthesize("我")
    assert len(http_mock.requests) == 3


def test_api_errors_return_none_and_are_not_cached(http_mock, isolated_config, monkeypatch):
    monkeypatch.setattr(isolated_config, "GOOGLE_TTS_KEY", "test-key")
    http_mock.handler = lambda request: httpx.Response(403, json={"error": "API disabled"})

    assert synthesize("你好") is None
    assert synthesize("你好") is None
    assert len(http_mock.requests) == 2


def test_network_errors_return_none(http_mock, isolated_config, monkeypatch):
    monkeypatch.setattr(isolated_config, "GOOGLE_TTS_KEY", "test-key")

    def fail(request):
        raise httpx.ConnectError("offline", request=request)

    http_mock.handler = fail
    assert synthesize("你好") is None
