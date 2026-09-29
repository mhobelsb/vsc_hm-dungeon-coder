import { FONT_SIZE } from './constants.js';
import { imageFromPacks } from '../assets.js';

/**
 * Screen-level overlays: the entry screen, the level-darkness overlay, and
 * the two round-end summary screens (game over / level complete).
 * Deliberately knows nothing about how a level's layers/objects get drawn -
 * that's GameRenderer's job to orchestrate via LevelRenderer; HudRenderer
 * only draws things *on top of* whatever the world renderer already put on
 * the canvas. It also doesn't decide *which* round-end screen applies -
 * that's Game's job, expressed via which GAME_STATE it's in.
 */
export class HudRenderer {
    constructor(ctx, canvasWidth, canvasHeight, pathPrefix) {
        this.ctx = ctx;
        this.canvasWidth = canvasWidth;
        this.canvasHeight = canvasHeight;

        // Fire-and-forget, same as the original Game.start(): the game
        // loop doesn't wait for these to load - drawImage() on an
        // incomplete Image is a silent no-op in every browser.
        this.entryScreenImage = imageFromPacks('images/dungeon_coder.png', pathPrefix);

        this.gameOverImage = imageFromPacks('images/game_over.jpeg', pathPrefix);

        this.dungeonCompleteImage = imageFromPacks('images/dungeon_complete.jpeg', pathPrefix);
    }

    /** Draws the "waiting for a level to be loaded" entry screen. */
    drawWaitingScreen() {
        const ctx = this.ctx;
        ctx.drawImage(this.entryScreenImage, 0, 0, this.canvasWidth, this.canvasHeight);
        ctx.fillStyle = 'black';
        ctx.fillRect(10, this.canvasHeight - 30, this.canvasWidth - 20, 20);

        ctx.fillStyle = 'green';
        ctx.font = `${FONT_SIZE}px Arial`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('Use the Python API to connect and load a level!', this.canvasWidth / 2, this.canvasHeight - 20);
    }

    /** Draws a full-screen darkness tint based on the level's current brightness. */
    drawDarkOverlay(level) {
        const ctx = this.ctx;
        const opacity = 1 - level.getBrightness();
        ctx.fillStyle = `rgba(0, 0, 0, ${opacity})`;
        ctx.fillRect(0, 0, this.canvasWidth, this.canvasHeight);
    }

    /** Banner shown while the hero stands on the goal but win conditions are still unmet. */
    drawGoalHint(missing) {
        const ctx = this.ctx;
        ctx.fillStyle = 'rgba(0, 0, 0, 0.75)';
        ctx.fillRect(10, 8, this.canvasWidth - 20, 22);
        ctx.fillStyle = '#ffcc00';
        ctx.font = `${FONT_SIZE}px Arial`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(`Goal reached, but still missing: ${missing.join(', ')}`, this.canvasWidth / 2, 19);
    }

    /** Draws the "Game Over" screen shown when the character has died. */
    drawGameOverScreen(remainingTime) {
        const ctx = this.ctx;
        ctx.drawImage(this.gameOverImage, 0, 0, this.canvasWidth, this.canvasHeight);

        ctx.fillStyle = 'red';
        ctx.font = `${FONT_SIZE}px Arial`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';

        const text = `Continue in ${Math.ceil(remainingTime / 1000)}s.`;
        this.drawMultilineText(text, this.canvasWidth / 2, this.canvasHeight / 2, FONT_SIZE * 1.2);
    }

    /** Draws the "Level Complete" summary screen shown when a level is finished successfully. */
    drawLevelCompleteScreen(statistics, remainingTime) {
        const ctx = this.ctx;
        ctx.drawImage(this.dungeonCompleteImage, 0, 0, this.canvasWidth, this.canvasHeight);

        ctx.fillStyle = 'green';
        ctx.font = `${FONT_SIZE}px Arial`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';

        let text = `\nMoves: ${statistics.number_of_moves}\n`;
        text += `Turns: ${statistics.number_of_turns}\n`;
        if (statistics.number_of_keyboard_moves > 0) {
            text += `Keyboard moves: ${statistics.number_of_keyboard_moves}\n`;
        }
        text += `Continue in ${Math.ceil(remainingTime / 1000)}s.`;

        this.drawMultilineText(text, this.canvasWidth / 2, this.canvasHeight / 2, FONT_SIZE * 1.2);
    }

    drawMultilineText(text, x, y, lineHeight) {
        const ctx = this.ctx;
        const lines = text.split('\n');
        let currentY = y - (lines.length - 1) * lineHeight / 2; // Center the whole block

        lines.forEach((line) => {
            ctx.fillText(line, x, currentY);
            currentY += lineHeight;
        });
    }
}
