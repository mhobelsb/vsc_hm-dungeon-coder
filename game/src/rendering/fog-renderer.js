/**
 * Draws the fog of war (game/src/fog.js) over an already drawn level:
 * hidden cells black, remembered cells dimmed, visible cells untouched.
 */
export class FogRenderer {
    static REMEMBERED_ALPHA = 0.55;

    constructor(ctx) {
        this.ctx = ctx;
    }

    draw(fog, level, character) {
        if (!fog || !fog.isActive() || !level || !character) {
            return;
        }
        const ctx = this.ctx;
        const torchLight = fog.litByTorches();
        const heroKey = character.currentCell().join(",");
        for (let row = 0; row < level.height; row++) {
            for (let col = 0; col < level.width; col++) {
                const visibility = fog.visibility(col, row, torchLight, heroKey);
                if (visibility === "visible") {
                    continue;
                }
                ctx.fillStyle = visibility === "hidden"
                    ? "rgb(0, 0, 0)"
                    : `rgba(0, 0, 0, ${FogRenderer.REMEMBERED_ALPHA})`;
                ctx.fillRect(col * level.tileWidth, row * level.tileHeight, level.tileWidth, level.tileHeight);
            }
        }
    }
}
