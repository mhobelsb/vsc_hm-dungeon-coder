import { Torch } from './game-objects.js';

/**
 * Fog of war: which cells the player may see. The hero only knows what it has
 * sensed; with fog, the screen shows no more than that.
 *
 * Modes (map property `fog`, a string; `true` means "explored"):
 *   none      everything is visible (default)
 *   explored  cells the hero stood on or sensed stay visible (dimmed)
 *   dark      only the hero's cell and cells sensed in the last moment are visible
 * In both fog modes, cells near a burning torch are lit.
 *
 * Game logic only; rendering/fog-renderer.js draws it.
 */
export class Fog {
    static MODES = ["none", "explored", "dark"];
    static SENSE_FLASH_MS = 1500;   // how long a sensed cell stays lit
    static TORCH_RADIUS = 2;        // cells around a burning torch that are lit (Chebyshev distance)

    constructor(level, mode) {
        this.level = level;
        this.mode = Fog.MODES.includes(mode) ? mode : "none";
        this.seen = new Set();      // "col,row" of cells ever seen ("explored" mode)
        this.flashes = new Map();   // "col,row" -> remaining ms of a sensor flash
    }

    /** Reads the mode from the level's map property `fog`. */
    static fromLevel(level) {
        const value = level.getProperty('fog');
        if (value === true) {
            return new Fog(level, "explored");
        }
        return new Fog(level, typeof value === 'string' ? value : "none");
    }

    isActive() {
        return this.mode !== "none";
    }

    static key(col, row) {
        return `${col},${row}`;
    }

    /** The hero stands on (or walks through) this cell. */
    markPresent(col, row) {
        this.seen.add(Fog.key(col, row));
    }

    /** A sensor looked at this cell: light it briefly, and remember it in "explored" mode. */
    markSensed(col, row) {
        this.seen.add(Fog.key(col, row));
        this.flashes.set(Fog.key(col, row), Fog.SENSE_FLASH_MS);
    }

    update(deltaTime) {
        for (const [key, remaining] of this.flashes) {
            if (remaining - deltaTime <= 0) {
                this.flashes.delete(key);
            } else {
                this.flashes.set(key, remaining - deltaTime);
            }
        }
    }

    /** Cells lit by burning torches. */
    litByTorches() {
        const lit = new Set();
        for (const object of this.level.objectFactory.gameObjects) {
            if (object instanceof Torch && object.isBurning()) {
                const col = Math.floor(object.x / this.level.tileWidth);
                const row = Math.floor((object.y - 1) / this.level.tileHeight);
                for (let dr = -Fog.TORCH_RADIUS; dr <= Fog.TORCH_RADIUS; dr++) {
                    for (let dc = -Fog.TORCH_RADIUS; dc <= Fog.TORCH_RADIUS; dc++) {
                        lit.add(Fog.key(col + dc, row + dr));
                    }
                }
            }
        }
        return lit;
    }

    /**
     * Visibility of a cell: "visible", "remembered" (seen before, drawn dimmed)
     * or "hidden".
     * @param {Set<string>} torchLight result of litByTorches(), computed once per frame
     * @param {string} heroKey the hero's current cell
     */
    visibility(col, row, torchLight, heroKey) {
        const key = Fog.key(col, row);
        if (!this.isActive() || key === heroKey || this.flashes.has(key) || torchLight.has(key)) {
            return "visible";
        }
        if (this.mode === "explored" && this.seen.has(key)) {
            return "remembered";
        }
        return "hidden";
    }
}
