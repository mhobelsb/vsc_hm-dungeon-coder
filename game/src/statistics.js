export class Statistics {
    constructor() {
        this.reset();
    }

    reset() {
        this.number_of_moves = 0;
        this.number_of_turns = 0;
        this.number_of_keyboard_moves = 0;
        this.number_of_bumps = 0;
        this.number_of_interactions = 0;
        this.number_of_pickups = 0;
        this.number_of_drops = 0;
        this.number_of_sensor_calls = 0;
    }

    addMove() {
        this.number_of_moves += 1;
    }

    addTurn() {
        this.number_of_turns += 1;
    }

    /** Moves made by hand (WASD), kept apart from the scripted ones. */
    addKeyboardMove() {
        this.number_of_keyboard_moves += 1;
    }

    /** A move() that was blocked: the cost of walking into walls. */
    addBump() {
        this.number_of_bumps += 1;
    }

    addInteraction() {
        this.number_of_interactions += 1;
    }

    addPickup() {
        this.number_of_pickups += 1;
    }

    addDrop() {
        this.number_of_drops += 1;
    }

    /** A sensor call: is_*_in_front, is_facing_north, is_at_goal, get_items_at_position. */
    addSensorCall() {
        this.number_of_sensor_calls += 1;
    }

    /** The counters as sent to Python (see Statistics in api/openapi.yaml). */
    snapshot() {
        return {
            moves: this.number_of_moves,
            turns: this.number_of_turns,
            bumps: this.number_of_bumps,
            keyboard_moves: this.number_of_keyboard_moves,
            interactions: this.number_of_interactions,
            pickups: this.number_of_pickups,
            drops: this.number_of_drops,
            sensor_calls: this.number_of_sensor_calls,
        };
    }
}
