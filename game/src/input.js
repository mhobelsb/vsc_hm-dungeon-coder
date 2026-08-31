export class KeyBoardInput {
    constructor() {
        this.keys = {
            w: false,
            a: false,
            s: false,
            d: false,
            i: false,
            space: false
        };
        this.lastMoveAttemptKey = null;
        this.isInteracting = false;

        this.character = null;
        this.setupEventListeners();
    }

    setCharacter(character) {
        this.character = character;
    }

    reset() {
        this.keys.w = false;
        this.keys.a = false;
        this.keys.s = false;
        this.keys.d = false;
        this.keys.space = false;
        this.isInteracting = false;
        this.lastMoveAttemptKey = null;
        this.character = null;
    }

    setupEventListeners() {
        window.addEventListener('keydown', (e) => {
            switch (e.key.toLowerCase()) {
                case 'w':
                    this.keys.w = true;
                    break;
                case 'a':
                    this.keys.a = true;
                    break;
                case 's':
                    this.keys.s = true;
                    break;
                case 'd':
                    this.keys.d = true;
                    break;
                case 'i':
                    // We only want to detect the *initial* press for toggles
                    // The consuming class (Game) will handle the debounce
                    this.keys.i = true;
                    break;
                case ' ':
                    this.keys.space = true;
                    break;
            }
        });

        window.addEventListener('keyup', (e) => {
            switch (e.key.toLowerCase()) {
                case 'w':
                    this.keys.w = false;
                    break;
                case 'a':
                    this.keys.a = false;
                    break;
                case 's':
                    this.keys.s = false;
                    break;
                case 'd':
                    this.keys.d = false;
                    break;
                case 'i':
                    this.keys.i = false;
                    break;
                case ' ':
                    this.keys.space = false;
                    break;
            }
        });
    }

    /**
     * Returns the current state of all monitored keys.
     * @returns {object} An object where keys are key codes and values are boolean (true if pressed).
     */
    getKeys() {
        return this.keys;
    }

    update(deltaTime, level) {
        if (!this.character) {
            return;
        }

        // Only try to initiate a new move if the character is NOT currently moving
        if (!this.character.isMoving()) {
            let directionToMove = null;
            let currentPressedKey = null; // To prevent multiple simultaneous moves

            if (this.keys.w) {
                directionToMove = "north";
                currentPressedKey = 'w';
            } else if (this.keys.a) {
                directionToMove = "west";
                currentPressedKey = 'a';
            } else if (this.keys.s) {
                directionToMove = "south";
                currentPressedKey = 's';
            } else if (this.keys.d) {
                directionToMove = "east";
                currentPressedKey = 'd';
            }

            if (this.keys.space && !this.isInteracting) {
                this.isInteracting = true;
            }
            if (!this.keys.space && this.isInteracting) {
                this.character.interact(level);
                this.isInteracting = false;
            }

            // Only attempt to move if a *new* direction key is pressed
            // or if a direction key is held down but it's a new press since last frame
            // AND we're not currently moving
            if (directionToMove && currentPressedKey !== this.lastMoveAttemptKey) {
                this.character.move(directionToMove, level);
            }
            this.lastMoveAttemptKey = currentPressedKey; // Remember which key was active
        } else {
             // If character IS moving, we don't allow new move inputs until it's done.
             // This line ensures `lastMoveAttemptKey` is cleared once the key is released
             // while the character is still moving, allowing a new move to be queued up.
             if (!this.keys.w && !this.keys.a && !this.keys.s && !this.keys.d) {
                 this.lastMoveAttemptKey = null;
             }
        }
    }
}
