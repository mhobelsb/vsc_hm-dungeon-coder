import { AnimatedTile } from './tiles.js';

export class GameObject {
    /**
     * @param {Array<Object>} objectDescription Raw object from Tiled Level JSON
     * @param {import('./tiles.js').TileFactory} tileFactory Tile Factory that was generated from the Tiled Level JSON
     */
    constructor(objectDescription, tileFactory, className = "", states = null) {
        const {
            gid, // Global Tile Id
            height,
            id,
            name,
            properties = [],
            rotation,
            state = "default",
            type,
            visible,
            width,
            x,
            y
        } = objectDescription;

        let defaultTile = tileFactory.getTileByGlobalTileId(gid);
        if (defaultTile.hasAnimation()) {
            defaultTile = AnimatedTile.create(defaultTile, tileFactory.getTilesetByGlobalTileId(gid));
        }

        this.id = id;
        this.tileMap = new Map();
        this.tileMap.set(state, defaultTile);

        if (states) {
            states.forEach(state => {
                let tile = tileFactory.getTileByTypeAndState(className, state);
                if (!tile) {
                    console.error(`Tile with type/class "${className}" and state "${state} not found!`)
                }

                if (tile.hasAnimation()) {
                    tile = AnimatedTile.create(tile, tileFactory.getTilesetByTile(tile));
                }
                this.tileMap.set(state, tile);
            });
        }

        this.tile = defaultTile;
        if (this.tile.getProperty("state")) {
            this.state = this.tile.getProperty("state");
        }

        this.properties = properties;
        this.name = name;
        this.type = className;
        this.visible = visible;
        this.height = height;
        this.width = width;
        this.x = x;
        this.y = y;

        console.log(`Constructed game object of type "${this.type}" at location ("${this.x}", "${this.y}")`);
    }

    isCollision() {
        const collision = this.tile.getProperty('collision');
        if (!collision)
            return false;
        return collision;
    }

    update(deltaTime) {
        if (this.tile instanceof AnimatedTile) {
            this.tile.update(deltaTime);
        }
    }

    setCurrentTile(tile) {
        // TODO: this.tile.reset();
        this.tile = tile;
    }

    getState() {
        return this.state;
    }

    setState(state) {
        if (this.tileMap.has(state)) {
            // TODO: tile.reset
            this.tile = this.tileMap.get(state);
            this.state = state;
        } else {
            console.warn(`State "${state}" of object "${this.name}" not found.`)
        }
    }

    getProperty(name) {
        let property = this.properties.find(p => p.name === name);
        if (!property) {
            property = this.tile.getProperty(name);
        }
        return property;
    }

    isAtPosition(x, y) {
        if (x >= this.x && x < (this.x + this.width) &&
            y >= (this.y - this.height) && y < this.y) {
            return true;
        }

        return false;
    }

    /**
     * Passes the interaction on to the object this one `controls`, if any.
     * @returns {boolean} true if the controlled object reacted.
     */
    interact(level) {
        if (this.getProperty('controls')) {
            const propertyControls = this.getProperty('controls');
            let object = null;
            if (propertyControls) {
                object = level.getObjectById(propertyControls.value);
            } else {
                console.warn(`GameObject has no property controls set.`);
            }
            if (object) {
                if (typeof object.interact === 'function') {
                    return object.interact(level);
                } else {
                    console.log(`Error: the GameObject cannot interact with the object with ID "${propertyControls.value}.`)
                }
            } else {
                console.warn(`Object with ID "${propertyControls.value}" not found.`);
            }
        }
        return false;
    }
}

/**
 * Base for GameObjects that flip between exactly two named states when
 * interacted with (a torch, a switch, a door, a chest, ...). Subclasses
 * declare `static STATES = [stateA, stateB]` and, if interacting with them
 * should also trigger whatever they `controls` (see GameObject.interact),
 * override propagatesInteract() to return true.
 */
export class TwoStateGameObject extends GameObject {
    toggleState() {
        const [stateA, stateB] = this.constructor.STATES;
        this.setState(this.getState() === stateA ? stateB : stateA);
    }

    /** @returns {boolean} true if this object changed state or a controlled object reacted. */
    interact(level) {
        const stateBefore = this.getState();
        this.toggleState();
        const changed = this.getState() !== stateBefore;
        const propagated = this.propagatesInteract() ? super.interact(level) : false;
        return changed || propagated;
    }

    propagatesInteract() {
        return false;
    }
}

export class Torch extends TwoStateGameObject {
    static STATES = ["burning", "off"]; // Add all states here

    constructor(objectDescription, tileFactory) {
        super(objectDescription, tileFactory, Torch.name, Torch.STATES);
    }

    isBurning() {
        return this.getState() === "burning";
    }

    isOff() {
        return this.getState() === "off";
    }

