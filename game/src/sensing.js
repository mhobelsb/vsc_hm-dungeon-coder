/**
 * Visible sensing (DC-T1j): the cell a sensor looked at is outlined for a moment, in the colour
 * of its answer, so the program's view of the world and the world on screen meet. In every
 * level; a level can switch it off with the map property `show_sensing: false`.
 *
 * Game logic only; rendering/sensing-renderer.js draws it.
 */
export class Sensing {
    static FLASH_MS = 1200;

    constructor(enabled = true) {
        this.enabled = enabled;
        this.marks = new Map();     // "col,row" -> { col, row, positive, remaining }
    }

    static fromLevel(level) {
        return new Sensing(level.getBooleanProperty('show_sensing', true));
    }

    /** A sensor looked at (col, row); `answer` is what it said (true/false, a number, null). */
    mark(col, row, answer) {
        if (!this.enabled) {
            return;
        }
        const positive = answer !== false && answer !== null && answer !== undefined;
        this.marks.set(`${col},${row}`, { col, row, positive, remaining: Sensing.FLASH_MS });
    }

    update(deltaTime) {
        for (const [key, mark] of this.marks) {
            mark.remaining -= deltaTime;
            if (mark.remaining <= 0) {
                this.marks.delete(key);
            }
        }
    }
}
