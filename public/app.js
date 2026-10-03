// ── SingJyut App ────────────────────────────────────────────────────────────

let currentSongData = null;
let karaokeLines = [];
let searchResults = [];
let searchSeq = 0;     // only the latest search may render
let songLoadId = 0;    // bumps on every song change; stale lyric loads are dropped

// ── Featured Songs ──────────────────────────────────────────────────────────

const FEATURED_SONGS = [
    { title: '海闊天空', artist: 'Beyond', query: '海闊天空 Beyond' },
    { title: '喜歡你', artist: 'Beyond', query: '喜歡你 Beyond' },
    { title: '紅日', artist: '李克勤', query: '紅日 李克勤' },
    { title: '富士山下', artist: '陳奕迅', query: '富士山下 陳奕迅' },
    { title: '光輝歲月', artist: 'Beyond', query: '光輝歲月 Beyond' },
    { title: '單車', artist: '陳奕迅', query: '單車 陳奕迅' },
    { title: '夠鐘', artist: '周柏豪', query: '夠鐘 周柏豪' },
    { title: '歲月如歌', artist: '陳奕迅', query: '歲月如歌 陳奕迅' },
];

function renderFeatured() {
    const grid = document.getElementById('featured-grid');
    if (!grid) return;
    grid.innerHTML = FEATURED_SONGS.map((s, i) => `
        <div class="featured-card" data-index="${i}">
            <span class="featured-char">${escapeHtml(s.title[0])}</span>
            <div class="featured-text">
                <span class="featured-title">${escapeHtml(s.title)}</span>
                <span class="featured-artist">${escapeHtml(s.artist)}</span>
            </div>
        </div>
    `).join('');

    grid.querySelectorAll('.featured-card').forEach(card => {
        card.addEventListener('click', () => {
            const s = FEATURED_SONGS[parseInt(card.dataset.index)];
            searchInput.value = s.query;
            doSearch();
        });
    });
}

// Initialize featured songs on load
renderFeatured();

// ── Search ──────────────────────────────────────────────────────────────────

const searchInput = document.getElementById('search-input');
searchInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') doSearch();
});

function searchMessage(text) {
    return `<div class="empty-state search-message"><p>${escapeHtml(text)}</p></div>`;
}

async function doSearch() {
    const query = searchInput.value.trim();
    if (!query) return;

    const seq = ++searchSeq;
    const resultsList = document.getElementById('results-list');
    const emptyState = document.getElementById('search-empty');

    // Messages go into the results list; #search-empty holds the hero and
    // featured songs and must survive a failed search.
    resultsList.innerHTML = '<div class="empty-state"><div class="spinner"></div><p>Searching...</p></div>';
    emptyState.classList.add('hidden');

    try {
        const resp = await fetch(`/api/youtube/search?q=${encodeURIComponent(query)}`);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        if (seq !== searchSeq) return;

        if (data.error) {
            resultsList.innerHTML = searchMessage(data.error);
            return;
        }
        if (!data.results || data.results.length === 0) {
            resultsList.innerHTML = searchMessage('No results found. Try a different search.');
            return;
        }

        searchResults = data.results;
        resultsList.innerHTML = data.results.map((r, i) => `
            <div class="result-card" data-index="${i}">
                <img src="${escapeHtml(r.thumbnail)}" alt="" loading="lazy">
                <div class="result-info">
                    <h3>${escapeHtml(r.title)}</h3>
                    <p>${escapeHtml(r.channelTitle)}</p>
                </div>
            </div>
        `).join('');

        resultsList.querySelectorAll('.result-card').forEach(card => {
            card.addEventListener('click', () => {
                const r = searchResults[parseInt(card.dataset.index)];
                selectSong(r.videoId, r.title, r.channelTitle);
            });
        });
    } catch (err) {
        if (seq !== searchSeq) return;
        resultsList.innerHTML = searchMessage(`Search failed: ${err.message}`);
    }
}

// ── Player Events ───────────────────────────────────────────────────────────

