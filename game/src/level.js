import { AnimatedTile, TileFactory } from './tiles.js';
import { TileLayer, ObjectLayer } from './layers.js';
import { GameObjectFactory } from './game-object-factory.js';
import { Torch, PatternDoor, Guard } from './game-objects.js';

/**
 * Tiles for items the engine creates itself (the start inventory, map property
 * `hero_inventory`, e.g. "Pebble*20"). Their tileset is added to a level that lacks it.
 */
export const ITEM_TILES = {
    Pebble: { source: "../tilesets/Icon sheet (16x16).json", local: 155 },
    Crystal: { source: "../tilesets/Icon sheet (16x16).json", local: 109 },
};

/** [[type, count], ...] from a start inventory like "Pebble*20, Crystal". */
export function parseStartInventory(text) {
    return String(text ?? "").split(",").map(s => s.trim()).filter(s => s).map(entry => {
        const [type, count = "1"] = entry.split("*").map(s => s.trim());
        return [type, Math.max(0, parseInt(count, 10) || 0)];
    });
}

/**
 * Represents a complete Tiled level, containing multiple layers.
 */
export class Level {
    /**
     * @param {Array<Object>} levelDescription Raw level data from Tiled Level JSON
     * @param {TileFactory} tileFactory Tile Factory that was generated from the Tiled Level JSON
     */
    constructor(levelDescription, tileFactory) {
        const {
            compressionlevel = -1,
            height = 0,
            infinite = false,
            layers = [],
            properties = [],
            nextlayerid = 0,
            nextobjectid = 0,
            orientation = "orthogonal",
            renderorder = "right-down",
            tiledversion = "0.0.0",
            tileheight = 0,
            tilesets = [],
            tilewidth = 0,
            type="map",
            version = "0.0.0",
            width = 30
        } = levelDescription;

        this.width = width;
        this.height = height;
        this.properties = properties;   // custom map properties set in Tiled
        this.infinite = infinite;
        this.tileWidth = tilewidth;
        this.tileHeight = tileheight;
        this.layers = [];
        this.animatedTiles = [];
        this.objectFactory = new GameObjectFactory();
        this.character = null;
        this.goal = null;

        for (const layerDescription of layers) {
            if (layerDescription.type === "tilelayer") {
                this.layers.push(new TileLayer(layerDescription, tileFactory));
            } else if (layerDescription.type === "objectgroup") {
                this.layers.push(new ObjectLayer(layerDescription, tileFactory, this.objectFactory));
            }
        }

        // Create a list of animated tiles allowing a quick update
        this.layers.forEach((layer, layerIndex) => {
            if (layer instanceof TileLayer) {
                layer.tileMap.forEach((row, rowIndex) => {
                    row.forEach((tile, colIndex) => {
                        if (tile) {
                            if (tile.hasAnimation()) {
                                const tileset = tileFactory.getTilesetByGlobalTileId(levelDescription.layers[layerIndex].data[colIndex + rowIndex * this.width]);
                                const animatedTile = AnimatedTile.create(tile, tileset);
                                this.animatedTiles.push(animatedTile);

                                // Replace the tile with the animated tile to get it drawn
                                layer.replaceTile(colIndex, rowIndex, animatedTile);
                            }
                        }
                    });
                });
            }
        });

        this.tileFactory = tileFactory;
        this.character = this.getObjectByName("MainCharacter");
        this.character?.setTileSize(this.tileWidth, this.tileHeight);
        this.goal = this.getObjectByType("Goal");
        this.slots = this.findSlots();
        this.giveStartInventory();
    }

    /**
     * The fields where valued items (crystals) lie at the start, in reading order
     * (north to south, west to east). Each item remembers its start rank for "stable".
     */
    findSlots() {
        const cellOf = o => [Math.floor(o.x / this.tileWidth), Math.floor((o.y - 1) / this.tileHeight)];
        const items = this.objectFactory.gameObjects.filter(o => Number.isInteger(o.value));
        items.sort((a, b) => {
            const [ac, ar] = cellOf(a), [bc, br] = cellOf(b);
            return ar - br || ac - bc;
        });
        items.forEach((item, rank) => { item.startRank = rank; });
        return items.map(cellOf);
    }

