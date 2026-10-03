"""Browser tests: the real frontend served by the real FastAPI app.

YouTube (IFrame API) is replaced by fake_youtube_api.js, and the endpoints
that call external services (/api/youtube/search, /api/lyrics/fetch,
/api/tts) are answered by `FakeApi` in the browser. Jyutping and manual
lyrics go through the real server.
"""

import json
import socket
import threading
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
import uvicorn

sync_api = pytest.importorskip("playwright.sync_api")

FAKE_YOUTUBE_API = (Path(__file__).parent / "fake_youtube_api.js").read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def live_server():
    from server import app

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]

    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", ws="none"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 15
    while not server.started:
        if time.time() > deadline or not thread.is_alive():
            raise RuntimeError("test server did not start")
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=5)


# Module scope: Playwright's sync API keeps an event loop running in this
# thread, which would break asyncio.run() in tests collected after this one.
@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except sync_api.Error as exc:
            pytest.skip(f"Chromium is not available: {exc}")
        yield browser
        browser.close()


class FakeApi:
    """Answers external-service endpoints inside the browser."""

    def __init__(self):
        self.search_response = {"results": []}
        self.lyrics_response = {"lines": []}
        self.hold_lyrics = False
        self.held = []           # held /api/lyrics/fetch routes, fulfil later
        self.requests = []       # (path, json body or query)

    def route(self, route):
        request = route.request
        url = request.url
        if "youtube.com/iframe_api" in url:
            return route.fulfill(body=FAKE_YOUTUBE_API, content_type="text/javascript")
        if "fonts.googleapis.com" in url or "fonts.gstatic.com" in url:
            return route.abort()
        if "/api/youtube/search" in url:
            self.requests.append(("search", parse_qs(urlparse(url).query)["q"][0]))
            return route.fulfill(json=self.search_response)
        if "/api/lyrics/fetch" in url:
            self.requests.append(("lyrics", json.loads(request.post_data)))
            if self.hold_lyrics:
                self.held.append(route)
                return None
            return route.fulfill(json=self.lyrics_response)
        if "/api/tts" in url:
            self.requests.append(("tts", json.loads(request.post_data)))
            return route.fulfill(json={"audio": None, "error": "no key in tests"})
        if url.startswith("http://127.0.0.1"):
            return route.continue_()
        return route.abort()

    def bodies(self, kind):
        return [body for k, body in self.requests if k == kind]


class App:
    def __init__(self, page, api):
        self.page = page
        self.api = api

    def search(self, query, results):
        self.api.search_response = results
        self.page.fill("#search-input", query)
        self.page.press("#search-input", "Enter")

    def open_song(self, lyrics, title="Beyond - 海闊天空", video_id="vid1"):
        self.api.lyrics_response = lyrics
        self.search("海闊天空", {"results": [
            {"videoId": video_id, "title": title, "thumbnail": "", "channelTitle": "Beyond"},
        ]})
        self.page.click(".result-card")
        self.page.wait_for_function("window.__ytPlayer !== undefined")

    def player(self, script):
        return self.page.evaluate(f"(() => {{ const p = window.__ytPlayer; return {script}; }})()")

    def lines(self):
        return self.page.locator(".lyric-line")

    def active_index(self):
        return self.page.evaluate(
            "[...document.querySelectorAll('.lyric-line')].findIndex(el => el.classList.contains('active'))"
        )


@pytest.fixture
def app(browser, live_server):
    context = browser.new_context(viewport={"width": 390, "height": 844})
    page = context.new_page()
    page.set_default_timeout(5000)
    api = FakeApi()
    page.route("**/*", api.route)
    errors = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.goto(live_server)
    yield App(page, api)
    context.close()
    assert errors == [], f"uncaught page errors: {errors}"
