import { Character } from '../character.js';

/**
 * Draws any GameObject (Torch, Door, Chest, Character, ...) at its own
 * position, dispatching to CharacterRenderer for Character instances.
 */
export class GameObjectRenderer {
    constructor(ctx, tileRenderer, characterRenderer) {
        this.ctx = ctx;
        this.tileRenderer = tileRenderer;
        this.characterRenderer = characterRenderer;
    }

    drawGameObject(object) {
        if (object instanceof Character) {
            this.characterRenderer.drawCharacter(object);
            return;
        }

        if (object.visible) {
            this.tileRenderer.drawAnyTile(object.tile, object.x, object.y, object.width, object.height, 0, 1.0);
        }
    }
}
