# 聲粵 SingJyut

Learn Cantonese through songs — Jyutping annotation, TTS pronunciation, karaoke sync.

## What it does

SingJyut layers a learning experience on top of YouTube music videos:
- **Song search** — find any Cantonese song on YouTube (music category filter)
- **Jyutping above every character** — see pronunciation at a glance
- **Tap any character** — hear it spoken in Cantonese (Google Cloud TTS)
- **Karaoke sync** — lyrics highlight in time with YouTube playback
- **Mini-player** — video shrinks to top-right corner when you scroll through lyrics
- **Playback bar** — fixed bottom bar with play/pause, prev/next line, progress bar, and time display
- **Tap-to-seek** — tap any lyric line to jump the video to that timestamp
- **Manual lyrics paste** — fallback when automatic lyrics search fails
- **Multi-strategy lyrics search** — tries extracted title, user query, and full YouTube title
- **Mobile-first PWA** — add to home screen for app-like experience

## Quick Start

```bash
# Clone
git clone https://github.com/LOKTSN/singjyut.git
cd singjyut

# Install dependencies (a virtualenv is recommended)
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Set up API keys
cp .env.example .env
# Edit .env with your keys (see API Keys section below)

# Run
uvicorn server:app --reload

# Open on phone: http://<your-local-ip>:8000
```

## API Keys

You need two API keys from Google Cloud Console:

| Key | How to Get |
|-----|-----------|
| `YOUTUBE_API_KEY` | GCP Console → APIs & Services → YouTube Data API v3 |
| `GOOGLE_TTS_KEY` | GCP Console → APIs & Services → Cloud Text-to-Speech API |

Both are free tier eligible. Set them in your `.env` file (never commit this file).
Without them the app still runs: search and TTS report that they are not configured,
while lyrics, Jyutping and manual paste keep working.

### Optional settings

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATA_DIR` | `./data` | Writable directory for the lyrics and TTS caches |
| `HTTP_TIMEOUT` | `10` | Timeout (seconds) for calls to Google APIs |
| `PORT` | `8000` | Listening port of the Docker image |

`GET /api/health` returns `{"status": "ok", "youtube": bool, "tts": bool}` so you can check
which keys the server picked up.

## Tests

```bash
pip install -r requirements-dev.txt
python -m playwright install chromium   # once, for the browser tests
pytest                                   # everything
pytest --ignore=tests/e2e                # backend only (no browser needed)
```

- `tests/test_*.py` — API routes, LRC parsing, caching, Jyutping and TTS, with all
  external services (YouTube, Google TTS, lyrics providers) mocked.
- `tests/e2e/` — drives the real frontend in headless Chromium against the real
  server, with a fake YouTube IFrame API (`tests/e2e/fake_youtube_api.js`).

CI (`.github/workflows/ci.yml`) runs the full suite and builds and smoke-tests
the Docker image.

## Tech Stack

- **Backend:** FastAPI + ToJyutping + syncedlyrics
- **Frontend:** Vanilla JS + CSS (no build step)
- **Music:** YouTube IFrame API (embedded)
- **TTS:** Google Cloud TTS (yue-HK Cantonese)
- **Fonts:** Inter + Noto Sans TC + Noto Serif TC (Google Fonts)
- **Theme:** Light cream (#F5F0E8) with terracotta accent (#C4654A)

## Deployment

### Render (recommended)
1. Connect this GitHub repo on [render.com](https://render.com)
2. Build command: `pip install -r requirements.txt`
3. Start command: `uvicorn server:app --host 0.0.0.0 --port $PORT`
4. Add `YOUTUBE_API_KEY` and `GOOGLE_TTS_KEY` as environment variables
5. Health check path: `/api/health`

### Docker
```bash
docker build -t singjyut .
docker run -p 8000:8000 --env-file .env singjyut
```

The image runs as a non-root user, honours `$PORT`, and has a `HEALTHCHECK` on
`/api/health`. `.env` is excluded from the build context, so pass keys at run time.
Mount a volume on `/app/data` to keep the caches across restarts.

## Docs

- [PRD](docs/PRD.md) — Product requirements
- [SDD](docs/SDD.md) — System design
- [Tech Spec](docs/TECH_SPEC.md) — Technical specification
- [Roadmap](docs/ROADMAP.md) — Development phases

## License

MIT
