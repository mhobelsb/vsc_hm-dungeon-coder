import { COMMANDS } from './commands.js';

/**
 * The program's last calls, next to the game (DC-T1j): `move()  ✓`, `move()  ✗ blocked`,
 * `is_switch_in_front()  → False`. Connects what the code asked with what happened on screen.
 * An HTML list over the page's corner, not drawn on the canvas. Off unless the level switches it on
 * with the map property `show_calls: true` (each level load decides anew); L shows or hides it.
 */
export class CallLog {
    static LENGTH = 10;
    static ACTIONS = new Set([COMMANDS.MOVE, COMMANDS.TURN_LEFT, COMMANDS.INTERACT, COMMANDS.PICKUP, COMMANDS.DROP,
        COMMANDS.CONFIGURE, COMMANDS.SET_PACE, COMMANDS.RESET_LEVEL]);
    static ARGUMENTS = { pickup: ['name'], drop: ['name'], peek_item_value: ['distance'], set_pace: ['factor'],
        configure: ['name', 'typeNumber'] };

    constructor(element) {
        this.element = element;
        this.entries = [];
    }

    /** Python's way of writing a value: True, None, ['Sweets'], 'north'. */
    static python(value) {
        if (value === true) {
            return 'True';
        }
        if (value === false) {
            return 'False';
        }
        if (value === null || value === undefined) {
            return 'None';
        }
        if (typeof value === 'string') {
            return `'${value}'`;
        }
        if (Array.isArray(value)) {
            return `[${value.map(CallLog.python).join(', ')}]`;
        }
        return String(value);
    }

    /** One line for a call and its answer, or null for calls that aren't the program's own. */
    static describe(method, params, payload) {
        if (method === COMMANDS.IS_MOVING || method === COMMANDS.GET_STATISTICS) {
            return null;
        }
        if (method === COMMANDS.LOAD_LEVEL) {
            return payload.result?.success ? '— level loaded —' : '— level refused —';
        }
        const args = (CallLog.ARGUMENTS[method] ?? []).filter(k => params && k in params)
            .map(k => CallLog.python(params[k])).join(', ');
        const who = params?.hero ? `heroes[${params.hero}]: ` : '';      // as in Python: game.get_heroes()[1]
        const call = `${who}${method}(${args})`;
        if (payload.error) {
            return `${call}  ✗ error`;
        }
        const { success, result, message } = payload.result ?? {};
        if (CallLog.ACTIONS.has(method)) {
            if (success) {
                return `${call}  ✓`;
            }
            const reason = /blocked/i.test(message ?? '') ? 'blocked' : /over/i.test(message ?? '') ? 'level over'
                : /moves left/i.test(message ?? '') ? 'no moves left' : '';
            return `${call}  ✗ ${reason}`.trimEnd();
        }
        return success === false && result === null && message ? `${call}  ✗ ${message}` : `${call}  → ${CallLog.python(result)}`;
    }

    add(method, params, payload) {
        if (method === COMMANDS.LOAD_LEVEL) {
            this.entries = [];
        }
        const line = CallLog.describe(method, params, payload);
        if (line === null) {
            return;
        }
        this.entries.push(line);
        this.entries = this.entries.slice(-CallLog.LENGTH);
        this.render();
    }

    render() {
        if (!this.element) {
            return;
        }
        this.element.textContent = this.entries.join('\n');
        this.element.dataset.empty = this.entries.length === 0 ? 'true' : 'false';
    }

    /** At a level load: shown only if the level says `show_calls: true`. */
    showFor(level) {
        this.setVisible(level.getBooleanProperty('show_calls', false));
    }

    setVisible(visible) {
        if (this.element) {
            this.element.hidden = !visible;
        }
    }

    toggle() {
        if (this.element) {
            this.element.hidden = !this.element.hidden;
        }
    }
}
