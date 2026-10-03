import pytest

pytestmark = pytest.mark.e2e


def lyrics_payload(texts, start=10, step=10, synced=True):
    """Build a /api/lyrics/fetch response; each char gets a dummy reading."""
    return {
        "title": "t",
        "artist": "a",
        "synced": synced,
        "lines": [
            {
                "time": start + i * step if synced else None,
                "text": text,
                "chars": [
                    {"char": c, "jyutping": None if c in " ，" else f"jp{i}"} for c in text
                ],
            }
            for i, text in enumerate(texts)
        ],
    }


LYRICS = lyrics_payload(["今天我", "寒冷的站在", "遠方"])  # lines at 10s, 20s, 30s


# ── Search view ─────────────────────────────────────────────────────────────


def test_featured_songs_start_a_search(app):
    assert app.page.locator(".featured-card").count() == 8
    app.page.click(".featured-card >> nth=0")
    app.page.wait_for_selector(".search-message")
    assert app.page.input_value("#search-input") == "海闊天空 Beyond"
    assert app.api.bodies("search") == ["海闊天空 Beyond"]


def test_featured_songs_survive_an_empty_search(app):
    app.search("zzz", {"results": []})
    app.page.wait_for_selector("text=No results found")
    app.page.click("#logo")
    assert app.page.locator("#featured-grid .featured-card").count() == 8
    assert app.page.locator("#hero").is_visible()


def test_search_errors_are_shown(app):
    app.search("beyond", {"results": [], "error": "YouTube API key not configured"})
    app.page.wait_for_selector("text=YouTube API key not configured")


def test_result_titles_are_rendered_as_text(app):
    title = "Beyond - Don't Cry <b>bold</b> & \"quotes\""
    app.search("beyond", {"results": [
        {"videoId": "v", "title": title, "thumbnail": 'x" onerror="window.__xss=1', "channelTitle": "A&B"},
    ]})
    card = app.page.wait_for_selector(".result-card")
    assert card.query_selector("h3").inner_text() == title
    assert card.query_selector("p").inner_text() == "A&B"
    assert card.query_selector("b") is None
    assert app.page.evaluate("window.__xss") is None


# ── Song view ───────────────────────────────────────────────────────────────


def test_lyrics_render_with_jyutping(app):
    app.open_song(LYRICS)
    app.page.wait_for_selector(".lyric-line")
    assert app.lines().count() == 3
    first = app.lines().nth(0)
    assert first.locator(".hanzi").all_inner_texts() == ["今", "天", "我"]
    assert first.locator(".jyutping").all_inner_texts() == ["jp0", "jp0", "jp0"]
    assert app.page.is_visible("#playback-bar")


def test_lyrics_search_uses_cleaned_title_then_fallbacks(app):
    app.open_song({"lines": []}, title="陳奕迅 Eason Chan《富士山下》[Official MV]")
    app.page.wait_for_selector("#manual-lyrics-section:not(.hidden)")
    assert app.api.bodies("lyrics") == [
        {"title": "富士山下", "artist": "陳奕迅 Eason Chan"},
        {"title": "海闊天空", "artist": ""},
        {"title": "陳奕迅 Eason Chan《富士山下》[Official MV]", "artist": ""},
    ]


def test_duplicate_lyrics_attempts_are_skipped(app):
    app.open_song({"lines": []}, title="海闊天空")
    app.page.wait_for_selector("#manual-lyrics-section:not(.hidden)")
    assert app.api.bodies("lyrics") == [
        {"title": "海闊天空", "artist": "Beyond"},
        {"title": "海闊天空", "artist": ""},
    ]


