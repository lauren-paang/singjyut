import re
import hashlib
import json
from pathlib import Path

import syncedlyrics

from lib.jyutping import annotate

CACHE_DIR = Path("data/lyrics_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _cache_key(title: str, artist: str) -> str:
    raw = f"{title.lower().strip()}|{artist.lower().strip()}"
    return hashlib.md5(raw.encode()).hexdigest()


def _parse_lrc(lrc_text: str) -> list[dict]:
    """Parse LRC format into list of {time, text} dicts."""
    lines = []
    pattern = re.compile(r"\[(\d{2}):(\d{2})\.(\d{2,3})\](.*)")
    for line in lrc_text.strip().splitlines():
        m = pattern.match(line.strip())
        if not m:
            continue
        minutes, seconds, centis, text = m.groups()
        # Handle both 2-digit and 3-digit centiseconds
        if len(centis) == 3:
            frac = int(centis) / 1000
        else:
            frac = int(centis) / 100
        time_s = int(minutes) * 60 + int(seconds) + frac
        text = text.strip()
        if text:
            lines.append({"time": round(time_s, 2), "text": text})
    return lines


def search_lyrics(title: str, artist: str) -> dict:
    """Check if synced lyrics are available."""
    cache_file = CACHE_DIR / f"{_cache_key(title, artist)}.json"
    if cache_file.exists():
        return {"found": True, "synced": True, "source": "cache"}

    try:
        lrc = syncedlyrics.search(f"{title} {artist}")
        if lrc:
            return {"found": True, "synced": True, "source": "syncedlyrics"}
        # Try unsynced (plain format)
        lrc = syncedlyrics.search(f"{title} {artist}", allow_plain_format=True)
        if lrc:
            return {"found": True, "synced": False, "source": "syncedlyrics"}
    except Exception:
        pass
    return {"found": False, "synced": False, "source": None}


def fetch_lyrics(title: str, artist: str) -> dict:
    """Fetch lyrics, parse LRC, annotate with Jyutping."""
    cache_file = CACHE_DIR / f"{_cache_key(title, artist)}.json"

    # Check cache
    if cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8"))

    # Fetch from syncedlyrics
    synced = True
    lrc = None
    try:
        lrc = syncedlyrics.search(f"{title} {artist}")
        if not lrc:
            lrc = syncedlyrics.search(f"{title} {artist}", allow_plain_format=True)
            synced = False
    except Exception:
        pass

    if not lrc:
        return {"title": title, "artist": artist, "synced": False, "lines": []}

    # Parse and annotate
    parsed = _parse_lrc(lrc)
    lines = []
    for entry in parsed:
        chars = annotate(entry["text"])
        lines.append({
            "time": entry["time"],
            "text": entry["text"],
            "chars": chars,
        })

    result = {
        "title": title,
        "artist": artist,
        "synced": synced,
        "lines": lines,
    }

    # Cache result
    cache_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def parse_manual_lyrics(text: str) -> dict:
    """Parse manually pasted lyrics (plain text, no timestamps)."""
    lines = []
    for line_text in text.strip().splitlines():
        line_text = line_text.strip()
        if not line_text:
            continue
        chars = annotate(line_text)
        lines.append({
            "time": None,
            "text": line_text,
            "chars": chars,
        })
    return {
        "title": "Manual Lyrics",
        "artist": "",
        "synced": False,
        "lines": lines,
    }
