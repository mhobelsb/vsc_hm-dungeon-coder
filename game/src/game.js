import { Level } from './level.js';
import { KeyBoardInput } from './input.js';
import { CharacterInterface } from './character.js';
import { Statistics } from './statistics.js';
import { createRenderer } from './rendering/create-renderer.js';
import { GAME_STATE } from './game-state.js';
import { Fog } from './fog.js';

/** The view before a level is loaded, in game pixels: 30 x 20 cells of 16 px. */
export const GAME_WIDTH = 480;
export const GAME_HEIGHT = 320;
/**
 * The canvas buffer is larger than the view (sharp text); drawing uses game pixels.
 * At the default view the factor is RENDER_SCALE; other views get the whole factor
 * that brings them to about the same buffer size (see bufferScale).
 */
export const RENDER_SCALE = 2;

/** Whole number of buffer pixels per game pixel for a view of this size. */
export function bufferScale(viewWidth, viewHeight) {
    return Math.max(1, Math.ceil(Math.min(GAME_WIDTH * RENDER_SCALE / viewWidth, GAME_HEIGHT * RENDER_SCALE / viewHeight)));
}

export class Game {
    static GAME_STATE = GAME_STATE;

    constructor(canvas, pathPrefix) {
        this.lastFrameTimeMs = 0;
        this.lastFpsUpdateTime = 0;
        this.framesThisSecond = 0;
        this.updatesThisSecond = 0;
        this.accumulatedTime = 0;
        this.animationFrameId = null;
        this.FIXED_TIME_STEP = 1000 / 60;
        this.goal = null;
        this.level = null;
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.renderer = createRenderer(this.ctx, GAME_WIDTH, GAME_HEIGHT, pathPrefix);
        /** Called after the view size changed, so the page can fit the canvas again. */
        this.onViewChange = null;
        this.setViewSize(GAME_WIDTH, GAME_HEIGHT);
        this.inputManager = new KeyBoardInput();
        this.currentGameState = GAME_STATE.WAITING_FOR_LEVEL;
        this.remainingTime = 5000;
        this.character = null;
        this.characterInterface = null;
        this.pathPrefix = pathPrefix;
        this.statistics = new Statistics();
        this.lastLevelData = null;
        this.fog = null;
    }

    /**
     * The view is as large as the level (in game pixels). Sets the canvas buffer,
     * the drawing transform and the renderers' size.
     */
    setViewSize(width, height) {
        this.viewWidth = width;
        this.viewHeight = height;
        const scale = bufferScale(width, height);
        this.canvas.width = width * scale;          // also resets the context's state
        this.canvas.height = height * scale;
        this.canvas.dataset.viewWidth = width;
        this.canvas.dataset.viewHeight = height;
        this.ctx.setTransform(scale, 0, 0, scale, 0, 0);
        this.ctx.imageSmoothingEnabled = false;
        this.renderer.setViewSize(width, height);
        if (this.onViewChange) {
            this.onViewChange();
        }
    }

    async loadLevel(levelData) {
        // a level that can't be built (e.g. a missing tileset) throws here and leaves the old one
        this.level = await Level.create(levelData, this.pathPrefix);
        this.statistics.reset();
        const width = this.level.width * this.level.tileWidth, height = this.level.height * this.level.tileHeight;
        if (width > 0 && height > 0 && (width !== this.viewWidth || height !== this.viewHeight)) {
            this.setViewSize(width, height);
        }
        this.character = this.level.getObjectByName("MainCharacter");
        this.characterInterface = new CharacterInterface(this, this.level, this.character, this.statistics);
        this.inputManager.setCharacter(this.character);
        this.inputManager.setStatistics(this.statistics);
        this.fog = Fog.fromLevel(this.level);
        // With fog, walking around by hand would uncover the level, so the keyboard is
        // off unless the level explicitly sets `keyboard`.
        const keyboard = this.level.getProperty('keyboard');
        this.inputManager.setEnabled(keyboard === undefined ? !this.fog.isActive() : keyboard !== false);
        this.lastLevelData = levelData;
        console.log("Level successfully loaded.");
        this.currentGameState = GAME_STATE.PLAYING;
        this.remainingTime = 5000;
        return true;
    }

    /** Reloads the most recently loaded level from scratch. */
    async resetLevel() {
        if (!this.lastLevelData) {
            return false;
        }
        await this.loadLevel(this.lastLevelData);
        return true;
    }

    start() {
        if (!this.animationFrameId) {
            this.animationFrameId = requestAnimationFrame(this.gameLoop.bind(this));
            console.log("Game loop started.");
        }
    }

    /**
     * true while a level is being played (not waiting, complete or game over).
     * A falling hero is already lost: the game-over screen follows after the fall
     * animation, but actions are refused from the first moment (B19).
     */
    isRunning() {
        return this.currentGameState === GAME_STATE.PLAYING
            && !(this.character && (this.character.isFalling() || this.character.isDead()));
    }

    getCharacterInterface() {
        return this.characterInterface;
    }

    isComplete() {
        return this.level.isComplete();
    }

    gameLoop(currentTime) {
        const deltaTimeMs = currentTime - this.lastFrameTimeMs;
        this.lastFrameTimeMs = currentTime;
        this.accumulatedTime += deltaTimeMs;

        while (this.accumulatedTime >= this.FIXED_TIME_STEP) {
            if (this.currentGameState === GAME_STATE.PLAYING)  {
                if (this.level) {
                    this.level.update(this.FIXED_TIME_STEP);
                    this.fog.update(this.FIXED_TIME_STEP);
                    // a level without a hero must not end the game loop for good (bug B23)
                    if (this.character) {
                        this.fog.markPresent(...this.character.currentCell());
                    }
                }
            }
            this.updatesThisSecond++;
            this.accumulatedTime -= this.FIXED_TIME_STEP;
        }

        this.renderer.draw(this.currentGameState, {
            level: this.level,
            statistics: this.statistics,
            remainingTime: this.remainingTime,
            fog: this.fog,
            character: this.character,
        });

        // State transitions are game logic, not rendering, so they stay
        // here rather than in GameRenderer.draw(). Whether the character is
        // dead is decided here too, via which state it transitions into -
        // the renderer never needs the character itself.
        switch (this.currentGameState) {
            case GAME_STATE.PLAYING:
                if (this.character.isDead()) {
                    this.currentGameState = GAME_STATE.GAME_OVER;
                } else if (this.level.isComplete()) {
                    this.currentGameState = GAME_STATE.LEVEL_COMPLETE;
                }
                break;
            case GAME_STATE.GAME_OVER:
            case GAME_STATE.LEVEL_COMPLETE:
                this.remainingTime -= deltaTimeMs;
                if (this.remainingTime <= 0) {
                    this.currentGameState = GAME_STATE.WAITING_FOR_LEVEL;
                }
                break;
        }

        this.framesThisSecond++;
        this.inputManager.update(deltaTimeMs, this.level);
        this.animationFrameId = requestAnimationFrame(this.gameLoop.bind(this));
    }
}
