export class CharacterRenderer {
    constructor(ctx, tileRenderer) {
        this.ctx = ctx;
        this.tileRenderer = tileRenderer;
    }

    /**
     * Draws a Character, including its fall/rotation/shrink animation state.
     */
    drawCharacter(character) {
        if (character.debugDraw) {
            this.drawCharacterDebugOverlay(character);
        }

        if (character.visible) {
            this.tileRenderer.drawAnyTile(character.tile, character.x, character.y, character.width, character.height, character.angle, character.scaling_factor);
        }
    }

    /**
     * Draws the character's bounding box, its anchor point, and the tile it
     * is currently facing - useful when debugging positioning/collision.
     * Enabled via the `debugDraw` flag passed to the Character constructor.
     */
    drawCharacterDebugOverlay(character) {
        const ctx = this.ctx;
        ctx.save();

        // Tiled coordinates are bottom-left, matching TileRenderer's convention.
        ctx.strokeStyle = 'lime';
        ctx.lineWidth = 1;
        ctx.strokeRect(character.x, character.y - character.height, character.width, character.height);

        ctx.fillStyle = 'black';
        ctx.fillRect(character.x, character.y, 1, 1);

        const newTargetXY = character.getPositionInDirection(character.getDirection(), true);
        ctx.fillStyle = 'red';
        ctx.fillRect(newTargetXY[0], newTargetXY[1], 1, 1);

        ctx.restore();
    }
}
