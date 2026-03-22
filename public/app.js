// ── SingJyut App ────────────────────────────────────────────────────────────

let currentSongData = null;
let karaokeLines = [];
let searchResults = [];

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
            <span class="featured-char">${s.title[0]}</span>
            <div class="featured-text">
                <span class="featured-title">${s.title}</span>
                <span class="featured-artist">${s.artist}</span>
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

async function doSearch() {
    const query = searchInput.value.trim();
    if (!query) return;

    const resultsList = document.getElementById('results-list');
    const emptyState = document.getElementById('search-empty');

    resultsList.innerHTML = '<div class="empty-state"><div class="spinner"></div><p>Searching...</p></div>';
    emptyState.classList.add('hidden');

    try {
        const resp = await fetch(`/api/youtube/search?q=${encodeURIComponent(query)}`);
        const data = await resp.json();

        if (!data.results || data.results.length === 0) {
            resultsList.innerHTML = '';
            emptyState.innerHTML = '<p>No results found. Try a different search.</p>';
            emptyState.classList.remove('hidden');
            return;
        }

        searchResults = data.results;
        resultsList.innerHTML = data.results.map((r, i) => `
            <div class="result-card" data-index="${i}">
                <img src="${r.thumbnail}" alt="" loading="lazy">
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
        resultsList.innerHTML = `<div class="empty-state"><p>Search failed: ${err.message}</p></div>`;
    }
}

// ── Song Selection ──────────────────────────────────────────────────────────

async function selectSong(videoId, title, artist) {
    document.getElementById('search-view').classList.remove('active');
    document.getElementById('song-view').classList.add('active');

    const decodedTitle = decodeHtmlEntities(title);
    document.getElementById('song-title').textContent = decodedTitle;
    document.getElementById('song-artist').textContent = artist;

    // Show playback bar
    document.getElementById('playback-bar').classList.remove('hidden');

    // Load YouTube video
    YTPlayer.loadVideo(videoId);

    // Show loading
    const lyricsContainer = document.getElementById('lyrics-container');
    const lyricsLoading = document.getElementById('lyrics-loading');
    const manualSection = document.getElementById('manual-lyrics-section');

    lyricsContainer.innerHTML = '';
    lyricsLoading.classList.remove('hidden');
    manualSection.classList.add('hidden');

    // Extract title/artist for lyrics search
    const cleanTitle = extractSongInfo(decodedTitle);
    const userQuery = searchInput.value.trim();

    // Try multiple search strategies
    let data = null;
    const attempts = [
        { title: cleanTitle.title, artist: cleanTitle.artist || artist },
        { title: userQuery, artist: '' },
        { title: decodedTitle, artist: '' },
    ];

    for (const attempt of attempts) {
        try {
            const resp = await fetch('/api/lyrics/fetch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(attempt),
            });
            const result = await resp.json();
            if (result.lines && result.lines.length > 0) {
                data = result;
                break;
            }
        } catch (err) {
            // try next
        }
    }

    currentSongData = data;
    lyricsLoading.classList.add('hidden');

    if (data && data.lines && data.lines.length > 0) {
        renderLyrics(data);
    } else {
        manualSection.classList.remove('hidden');
    }

    // Karaoke sync: always active when video plays
    YTPlayer.onStateChange((state) => {
        if (state === YT.PlayerState.PLAYING) {
            Karaoke.start(karaokeLines);
            Playback.updatePlayBtn(true);
        } else if (state === YT.PlayerState.PAUSED || state === YT.PlayerState.ENDED) {
            Karaoke.stop();
            Playback.updatePlayBtn(false);
        }
    });

    // Start playback bar progress updates
    Playback.startProgress();

    saveRecentSong(videoId, title, artist);
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
}

// ── Manual Lyrics ───────────────────────────────────────────────────────────

async function submitManualLyrics() {
    const text = document.getElementById('manual-lyrics-input').value.trim();
    if (!text) return;

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
        const data = await resp.json();
        currentSongData = data;

        lyricsLoading.classList.add('hidden');
        renderLyrics(data);
    } catch (err) {
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

    function prev() {
        // Find the current active line index, jump to previous
        const activeIdx = Karaoke.getActiveIndex();
        const target = activeIdx > 0 ? activeIdx - 1 : 0;
        if (karaokeLines[target] && karaokeLines[target].time !== null) {
            YTPlayer.seekTo(karaokeLines[target].time);
        }
    }

    function next() {
        const activeIdx = Karaoke.getActiveIndex();
        const target = activeIdx + 1;
        if (target < karaokeLines.length && karaokeLines[target] && karaokeLines[target].time !== null) {
            YTPlayer.seekTo(karaokeLines[target].time);
        }
    }

    function updatePlayBtn(playing) {
        const icon = document.getElementById('pb-play-icon');
        if (playing) {
            // Pause icon
            icon.innerHTML = '<path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>';
        } else {
            // Play icon
            icon.innerHTML = '<path d="M8 5v14l11-7z"/>';
        }
    }

    function startProgress() {
        stopProgress();
        progressInterval = setInterval(() => {
            const current = YTPlayer.getCurrentTime();
            const duration = YTPlayer.getDuration();
            if (duration > 0) {
                const pct = (current / duration) * 100;
                document.getElementById('progress-fill').style.width = pct + '%';

                // Update time display
                const mins = Math.floor(current / 60);
                const secs = Math.floor(current % 60);
                document.getElementById('pb-time').textContent =
                    `${mins}:${secs.toString().padStart(2, '0')}`;
            }
        }, 500);
    }

    function stopProgress() {
        if (progressInterval) {
            clearInterval(progressInterval);
            progressInterval = null;
        }
    }

    return { toggle, prev, next, updatePlayBtn, startProgress, stopProgress };
})();

// ── Progress bar seek ───────────────────────────────────────────────────────

document.getElementById('progress-bar').addEventListener('click', (e) => {
    const bar = e.currentTarget;
    const rect = bar.getBoundingClientRect();
    const pct = (e.clientX - rect.left) / rect.width;
    const duration = YTPlayer.getDuration();
    if (duration > 0) {
        YTPlayer.seekTo(pct * duration);
    }
});

// ── Navigation ──────────────────────────────────────────────────────────────

function showSearch() {
    document.getElementById('song-view').classList.remove('active');
    document.getElementById('search-view').classList.add('active');
    document.getElementById('playback-bar').classList.add('hidden');
    // Reset search view: clear results, show featured
    document.getElementById('results-list').innerHTML = '';
    document.getElementById('search-empty').classList.remove('hidden');
    renderFeatured();
    Karaoke.stop();
    TTS.stop();
    Playback.stopProgress();
}

// ── Helpers ─────────────────────────────────────────────────────────────────

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function decodeHtmlEntities(str) {
    const txt = document.createElement('textarea');
    txt.innerHTML = str;
    return txt.value;
}

function extractSongInfo(youtubeTitle) {
    const parts = youtubeTitle.split(/[-–—]/).map(s => s.trim());
    if (parts.length >= 2) {
        return { artist: parts[0], title: parts.slice(1).join(' ') };
    }
    return { title: youtubeTitle, artist: '' };
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