// Registered once, so play/pause works even before lyrics finish loading.
YTPlayer.onStateChange((state) => {
    if (state === YT.PlayerState.PLAYING) {
        Karaoke.start();
        Playback.updatePlayBtn(true);
    } else if (state === YT.PlayerState.ENDED) {
        Karaoke.stop();
        Playback.updatePlayBtn(false);
    } else if (state !== YT.PlayerState.BUFFERING) {
        Karaoke.pause();
        Playback.updatePlayBtn(false);
    }
});

YTPlayer.onError((code) => {
    const messages = {
        100: 'This video was removed or is private.',
        101: "This video can't be played outside YouTube. Go back and pick another result.",
        150: "This video can't be played outside YouTube. Go back and pick another result.",
    };
    const el = document.getElementById('player-error');
    el.textContent = messages[code] || 'The video failed to load. Go back and pick another result.';
    el.classList.remove('hidden');
});

// ── Song Selection ──────────────────────────────────────────────────────────

async function selectSong(videoId, title, artist) {
    const loadId = ++songLoadId;

    document.getElementById('search-view').classList.remove('active');
    document.getElementById('song-view').classList.add('active');
    window.scrollTo(0, 0);

    document.getElementById('song-title').textContent = title;
    document.getElementById('song-artist').textContent = artist;
    document.getElementById('player-error').classList.add('hidden');

    // Forget the previous song before anything async happens
    currentSongData = null;
    karaokeLines = [];
    Karaoke.stop();
    Karaoke.setLines([]);
    TTS.stop();

    // Show playback bar
    document.getElementById('playback-bar').classList.remove('hidden');
    Playback.reset();
    Playback.startProgress();

    // Load YouTube video
    YTPlayer.loadVideo(videoId);
    saveRecentSong(videoId, title, artist);

    // Show loading
    const lyricsContainer = document.getElementById('lyrics-container');
    const lyricsLoading = document.getElementById('lyrics-loading');
    const manualSection = document.getElementById('manual-lyrics-section');

    lyricsContainer.innerHTML = '';
    lyricsLoading.classList.remove('hidden');
    manualSection.classList.add('hidden');

    // Extract title/artist for lyrics search
    const songInfo = extractSongInfo(title);
    const userQuery = searchInput.value.trim();

    // Try multiple search strategies
    const attempts = [
        { title: songInfo.title, artist: songInfo.artist || artist },
        { title: userQuery, artist: '' },
        { title: title, artist: '' },
    ];
    const tried = new Set();
    let data = null;

    for (const attempt of attempts) {
        const key = `${attempt.title}|${attempt.artist}`.toLowerCase();
        if (!attempt.title || tried.has(key)) continue;
        tried.add(key);
        try {
            const resp = await fetch('/api/lyrics/fetch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(attempt),
            });
            const result = await resp.json();
            if (result.lines && result.lines.length > 0) {
                data = result;
            }
        } catch (err) {
            // try next
        }
        // The user picked another song (or went back) meanwhile.
        if (loadId !== songLoadId) return;
        if (data) break;
    }

    currentSongData = data;
    lyricsLoading.classList.add('hidden');

    if (data) {
        renderLyrics(data);
    } else {
        manualSection.classList.remove('hidden');
    }
}

// ── Lyrics Rendering ────────────────────────────────────────────────────────

