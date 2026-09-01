import { TILE_SIZE } from './tiles.js';
import { GameObject } from './game-objects.js';

export class Character extends GameObject {
    static STATES = ["walking", "standing"];
    static DIRECTIONS = ["south", "east", "north", "west"];

    static generateCombinedStrings(array1, array2) {
        const combined = [];
        for (var i = 0; i <= 15; i++) {
            for (const item1 of array1) {
                for (const item2 of array2) {
                    combined.push(`${item1}_${item2}_${i}`);
                }
            }
        }
        return combined;
    }

    getDirection() {
        const parts = this.state.split('_');
        return parts[1];
    }

    getState() {
        const parts = this.state.split('_');
        return parts[0];
    }

    /**
     * @param {boolean} debugDraw When true, rendering/character-renderer.js
     *   also draws a debug overlay (bounding box, anchor point, facing-tile
     *   marker). Off by default - flip it at construction time when
     *   debugging positioning.
     */
    constructor(objectDescription, tileFactory, _objectType, debugDraw = false) {
        const all_states = Character.generateCombinedStrings(Character.STATES, Character.DIRECTIONS);
        super(objectDescription, tileFactory, Character.name, all_states);
        // Movement Properties
        this.targetX = this.x;        // Target pixel x-coordinate for current movement
        this.targetY = this.y;        // Target pixel y-coordinate for current movement
        this.movementProgress = 0;    // 0.0 to 1.0, progress along the current tile move
        this.moveDuration = 1000 / 2; // Duration in ms to move one tile
        this.setName("Alina");
        this.setTypeNumber(7);
        this.isCharacterDead = false;
        this.pace_factor = 1.0;

        this.isCharacterFalling = false;
        this.angle = 0;
        this.scaling_factor = 1.0;
        this.fallDuration = 0;
        this.MAX_FALL_TIME_MS = 3000;
        this.ROTATION_PER_SECOND = 6;
        this.SHRINK_RATE_PER_SECOND = 0.6;
        this.inventory = [] // TODO: Add items essential to survive: Towel, Baby Wipes and Tissues
        this.debugDraw = debugDraw;
    }

    setName(name) {
        this.heroName = name;
        return true;
    }

    setTypeNumber(typeNumber) {
        var success = true;
        if (typeNumber > 0 && typeNumber <= 15) {
            this.typeNumber = typeNumber;
            this.setStateAndDirection(this.getState(), this.getDirection());
        } else {
            console.log("Error: type number is out of range. It must be a value from 0 to 15.");
            success = false;
        }
        return success;
    }

    setPace(factor) {
        this.pace_factor = factor;
        return true;
    }

    isMoving() {
        return this.getState() === "walking";
    }

    isFacingNorth() {
        return this.getDirection() === "north";
    }

    isFalling() {
        return this.isCharacterFalling;
    }

    turnLeft() {
        const direction = this.getDirection();
        const state = this.getState();

        if (this.isMoving()) {
            return false;
        }

        const nextDirectionMap = {
            "north": "west",
            "west": "south",
            "south": "east",
            "east": "north"
        };
        const newDirection = nextDirectionMap[direction];

        this.setStateAndDirection(state, newDirection)

        return true;
    }

    getPositionInDirection(direction, center = false) {
        let newTargetX = this.x;
        let newTargetY = this.y;

        let centerOffset = center ? TILE_SIZE / 2 : 0;

        switch (direction) {
            case "north":
                newTargetX += centerOffset;
                newTargetY -= (TILE_SIZE + centerOffset);
                break;
            case "south":
                newTargetX += centerOffset;
                newTargetY += TILE_SIZE - centerOffset;
                break;
            case "west":
                newTargetX -= TILE_SIZE - centerOffset;
                newTargetY += -centerOffset;
                break;
            case "east":
                newTargetX += TILE_SIZE + centerOffset;
                newTargetY -= centerOffset;
                break;
        }

        //console.log(`Current position: ("${this.x}", "${this.y}"). Direction: "${direction}". New position: ("${newTargetX}", "${newTargetY}").`)

        return [newTargetX, newTargetY];
    }

    isCollisionInFront(level, newDirection = this.getDirection()) {
        const newTargetXY = this.getPositionInDirection(newDirection, true);
        return level.isCollision(newTargetXY[0], newTargetXY[1]);
    }

    isInDirection(level, direction, name) {
        const newTargetXY = this.getPositionInDirection(direction, true);
        const objects = level.getObjectsAtPosition(newTargetXY[0], newTargetXY[1]);
        if (Array.isArray(objects) && objects.length != 0) {
            for (const object of objects) {
                if (object) {
                    if (object.type === name) {
                        return true;
                    }
                }
            }
        }

        const tiles = level.getTilesAtPosition(newTargetXY[0], newTargetXY[1]);
        for(const tile of tiles) {
            if (tile) {
                if (tile.type === name) {
                    return true;
                }
            }
        }

        return false;
    }

    isInFront(level, name) {
        return this.isInDirection(level, this.getDirection(), name);
    }

    isDead() {
        return this.isCharacterDead;
    }

    getCurrentPosition(centered = true) {
        let current_x = this.x;
        let current_y = this.y;

        if (centered) {
            current_x += TILE_SIZE / 2;
            current_y -= TILE_SIZE / 2;
        }

        return [current_x, current_y];
    }

    getItemsAtCurrentPosition(level) {
        let item_names = []
        const current_position = this.getCurrentPosition();
        const objects =  level.getObjectsAtPosition(current_position[0], current_position[1]);
        for (const object of objects) {
            if (object.type != "Character") {
                item_names.push(object.type);
            }
        }
        return item_names;
    }

