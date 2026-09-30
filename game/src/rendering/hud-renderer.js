import { FONT_SIZE, REFERENCE_WIDTH, REFERENCE_HEIGHT } from './constants.js';
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
        this.setViewSize(canvasWidth, canvasHeight);

        // Fire-and-forget, same as the original Game.start(): the game
        // loop doesn't wait for these to load - drawImage() on an
        // incomplete Image is a silent no-op in every browser.
        this.entryScreenImage = imageFromPacks('images/dungeon_coder.png', pathPrefix);

        this.gameOverImage = imageFromPacks('images/game_over.jpeg', pathPrefix);

        this.dungeonCompleteImage = imageFromPacks('images/dungeon_complete.jpeg', pathPrefix);
        this.pathPrefix = pathPrefix;
        this.worldImages = new Map();
    }

    /**
     * The end-screen picture of a level's world (map property `world`, e.g. "station"):
     * images/welt_<world>_<kind>.png from the asset packs. Falls back to `fallback`
     * while it isn't loaded, or when the world has no such picture.
     */
    worldImage(world, kind, fallback) {
        if (!world) {
            return fallback;
        }
        const key = `${world}_${kind}`;
        if (!this.worldImages.has(key)) {
            this.worldImages.set(key, imageFromPacks(`images/welt_${key}.png`, this.pathPrefix));
        }
        const image = this.worldImages.get(key);
        return image.complete && image.naturalWidth > 0 ? image : fallback;
    }

    /**
     * The view's size in game pixels. Texts, bars and the screen pictures are laid out
     * for the reference view (REFERENCE_WIDTH x REFERENCE_HEIGHT) and scale with the
     * view; the pictures keep their shape and are centred.
     */
    setViewSize(width, height) {
        this.canvasWidth = width;
        this.canvasHeight = height;
        this.scale = Math.min(width / REFERENCE_WIDTH, height / REFERENCE_HEIGHT);
    }

    /** Font for HUD texts, scaled with the view. */
    font() {
        return `${FONT_SIZE * this.scale}px Arial`;
    }

    /** A full-screen picture: black background, the picture centred in its reference shape. */
    drawScreenImage(image) {
        const ctx = this.ctx;
        const width = REFERENCE_WIDTH * this.scale, height = REFERENCE_HEIGHT * this.scale;
        ctx.fillStyle = 'black';
        ctx.fillRect(0, 0, this.canvasWidth, this.canvasHeight);
        ctx.drawImage(image, (this.canvasWidth - width) / 2, (this.canvasHeight - height) / 2, width, height);
    }

    /** Draws the "waiting for a level to be loaded" entry screen. */
    drawWaitingScreen() {
        const ctx = this.ctx;
        const s = this.scale;
        this.drawScreenImage(this.entryScreenImage);
        ctx.fillStyle = 'black';
        ctx.fillRect(10 * s, this.canvasHeight - 30 * s, this.canvasWidth - 20 * s, 20 * s);

        ctx.fillStyle = 'green';
        ctx.font = this.font();
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('Use the Python API to connect and load a level!', this.canvasWidth / 2, this.canvasHeight - 20 * s);
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
        const s = this.scale;
        ctx.fillStyle = 'rgba(0, 0, 0, 0.75)';
        ctx.fillRect(10 * s, 8 * s, this.canvasWidth - 20 * s, 22 * s);
        ctx.fillStyle = '#ffcc00';
        ctx.font = this.font();
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(`Goal reached, but still missing: ${missing.join(', ')}`, this.canvasWidth / 2, 19 * s);
    }

    /** Draws the "Game Over" screen shown when the character has died. */
    drawGameOverScreen(remainingTime, world) {
        const ctx = this.ctx;
        this.drawScreenImage(this.worldImage(world, 'halt', this.gameOverImage));

        ctx.fillStyle = 'red';
        ctx.font = this.font();
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';

        const text = `Continue in ${Math.ceil(remainingTime / 1000)}s.`;
        this.drawMultilineText(text, this.canvasWidth / 2, this.canvasHeight / 2, FONT_SIZE * 1.2 * this.scale);
    }

    /** Draws the "Level Complete" summary screen shown when a level is finished successfully. */
    drawLevelCompleteScreen(statistics, remainingTime, world) {
        const ctx = this.ctx;
        this.drawScreenImage(this.worldImage(world, 'geschafft', this.dungeonCompleteImage));

        ctx.fillStyle = 'green';
        ctx.font = this.font();
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';

        let text = `\nMoves: ${statistics.number_of_moves}\n`;
        text += `Turns: ${statistics.number_of_turns}\n`;
        if (statistics.number_of_keyboard_moves > 0) {
            text += `Keyboard moves: ${statistics.number_of_keyboard_moves}\n`;
        }
        text += `Continue in ${Math.ceil(remainingTime / 1000)}s.`;

        this.drawMultilineText(text, this.canvasWidth / 2, this.canvasHeight / 2, FONT_SIZE * 1.2 * this.scale);
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