    /** Items in the hero's inventory from the start (map property `hero_inventory`). */
    giveStartInventory() {
        if (!this.character) {
            return;
        }
        const layer = this.layers.find(l => l instanceof ObjectLayer);
        let nextId = 1 + Math.max(0, ...this.objectFactory.gameObjects.map(o => o.id || 0));
        for (const [type, count] of parseStartInventory(this.getProperty('hero_inventory'))) {
            const spec = ITEM_TILES[type];
            const tileset = spec && this.tileFactory.getTilesetBySource(spec.source);
            if (!tileset) {
                console.warn(`Start inventory: no tile for item type "${type}".`);
                continue;
            }
            for (let i = 0; i < count; i++) {
                const item = this.objectFactory.create({
                    gid: tileset.firstgid + spec.local, id: nextId++, name: "", type, visible: false,
                    x: -100, y: -100, width: this.tileWidth, height: this.tileHeight, properties: [],
                }, this.tileFactory);
                layer?.objects.push(item);
                this.character.inventory.push(item);
            }
        }
    }

    static async create(levelData, pathPrefix = "") {
        if (!levelData) return;

        // the start inventory needs its item tiles, even if the level doesn't use them
        const tilesets = [...(levelData.tilesets || [])];
        const properties = levelData.properties || [];
        const inventory = properties.find(p => p.name === 'hero_inventory')?.value;
        let nextGid = Math.max(1, ...tilesets.map(t => t.firstgid)) + 10000;
        for (const [type] of parseStartInventory(inventory)) {
            const spec = ITEM_TILES[type];
            if (spec && !tilesets.some(t => t.source === spec.source)) {
                tilesets.push({ firstgid: nextGid, source: spec.source });
                nextGid += 10000;
            }
        }
        levelData = { ...levelData, tilesets };

        const tileFactory = await TileFactory.create(levelData.tilesets, pathPrefix);
        const level = new Level(levelData, tileFactory);

        return level;
    }

    /**
     * Reads a bool custom property of the map (Tiled: Map > Map Properties).
     * @param {string} name
     * @param {boolean} defaultValue used when the property is not set
     */
    getBooleanProperty(name, defaultValue = false) {
        const prop = this.properties.find(p => p.name === name);
        return prop && prop.type === 'bool' ? prop.value : defaultValue;
    }

    /** Value of a custom map property of any type, or undefined if it isn't set. */
    getProperty(name) {
        const prop = this.properties.find(p => p.name === name);
        return prop ? prop.value : undefined;
    }

    /** Levels can forbid moving the hero by hand with `keyboard: false`. */
    isKeyboardEnabled() {
        return this.getBooleanProperty('keyboard', true);
    }

    update(deltaTime) {
        for (const animatedTile of this.animatedTiles) {
            animatedTile.update(deltaTime);
        }

        this.layers.forEach(layer => {
            if (layer instanceof ObjectLayer) {
                layer.update(deltaTime);
            }
        });

        for (const object of this.objectFactory.gameObjects) {
            if (object instanceof PatternDoor) {
                object.evaluate(this);
            }
        }
    }

    getObjectByName(name) {
        return this.objectFactory.getObjectByName(name);
    }

    getObjectByType(type) {
        return this.objectFactory.getObjectByType(type);
    }

    getObjectsAtPosition(x, y) {
        return this.objectFactory.getObjectsAtPosition(x, y);
    }

    getTilesAtPosition(x, y) {
        const tileCol = Math.floor(x / this.tileWidth);
        const tileRow = Math.floor(y / this.tileHeight);
        let tiles = [];

        this.layers.forEach(layer => {
            if (layer instanceof TileLayer) {
                const tile = layer.getTileAt(tileRow, tileCol);
                if (tile) {
                    tiles.push(tile);
                }
            }
        });
        return tiles;
    }

    getObjectById(id) {
        return this.objectFactory.getObjectById(id);
    }

    getBrightness() {
        let totalNumberOfTorches = 0;
        let burningNumberOfTorches = 0;
        let brightness = 1.0;
        for (const gameObject of this.objectFactory.gameObjects) {
            if (gameObject instanceof Torch)  {
                totalNumberOfTorches += 1;
                if (gameObject.isBurning()) {
                    burningNumberOfTorches += 1;
                }
            }
        }

        if (totalNumberOfTorches > 0) {
            brightness = Math.min(burningNumberOfTorches / totalNumberOfTorches, 1.0);
        }

        return brightness;
    }

    /** The hero stands on the goal field (and has finished its step). */
    isHeroOnGoal() {
        if (this.character && this.goal) {
            // Only a hero that has finished its step counts. Mid-step, the
            // interpolated position can round to exactly the goal
            // (e.g. 320 + 16 * 0.9999999999999998 === 336), and completing then
            // freezes the hero in "walking" because updates stop.
            if (this.character.isMoving()) {
                return false;
            }
            if (this.character.x == this.goal.x && this.character.y == this.goal.y) {
                return true;
            }
        }

        return false;
    }

