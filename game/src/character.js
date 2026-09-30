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
        // Size of one cell in pixels. The level is the source of truth and sets it
        // (setTileSize); until then the hero's own size stands in.
        this.tileWidth = this.width;
        this.tileHeight = this.height;
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

    /** The level's cell size in pixels: one step is one cell. */
    setTileSize(tileWidth, tileHeight) {
        this.tileWidth = tileWidth;
        this.tileHeight = tileHeight;
    }

    setName(name) {
        this.heroName = name;
        return true;
    }

    setTypeNumber(typeNumber) {
        var success = true;
        if (typeNumber >= 0 && typeNumber <= 15) {
            this.typeNumber = typeNumber;
            this.setStateAndDirection(this.getState(), this.getDirection());
        } else {
            console.log("Error: type number is out of range. It must be a value from 0 to 15.");
            success = false;
        }
        return success;
    }

    setPace(factor) {
        // 0 or less would stop the hero forever (step duration / 0).
        if (!(factor > 0)) {
            return false;
        }
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

        const centerOffsetX = center ? this.tileWidth / 2 : 0;
        const centerOffsetY = center ? this.tileHeight / 2 : 0;

        switch (direction) {
            case "north":
                newTargetX += centerOffsetX;
                newTargetY -= (this.tileHeight + centerOffsetY);
                break;
            case "south":
                newTargetX += centerOffsetX;
                newTargetY += this.tileHeight - centerOffsetY;
                break;
            case "west":
                newTargetX -= this.tileWidth - centerOffsetX;
                newTargetY += -centerOffsetY;
                break;
            case "east":
                newTargetX += this.tileWidth + centerOffsetX;
                newTargetY -= centerOffsetY;
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
            current_x += this.tileWidth / 2;
            current_y -= this.tileHeight / 2;
        }

        return [current_x, current_y];
    }

    /** [col, row] of the cell the hero's centre is in (changes halfway through a step). */
    currentCell() {
        const [x, y] = this.getCurrentPosition(true);
        return [Math.floor(x / this.tileWidth), Math.floor(y / this.tileHeight)];
    }

    /** [col, row] of the cell in front of the hero. */
    frontCell() {
        const [x, y] = this.getPositionInDirection(this.getDirection(), true);
        return [Math.floor(x / this.tileWidth), Math.floor(y / this.tileHeight)];
    }

    /** The value of the first valued item (e.g. a crystal's weight) on a cell, or null. */
    itemValueAt(level, col, row) {
        const objects = level.getObjectsAtPosition(
            col * this.tileWidth + this.tileWidth / 2, row * this.tileHeight + this.tileHeight / 2);
        for (const object of objects) {
            if (object.type !== "Character" && object.visible !== false && Number.isInteger(object.value)) {
                return object.value;
            }
        }
        return null;
    }

    /** [col, row] of the cell `distance` cells ahead in the facing direction. */
    cellAhead(distance) {
        const [col, row] = this.currentCell();
        const [dx, dy] = { north: [0, -1], south: [0, 1], west: [-1, 0], east: [1, 0] }[this.getDirection()];
        return [col + dx * distance, row + dy * distance];
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

            const front = this.getPositionInDirection(newDirection, true);
            if (level.isAbyssAt(front[0], front[1])) {
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

    /**
     * Interacts with every object on the tile in front of the character.
     * @returns {boolean} true if at least one object reacted.
     */
    interact(level) {
        const position = this.getPositionInDirection(this.getDirection(), true);
        const objects =  level.getObjectsAtPosition(position[0], position[1]);
        let reacted = false;
        if (Array.isArray(objects) && objects.length != 0) {
            for (const object of objects) {
                if (object) {
                    if (typeof object.interact === 'function') {
                        reacted = object.interact(level) || reacted;
                    } else {
                        console.log(`You cannot interact with the object of class "${object.type}" and ID "${object.id}".`)
                    }
                }
            }
        }
        else {
            console.log(`There is no object in front of the player to interact with.`);
        }
        return reacted;
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

                if (this.deathAfterStep) {          // caught by a guard during this step
                    this.deathAfterStep = false;
                    this.isCharacterDead = true;
                }
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

    /** A sensor looked at the cell in front: count it and light it in the fog. */
    senseFront() {
        this.statistics.addSensorCall();
        if (this.game.fog) {
            this.game.fog.markSensed(...this.character.frontCell());
        }
    }

    move() {
        const target = this.character.frontCell();
        const from = this.character.currentCell();
        const ret = this.character.move(this.character.getDirection(), this.level);
        // guards take their step on every move, also a blocked one (DC-12)
        if (this.level.stepGuards(from, ret ? target : from)) {
            if (this.character.isMoving()) {
                // end the game once this step is done; ending it now would freeze the
                // hero mid-step (the level stops updating) and move() would time out
                this.character.deathAfterStep = true;
            } else {
                this.character.isCharacterDead = true;
            }
        }
        if (ret) {
            this.statistics.addMove();
            if (this.game.fog) {
                this.game.fog.markSensed(...target);   // stays lit while the hero walks in
            }
        } else {
            this.statistics.addBump();
        }
        return ret;
    }

    configure(name, typeNumber) {
        const nameSet = this.character.setName(name);
        const typeSet = this.character.setTypeNumber(typeNumber);
        return nameSet && typeSet;
    }

    set_pace(factor) {
        return this.character.setPace(factor);
    }

    turnLeft() {
        const ret = this.character.turnLeft();
        if (ret) {
            this.statistics.addTurn();
        }
        return ret;
    }

    isFacingNorth() {
        this.statistics.addSensorCall();
        return this.character.isFacingNorth();
    }

    isCollisionInFront() {
        this.senseFront();
        return this.character.isCollisionInFront(this.level);
    }

    isAbyssInFront() {
        this.senseFront();
        const front = this.character.getPositionInDirection(this.character.getDirection(), true);
        return this.level.isAbyssAt(front[0], front[1]);
    }

    isTorchInFront() {
        this.senseFront();
        return this.character.isInFront(this.level, "Torch");
    }

    isSwitchInFront() {
        this.senseFront();
        return this.character.isInFront(this.level, "Switch");
    }

    getInventory() {
        return this.character.getInventory();
    }

    getItemsAtHeroPosition() {
        this.statistics.addSensorCall();
        return this.character.getItemsAtCurrentPosition(this.level);
    }

    /** A guard on the field in front (sensor). */
    isEnemyInFront() {
        this.senseFront();
        return this.character.isInFront(this.level, "Guard");
    }

    /** Levels with the map property `orakel: true` have an oracle that knows the way. */
    hasOracle() {
        return this.level.getBooleanProperty('orakel', false);
    }

    /** The first step of a shortest way to the exit ("north", ...), or null. */
    askOracle() {
        this.statistics.addQuestion();
        return this.level.oracleDirection(...this.character.currentCell());
    }

    /** Value of the item on the hero's field (e.g. a crystal's weight), or null. */
    readItemValue() {
        this.statistics.addRead();
        return this.character.itemValueAt(this.level, ...this.character.currentCell());
    }

    /** Levels with the map property `fernrohr: true` let the hero read values from afar. */
    hasFernrohr() {
        return this.level.getBooleanProperty('fernrohr', false);
    }

    /** Value of the item `distance` fields ahead (1 = the field in front), or null. */
    peekItemValue(distance) {
        this.statistics.addRead();
        const [col, row] = this.character.cellAhead(distance);
        if (this.game.fog) {
            this.game.fog.markSensed(col, row);
        }
        if (col < 0 || row < 0 || col >= this.level.width || row >= this.level.height) {
            return null;
        }
        return this.character.itemValueAt(this.level, col, row);
    }

    /** The map property `inventory_size` limits how many items the hero can carry. */
    isInventoryFull() {
        const size = this.level.getProperty('inventory_size');
        return Number.isInteger(size) && this.character.inventory.length >= size;
    }

    pickup(name) {
        if (this.isInventoryFull()) {
            return false;
        }
        const ret = this.character.pickup(this.level, name);
        if (ret) {
            this.statistics.addPickup();
        }
        return ret;
    }

    drop(name) {
        const ret = this.character.drop(this.level, name);
        if (ret) {
            this.statistics.addDrop();
        }
        return ret;
    }

    isMoving() {
        return this.character.isMoving();
    }

    interact() {
        this.statistics.addInteraction();
        return this.character.interact(this.level);
    }

    /** The hero stands on the goal field (the level may still need its win conditions). */
    isAtGoal() {
        this.statistics.addSensorCall();
        return this.level.isHeroOnGoal();
    }

    /** Counters plus completion state, as described by Statistics in api/openapi.yaml. */
    getStatistics() {
        return {
            ...this.statistics.snapshot(),
            at_goal: this.level.isHeroOnGoal(),
            game_over: this.character.isFalling() || this.character.isDead(),
            level_complete: this.level.isComplete(),
            missing: this.level.unmetWinConditions(),
        };
    }
}
