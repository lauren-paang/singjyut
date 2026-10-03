// Minimal stand-in for https://www.youtube.com/iframe_api used by the e2e
// tests. Exposes the player instance as window.__ytPlayer so tests can drive
// playback time and state deterministically.
(function () {
    const PlayerState = { UNSTARTED: -1, ENDED: 0, PLAYING: 1, PAUSED: 2, BUFFERING: 3, CUED: 5 };

    function Player(elementId, opts) {
        this.videoId = opts.videoId;
        this.time = 0;
        this.state = PlayerState.UNSTARTED;
        this.events = opts.events || {};
        this.loadCount = 1;
        window.__ytPlayer = this;
        window.__ytPlayerCreated = (window.__ytPlayerCreated || 0) + 1;
        setTimeout(() => this.events.onReady && this.events.onReady({ target: this }), 0);
    }

    Player.prototype._setState = function (state) {
        this.state = state;
        if (this.events.onStateChange) this.events.onStateChange({ target: this, data: state });
    };
    Player.prototype.loadVideoById = function (videoId) {
        this.videoId = videoId;
        this.time = 0;
        this.loadCount += 1;
        this._setState(PlayerState.UNSTARTED);
    };
    Player.prototype.playVideo = function () { this._setState(PlayerState.PLAYING); };
    Player.prototype.pauseVideo = function () { this._setState(PlayerState.PAUSED); };
    Player.prototype.stopVideo = function () { this._setState(PlayerState.CUED); };
    Player.prototype.seekTo = function (seconds) { this.time = seconds; };
    Player.prototype.getCurrentTime = function () { return this.time; };
    Player.prototype.getDuration = function () { return 200; };
    Player.prototype.getPlayerState = function () { return this.state; };

    window.YT = { Player, PlayerState };
    if (typeof window.onYouTubeIframeAPIReady === 'function') window.onYouTubeIframeAPIReady();
})();
