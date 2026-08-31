import { Level } from './level.js';
import { KeyBoardInput } from './input.js';
import { CharacterInterface } from './character.js';
import { Statistics } from './statistics.js';

export const GAME_WIDTH = 480;
export const GAME_HEIGHT = 320;
const FONT_SIZE = 12;

export class Game {
    static GAME_STATE = {
        WAITING_FOR_LEVEL: "WAITING",
        PLAYING: "PLAYING",
        LEVEL_COMPLETE: "LEVEL_COMPLETE"
    };

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
        this.entryScreenImage = null;
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.inputManager = new KeyBoardInput();
        this.currentGameState = Game.GAME_STATE.WAITING_FOR_LEVEL;
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
        this.currentGameState = Game.GAME_STATE.PLAYING;
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
            this.entryScreenImage = new Image();
            this.entryScreenImage.src = this.pathPrefix + 'assets/images/dungeon_coder.png'; // Replace with your image URL or path
            this.entryScreenImage.onload = () => {
            };
            this.entryScreenImage.onerror = () => {
                console.error("Error loading image.");
            };

        if (!this.animationFrameId) {
            this.animationFrameId = requestAnimationFrame(this.gameLoop.bind(this));
            console.log("Game loop started.");
        }
    }

    drawDarkOverlay(ctx, canvasWidth, canvasHeight) {
        const opacity = 1 - this.level.getBrightness();
        ctx.fillStyle = `rgba(0, 0, 0, ${opacity})`;
        ctx.fillRect(0, 0, canvasWidth, canvasHeight);
    }

    getCharacterInterface() {
        return this.characterInterface;
    }

    isComplete() {
        return this.level.isComplete();
    }

    drawMultilineText(ctx, text, x, y, lineHeight) {
        const lines = text.split('\n');
        let currentY = y - (lines.length - 1) * lineHeight / 2; // Center the whole block

        lines.forEach((line) => {
            ctx.fillText(line, x, currentY);
            currentY += lineHeight;
        });
    }

    gameLoop(currentTime) {
        const deltaTimeMs = currentTime - this.lastFrameTimeMs;
        this.lastFrameTimeMs = currentTime;
        this.accumulatedTime += deltaTimeMs;

        while (this.accumulatedTime >= this.FIXED_TIME_STEP) {
            if (this.currentGameState === Game.GAME_STATE.PLAYING)  {
                if (this.level) {
                    this.level.update(this.FIXED_TIME_STEP);
                }
            }
            this.updatesThisSecond++;
            this.accumulatedTime -= this.FIXED_TIME_STEP;
        }

        const centerX = GAME_WIDTH / 2;
        const centerY = GAME_HEIGHT / 2;
        switch(this.currentGameState) {
            case Game.GAME_STATE.WAITING_FOR_LEVEL:
                this.ctx.drawImage(this.entryScreenImage, 0, 0, GAME_WIDTH, GAME_HEIGHT);
                this.ctx.fillStyle = 'black';
                this.ctx.fillRect(10, GAME_HEIGHT- 30, GAME_WIDTH -20, 20);

                this.ctx.fillStyle = 'green';
                this.ctx.font = `${FONT_SIZE}px Arial`;
                this.ctx.textAlign = 'center';
                this.ctx.textBaseline = 'middle';
                this.ctx.fillText('Use the Python API to connect and load a level!', centerX, GAME_HEIGHT - 20);
                break;
            case Game.GAME_STATE.PLAYING:
                this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
                this.level.draw(this.ctx);
                this.drawDarkOverlay(this.ctx, this.canvas.width, this.canvas.height);
                if (this.level.isComplete() || this.character.isDead()) {
                    this.currentGameState =  Game.GAME_STATE.LEVEL_COMPLETE;
                }
                break;
            case Game.GAME_STATE.LEVEL_COMPLETE:
                this.ctx.globalAlpha = 0.7;
                this.ctx.fillStyle = 'black';
                this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
                this.ctx.globalAlpha = 1.0;
                let text = ""
                let color = ""

                if (this.character.isDead()) {
                    color = 'red';
                    text = `Game Over! Continue in ${Math.ceil(this.remainingTime / 1000)}s.`
                } else {
                    text = `Good job! Level Complete!\n\n`;
                    text += `**Level Statistics**\n`;
                    text += `Moves: ${this.statistics.number_of_moves}\n`;
                    text += `Turns: ${this.statistics.number_of_turns}\n\n`;
                    text += `Continue in ${Math.ceil(this.remainingTime / 1000)}s.`;
                    color = 'green';
                }

                this.ctx.fillStyle = color;
                this.ctx.font = `${FONT_SIZE}px Arial`;
                this.ctx.textAlign = 'center';
                this.ctx.textBaseline = 'middle';

                this.drawMultilineText(this.ctx, text, centerX, centerY, FONT_SIZE * 1.2);

                this.remainingTime -= deltaTimeMs;
                if (this.remainingTime <= 0) {
                    this.currentGameState = Game.GAME_STATE.WAITING_FOR_LEVEL;
                }
                break;
        }

        this.framesThisSecond++;
        this.inputManager.update(deltaTimeMs, this.level);
        this.animationFrameId = requestAnimationFrame(this.gameLoop.bind(this));
    }
}
