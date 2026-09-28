export class Statistics {
    constructor() {
        this.reset();
    }

    reset() {
        this.number_of_moves = 0;
        this.number_of_turns = 0;
        this.number_of_keyboard_moves = 0;
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
}
