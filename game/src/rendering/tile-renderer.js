import { AnimatedTile } from '../tiles.js';

export class TileRenderer {
    constructor(ctx) {
        this.ctx = ctx;
    }

    /**
     * Draws a single Tile onto this renderer's 2D rendering context.
     * @param {import('../tiles.js').Tile} tile The tile to draw.
     * @param {number} destX The X-coordinate (pixel) on the canvas to draw the tile.
     * @param {number} destY The Y-coordinate (pixel) on the canvas to draw the tile.
     * @param {number} [destWidth=tile.width] Unused - kept for call-site compatibility.
     * @param {number} [destHeight=tile.height] Unused - kept for call-site compatibility.
     */
    drawTile(tile, destX, destY, destWidth = tile.width, destHeight = tile.height, angle = 0, scaling_factor = 1.0) {
        if (!tile.visible) {
            return;
        }

        destY -= tile.height; // tiled coordinates are bottom left corner

        const ctx = this.ctx;
        ctx.save();
        ctx.translate(destX + tile.width / 2, destY + tile.height / 2); // Move to the tile's center

        // Rotate the canvas
        ctx.rotate(angle);
        // Tiled's flip flags: the picture is swapped diagonally first, then mirrored
        // horizontally, then vertically (canvas transforms apply in reverse order)
        if (tile.flipV) {
            ctx.scale(1, -1);
        }
        if (tile.flipH) {
            ctx.scale(-1, 1);
        }
        if (tile.flipD) {
            ctx.transform(0, 1, 1, 0, 0, 0);
        }

        // Draw the image centered at (0, 0)
        ctx.drawImage(tile.image,
                      tile.x,
                      tile.y,
                      tile.width,
                      tile.height,
                      -tile.width / 2 + tile.x_offset,
                      -tile.height / 2 + tile.y_offset,
                      tile.width * scaling_factor,
                      tile.height * scaling_factor);
        ctx.restore(); // Restore the original state
    }

    /**
     * Draws a Tile or AnimatedTile - the two "drawable" tile types produced
     * by TileFactory/Tileset - without the caller needing to know which one
     * it has.
     */
    drawAnyTile(tileOrAnimatedTile, destX, destY, destWidth, destHeight, angle = 0, scaling_factor = 1.0) {
        const tile = tileOrAnimatedTile instanceof AnimatedTile
            ? tileOrAnimatedTile.getCurrentTile()
            : tileOrAnimatedTile;
        this.drawTile(tile, destX, destY, destWidth, destHeight, angle, scaling_factor);
    }
}
