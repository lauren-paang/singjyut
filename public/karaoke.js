// ── Karaoke Engine ──────────────────────────────────────────────────────────
// Polls YouTube player time and highlights the active lyric line.

const Karaoke = (() => {
    let lines = [];       // [{time, element}, ...]
    let interval = null;
    let activeIndex = -1;
    let offset = 0;       // timing offset in seconds

    function start(lyricLines) {
        stop();
        lines = lyricLines;
        activeIndex = -1;
        interval = setInterval(tick, 200);
    }

    function stop() {
        if (interval) {
            clearInterval(interval);
            interval = null;
        }
        clearHighlight();
    }

    function tick() {
        if (!YTPlayer.isPlaying()) return;

        const currentTime = YTPlayer.getCurrentTime() + offset;
        let newIndex = -1;

        // Find the last line whose time <= currentTime
        for (let i = lines.length - 1; i >= 0; i--) {
            if (lines[i].time !== null && lines[i].time <= currentTime) {
                newIndex = i;
                break;
            }
        }

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

    return { start, stop, setOffset, getActiveIndex };
})();