    propagatesInteract() {
        return true;
    }

    on() {
        this.setState("burning");
    }

    off() {
        this.setState("off");
    }
}

export class TwoWaySwitch extends TwoStateGameObject {
    static STATES = ["left", "right"];

    constructor(objectDescription, tileFactory) {
        super(objectDescription, tileFactory, "Switch", TwoWaySwitch.STATES);
        this.initialState = this.getState();   // for the win condition "all_switches"
    }

    isLeft() {
        return this.getState() === "left";
    }

    isRight() {
        return this.getState() === "right";
    }

    propagatesInteract() {
        return true;
    }

    left() {
        this.setState("left");
    }

    right() {
        this.setState("right");
    }
}

/**
 * Base for GameObjects that simply toggle between an "open" and "closed"
 * state on interact, without propagating to anything they control
 * (Door and its variants, Chest).
 */
export class OpenableGameObject extends TwoStateGameObject {
    static STATES = ["open", "closed"];

    isOpen() {
        return this.getState() === "open";
    }

    open() {
        this.setState("open");
    }

    close() {
        this.setState("closed");
    }
}

export class Door extends OpenableGameObject {
    constructor(objectDescription, tileFactory, name=Door.name) {
        super(objectDescription, tileFactory, name, OpenableGameObject.STATES);
    }
}

/**
 * A door that opens exactly while a row of torches shows its bit pattern
 * (burning = 1, off = 0). Object properties: `pattern` (e.g. "101") and
 * `torches` (the torch object ids in pattern order, e.g. "12,13,14").
 * It can't be opened by hand; Level.update() calls evaluate() every frame.
 */
/**
 * A thing the hero can pick up and carry, e.g. a crystal or a pebble.
 * The integer property `value` (a crystal's weight) is never drawn:
 * only read_item_value() / peek_item_value() reveal it.
 */
export class Item extends GameObject {
    constructor(objectDescription, tileFactory, name = "Item") {
        super(objectDescription, tileFactory, name);
        const value = (objectDescription.properties || []).find(p => p.name === 'value')?.value;
        this.value = Number.isInteger(value) ? value : null;
    }

    isCollision() {
        return false;
    }
}

export class PatternDoor extends Door {
    constructor(objectDescription, tileFactory) {
        // look like the door tile it was placed with (horizontal or vertical door)
        const tile = tileFactory.getTileByGlobalTileId(objectDescription.gid);
        super(objectDescription, tileFactory, (tile && tile.type) || Door.name);
        const property = name => (objectDescription.properties || []).find(p => p.name === name)?.value;
        this.pattern = String(property('pattern') ?? '');
        this.torchIds = String(property('torches') ?? '')
            .split(',').map(s => parseInt(s.trim(), 10)).filter(n => !isNaN(n));
    }

    /** The torches' current bits, e.g. "101". */
    currentBits(level) {
        return this.torchIds.map(id => {
            const torch = level.getObjectById(id);
            return torch && typeof torch.isBurning === 'function' && torch.isBurning() ? '1' : '0';
        }).join('');
    }

    evaluate(level) {
        const shouldOpen = this.pattern !== '' && this.currentBits(level) === this.pattern;
        if (shouldOpen !== this.isOpen()) {
            this.setState(shouldOpen ? 'open' : 'closed');
        }
    }

    interact(level) {
        return false;
    }
}

export class VerticalDoor extends Door {
    constructor(objectDescription, tileFactory, name=VerticalDoor.name) {
        super(objectDescription, tileFactory, name);
    }
}

export class Grille extends Door {
    constructor(objectDescription, tileFactory, name=Grille.name) {
        super(objectDescription, tileFactory, name);
    }
}

export class VerticalGrille extends Door {
    constructor(objectDescription, tileFactory, name=VerticalGrille.name) {
        super(objectDescription, tileFactory, name);
    }
}

export class Chest extends OpenableGameObject {
    constructor(objectDescription, tileFactory) {
        super(objectDescription, tileFactory, Chest.name, OpenableGameObject.STATES);
    }
}

export class Jug extends TwoStateGameObject {
    static STATES = ["unbroken", "broken"];

    constructor(objectDescription, tileFactory) {
        super(objectDescription, tileFactory, Jug.name, Jug.STATES);
    }

    isBroken() {
        return this.getState() === "broken";
    }

    // A jug can only break, not un-break - overrides the bidirectional
    // toggle from TwoStateGameObject.
    toggleState() {
        if (!this.isBroken()) {
            this.break();
        }
    }

    break() {
        this.setState("broken");
    }
}

export class Goal extends GameObject {
    static STATES = ["default"];

    constructor(objectDescription, tileFactory) {
        super(objectDescription, tileFactory, Goal.name, Goal.STATES);
    }

    interact(level) {
        return false;
    }
}
