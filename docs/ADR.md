# SingJyut 聲粵 — Architecture Decision Record

**Status:** Accepted
**Date:** 2026-03-22 (MVP)
**Last revised:** 2026-03-22

---

## Context

SingJyut is a mobile-first Progressive Web App for learning Cantonese through songs. It layers Jyutping romanization annotation, text-to-speech pronunciation, and karaoke-style lyric synchronization on top of YouTube video embeds.

The architecture is shaped by two hard constraints:

1. **Python-only libraries.** ToJyutping (99% accuracy Cantonese romanization) and syncedlyrics (multi-provider time-stamped lyric fetching) are Python packages with no production-ready JavaScript equivalents. Any architecture must provide native Python execution for these.
2. **Server-side API keys.** YouTube Data API v3 and Google Cloud TTS API keys must never be exposed to the client. A server component is required regardless of frontend strategy.

This document records the decisions made for the MVP and their trade-offs.

---

## Decision 1: Backend — FastAPI (Python 3.11+)

**Status:** Accepted

### Options Evaluated

| Option | Pros | Cons |
|--------|------|------|
| **FastAPI (Python)** | Native access to ToJyutping + syncedlyrics; async by default; auto-generated OpenAPI docs; single-process deployment | Smaller ecosystem than Express for real-time features |
| Flask (Python) | Mature, simple | Synchronous by default; no auto-generated API docs; requires Gunicorn for production |
| Django (Python) | Batteries-included (ORM, admin, auth) | Massive overhead for a 3-endpoint API; ORM unused (no database in MVP) |
| Express.js + Python microservice | Unified JS runtime for frontend/backend | Requires IPC or HTTP hop to Python for every Jyutping/lyrics call; two processes to deploy and monitor |
| Next.js API routes + Python microservice | SSR, unified framework | Same two-process penalty as Express; Vercel serverless adds cold start to the Python hop; overengineered for 2 pages |

### Decision

FastAPI. It provides direct, in-process access to ToJyutping and syncedlyrics with zero serialization overhead. Async request handling is native via `asyncio`. The auto-generated `/docs` endpoint (Swagger UI) eliminates the need for separate API documentation tooling during development.

### Trade-offs

- A Node.js backend would unify the runtime with the frontend. However, every Jyutping annotation or lyrics fetch would require either spawning a Python subprocess or calling a separate Python microservice over HTTP. This adds deployment complexity, latency, and a failure mode — for zero functional gain in the MVP.
- FastAPI's ecosystem for background tasks (Celery, etc.) is less mature than Node.js workers, but the MVP has no background processing requirements.

---

## Decision 2: Frontend — Vanilla JavaScript (No Framework)

**Status:** Accepted

### Options Evaluated

| Option | Runtime Size | Build Step | PWA Support | Trade-off |
|--------|-------------|------------|-------------|-----------|
| **Vanilla JS** | 0 KB | None | Manual SW registration | More verbose DOM manipulation |
| React / Next.js | ~42 KB (minified + gzipped) | Webpack/Vite | next-pwa plugin | Heavy for 2 views; SSR unnecessary with FastAPI backend |
| SvelteKit | ~2 KB (compiles away) | Vite | Built-in adapter | Best migration target; overkill for MVP scope |
| Vue 3 | ~33 KB | Vite | vite-plugin-pwa | Middle ground; still requires build tooling |
| Alpine.js | ~15 KB | None | Manual SW registration | Declarative but limited component model |

### Decision

Vanilla JavaScript with no build step. The frontend is served as static files (`public/`) by FastAPI. The entire application consists of two views (search and song page), making framework overhead unjustifiable.

### Rationale

- **Zero build step** means the development loop is edit-save-reload. No bundler configuration, no source maps, no transpilation.
- **Zero runtime overhead** matters on mobile. The target user opens this on a phone over potentially slow connections. Every kilobyte of framework runtime is a kilobyte not spent on the 1.28 MB Jyutping dictionary (planned for Phase 2 client-side annotation).
- **Immediate deployability.** Static files are served directly by FastAPI's `StaticFiles` mount. No separate build artifact, no CI/CD pipeline for the frontend.
- **Precedent.** This pattern is proven in production — single vanilla JS files serving full-featured learning applications without a framework, with manageable complexity for up to ~100 KB of client code.

### Trade-offs

- DOM manipulation is more verbose than declarative frameworks. `document.createElement` / `innerHTML` patterns replace JSX or template syntax.
- No component model. UI reuse relies on functions returning DOM elements rather than encapsulated components.
- **Migration trigger:** If the UI grows beyond the current 2 views (e.g., saved items, user accounts, settings pages), migrate to SvelteKit. It compiles away the framework at build time (preserving the minimal-runtime property) and has first-class PWA support via `@sveltejs/adapter-static`.

---

## Decision 3: Client-Side Jyutping Annotation — Deferred to Phase 2

**Status:** Deferred

### Context

The `to-jyutping` npm package is an official JavaScript port of the ToJyutping library. Running it in-browser would eliminate the server round-trip for annotation, enabling offline Jyutping and instant response times.

### Why Deferred

