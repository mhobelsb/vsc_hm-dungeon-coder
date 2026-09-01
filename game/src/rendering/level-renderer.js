import { TileLayer, ObjectLayer } from '../layers.js';

export class LevelRenderer {
    constructor(ctx, layerRenderer) {
        this.ctx = ctx;
        this.layerRenderer = layerRenderer;
    }

    /**
     * Draws all layers of a Level onto this renderer's 2D rendering context.
     * Layers are drawn in the order they appear in the Tiled JSON.
     * @param {import('../level.js').Level} level The level to draw.
     */
    drawLevel(level) {
        if (!this.ctx) {
            console.warn("Cannot draw tile layers: ctx not provided.");
            return;
        }

        level.layers.forEach(layer => {
            if (layer instanceof TileLayer) {
                this.layerRenderer.drawTileLayer(layer, level.tileWidth, level.tileHeight);
            } else if (layer instanceof ObjectLayer) {
                this.layerRenderer.drawObjectLayer(layer);
            }
        });
    }
}
