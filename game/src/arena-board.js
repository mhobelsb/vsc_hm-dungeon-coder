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

    /** The board's words: map property `lang` ("de" or "en", default "en"). */
    static TEXT = {
        en: { title: 'Dungeon Coder: Arena', over: 'Round over', waiting: 'Waiting for the start (Space)', running: 'Running',
            ready: (n, m) => `Ready: ${n} of ${m}`, team: 'Team', state: 'State', value: 'Value', moves: 'Moves',
            out: 'out', exit: 'at the exit', playing: 'playing', joined: 'ready', missing: 'not joined',
            room: (c, t, p) => `The room: ${c} of ${t} (${p} %)`, goal: '80 %', round: 'round', keys: 'Space: start · E: end the round' },
        de: { title: 'Dungeon Coder: Arena', over: 'Runde beendet', waiting: 'Warten auf den Start (Leertaste)', running: 'Läuft',
            ready: (n, m) => `Bereit: ${n} von ${m}`, team: 'Team', state: 'Stand', value: 'Wert', moves: 'Züge',
            out: 'aus', exit: 'am Ausgang', playing: 'läuft', joined: 'bereit', missing: 'fehlt noch',
            room: (c, t, p) => `Der Raum: ${c} von ${t} (${p} %)`, goal: '80 %', round: 'Runde', keys: 'Leertaste: Start · E: Runde beenden' },
    };

    /** The panel's content from the game's state. */
    update() {
        const game = this.game;
        if (this.element.hidden || !game.level || !game.arena) {
            return;
        }
        this.element.innerHTML = ArenaBoard.render(game);
    }

    /** The panel's HTML for a game (also used by the unit tests). */
    static render(game) {
        const level = game.level;
        const text = ArenaBoard.TEXT[String(level.getProperty('lang') ?? 'en')] ?? ArenaBoard.TEXT.en;
        const names = game.arenaDisplayNames ? game.arenaDisplayNames() : level.arenaNames();
        const heroes = game.characterInterfaces;
        const joined = heroes.map((_, i) => Boolean(game.arenaJoined?.[i]));
        const readyCount = joined.filter(j => j).length;
        let phase;
        if (game.arenaOver) {
            phase = text.over;
        } else if (!game.arenaStarted) {
            phase = `${text.ready(readyCount, heroes.length)} · ${text.waiting}`;
        } else {
            phase = `${text.running} ${ArenaBoard.clock(game.arenaSeconds() ?? 0)}`;
        }
        const rows = heroes.map((hero, i) => {
            const out = hero.isOut();
            const atGoal = !out && level.isOnGoal(hero.character);
            let state;
            if (out) {
                state = text.out;
            } else if (atGoal) {
                state = text.exit;
            } else if (game.arenaStarted) {
                state = text.playing;
            } else {
                state = joined[i] ? text.joined : text.missing;
            }
            const movesLeft = hero.movesLeft();
            const waiting = !game.arenaStarted && !joined[i];
            return `<tr class="${out || waiting ? 'out' : ''}">`
                + `<td><span class="swatch" style="background:${HudRenderer.teamColour(i)}"></span>${ArenaBoard.escape(names[i] ?? i + 1)}</td>`
                + `<td>${state}</td>`
                + `<td class="num">${hero.carriedValue()}</td>`
                + `<td class="num">${movesLeft === null ? '' : movesLeft}</td></tr>`;
        }).join('');
        const carried = heroes.reduce((sum, hero) => sum + hero.carriedValue(), 0);
        const total = game.arenaValueAtStart;
        const percent = total > 0 ? Math.round(100 * carried / total) : 0;
        const bar = `<div class="bar" role="img" aria-label="${percent} %"><i style="width:${Math.min(100, percent)}%"></i><b style="left:80%"></b></div>`;
        const round = game.arenaRoundLabel ? ` · ${text.round} ${game.arenaRoundLabel}` : '';
        return `<h2>${text.title}${round}</h2>`
            + `<div class="phase">${ArenaBoard.escape(phase)}</div>`
            + `<table><tr><th>${text.team}</th><th>${text.state}</th><th>${text.value}</th><th>${text.moves}</th></tr>${rows}</table>`
            + `<div class="room">${text.room(carried, total, percent)}${bar}</div>`
            + `<div class="keys">${text.keys}${window.DcRounds > 0 ? (text.round === 'Runde' ? ' · N: nächste Runde · R: noch einmal' : ' · N: next round · R: again') : ''}</div>`;
    }
}