1. **MVP already works.** Server-side annotation via ToJyutping is functional and returns results in under 200 ms for typical lyric lengths.
2. **Architectural restructuring required.** Moving annotation client-side changes the lyrics fetch flow: the server currently returns pre-annotated lyrics. Client-side annotation requires returning raw Chinese text and annotating in the browser, which touches the API contract, the frontend rendering pipeline, and the caching strategy.
3. **Dictionary payload.** The `to-jyutping` dictionary is 1.28 MB. This requires a service worker caching strategy to avoid re-downloading on every visit, which adds complexity to the PWA implementation.

### Phase 2 Plan

- Load `to-jyutping` via CDN or bundle it with the service worker cache.
- Annotate lyrics client-side after fetching raw text from the server.
- Fall back to server-side annotation if the dictionary fails to load.
- This enables offline annotation — a key feature for the PWA use case.

---

## Decision 4: Music Playback — YouTube IFrame API

**Status:** Accepted

### Context

No alternatives were formally evaluated. YouTube is the only source that is simultaneously free, legal, and comprehensive for Cantonese music. Licensing is handled entirely by YouTube's Content ID system.

### Decision

Embed YouTube videos via the IFrame Player API. The API provides:

- `getCurrentTime()` — polled to drive karaoke-style lyric highlighting
- `playVideo()` / `pauseVideo()` — programmatic playback control
- `onStateChange` — event-driven sync (play, pause, seek, end)

### Precedent

LingoClip (10M+ users, available on the App Store) uses the identical model: YouTube embeds with synchronized lyric display for language learning. This validates both the technical approach and the content licensing model.

### Trade-offs

- Dependent on YouTube's embed availability. Some videos have embedding disabled by the uploader; these are unsupported.
- `getCurrentTime()` polling introduces up to ~250 ms of sync jitter (polling interval). This is acceptable for lyric highlighting but would not be sufficient for audio-level synchronization.

---

## Decision 5: Deployment — Render Free Tier

**Status:** Accepted

### Options Evaluated

| Option | Pros | Cons |
|--------|------|------|
| **Render (free)** | GitHub auto-deploy; single service for API + static files; zero config | 15-min spin-down; ~30s cold start |
| Vercel | Best-in-class for Next.js; supports Python serverless functions | Optimized for Next.js, not FastAPI; Python functions have 10s timeout on free tier |
| AWS Free Tier (EC2/ECS) | Always-on; no cold start; 12-month free | Significant infrastructure configuration (VPC, security groups, IAM); ongoing maintenance |
| Google Cloud Run | Pay-per-request; user has existing GCP credits | Requires containerization; more config than Render for equivalent result |

### Decision

Render free tier. A single `Dockerfile` and a GitHub connection produce a public URL with automatic deploys on push to `main`. One service serves both the FastAPI application and the static frontend files.

### Trade-offs

- **Cold starts.** The free tier spins down after 15 minutes of inactivity. First request after spin-down takes approximately 30 seconds. This is acceptable for a personal learning tool with a single user.
- **Upgrade path.** If cold starts become unacceptable: Render paid tier ($7/month) eliminates spin-down. Alternatively, migrate to Google Cloud Run using the existing Dockerfile and GCP credits.

---

## Decision 6: No Database (MVP)

**Status:** Accepted

### Context

The MVP has no features that require persistent server-side state:

- **Lyrics cache** — written to the filesystem (`data/` directory) as JSON files, keyed by song identifier. Survives container restarts on Render's persistent disk.
- **Recent songs** — stored in the browser's `localStorage`. No server involvement.
- **User accounts** — not in MVP scope.

### Decision

No database. All persistence is handled by filesystem caching (server-side) and `localStorage` (client-side).

### Rationale

A database adds three categories of cost to the MVP:

1. **Deployment complexity.** A managed database (Supabase, PlanetScale, Render Postgres) is a separate service to provision, connect, and monitor. Connection strings, SSL certificates, and connection pooling become concerns.
2. **Financial cost.** Most managed database free tiers have storage or connection limits that would eventually require a paid plan.
3. **Schema management.** Even a simple schema requires migration tooling (Alembic, Prisma Migrate) and version control of schema changes.

None of these costs are justified when the MVP's persistence needs are fully met by files and `localStorage`.

### Migration Trigger

Add a database when any of these features enter scope:

- **User accounts** — authentication state, preferences, and progress tracking require server-side persistence.
- **Saved/favorited songs** — cross-device sync requires a user-associated data store.
- **Shared playlists** — multi-user data requires relational storage.

Planned provider: Supabase (Postgres + auth + real-time, generous free tier) or Firebase (if real-time sync is prioritized over SQL flexibility).

---

## Summary

| Concern | Decision | Key Rationale |
|---------|----------|---------------|
| Backend | FastAPI (Python) | Native access to ToJyutping + syncedlyrics; no IPC overhead |
| Frontend | Vanilla JS | Zero build step; zero runtime; sufficient for 2-view MVP |
| Jyutping | Server-side (Phase 1); client-side planned (Phase 2) | MVP simplicity now; offline capability later |
| Music | YouTube IFrame API | Only free, legal, comprehensive source; Content ID handles licensing |
| Deployment | Render free tier | Simplest GitHub-to-URL path; single service |
| Database | None (MVP) | Filesystem + localStorage cover all MVP persistence needs |

---

## Revision History

| Date | Change |
|------|--------|
| 2026-03-22 | Initial ADR established for MVP |
