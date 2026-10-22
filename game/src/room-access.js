import { COMMANDS } from './commands.js';

/**
 * Who may do what when the game is open to the room (a live game: the dev server with DC_HOST, or
 * the extension after "Dungeon Coder: Open the game to the room"). Shared by both servers, so the
 * rules are the same. Without `exposed` nothing is refused.
 *
 * - The referee's commands (load, reset, start, end) come only from the game's own computer.
 * - A hero belongs to the computer that joined it with the team's code; requests for it from
 *   another address are refused, as are requests for a hero nobody joined yet.
 * - Loading a level frees every hero again.
 */
export class RoomAccess {
    static REFEREE = new Set([COMMANDS.LOAD_LEVEL, COMMANDS.RESET_LEVEL, COMMANDS.START_GAME, COMMANDS.END_GAME]);
    static OPEN = new Set([COMMANDS.JOIN, COMMANDS.GET_VERSION]);

    constructor(exposed = false) {
        this.exposed = exposed;
        this.owners = new Map();            // hero index -> the address that joined it
    }

    static isLoopback(address) {
        return ['127.0.0.1', '::1', '::ffff:127.0.0.1'].includes(String(address));
    }

    /** The reason to refuse this request, or null. `params.hero` is the hero index (0 without one). */
    refusal(command, address, params) {
        if (!this.exposed || RoomAccess.isLoopback(address)) {
            return null;
        }
        if (RoomAccess.REFEREE.has(command)) {
            return 'Only the referee (on the game\'s own computer) may load levels and start or end the game.';
        }
        if (RoomAccess.OPEN.has(command)) {
            return null;
        }
        const hero = params?.hero ?? 0;
        if (!this.owners.has(hero)) {
            return `Join the game first: Game.join("<your team code>") (hero ${hero} has no team yet).`;
        }
        if (this.owners.get(hero) !== address) {
            return `Hero ${hero} belongs to another team (it was joined from another computer).`;
        }
        return null;
    }

    /** After the game answered a command: remember who joined, forget everyone on a new level. */
    answered(command, address, response) {
        if (!response?.success) {
            return;
        }
        if (command === COMMANDS.JOIN && !RoomAccess.isLoopback(address)) {
            this.owners.set(response.result.hero, address);
        }
        if (command === COMMANDS.LOAD_LEVEL || command === COMMANDS.RESET_LEVEL) {
            this.owners.clear();
        }
    }
}
