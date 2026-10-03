import re
import hashlib
import json
import logging
from pathlib import Path

import syncedlyrics

from lib import cache, config
from lib.jyutping import annotate

logger = logging.getLogger(__name__)

# [mm:ss.xx], [m:ss], [mm:ss.xxx], [mm:ss:xx]
_TIMESTAMP = re.compile(r"\[(\d{1,3}):(\d{1,2})(?:[.:](\d{1,3}))?\]")
# Word-level timestamps from enhanced LRC: <mm:ss.xx>
_WORD_TIMESTAMP = re.compile(r"<\d{1,3}:\d{1,2}(?:[.:]\d{1,3})?>")
# Whole-line tags such as [ar:Beyond] or [Chorus]
_TAG_LINE = re.compile(r"^\[[^\]]*\]$")


def _cache_key(title: str, artist: str) -> str:
    raw = f"{title.lower().strip()}|{artist.lower().strip()}"
    return hashlib.md5(raw.encode()).hexdigest()


def _cache_file(title: str, artist: str) -> Path:
    return config.DATA_DIR / "lyrics_cache" / f"{_cache_key(title, artist)}.json"


def _read_cache(title: str, artist: str) -> dict | None:
    path = _cache_file(title, artist)
    raw = cache.read_text(path)
    if raw is None:
        return None
    try:
        data = json.loads(raw)
    except ValueError:
        logger.warning("Ignoring corrupt lyrics cache %s", path)
        return None
    # Older versions cached empty results; treat those as misses.
    if not isinstance(data, dict) or not data.get("lines"):
        return None
    return data


def _search_term(title: str, artist: str) -> str:
    return " ".join(part.strip() for part in (title, artist) if part and part.strip())


def _search(term: str, allow_plain_format: bool = False) -> str | None:
    try:
        return syncedlyrics.search(term, allow_plain_format=allow_plain_format)
    except Exception:
        logger.exception("syncedlyrics search failed for %r", term)
        return None


def _parse_lrc(lrc_text: str) -> list[dict]:
    """Parse LRC format into list of {time, text} dicts, sorted by time.

    A line may carry several timestamps (a repeated chorus); it then yields
    one entry per timestamp.
    """
    lines = []
    for raw in lrc_text.splitlines():
        raw = raw.strip()
        times = []
        pos = 0
        while m := _TIMESTAMP.match(raw, pos):
            minutes, seconds, frac = m.groups()
            time_s = int(minutes) * 60 + int(seconds)
            if frac:
                time_s += int(frac) / 10 ** len(frac)
            times.append(round(time_s, 2))
            pos = m.end()
        if not times:
            continue
        text = " ".join(_WORD_TIMESTAMP.sub("", raw[pos:]).split())
        if text:
            lines.extend({"time": t, "text": text} for t in times)
    lines.sort(key=lambda line: line["time"])
    return lines


def _parse_plain(text: str) -> list[dict]:
    """Parse unsynced lyrics: one entry per non-empty line, no timestamps."""
    lines = []
    for raw in text.splitlines():
        line = " ".join(raw.split())
        if line and not _TAG_LINE.match(line):
            lines.append({"time": None, "text": line})
    return lines


def search_lyrics(title: str, artist: str) -> dict:
    """Check if synced lyrics are available."""
    cached = _read_cache(title, artist)
    if cached is not None:
        return {"found": True, "synced": cached.get("synced", False), "source": "cache"}

    term = _search_term(title, artist)
    if term:
        if _search(term):
            return {"found": True, "synced": True, "source": "syncedlyrics"}
        if _search(term, allow_plain_format=True):
            return {"found": True, "synced": False, "source": "syncedlyrics"}
    return {"found": False, "synced": False, "source": None}


def fetch_lyrics(title: str, artist: str) -> dict:
    """Fetch lyrics, parse LRC (or plain text), annotate with Jyutping."""
    cached = _read_cache(title, artist)
    if cached is not None:
        return cached

    term = _search_term(title, artist)
    lrc = None
    if term:
        lrc = _search(term) or _search(term, allow_plain_format=True)

    parsed = _parse_lrc(lrc) if lrc else []
    synced = bool(parsed)
    if lrc and not parsed:
        parsed = _parse_plain(lrc)

    lines = [
        {"time": entry["time"], "text": entry["text"], "chars": annotate(entry["text"])}
        for entry in parsed
    ]
    result = {
        "title": title,
        "artist": artist,
        "synced": synced,
        "lines": lines,
    }

    # Only cache hits: a miss may succeed later (providers change).
    if lines:
        cache.write_text(
            _cache_file(title, artist),
            json.dumps(result, ensure_ascii=False, indent=2),
        )
    return result


def parse_manual_lyrics(text: str) -> dict:
    """Parse manually pasted lyrics.

    Plain text gives unsynced lines; pasted LRC keeps its timestamps so
    karaoke sync and tap-to-seek still work.
    """
    parsed = _parse_lrc(text)
    synced = bool(parsed)
    if not parsed:
        parsed = [{"time": None, "text": line.strip()} for line in text.splitlines() if line.strip()]
    lines = [
        {"time": entry["time"], "text": entry["text"], "chars": annotate(entry["text"])}
        for entry in parsed
    ]
    return {
        "title": "Manual Lyrics",
        "artist": "",
        "synced": synced,
        "lines": lines,
    }
