"""Tiny file cache helpers shared by the lyrics and TTS caches.

Cache failures (unreadable entries, read-only disk) are logged and treated as
misses so they never break a request.
"""

import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except (OSError, UnicodeDecodeError) as exc:
        logger.warning("Ignoring unreadable cache entry %s: %s", path, exc)
        return None


def write_text(path: Path, text: str) -> None:
    """Write atomically so concurrent readers never see a partial file."""
    tmp = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
        tmp = None
    except OSError as exc:
        logger.warning("Could not write cache entry %s: %s", path, exc)
    finally:
        if tmp is not None:
            try:
                os.unlink(tmp)
            except OSError:
                pass
