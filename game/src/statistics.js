export class Statistics {
    constructor() {
        this.reset();
    }

    reset() {
        this.number_of_moves = 0;
        this.number_of_turns = 0;
    }

    addMove() {
        this.number_of_moves += 1;
    }

    addTurn() {
        this.number_of_turns += 1;
    }
}