function renderLyrics(data) {
    const container = document.getElementById('lyrics-container');
    container.innerHTML = '';
    karaokeLines = [];

    data.lines.forEach((line, idx) => {
        const lineEl = document.createElement('div');
        lineEl.className = 'lyric-line';
        lineEl.dataset.index = idx;

        const charsRow = document.createElement('div');
        charsRow.className = 'chars-row';

        line.chars.forEach(c => {
            const block = document.createElement('span');

            if (!c.char.trim()) {
                block.className = 'char-block space';
                charsRow.appendChild(block);
                return;
            }

            const isPunct = !c.jyutping;
            block.className = 'char-block' + (isPunct ? ' punct' : '');

            if (!isPunct) {
                const jp = document.createElement('span');
                jp.className = 'jyutping';
                jp.textContent = c.jyutping;
                block.appendChild(jp);
            }

            const hz = document.createElement('span');
            hz.className = 'hanzi';
            hz.textContent = c.char;
            block.appendChild(hz);

            // Tap character for TTS
            if (!isPunct) {
                block.addEventListener('click', (e) => {
                    e.stopPropagation();
                    TTS.speak(c.char);
                });
            }

            charsRow.appendChild(block);
        });

        lineEl.appendChild(charsRow);

        // Speaker button for whole line TTS
        const speakerBtn = document.createElement('button');
        speakerBtn.className = 'line-speaker';
        speakerBtn.textContent = '🔊';
        speakerBtn.setAttribute('aria-label', 'Read line aloud');
        speakerBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            TTS.speak(line.text);
        });
        lineEl.appendChild(speakerBtn);

        // Tap line = seek video to this timestamp
        lineEl.addEventListener('click', () => {
            if (line.time !== null) {
                YTPlayer.seekTo(line.time);
            }
        });

        container.appendChild(lineEl);

        karaokeLines.push({
            time: line.time,
            element: lineEl,
        });
    });

    // Highlights right away if the video is already playing.
    Karaoke.setLines(karaokeLines);
}

// ── Manual Lyrics ───────────────────────────────────────────────────────────

async function submitManualLyrics() {
    const text = document.getElementById('manual-lyrics-input').value.trim();
    if (!text) return;

    const loadId = songLoadId;
    const lyricsLoading = document.getElementById('lyrics-loading');
    const manualSection = document.getElementById('manual-lyrics-section');

    manualSection.classList.add('hidden');
    lyricsLoading.classList.remove('hidden');

    try {
        const resp = await fetch('/api/lyrics/manual', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text }),
        });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        if (loadId !== songLoadId) return;
        currentSongData = data;

        lyricsLoading.classList.add('hidden');
        renderLyrics(data);
    } catch (err) {
        if (loadId !== songLoadId) return;
        lyricsLoading.classList.add('hidden');
        manualSection.classList.remove('hidden');
    }
}

// ── Playback Bar ────────────────────────────────────────────────────────────

const Playback = (() => {
    let progressInterval = null;

    function toggle() {
        if (YTPlayer.isPlaying()) {
            YTPlayer.pause();
        } else {
            YTPlayer.play();
        }
    }

    // Line index at the current playback position. Derived from the player
    // time rather than the karaoke highlight, which is idle while paused.
    // The small lead absorbs seek imprecision so "next" never repeats a line.
    function currentLineIndex() {
        return Karaoke.indexAt(YTPlayer.getCurrentTime() + 0.3);
    }

    function seekToLine(index) {
        const line = karaokeLines[index];
        if (line && line.time !== null) {
            YTPlayer.seekTo(line.time);
        }
    }

    function prev() {
        const idx = currentLineIndex();
        seekToLine(idx > 0 ? idx - 1 : 0);
    }

    function next() {
        seekToLine(currentLineIndex() + 1);
    }

    function updatePlayBtn(playing) {
        const icon = document.getElementById('pb-play-icon');
        const btn = document.getElementById('pb-play');
        if (playing) {
            // Pause icon
            icon.innerHTML = '<path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>';
            btn.setAttribute('aria-label', 'Pause');
        } else {
            // Play icon
            icon.innerHTML = '<path d="M8 5v14l11-7z"/>';
            btn.setAttribute('aria-label', 'Play');
        }
    }

    function formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }

    function render(current, duration) {
        const pct = duration > 0 ? Math.min(100, (current / duration) * 100) : 0;
        document.getElementById('progress-fill').style.width = pct + '%';
        document.getElementById('pb-time').textContent = formatTime(current);
    }

    function reset() {
        render(0, 0);
        updatePlayBtn(false);
    }

    function startProgress() {
        stopProgress();
        progressInterval = setInterval(() => {
            const duration = YTPlayer.getDuration();
            if (duration > 0) {
                render(YTPlayer.getCurrentTime(), duration);
            }
        }, 500);
    }

    function stopProgress() {
        if (progressInterval) {
            clearInterval(progressInterval);
            progressInterval = null;
        }
    }

    return { toggle, prev, next, updatePlayBtn, reset, startProgress, stopProgress };
})();

