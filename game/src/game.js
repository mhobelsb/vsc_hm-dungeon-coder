import { Level } from './level.js';
import { KeyBoardInput } from './input.js';
import { CharacterInterface } from './character.js';
import { Statistics } from './statistics.js';
import { createRenderer } from './rendering/create-renderer.js';
import { GAME_STATE } from './game-state.js';

export const GAME_WIDTH = 480;
export const GAME_HEIGHT = 320;

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
        this.renderer = createRenderer(this.ctx, canvas.width, canvas.height, pathPrefix);
        this.inputManager = new KeyBoardInput();
        this.currentGameState = GAME_STATE.WAITING_FOR_LEVEL;
        this.remainingTime = 5000;
        this.character = null;
        this.characterInterface = null;
        this.pathPrefix = pathPrefix;
        this.statistics = new Statistics();
        this.lastLevelData = null;
    }

    async loadLevel(levelData) {
        this.statistics.reset();
        this.level = await Level.create(levelData, this.pathPrefix);
        this.character = this.level.getObjectByName("MainCharacter");
        this.characterInterface = new CharacterInterface(this, this.level, this.character, this.statistics);
        this.inputManager.setCharacter(this.character);
        this.lastLevelData = levelData;
        console.log("Level successfully loaded.");
        this.currentGameState = GAME_STATE.PLAYING;
        this.remainingTime = 5000;
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
                }
            }
            this.updatesThisSecond++;
            this.accumulatedTime -= this.FIXED_TIME_STEP;
        }

        this.renderer.draw(this.currentGameState, {
            level: this.level,
            statistics: this.statistics,
            remainingTime: this.remainingTime,
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