def test_mixed_language_lines_keep_word_spacing(app, live_server):
    # Real server annotation: Latin words stay whole, spaces become gaps.
    app.open_song({"lines": []})
    app.page.wait_for_selector("#manual-lyrics-section:not(.hidden)")
    app.page.fill("#manual-lyrics-input", "Oh baby 你")
    app.page.click("#manual-lyrics-section button")
    line = app.page.wait_for_selector(".lyric-line")
    assert [el.inner_text() for el in line.query_selector_all(".hanzi")] == ["Oh", "baby", "你"]
    assert len(line.query_selector_all(".char-block.space")) == 2
    assert line.query_selector(".jyutping").inner_text() == "nei5"


def test_karaoke_highlight_follows_playback_and_survives_pause(app):
    app.open_song(LYRICS)
    app.page.wait_for_selector(".lyric-line")

    app.player("(p.time = 21, p.playVideo())")
    app.page.wait_for_function("document.querySelectorAll('.lyric-line.active').length === 1")
    assert app.active_index() == 1
    assert app.page.get_attribute("#pb-play", "aria-label") == "Pause"

    app.player("(p.time = 31, null)")
    app.page.wait_for_function("document.querySelector('.lyric-line.active')?.dataset.index === '2'")

    app.player("p.pauseVideo()")
    assert app.page.get_attribute("#pb-play", "aria-label") == "Play"
    app.page.wait_for_timeout(300)
    assert app.active_index() == 2


def test_tap_line_seeks_video(app):
    app.open_song(LYRICS)
    app.lines().nth(2).click()
    assert app.player("p.time") == 30
    assert app.player("p.state") == 1


def test_next_and_prev_use_playback_position_while_paused(app):
    app.open_song(LYRICS)
    app.page.wait_for_selector(".lyric-line")
    app.player("(p.time = 21, p.playVideo())")
    app.player("p.pauseVideo()")

    app.page.click("#pb-next")
    assert app.player("p.time") == 30

    app.player("(p.time = 21, p.pauseVideo())")
    app.page.click("#pb-prev")
    assert app.player("p.time") == 10

    # Right after a seek the player may report slightly less than the target
    app.player("(p.time = 19.9, p.pauseVideo())")
    app.page.click("#pb-next")
    assert app.player("p.time") == 30


def test_progress_bar_seeks(app):
    app.open_song(LYRICS)
    box = app.page.locator("#progress-bar").bounding_box()
    # Click just above the 3px bar: the enlarged tap target still counts.
    app.page.mouse.click(box["x"] + box["width"] / 2, box["y"] - 6)
    assert app.player("p.time") == pytest.approx(100, abs=1)


def test_back_stops_the_video(app):
    app.open_song(LYRICS)
    app.player("p.playVideo()")
    app.page.click("#back-btn")
    assert app.player("p.state") == 2  # paused
    assert app.page.is_hidden("#playback-bar")
    assert app.page.is_visible("#search-view")


def test_play_before_lyrics_load_still_syncs(app):
    app.api.hold_lyrics = True
    app.open_song(LYRICS)
    app.player("(p.time = 21, p.playVideo())")
    assert app.page.get_attribute("#pb-play", "aria-label") == "Pause"

    app.api.held.pop().fulfill(json=LYRICS)
    app.page.wait_for_function("document.querySelector('.lyric-line.active')?.dataset.index === '1'")


def test_stale_lyrics_from_previous_song_are_dropped(app):
    app.api.hold_lyrics = True
    app.open_song(LYRICS, title="Song A", video_id="a")
    app.page.wait_for_function("window.__ytPlayer.videoId === 'a'")
    stale_route = app.api.held.pop()

    app.page.click("#back-btn")
    app.api.hold_lyrics = False
    app.open_song(lyrics_payload(["新歌"]), title="Song B", video_id="b")
    app.page.wait_for_selector(".lyric-line")

    stale_route.fulfill(json=LYRICS)
    app.page.wait_for_timeout(300)
    assert app.lines().count() == 1
    assert app.page.inner_text("#song-title") == "Song B"
    assert app.player("p.videoId") == "b"


