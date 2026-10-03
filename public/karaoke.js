// ── Karaoke Engine ──────────────────────────────────────────────────────────
// Polls YouTube player time and highlights the active lyric line.

const Karaoke = (() => {
    let lines = [];       // [{time, element}, ...]
    let interval = null;
    let activeIndex = -1;
    let offset = 0;       // timing offset in seconds

    function setLines(lyricLines) {
        lines = lyricLines || [];
        clearHighlight();
        if (interval) tick();
    }

    function start(lyricLines) {
        if (lyricLines) setLines(lyricLines);
        if (interval) clearInterval(interval);
        interval = setInterval(tick, 200);
        tick();
    }

    // Stop polling but keep the current line highlighted (paused video).
    function pause() {
        if (interval) {
            clearInterval(interval);
            interval = null;
        }
    }

    function stop() {
        pause();
        clearHighlight();
    }

    // Index of the last line whose time <= `time`, or -1.
    function indexAt(time) {
        const t = time + offset;
        for (let i = lines.length - 1; i >= 0; i--) {
            if (lines[i].time !== null && lines[i].time <= t) {
                return i;
            }
        }
        return -1;
    }

    function tick() {
        const newIndex = indexAt(YTPlayer.getCurrentTime());
        if (newIndex !== activeIndex) {
            activeIndex = newIndex;
            highlightLine(activeIndex);
        }
    }

    function highlightLine(index) {
        // Remove previous highlight
        const allLines = document.querySelectorAll('.lyric-line');
        allLines.forEach(el => el.classList.remove('active'));

        if (index >= 0 && index < lines.length && lines[index].element) {
            const el = lines[index].element;
            el.classList.add('active');

            // Auto-scroll to active line
            el.scrollIntoView({
                behavior: 'smooth',
                block: 'center',
            });
        }
    }

    function clearHighlight() {
        activeIndex = -1;
        document.querySelectorAll('.lyric-line').forEach(el => el.classList.remove('active'));
    }

    function setOffset(seconds) {
        offset = seconds;
    }

    function getActiveIndex() {
        return activeIndex;
    }

    return { start, pause, stop, setLines, indexAt, setOffset, getActiveIndex };
})();
