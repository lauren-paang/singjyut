import inspect
import json
import re

import httpx
import pytest
from fastapi.testclient import TestClient

import server
from lib import config

LRC = "[00:01.00]今天我\n[00:05.00]寒冷的站在"


@pytest.fixture
def client():
    return TestClient(server.app)


@pytest.fixture
def youtube_key(isolated_config, monkeypatch):
    monkeypatch.setattr(isolated_config, "YOUTUBE_API_KEY", "yt-key")


@pytest.fixture
def tts_key(isolated_config, monkeypatch):
    monkeypatch.setattr(isolated_config, "GOOGLE_TTS_KEY", "tts-key")


# ── Health & static ─────────────────────────────────────────────────────────


def test_health_reports_missing_keys(client):
    assert client.get("/api/health").json() == {"status": "ok", "youtube": False, "tts": False}


def test_health_reports_configured_keys(client, youtube_key, tts_key):
    assert client.get("/api/health").json() == {"status": "ok", "youtube": True, "tts": True}


def test_spa_fallback_serves_index(client):
    for path in ("/", "/song/abc"):
        resp = client.get(path)
        assert resp.status_code == 200
        assert "聲粵 SingJyut" in resp.text
        assert resp.headers["cache-control"] == "no-cache"


def test_head_request_on_root(client):
    resp = client.head("/")
    assert resp.status_code == 200
    assert resp.content == b""


def test_unknown_api_routes_are_404(client):
    assert client.get("/api/does-not-exist").status_code == 404
    assert client.get("/api").status_code == 404


def test_static_assets_revalidate(client):
    resp = client.get("/public/app.js")
    assert resp.status_code == 200
    assert resp.headers["cache-control"] == "no-cache"
    assert "etag" in resp.headers


def test_api_responses_are_not_marked_cacheable(client):
    assert "cache-control" not in client.get("/api/health").headers


def test_every_asset_referenced_by_index_exists(client):
    html = client.get("/").text
    paths = set(re.findall(r'(?:href|src)="(/public/[^"?]+)', html))
    assert {"/public/app.js", "/public/style.css", "/public/manifest.json"} <= paths
    for path in paths:
        assert client.get(path).status_code == 200, path


def test_manifest_icons_exist(client):
    manifest = client.get("/public/manifest.json").json()
    assert manifest["icons"]
    for icon in manifest["icons"]:
        resp = client.get(icon["src"])
        assert resp.status_code == 200, icon["src"]
        assert resp.headers["content-type"] == icon["type"]


# ── YouTube search ──────────────────────────────────────────────────────────


def test_youtube_search_without_key(client, http_mock):
    assert client.get("/api/youtube/search?q=beyond").json() == {
        "results": [], "error": "YouTube API key not configured",
    }
    assert http_mock.requests == []


def test_youtube_search_requires_query(client):
    assert client.get("/api/youtube/search").status_code == 422
    assert client.get("/api/youtube/search?q=").status_code == 422
    assert client.get("/api/youtube/search?q=" + "x" * 201).status_code == 422


def test_youtube_search_maps_results(client, youtube_key, http_mock):
    http_mock.handler = lambda request: httpx.Response(200, json={"items": [
        {
            "id": {"videoId": "abc123"},
            "snippet": {
                "title": "Beyond - Don&#39;t Cry &amp; 海闊天空",
                "channelTitle": "Rock &amp; Roll",
                "thumbnails": {"medium": {"url": "https://i.ytimg.com/m.jpg"}},
            },
        },
        {"id": {"channelId": "not-a-video"}, "snippet": {"title": "channel"}},
        {"id": {"videoId": "def456"}, "snippet": {"title": "No medium thumb",
                                                    "thumbnails": {"default": {"url": "d.jpg"}}}},
    ]})

    data = client.get("/api/youtube/search", params={"q": "海闊天空"}).json()

    assert data == {"results": [
        {"videoId": "abc123", "title": "Beyond - Don't Cry & 海闊天空",
         "thumbnail": "https://i.ytimg.com/m.jpg", "channelTitle": "Rock & Roll"},
        {"videoId": "def456", "title": "No medium thumb", "thumbnail": "d.jpg", "channelTitle": ""},
    ]}
    params = http_mock.requests[0].url.params
    assert params["q"] == "海闊天空"
    assert params["videoCategoryId"] == "10"
    assert params["type"] == "video"
    assert params["key"] == "yt-key"


