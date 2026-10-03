"""Fake for syncedlyrics.search, shared by tests/conftest.py and tests."""

import syncedlyrics

# Captured before conftest patches it, for the signature check.
REAL_SEARCH = syncedlyrics.search


class LyricsProvider:
    """Stand-in for syncedlyrics.search; records every search term.

    Mirrors the real signature (see test_lyrics_provider_matches_syncedlyrics)
    and its default behaviour: synced LRC if available, else plain lyrics.
    """

    def __init__(self):
        self.calls = []
        self.synced = None   # LRC text a provider has
        self.plain = None    # plain lyrics a provider has
        self.error = None

    def __call__(self, search_term, plain_only=False, synced_only=False, save_path=None,
                 providers=None, lang=None, enhanced=False):
        self.calls.append(search_term)
        if self.error:
            raise self.error
        return self.synced or self.plain