    getInventory() {
        let list_of_names = []
        for (const item of this.inventory) {
            list_of_names.push(item.type);
        }
        return list_of_names;
    }

    pickup(level, name) {
        const current_position = this.getCurrentPosition();
        const objects =  level.getObjectsAtPosition(current_position[0], current_position[1]);
        for (const object of objects) {
            if (object.type === name) {
                this.inventory.push(object);
                object.x = -100;
                object.y = -100;
                object.visible = false;
                return true;
            }
        }

        return false;
    }

    drop(level, name) {
        for (let i = 0; i < this.inventory.length; i++) {
            const item = this.inventory[i];
            if (item.type === name) {
                item.x = this.x;
                item.y = this.y;
                item.visible = true;
                this.inventory.splice(i, 1);

                return true;
            }
        }

        return false;
    }

    move(newDirection, level) {
        if (this.isMoving()) {
            return false; // Already moving, cannot initiate a new movement
        }

        if (this.isCollisionInFront(level, newDirection)) {
            this.setStateAndDirection("standing", newDirection);
            return false;
        } else {
            const newTargetXY = this.getPositionInDirection(newDirection);

            if (this.isInDirection(level, newDirection, "Abyss")) {
                this.isCharacterFalling = true;
                this.x = newTargetXY[0];
                this.y = newTargetXY[1];
            } else {
                this.targetX = newTargetXY[0];
                this.targetY = newTargetXY[1];
                this.movementProgress = 0;
                this.setStateAndDirection("walking", newDirection);

                // Store the exact pixel coordinates where this current movement starts
                this.currentMoveStartX = this.x;
                this.currentMoveStartY = this.y;
            }

            return true;
        }
    }

    interact(level) {
        const position = this.getPositionInDirection(this.getDirection(), true);
        const objects =  level.getObjectsAtPosition(position[0], position[1]);
        if (Array.isArray(objects) && objects.length != 0) {
            for (const object of objects) {
                if (object) {
                    if (typeof object.interact === 'function') {
                        object.interact(level);
                    } else {
                        console.log(`You cannot interact with the object of class "${object.type}" and ID "${object.id}".`)
                    }
                }
            }
        }
        else {
            console.log(`There is no object in front of the player to interact with.`);
        }
        return false;
    }

    setStateAndDirection(state, direction) {
        if (!Character.STATES.includes(state)) {
            console.warn(`Cannot set state "${state}" for character.`);
            return false;
        }

        if (!Character.DIRECTIONS.includes(direction)) {
            console.warn(`Cannot set direction "${direction}" for character.`);
            return false;
        }

        super.setState(state + "_" + direction + "_" + this.typeNumber);
        return true;
    }

    update(deltaTime) {
        if (this.isFalling()) {
            const dt = deltaTime / 1000;
            this.fallDuration += deltaTime;
            this.angle += this.ROTATION_PER_SECOND * dt;
            this.angle %= (2 * Math.PI);
            this.scaling_factor = Math.max(0.1, this.scaling_factor - (this.SHRINK_RATE_PER_SECOND * dt));

            if (this.fallDuration > this.MAX_FALL_TIME_MS) {
                this.isCharacterDead = true;
            }
        }
        else if (this.isMoving()) {
            this.movementProgress += deltaTime; // Accumulate time for movement
            const progressRatio = Math.min(1, this.movementProgress / (this.moveDuration / this.pace_factor));

            // Interpolate position from the *stored start* position to target tile position
            this.x = this.currentMoveStartX + (this.targetX - this.currentMoveStartX) * progressRatio;
            this.y = this.currentMoveStartY + (this.targetY - this.currentMoveStartY) * progressRatio;

            // Check if movement is complete
            if (progressRatio >= 1) {
                this.movementProgress = 0;
                this.x = this.targetX;
                this.y = this.targetY;
                this.setStateAndDirection("standing", this.getDirection()); // Return to standing state, but keep direction

                // Reset start position for the *next* potential move
                this.currentMoveStartX = this.x;
                this.currentMoveStartY = this.y;
            }
        }

        super.update(deltaTime);
    }
}

export class CharacterInterface {
    constructor(game, level, character, statistics) {
        this.game = game;
        this.level = level;
        this.character = character;
        this.statistics = statistics;
    }

    move() {
        const ret = this.character.move(this.character.getDirection(), this.level);
        if (ret) {
            this.statistics.addMove();
        }
        return ret;
    }

    configure(name, typeNumber) {
        var success = true;
        success = this.character.setName(name);
        success &= this.character.setTypeNumber(typeNumber);
        return success;
    }

    set_pace(factor) {
        return this.character.setPace(factor);
    }

    turnLeft() {
        this.statistics.addTurn();
        return this.character.turnLeft();
    }

    isFacingNorth() {
        return this.character.isFacingNorth();
    }

    isCollisionInFront() {
        return this.character.isCollisionInFront(this.level);
    }

    isAbyssInFront() {
        return this.character.isInFront(this.level, "Abyss");
    }

    isTorchInFront() {
        return this.character.isInFront(this.level, "Torch");
    }

    isSwitchInFront() {
        return this.character.isInFront(this.level, "Switch");
    }

    getInventory() {
        return this.character.getInventory();
    }

    getItemsAtHeroPosition() {

        return this.character.getItemsAtCurrentPosition(this.level);
    }

    pickup(name) {
        this.character.pickup(this.level, name);
    }

    drop(name) {
        this.character.drop(this.level, name);
    }

    isMoving() {
        return this.character.isMoving();
    }

    interact() {
        return this.character.interact(this.level);
    }

    isAtGoal() {
        return this.level.isComplete();
    }
}
