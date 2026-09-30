export class LayerRenderer {
    constructor(ctx, tileRenderer, gameObjectRenderer) {
        this.ctx = ctx;
        this.tileRenderer = tileRenderer;
        this.gameObjectRenderer = gameObjectRenderer;
    }

    /**
     * Draws a TileLayer onto this renderer's 2D rendering context.
     */
    drawTileLayer(layer, levelTileWidth, levelTileHeight) {
        if (!layer.visible || layer.opacity <= 0) {
            return;
        }

        const ctx = this.ctx;
        ctx.globalAlpha = layer.opacity;

        layer.tileMap.forEach((row, rowIndex) => {
            row.forEach((tile, colIndex) => {
                if (tile) {
                    const destX = colIndex * levelTileWidth;
                    const destY = rowIndex * levelTileHeight + levelTileHeight; // Compute tiled coordinates here, i.e. bottom left
                    this.tileRenderer.drawAnyTile(tile, destX, destY);
                }
            });
        });

        ctx.globalAlpha = 1.0;
    }

    /**
     * Draws an ObjectLayer onto this renderer's 2D rendering context.
     */
    drawObjectLayer(layer) {
        if (layer.visible) {
            // figures (the hero, guards) are drawn last, so an item on their field
            // (a bed, a crystal) doesn't hide them
            const isFigure = object => object.type === "Character" || object.type === "Guard";
            layer.objects.filter(object => !isFigure(object)).forEach((object) => {
                this.gameObjectRenderer.drawGameObject(object);
            });
            layer.objects.filter(isFigure).forEach((object) => {
                this.gameObjectRenderer.drawGameObject(object);
            });
        }
    }
}
