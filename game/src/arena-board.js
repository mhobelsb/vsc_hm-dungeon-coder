import { HudRenderer } from './rendering/hud-renderer.js';

/**
 * The scoreboard of a live game (map property `arena`): an HTML panel beside the canvas, for the beamer.
 * One row per team: colour, name, state (waiting, playing, at the exit, out), the value it carries,
 * its moves left; above it the phase (waiting for teams, running with a clock, round over); below it
 * what the room collected together. Hidden unless an arena is loaded. Reads the game's state a few
 * times per second; it never changes it (the referee's keys live in script.js).
 */
export class ArenaBoard {
    static INTERVAL_MS = 250;

    constructor(element, game, onToggle = null) {
        this.element = element;
        this.game = game;
        this.onToggle = onToggle;
        this.timer = null;
    }

    /** Called after every level load: show the panel for an arena, hide it otherwise. */
    showFor(level) {
        const show = Boolean(level && level.isArena());
        if (this.element.hidden === !show) {
            return;
        }
        this.element.hidden = !show;
        if (this.onToggle) {
            this.onToggle();
        }
    }

    start() {
        if (!this.timer) {
            this.timer = setInterval(() => this.update(), ArenaBoard.INTERVAL_MS);
        }
    }

    static escape(text) {
        return String(text).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
    }

    static clock(seconds) {
        const s = Math.max(0, Math.floor(seconds));
        return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
    }

    /** The panel's content from the game's state. */
    update() {
        const game = this.game;
        if (this.element.hidden || !game.level || !game.arena) {
            return;
        }
        const level = game.level;
        const names = level.arenaNames();
        const heroes = game.characterInterfaces;
        let phase;
        if (game.arenaOver) {
            phase = 'Round over';
        } else if (!game.arenaStarted) {
            phase = 'Waiting for the start (Space)';
        } else {
            phase = `Running ${ArenaBoard.clock(game.arenaSeconds() ?? 0)}`;
        }
        const rows = heroes.map((hero, i) => {
            const out = hero.isOut();
            const atGoal = !out && level.isOnGoal(hero.character);
            const state = out ? 'out' : (atGoal ? 'at the exit' : (game.arenaStarted ? 'playing' : 'ready'));
            const movesLeft = hero.movesLeft();
            return `<tr class="${out ? 'out' : ''}">`
                + `<td><span class="swatch" style="background:${HudRenderer.teamColour(i)}"></span>${ArenaBoard.escape(names[i] ?? i + 1)}</td>`
                + `<td>${state}</td>`
                + `<td class="num">${hero.carriedValue()}</td>`
                + `<td class="num">${movesLeft === null ? '' : movesLeft}</td></tr>`;
        }).join('');
        const carried = heroes.reduce((sum, hero) => sum + hero.carriedValue(), 0);
        const total = game.arenaValueAtStart;
        const percent = total > 0 ? Math.round(100 * carried / total) : 0;
        this.element.innerHTML = `<h2>Dungeon Coder: Arena</h2>`
            + `<div class="phase">${ArenaBoard.escape(phase)}</div>`
            + `<table><tr><th>Team</th><th>State</th><th>Value</th><th>Moves</th></tr>${rows}</table>`
            + `<div class="room">The room: ${carried} of ${total} (${percent} %)</div>`
            + `<div class="keys">Space: start · E: end the round</div>`;
    }
}