def test_manual_lrc_keeps_timestamps(app):
    app.open_song({"lines": []})
    app.page.wait_for_selector("#manual-lyrics-section:not(.hidden)")
    app.page.fill("#manual-lyrics-input", "[00:05.00]今天我\n[00:12.50]寒冷")
    app.page.click("#manual-lyrics-section button")
    app.page.wait_for_selector(".lyric-line")
    app.lines().nth(1).click()
    assert app.player("p.time") == 12.5


def test_tapping_a_character_requests_tts(app):
    app.open_song(LYRICS)
    app.lines().nth(0).locator(".char-block").nth(1).click()
    app.lines().nth(1).locator(".line-speaker").click()
    app.page.wait_for_timeout(200)
    assert app.api.bodies("tts") == [{"text": "天"}, {"text": "寒冷的站在"}]
    assert app.player("p.time") == 0  # tapping a character must not seek


def test_unembeddable_video_shows_a_message(app):
    app.open_song(LYRICS)
    app.player("p.events.onError({ data: 150 })")
    assert "can't be played outside YouTube" in app.page.inner_text("#player-error")

    # Opening another song clears it
    app.page.click("#back-btn")
    app.open_song(LYRICS)
    assert app.page.is_hidden("#player-error")


def test_mini_player_pins_while_scrolling_lyrics(app):
    app.open_song(lyrics_payload([f"第{i}句歌詞" for i in range(40)]))
    app.page.wait_for_selector(".lyric-line")
    container = app.page.locator("#player-container")
    is_mini = "document.getElementById('player-container').classList.contains('mini')"
    assert not app.page.evaluate(is_mini)
    section_height = app.page.locator("#player-section").bounding_box()["height"]

    app.page.mouse.wheel(0, 900)
    app.page.wait_for_function(is_mini)
    box = container.bounding_box()
    assert box["y"] >= app.page.locator("#header").bounding_box()["height"]  # below the header
    assert box["x"] + box["width"] <= 390 and box["x"] > 390 / 2               # top-right corner
    # The page keeps the video's space, so lyrics don't jump
    assert app.page.locator("#player-section").bounding_box()["height"] == section_height

    app.page.mouse.wheel(0, -5000)
    app.page.wait_for_function(f"!{is_mini}")

    app.page.mouse.wheel(0, 900)
    app.page.wait_for_function(is_mini)
    app.page.click("#logo")
    assert not app.page.evaluate(is_mini)


@pytest.mark.parametrize("title, expected", [
    ("Beyond - 海闊天空", {"artist": "Beyond", "title": "海闊天空"}),
    ("Beyond - 海闊天空 (Official MV)", {"artist": "Beyond", "title": "海闊天空"}),
    ("周柏豪 Pakho Chau - 夠鐘 [Official Music Video]", {"artist": "周柏豪 Pakho Chau", "title": "夠鐘"}),
    ("陳奕迅 Eason Chan《富士山下》[Official MV]", {"artist": "陳奕迅 Eason Chan", "title": "富士山下"}),
    ("李克勤 Hacken Lee 「紅日」 官方MV", {"artist": "李克勤 Hacken Lee", "title": "紅日"}),
    ("海闊天空", {"artist": "", "title": "海闊天空"}),
    ("【歌詞】Beyond - 喜歡你", {"artist": "Beyond", "title": "喜歡你"}),
])
def test_extract_song_info(app, title, expected):
    assert app.page.evaluate("extractSongInfo", title) == expected


def test_desktop_playback_bar_matches_content_width(browser, live_server):
    context = browser.new_context(viewport={"width": 900, "height": 800})
    page = context.new_page()
    page.goto(live_server)
    page.evaluate("document.getElementById('playback-bar').classList.remove('hidden')")
    bar = page.locator("#playback-bar").bounding_box()
    assert bar["width"] == 600
    assert bar["x"] == pytest.approx((900 - 600) / 2, abs=1)
    context.close()


def test_no_page_errors_on_load(app):
    # The `app` fixture fails the test on any uncaught page error.
    assert app.page.evaluate("typeof YTPlayer") == "object"
