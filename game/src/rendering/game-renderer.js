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
    constructor({ ctx, canvasWidth, canvasHeight, tileRenderer, characterRenderer, gameObjectRenderer, layerRenderer, levelRenderer, hudRenderer, fogRenderer, sensingRenderer }) {
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
        this.sensingRenderer = sensingRenderer;
    }

    /** The view's size in game pixels (the level's size; Game.setViewSize). */
    setViewSize(width, height) {
        this.canvasWidth = width;
        this.canvasHeight = height;
        this.hudRenderer.setViewSize(width, height);
    }

    drawWaitingScreen() {
        this.hudRenderer.drawWaitingScreen();
    }

    /**
     * Clears the canvas, draws the level's world content, the fog of war, the HUD's darkness
     * overlay, then what the sensors just looked at (visible in the dark too) and the move budget.
     */
    drawPlayingScreen(level, fog, character, sensing, movesLeft) {
        this.ctx.clearRect(0, 0, this.canvasWidth, this.canvasHeight);
        this.levelRenderer.drawLevel(level);
        this.fogRenderer.draw(fog, level, character);
        this.hudRenderer.drawDarkOverlay(level);
        this.sensingRenderer.draw(sensing, level);
        if (movesLeft !== null && movesLeft !== undefined) {
            this.hudRenderer.drawMovesLeft(movesLeft);
        }
        if (level.character && level.isOnGoal(level.character)) {
            const missing = level.unmetWinConditions();
            if (missing.length > 0) {
                this.hudRenderer.drawGoalHint(missing);
            }
        }
    }

    /** Draws the "Game Over" screen shown when the character has died. */
    drawGameOverScreen(remainingTime, world, seed, outOfMoves) {
        this.hudRenderer.drawGameOverScreen(remainingTime, world, seed, outOfMoves);
    }

    /** Draws the "Level Complete" summary screen shown when a level is finished successfully. */
    drawLevelCompleteScreen(statistics, remainingTime, world, seed) {
        this.hudRenderer.drawLevelCompleteScreen(statistics, remainingTime, world, seed);
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
    draw(gameState, { level, statistics, remainingTime, fog, character, sensing, movesLeft, outOfMoves }) {
        // a generated level or a variant names its seed (map property `seed`): on the end
        // screens, so a failure can be reproduced (DC-T1p, DC-T1k)
        const seed = level?.getProperty('seed');
        switch (gameState) {
            case GAME_STATE.WAITING_FOR_LEVEL:
                this.drawWaitingScreen();
                break;
            case GAME_STATE.PLAYING:
                this.drawPlayingScreen(level, fog, character, sensing, movesLeft);
                break;
            case GAME_STATE.GAME_OVER:
                this.drawGameOverScreen(remainingTime, level?.getProperty('world'), seed, outOfMoves);
                break;
            case GAME_STATE.LEVEL_COMPLETE:
                this.drawLevelCompleteScreen(statistics, remainingTime, level?.getProperty('world'), seed);
                break;
        }
    }
}