// ── Progress bar seek ───────────────────────────────────────────────────────

document.getElementById('progress-bar').addEventListener('click', (e) => {
    const bar = e.currentTarget;
    const rect = bar.getBoundingClientRect();
    const pct = Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width));
    const duration = YTPlayer.getDuration();
    if (duration > 0) {
        YTPlayer.seekTo(pct * duration);
    }
});

// ── Mini-Player ─────────────────────────────────────────────────────────────
// When the video scrolls out of view under the header, pin it to the
// top-right corner so it stays visible while reading lyrics.

const MiniPlayer = (() => {
    const container = document.getElementById('player-container');
    const sentinel = document.getElementById('player-sentinel');
    const songView = document.getElementById('song-view');
    const header = document.getElementById('header');

    function set(mini) {
        container.classList.toggle('mini', mini);
    }

    if ('IntersectionObserver' in window) {
        const observer = new IntersectionObserver(([entry]) => {
            const rootTop = entry.rootBounds ? entry.rootBounds.top : 0;
            const scrolledPast = !entry.isIntersecting && entry.boundingClientRect.top < rootTop;
            set(songView.classList.contains('active') && scrolledPast);
        }, { rootMargin: `-${header.offsetHeight}px 0px 0px 0px` });
        observer.observe(sentinel);
    }

    return { reset: () => set(false) };
})();

// ── Navigation ──────────────────────────────────────────────────────────────

function showSearch() {
    songLoadId++;   // abandon any lyrics load still in flight
    YTPlayer.stop();
    MiniPlayer.reset();
    document.getElementById('song-view').classList.remove('active');
    document.getElementById('search-view').classList.add('active');
    document.getElementById('playback-bar').classList.add('hidden');
    // Reset search view: clear results, show featured
    searchSeq++;
    document.getElementById('results-list').innerHTML = '';
    document.getElementById('search-empty').classList.remove('hidden');
    renderFeatured();
    Karaoke.stop();
    TTS.stop();
    Playback.stopProgress();
}

// ── Helpers ─────────────────────────────────────────────────────────────────

// Safe for both element content and quoted attribute values. (Function
// declarations are hoisted; renderFeatured() calls this at load.)
function escapeHtml(str) {
    const escapes = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
    return String(str ?? '').replace(/[&<>"']/g, c => escapes[c]);
}

// Bracketed noise in YouTube titles: (Official MV) [HD] 【歌詞】 （高清）
const TITLE_NOISE = /[(\[【（][^)\]】）]*[)\]】）]/g;
const TITLE_NOISE_WORDS = /\b(official|music|lyrics?|video|mv|hd|4k)\b/gi;

function tidyTitlePart(str) {
    return str.replace(TITLE_NOISE, ' ').replace(TITLE_NOISE_WORDS, ' ').replace(/\s+/g, ' ').trim();
}

function extractSongInfo(youtubeTitle) {
    const raw = youtubeTitle.trim();

    // 陳奕迅 Eason Chan《富士山下》[Official MV]: title is inside 《》「」『』
    const quoted = raw.match(/[《「『]([^》」』]+)[》」』]/);
    if (quoted) {
        return { title: quoted[1].trim(), artist: tidyTitlePart(raw.slice(0, quoted.index)) };
    }

    // Beyond - 海闊天空 (Official MV)
    const parts = tidyTitlePart(raw).split(/\s*[-–—|｜]\s*/).filter(Boolean);
    if (parts.length >= 2) {
        return { artist: parts[0], title: parts.slice(1).join(' ') };
    }
    return { title: parts[0] || raw, artist: '' };
}

// ── Recent Songs (localStorage) ─────────────────────────────────────────────

function saveRecentSong(videoId, title, artist) {
    try {
        const key = 'singjyut_recent';
        let recent = JSON.parse(localStorage.getItem(key) || '[]');
        recent = recent.filter(s => s.videoId !== videoId);
        recent.unshift({ videoId, title, artist, ts: Date.now() });
        recent = recent.slice(0, 20);
        localStorage.setItem(key, JSON.stringify(recent));
    } catch (e) {
        // localStorage might be unavailable
    }
}
