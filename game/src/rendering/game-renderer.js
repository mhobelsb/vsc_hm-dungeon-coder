import { GAME_STATE } from '../game-state.js';

/**
 * Top-level renderer: glues the whole rendering/ dependency graph together
 * and owns screen-level orchestration - e.g. "clear the canvas, draw the
 * level, then draw the HUD overlay on top of it" for the playing screen.
 * Built by create-renderer.js's createRenderer() and handed to Game as
 * `this.renderer`. Every individual renderer stays reachable as a property,
 * in case a caller ever needs something more targeted than a full screen
 * (e.g. drawing a single level or object) without going through
 * create-renderer.js again.
 */
export class GameRenderer {
    constructor({ ctx, canvasWidth, canvasHeight, tileRenderer, characterRenderer, gameObjectRenderer, layerRenderer, levelRenderer, hudRenderer, fogRenderer }) {
        this.ctx = ctx;
        this.canvasWidth = canvasWidth;
        this.canvasHeight = canvasHeight;
        this.tileRenderer = tileRenderer;
        this.characterRenderer = characterRenderer;
        this.gameObjectRenderer = gameObjectRenderer;
        this.layerRenderer = layerRenderer;
        this.levelRenderer = levelRenderer;
        this.hudRenderer = hudRenderer;
        this.fogRenderer = fogRenderer;
    }

    drawWaitingScreen() {
        this.hudRenderer.drawWaitingScreen();
    }

    /** Clears the canvas, draws the level's world content, the fog of war, then the HUD's darkness overlay on top. */
    drawPlayingScreen(level, fog, character) {
        this.ctx.clearRect(0, 0, this.canvasWidth, this.canvasHeight);
        this.levelRenderer.drawLevel(level);
        this.fogRenderer.draw(fog, level, character);
        this.hudRenderer.drawDarkOverlay(level);
    }

    /** Draws the "Game Over" screen shown when the character has died. */
    drawGameOverScreen(remainingTime) {
        this.hudRenderer.drawGameOverScreen(remainingTime);
    }

    /** Draws the "Level Complete" summary screen shown when a level is finished successfully. */
    drawLevelCompleteScreen(statistics, remainingTime) {
        this.hudRenderer.drawLevelCompleteScreen(statistics, remainingTime);
    }

    /**
     * Draws whichever screen matches the current game state. This is the
     * single call Game.gameLoop() makes each frame; state *transitions*
     * are game logic and stay in Game, not here. Game.currentGameState
     * already distinguishes GAME_OVER from LEVEL_COMPLETE, so this never
     * needs the character itself to decide what to draw.
     * @param {string} gameState One of GAME_STATE (game-state.js).
     * @param {{level, statistics, remainingTime, fog, character}} scene
     *   Only the fields relevant to the current gameState need to be set.
     */
    draw(gameState, { level, statistics, remainingTime, fog, character }) {
        switch (gameState) {
            case GAME_STATE.WAITING_FOR_LEVEL:
                this.drawWaitingScreen();
                break;
            case GAME_STATE.PLAYING:
                this.drawPlayingScreen(level, fog, character);
                break;
            case GAME_STATE.GAME_OVER:
                this.drawGameOverScreen(remainingTime);
                break;
            case GAME_STATE.LEVEL_COMPLETE:
                this.drawLevelCompleteScreen(statistics, remainingTime);
                break;
        }
    }
}
