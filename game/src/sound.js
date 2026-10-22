/**
 * Small sounds for a live game in the room (map property `arena`): a blip for every rune picked up,
 * a rising chord at the start, a falling one at the end. Made with WebAudio, no files. Browsers
 * allow sound only after the page got a key or a click, so `unlock()` runs on the referee's Space.
 * A level can switch the sounds off with `sound: false`.
 */
export class Sound {
    constructor() {
        this.context = null;
        this.enabled = true;
    }

    unlock() {
        try {
            const Context = globalThis.AudioContext || globalThis.webkitAudioContext;
            if (!this.context && Context) {
                this.context = new Context();
            }
            this.context?.resume?.();
        } catch {
            this.context = null;
        }
    }

    tone(frequency, start, length, volume = 0.15) {
        if (!this.enabled || !this.context || this.context.state !== 'running') {
            return;
        }
        const now = this.context.currentTime + start;
        const oscillator = this.context.createOscillator();
        const gain = this.context.createGain();
        oscillator.type = 'square';
        oscillator.frequency.value = frequency;
        gain.gain.setValueAtTime(volume, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + length);
        oscillator.connect(gain).connect(this.context.destination);
        oscillator.start(now);
        oscillator.stop(now + length);
    }

    pickup() {
        this.tone(880, 0, 0.08);
        this.tone(1320, 0.07, 0.1);
    }

    start() {
        [523, 659, 784].forEach((f, i) => this.tone(f, i * 0.12, 0.18));
    }

    end() {
        [784, 659, 523].forEach((f, i) => this.tone(f, i * 0.14, 0.22));
    }
}
