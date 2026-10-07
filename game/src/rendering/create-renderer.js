import { TileRenderer } from './tile-renderer.js';
import { CharacterRenderer } from './character-renderer.js';
import { GameObjectRenderer } from './game-object-renderer.js';
import { LayerRenderer } from './layer-renderer.js';
import { LevelRenderer } from './level-renderer.js';
import { HudRenderer } from './hud-renderer.js';
import { GameRenderer } from './game-renderer.js';
import { FogRenderer } from './fog-renderer.js';
import { SensingRenderer } from './sensing-renderer.js';

/**
 * Composition root for the rendering/ classes: wires each renderer's
 * dependencies together and returns the GameRenderer that glues them all
 * together, which Game actually talks to.
 */
export function createRenderer(ctx, canvasWidth, canvasHeight, pathPrefix) {
    const tileRenderer = new TileRenderer(ctx);
    const characterRenderer = new CharacterRenderer(ctx, tileRenderer);
    const gameObjectRenderer = new GameObjectRenderer(ctx, tileRenderer, characterRenderer);
    const layerRenderer = new LayerRenderer(ctx, tileRenderer, gameObjectRenderer);
    const levelRenderer = new LevelRenderer(ctx, layerRenderer);
    const hudRenderer = new HudRenderer(ctx, canvasWidth, canvasHeight, pathPrefix);
    const fogRenderer = new FogRenderer(ctx);
    const sensingRenderer = new SensingRenderer(ctx);

    return new GameRenderer({
        ctx, canvasWidth, canvasHeight,
        tileRenderer, characterRenderer, gameObjectRenderer, layerRenderer, levelRenderer, hudRenderer, fogRenderer, sensingRenderer,
    });
}
