import inspect
import json

import pytest

from fake_lyrics import REAL_SEARCH, LyricsProvider
from lib import lyrics

LRC = """[ar:Beyond]
[ti:海闊天空]
[00:32.50]今天我
[00:37.20]寒冷的站在
"""


# ── LRC parsing ─────────────────────────────────────────────────────────────


def test_parse_lrc_basic():
    assert lyrics._parse_lrc(LRC) == [
        {"time": 32.5, "text": "今天我"},
        {"time": 37.2, "text": "寒冷的站在"},
    ]


@pytest.mark.parametrize(
    "line, expected_time",
    [
        ("[01:02.34]x", 62.34),
        ("[01:02.346]x", 62.35),  # milliseconds, rounded to 2 dp
        ("[01:02.5]x", 62.5),     # tenths
        ("[1:02.50]x", 62.5),     # single-digit minutes
        ("[01:02]x", 62.0),       # no fraction
        ("[01:02:50]x", 62.5),    # colon-separated fraction
        ("[100:00.00]x", 6000.0),
    ],
)
def test_parse_lrc_timestamp_formats(line, expected_time):
    assert lyrics._parse_lrc(line) == [{"time": expected_time, "text": "x"}]


def test_parse_lrc_repeated_lines_are_expanded_and_sorted():
    lrc = "[00:10.00]主歌\n[00:20.00][01:30.00]副歌\n[00:40.00]尾聲"
    assert lyrics._parse_lrc(lrc) == [
        {"time": 10.0, "text": "主歌"},
        {"time": 20.0, "text": "副歌"},
        {"time": 40.0, "text": "尾聲"},
        {"time": 90.0, "text": "副歌"},
    ]


def test_parse_lrc_strips_word_timestamps_and_normalises_spaces():
    lrc = "[00:10.12]<00:10.12>hello  <00:11.00>world  "
    assert lyrics._parse_lrc(lrc) == [{"time": 10.12, "text": "hello world"}]


def test_parse_lrc_skips_metadata_and_empty_lines():
    assert lyrics._parse_lrc("[ar:Beyond]\n[00:01.00]\n\n[offset:+100]\nplain") == []


def test_parse_plain_skips_section_tags():
    text = "[Verse 1]\n今天我\n\n  寒冷的   站在 \n[Chorus]"
    assert lyrics._parse_plain(text) == [
        {"time": None, "text": "今天我"},
        {"time": None, "text": "寒冷的 站在"},
    ]


def test_lyrics_provider_matches_syncedlyrics():
    # syncedlyrics 1.0 renamed search() arguments; keep the fake honest.
    real = inspect.signature(REAL_SEARCH)
    fake = inspect.signature(LyricsProvider.__call__)
    assert list(fake.parameters)[1:] == list(real.parameters)


# ── fetch_lyrics ────────────────────────────────────────────────────────────


def test_fetch_synced_lyrics_annotates_and_caches(lyrics_provider, isolated_config):
    lyrics_provider.synced = LRC

    result = lyrics.fetch_lyrics("海闊天空", "Beyond")

    assert result["synced"] is True
    assert result["title"] == "海闊天空" and result["artist"] == "Beyond"
    assert [line["time"] for line in result["lines"]] == [32.5, 37.2]
    assert result["lines"][0]["chars"][0] == {"char": "今", "jyutping": "gam1"}
    assert lyrics_provider.calls == ["海闊天空 Beyond"]

    cache_files = list((isolated_config.DATA_DIR / "lyrics_cache").glob("*.json"))
    assert len(cache_files) == 1
    assert json.loads(cache_files[0].read_text(encoding="utf-8")) == result

    # Second call is served from the cache
    assert lyrics.fetch_lyrics("海闊天空", "Beyond") == result
    assert len(lyrics_provider.calls) == 1


def test_fetch_falls_back_to_plain_lyrics(lyrics_provider):
    lyrics_provider.plain = "今天我\n寒冷的站在\n"

    result = lyrics.fetch_lyrics("海闊天空", "")

    assert result["synced"] is False
    assert [(line["time"], line["text"]) for line in result["lines"]] == [
        (None, "今天我"),
        (None, "寒冷的站在"),
    ]
    assert lyrics_provider.calls == ["海闊天空"]  # one search covers synced and plain


