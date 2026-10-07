/**
 * Draws the sensing marks (game/src/sensing.js): a thin frame around each cell a sensor
 * looked at, fading out; green where the answer was yes (or a value), white where it was no.
 * Only a frame at the cell's edge, so the cell itself stays visible.
 */
export class SensingRenderer {
    constructor(ctx) {
        this.ctx = ctx;
    }

    draw(sensing, level) {
        if (!sensing || !level || sensing.marks.size === 0) {
            return;
        }
        const ctx = this.ctx;
        const w = level.tileWidth, h = level.tileHeight;
        const line = Math.max(1, Math.round(w / 16));
        ctx.save();
        for (const mark of sensing.marks.values()) {
            const alpha = Math.min(1, mark.remaining / 400);
            ctx.strokeStyle = mark.positive ? `rgba(80, 230, 110, ${alpha})` : `rgba(235, 235, 235, ${alpha})`;
            ctx.lineWidth = line;
            ctx.strokeRect(mark.col * w + line / 2, mark.row * h + line / 2, w - line, h - line);
        }
        ctx.restore();
    }
}