    /**
     * Win conditions besides reaching the goal, from the map property `win`
     * (comma-separated): "all_sweets" (no sweets left lying around),
     * "all_switches" (every switch flipped away from its start position),
     * "sorted" (one valued item per slot, values rising in reading order),
     * "stable" (sorted, and equal values keep their start order).
     * @returns {string[]} descriptions of the unmet ones, e.g. ["3 sweets"]
     */
    unmetWinConditions() {
        const wanted = String(this.getProperty('win') ?? "").split(",").map(s => s.trim()).filter(s => s);
        const missing = [];
        const objects = this.objectFactory.gameObjects;
        if (wanted.includes("all_sweets")) {
            const left = objects.filter(o => o.type === "Sweets" && o.visible !== false).length;
            if (left > 0) {
                missing.push(`${left} sweets`);
            }
        }
        if (wanted.includes("all_switches")) {
            const unflipped = objects.filter(o => o.type === "Switch" && o.getState() === o.initialState).length;
            if (unflipped > 0) {
                missing.push(`${unflipped} switches`);
            }
        }
        if (wanted.includes("sorted") && !this.isRowSorted()) {
            missing.push("sorted row");
        }
        if (wanted.includes("stable") && !this.isRowStable()) {
            missing.push("equal values in start order");
        }
        return missing;
    }

    /**
     * The valued items lying on the slots, one list per slot (visible items only).
     * @returns {Array<Array<Object>>}
     */
    itemsOnSlots() {
        return this.slots.map(([col, row]) => this.getObjectsAtPosition(
            col * this.tileWidth + this.tileWidth / 2, row * this.tileHeight + this.tileHeight / 2)
            .filter(o => Number.isInteger(o.value) && o.visible !== false));
    }

    /** Every slot holds exactly one valued item and the values rise from slot to slot. */
    isRowSorted() {
        const slots = this.itemsOnSlots();
        if (slots.some(items => items.length !== 1)) {
            return false;
        }
        const values = slots.map(items => items[0].value);
        return values.every((v, i) => i === 0 || values[i - 1] <= v);
    }

    /** Sorted, and items with equal values are still in the order they started in. */
    isRowStable() {
        if (!this.isRowSorted()) {
            return false;
        }
        const items = this.itemsOnSlots().map(list => list[0]);
        return items.every((item, i) => i === 0 || items[i - 1].value < item.value
            || items[i - 1].startRank < item.startRank);
    }

    // --- guards and the oracle (DC-12), turn-based: the same rules run in dungeoncoder/sim.py ---

    /** [col, row] of an object (bottom-left anchored). */
    cellOf(object) {
        return [Math.floor(object.x / this.tileWidth), Math.floor((object.y - 1) / this.tileHeight)];
    }

    /**
     * Is there an abyss at the point (x, y)? An Abyss object, or an Abyss tile that is the
     * **topmost** tile of the field: a floor or wall drawn over an abyss background is solid
     * ground (many levels fill their background layer with abyss tiles, B20/B21).
     */
    isAbyssAt(x, y) {
        const tiles = this.getTilesAtPosition(x, y);
        const top = tiles[tiles.length - 1];
        return (top !== undefined && top.type === "Abyss")
            || this.getObjectsAtPosition(x, y).some(o => o.type === "Abyss");
    }

    /** A field anyone can walk on: inside, no collision, no abyss tile. */
    isWalkable(col, row) {
        if (col < 0 || row < 0 || col >= this.width || row >= this.height) {
            return false;
        }
        const x = col * this.tileWidth + this.tileWidth / 2, y = row * this.tileHeight + this.tileHeight / 2;
        if (this.isCollision(x, y)) {
            return false;
        }
        return !this.isAbyssAt(x, y);
    }