def test_youtube_search_api_error(client, youtube_key, http_mock):
    http_mock.handler = lambda request: httpx.Response(403, json={"error": {}})
    assert client.get("/api/youtube/search?q=x").json() == {
        "results": [], "error": "YouTube API error: 403",
    }


def test_youtube_search_network_error(client, youtube_key, http_mock):
    def fail(request):
        raise httpx.ReadTimeout("slow", request=request)

    http_mock.handler = fail
    data = client.get("/api/youtube/search?q=x").json()
    assert data["results"] == []
    assert "unreachable" in data["error"]


# ── Lyrics & Jyutping ───────────────────────────────────────────────────────


def test_lyrics_fetch(client, lyrics_provider):
    lyrics_provider.synced = LRC
    data = client.post("/api/lyrics/fetch", json={"title": "海闊天空", "artist": "Beyond"}).json()
    assert data["synced"] is True
    assert [line["text"] for line in data["lines"]] == ["今天我", "寒冷的站在"]


def test_lyrics_fetch_artist_is_optional(client, lyrics_provider):
    client.post("/api/lyrics/fetch", json={"title": "海闊天空"})
    assert lyrics_provider.calls[0] == "海闊天空"


def test_lyrics_search(client, lyrics_provider):
    lyrics_provider.synced = LRC
    assert client.post("/api/lyrics/search", json={"title": "海闊天空"}).json()["found"] is True


def test_lyrics_requests_are_validated(client):
    assert client.post("/api/lyrics/fetch", json={}).status_code == 422
    assert client.post("/api/lyrics/fetch", json={"title": "x" * 301}).status_code == 422


def test_blocking_lyrics_routes_run_in_threadpool():
    # syncedlyrics does blocking network I/O; as `async def` these routes would
    # freeze the event loop (and every other request) while searching.
    for route in (server.lyrics_fetch, server.lyrics_search, server.lyrics_manual):
        assert not inspect.iscoroutinefunction(route)


def test_jyutping(client):
    assert client.post("/api/jyutping", json={"text": "你好"}).json() == {"chars": [
        {"char": "你", "jyutping": "nei5"},
        {"char": "好", "jyutping": "hou2"},
    ]}


def test_manual_lyrics(client):
    data = client.post("/api/lyrics/manual", json={"text": "今天我\n寒冷的站在"}).json()
    assert data["title"] == "Manual Lyrics"
    assert [line["text"] for line in data["lines"]] == ["今天我", "寒冷的站在"]


# ── TTS ─────────────────────────────────────────────────────────────────────


def test_tts_without_key(client, http_mock):
    assert client.post("/api/tts", json={"text": "你"}).json() == {
        "audio": None, "error": "TTS unavailable — check GOOGLE_TTS_KEY",
    }
    assert http_mock.requests == []


def test_tts_success(client, tts_key, http_mock):
    http_mock.handler = lambda request: httpx.Response(200, json={"audioContent": "QUJD"})
    assert client.post("/api/tts", json={"text": "你"}).json() == {"audio": "QUJD"}
    assert json.loads(http_mock.requests[0].content)["voice"]["name"] == "yue-HK-Standard-A"


def test_tts_upstream_failure(client, tts_key, http_mock):
    http_mock.handler = lambda request: httpx.Response(500)
    data = client.post("/api/tts", json={"text": "你"}).json()
    assert data["audio"] is None
    assert data["error"] == "TTS request failed, please try again"


@pytest.mark.parametrize("body", [
    {"text": ""},
    {"text": "你" * 201},
    {"text": "你", "voice": "en-US-Standard-A"},
    {"text": "你", "voice": "yue-HK-A\"; DROP"},
])
def test_tts_rejects_invalid_requests(client, tts_key, http_mock, body):
    assert client.post("/api/tts", json=body).status_code == 422
    assert http_mock.requests == []