def test_misses_are_not_cached(lyrics_provider, isolated_config):
    result = lyrics.fetch_lyrics("Unknown", "Nobody")

    assert result == {"title": "Unknown", "artist": "Nobody", "synced": False, "lines": []}
    assert not (isolated_config.DATA_DIR / "lyrics_cache").exists()

    # A later request searches again, and can succeed
    lyrics_provider.synced = LRC
    assert lyrics.fetch_lyrics("Unknown", "Nobody")["lines"]


def test_provider_errors_are_treated_as_misses(lyrics_provider):
    lyrics_provider.error = RuntimeError("provider down")
    assert lyrics.fetch_lyrics("海闊天空", "Beyond")["lines"] == []


def test_blank_title_does_not_search(lyrics_provider):
    assert lyrics.fetch_lyrics("  ", "")["lines"] == []
    assert lyrics_provider.calls == []


def test_legacy_empty_cache_entries_are_ignored(lyrics_provider, isolated_config):
    cache_file = lyrics._cache_file("海闊天空", "Beyond")
    cache_file.parent.mkdir(parents=True)
    cache_file.write_text(json.dumps({"title": "海闊天空", "lines": []}), encoding="utf-8")
    lyrics_provider.synced = LRC

    assert len(lyrics.fetch_lyrics("海闊天空", "Beyond")["lines"]) == 2


def test_corrupt_cache_entries_are_ignored(lyrics_provider):
    cache_file = lyrics._cache_file("海闊天空", "Beyond")
    cache_file.parent.mkdir(parents=True)
    cache_file.write_text("{not json", encoding="utf-8")
    lyrics_provider.synced = LRC

    assert len(lyrics.fetch_lyrics("海闊天空", "Beyond")["lines"]) == 2


def test_unwritable_cache_does_not_fail_the_request(lyrics_provider, isolated_config):
    isolated_config.DATA_DIR.parent.mkdir(parents=True, exist_ok=True)
    isolated_config.DATA_DIR.write_text("not a directory")
    lyrics_provider.synced = LRC

    assert len(lyrics.fetch_lyrics("海闊天空", "Beyond")["lines"]) == 2


def test_cache_key_ignores_case_and_padding():
    assert lyrics._cache_file(" Hello ", "BEYOND") == lyrics._cache_file("hello", "beyond")


# ── search_lyrics ───────────────────────────────────────────────────────────


def test_search_reports_synced(lyrics_provider):
    lyrics_provider.synced = LRC
    assert lyrics.search_lyrics("海闊天空", "Beyond") == {
        "found": True, "synced": True, "source": "syncedlyrics",
    }


def test_search_reports_plain(lyrics_provider):
    lyrics_provider.plain = "今天我"
    assert lyrics.search_lyrics("海闊天空", "Beyond") == {
        "found": True, "synced": False, "source": "syncedlyrics",
    }


def test_search_reports_not_found():
    assert lyrics.search_lyrics("海闊天空", "Beyond") == {
        "found": False, "synced": False, "source": None,
    }


def test_search_uses_cached_synced_flag(lyrics_provider):
    lyrics_provider.plain = "今天我"
    lyrics.fetch_lyrics("海闊天空", "Beyond")
    calls = len(lyrics_provider.calls)

    assert lyrics.search_lyrics("海闊天空", "Beyond") == {
        "found": True, "synced": False, "source": "cache",
    }
    assert len(lyrics_provider.calls) == calls


# ── parse_manual_lyrics ─────────────────────────────────────────────────────


def test_manual_plain_text():
    result = lyrics.parse_manual_lyrics("今天我\n\n  寒冷的站在  \n")
    assert result["synced"] is False
    assert [(line["time"], line["text"]) for line in result["lines"]] == [
        (None, "今天我"),
        (None, "寒冷的站在"),
    ]
    assert result["lines"][0]["chars"][2] == {"char": "我", "jyutping": "ngo5"}


def test_manual_lrc_keeps_timestamps():
    result = lyrics.parse_manual_lyrics(LRC)
    assert result["synced"] is True
    assert [(line["time"], line["text"]) for line in result["lines"]] == [
        (32.5, "今天我"),
        (37.2, "寒冷的站在"),
    ]