    /**
     * One step of every guard, after the hero tried a move from `heroFrom` to `heroTo`
     * ([col, row]; equal if the move was blocked). Returns true if a guard caught the hero:
     * it stands on the hero's field, or hero and guard swapped fields.
     */
    stepGuards(heroFrom, heroTo) {
        const OFFSETS = { north: [0, -1], east: [1, 0], south: [0, 1], west: [-1, 0] };
        const OPPOSITE = { north: "south", south: "north", east: "west", west: "east" };
        const guards = this.objectFactory.gameObjects.filter(o => o instanceof Guard);
        let caught = guards.some(g => { const [c, r] = this.cellOf(g); return c === heroTo[0] && r === heroTo[1]; });
        for (const guard of guards) {
            const [col, row] = this.cellOf(guard);
            const free = (c, r) => this.isWalkable(c, r)
                && !guards.some(o => o !== guard && this.cellOf(o)[0] === c && this.cellOf(o)[1] === r);
            let options;
            if (guard.behaviour === "chase") {
                const dx = heroTo[0] - col, dy = heroTo[1] - row;
                const h = dx > 0 ? "east" : dx < 0 ? "west" : null, v = dy > 0 ? "south" : dy < 0 ? "north" : null;
                options = (Math.abs(dx) >= Math.abs(dy) ? [h, v] : [v, h]).filter(d => d);
            } else {
                options = [guard.direction, OPPOSITE[guard.direction]];
            }
            for (const d of options) {
                const [nc, nr] = [col + OFFSETS[d][0], row + OFFSETS[d][1]];
                if (free(nc, nr)) {
                    guard.x += OFFSETS[d][0] * this.tileWidth;
                    guard.y += OFFSETS[d][1] * this.tileHeight;
                    if (guard.behaviour !== "chase") {
                        guard.direction = d;
                    }
                    const onHero = nc === heroTo[0] && nr === heroTo[1];
                    const swapped = col === heroTo[0] && row === heroTo[1] && nc === heroFrom[0] && nr === heroFrom[1];
                    caught = caught || onHero || swapped;
                    break;
                }
            }
        }
        return caught;
    }

    /**
     * The oracle's answer: the direction of the first step of a shortest way from
     * [col, row] to the goal (breadth-first, neighbours in the order north, east, south,
     * west), or null if the hero stands on the goal or there is no way.
     */
    oracleDirection(col, row) {
        if (!this.goal) {
            return null;
        }
        const [gc, gr] = this.cellOf(this.goal);
        if (col === gc && row === gr) {
            return null;
        }
        const OFFSETS = [["north", 0, -1], ["east", 1, 0], ["south", 0, 1], ["west", -1, 0]];
        const first = new Map([[`${col},${row}`, null]]);
        const queue = [[col, row]];
        while (queue.length > 0) {
            const [c, r] = queue.shift();
            for (const [d, dx, dy] of OFFSETS) {
                const [nc, nr] = [c + dx, r + dy];
                const key = `${nc},${nr}`;
                if (first.has(key) || !this.isWalkable(nc, nr)) {
                    continue;
                }
                const step = first.get(`${c},${r}`) ?? d;
                if (nc === gc && nr === gr) {
                    return step;
                }
                first.set(key, step);
                queue.push([nc, nr]);
            }
        }
        return null;
    }

    /** The goal is reached and every win condition is met. */
    isComplete() {
        if (this.character && this.character.isDead()) {
            return false;                  // caught by a guard on the goal field
        }
        return this.isHeroOnGoal() && this.unmetWinConditions().length === 0;
    }

    isAbyss(x, y) {
        const tileCol = Math.floor(x / this.tileWidth);
        const tileRow = Math.floor(y / this.tileHeight);

        // Check for out of bounds
        if (tileCol < 0 || tileCol >= this.width || tileRow < 0 || tileRow >= this.height) {
            console.warn("Checking for collision out of bounds.")
            return true; // Consider out of bounds as a collision
        }

        for (const layer of this.layers) {
            if (layer instanceof TileLayer) {
                const tile = layer.getTileAt(tileRow, tileCol);
                if (tile) {
                    const property = tile.getProperty('abyss');
                    if (property) {
                        return property;
                    }
                }
            }
        }

        return false; // No collision detected
    }

    isCollision(x, y) {
        const tileCol = Math.floor(x / this.tileWidth);
        const tileRow = Math.floor(y / this.tileHeight);

        // Check for out of bounds
        if (tileCol < 0 || tileCol >= this.width || tileRow < 0 || tileRow >= this.height) {
            console.warn("Checking for collision out of bounds.")
            return true; // Consider out of bounds as a collision
        }

        for (const layer of this.layers) {
            if (layer instanceof TileLayer) {
                // Check collision for TileLayer
                const isLayerCollision = layer.getBooleanProperty('collision', false);

                if (isLayerCollision) {
                    const tile = layer.getTileAt(tileRow, tileCol);
                    // If the layer itself has collision=true, any non-empty tile within it is a collision
                    if (tile) {
                        if (tile.id !== 0) {
                            return true;
                        }
                    }
                }
            }
        }

        const objects =  this.getObjectsAtPosition(x, y);
        if (Array.isArray(objects) && objects.length != 0) {
            for (const object of objects) {
                if (object.isCollision()) {
                    return true;
                }
            }
        }

        return false; // No collision detected
    }
}
