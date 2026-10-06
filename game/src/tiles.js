import { loadFromPacks, packPath } from './assets.js';

/**
 * Tiled stores a tile's mirroring in the top bits of its global id: flipped horizontally,
 * vertically, diagonally (x and y swapped). The rest is the id.
 */
export const GID_MASK = 0x1FFFFFFF;
const FLIPPED_H = 0x80000000, FLIPPED_V = 0x40000000, FLIPPED_D = 0x20000000;

/** The flip flags of a global id, or null if it has none. */
export function flipsOf(gid) {
    const raw = gid >>> 0;
    if (raw <= GID_MASK) {
        return null;
    }
    return { h: (raw & FLIPPED_H) !== 0, v: (raw & FLIPPED_V) !== 0, d: (raw & FLIPPED_D) !== 0 };
}

/** The same tile, drawn mirrored: a view on it (rules and properties are the tile's own). */
export function flipped(tile, flips) {
    if (!tile || !flips) {
        return tile;
    }
    const view = Object.create(tile);
    view.flipH = flips.h;
    view.flipV = flips.v;
    view.flipD = flips.d;
    return view;
}

export class Tile {
    constructor(setTileId, image, imageHeight, imageWidth, x, y, width, height, tileDescription) {
        if (!tileDescription) {
            tileDescription = {};
        }
        this.id = setTileId;            // tileset tile id (not global!)
        this.image = image;             // image containing the tile
        this.imageHeight = imageHeight; // total height of the image
        this.imageWidth = imageWidth;   // total width of the image
        this.x = x;                     // the tiles x-position in the image
        this.y = y;                     // the tiles y-position in the image
        this.x_offset = 0;              // drawing offset in pixels
        this.y_offset = 0;
        this.width = width;             // tile width
        this.height = height;           // tile height

        const {
            visible = true,
            animation = [],
            properties = []
        } = tileDescription;

        this.visible = visible;

        if (tileDescription["class"]) {
            this.type = tileDescription["class"];
        } else {
            this.type = "";
        }
        this.properties = properties;
        this.animationDescription = animation;

        const x_offset_property = this.getProperty("x_offset");
        if (x_offset_property) {
            this.x_offset = x_offset_property;
        }

        const y_offset_property = this.getProperty("y_offset");
        if (y_offset_property) {
            this.y_offset = y_offset_property;
        }
    }

    getProperty(name) {
        if (this.properties[name]) {
            return this.properties[name];
        }
        return null;
    }

    getBooleanProperty(name, defaultValue = false) {
        if (this.properties) {
            const prop = this.properties.find(p => p.name === name);
            if (prop && prop.type === 'bool') {
                return prop.value;
            }
        }
        return defaultValue;
    }

    hasAnimation() {
        return (this.animationDescription?.length ?? 0) > 0;
    }
}

export class AnimationFrame {
    constructor(tile, duration) {
        this.tile = tile;
        this.duration = duration;
    }
}

export class AnimatedTile {
    constructor(width, height) {
        this.animationFrames = [];
        this.currentFrameIndex = 0;
        this.timeSinceLastFrameChange = 0;
        this.width = width;
        this.height = height;
    }

    add(tile, duration) {
        this.animationFrames.push(new AnimationFrame(tile, duration));
    }

    update(deltaTime) {
        this.timeSinceLastFrameChange += deltaTime;
        while (this.timeSinceLastFrameChange >= this.animationFrames[this.currentFrameIndex].duration) {
            this.timeSinceLastFrameChange -= this.animationFrames[this.currentFrameIndex].duration;
            this.currentFrameIndex++;
            this.currentFrameIndex = this.currentFrameIndex % this.animationFrames.length;
        }
    }

    getCurrentTile() {
        return this.animationFrames[this.currentFrameIndex].tile;
    }

    static create(tile, tileset) {
        const animatedTile = new AnimatedTile(tile.width, tile.height);
        for (const animation of tile.animationDescription) {
            const {
                tileid,
                duration
            } = animation;
            animatedTile.add(tileset.getTileBySetTileId(tileid), duration);
        }
        return animatedTile;
    }

    getProperty(name) {
        const tile = this.getCurrentTile();
        return tile.getProperty(name);
    }
}

export class Tileset {

    constructor(jsonPath, tilesetDescription, loadedImage, firstgid) {
        const {
            columns,
            image,
            imageheight,
            imagewidth,
            margin,
            name,
            spacing,
            tilecount,
            tiledversion,
            tileheight,
            tiles = [],
            tilewidth,
            type,
            version
        } = tilesetDescription;

        this.firstgid = firstgid;
        this.source = jsonPath;
        this.columns = columns;
        this.image = loadedImage;
        this.imageheight = imageheight;
        this.imagewidth = imagewidth;
        this.margin = margin;
        this.name = name;
        this.spacing = spacing;
        this.tilecount = tilecount;
        this.tiledversion = tiledversion;
        this.tileheight = tileheight;
        this.tilewidth = tilewidth;
        this.type = type;
        this.version = version;

        // Process the array with special tiles that have additional properties
        // and create a map for easy lookup
        this.tiles = new Map();
        const tileDescriptions = new Map();
        if (tiles) {
            tiles.forEach((tile) => {
                const tileDescription = {
                    id: tile.id,
                    class: tile.type || null,
                    animation: tile.animation || null,
                    properties: {},
                };
                if (tile.properties) {
                    tile.properties.forEach((prop) => {
                        tileDescription.properties[prop.name] = prop.value;
                    });
                }
                tileDescriptions.set(tile.id, tileDescription);
            });
        }

        // Create a tile for every tilecount, assigning special properties where they exist
        for (let setTileId = 0; setTileId < this.tilecount; setTileId++) {
            const tileDescription = tileDescriptions.get(setTileId);

            // Calculate sourceX and sourceY based on tile grid position
            const row = Math.floor(setTileId / this.columns);
            const col = setTileId % this.columns;
            const sourceX = this.margin + (col * (this.tilewidth + this.spacing));
            const sourceY = this.margin + (row * (this.tileheight + this.spacing));

            let tile = null;
            tile = new Tile(setTileId, this.image, this.imageheight, this.imagewidth, sourceX, sourceY, this.tilewidth, this.tileheight, tileDescription);
            this.tiles.set(setTileId, tile);
        }
    }

    getTileByGlobalTileId(globalTileId) {
        const tile = this.tiles.get(globalTileId - this.firstgid);
        if (!tile) {
            // global Tile ID zero is used for empty tiles, so no problem for that gid
            if (globalTileId !== 0) {
                console.warn(`Tile with global tile id "${globalTileId}" was not found in tile factory.`);
            }
        }

        return tile;
    }

    getTileBySetTileId(setTileId) {
        return this.tiles.get(setTileId);
    }

    getTileByTypeAndState(type, state) {
        for (const tile of this.tiles.values()) {
            if (tile.type === type) {
                const tileState = tile.getProperty("state");
                if (tileState === state) {
                    return tile;
                }
            }
        }

        return null;
    }

    has(tile) {
        for (const cur_tile of this.tiles.values()) {
            if (cur_tile === tile) {
                    return true;
            }
        }

        return false;
    }

    static async create(jsonPath, firstgid = 1, pathPrefix = "") {
        // the tileset and its image come from the first asset pack that has the tileset
        const found = await loadFromPacks(packPath(jsonPath), pathPrefix);
        if (!found) {
            return null;
        }
        const tileset_data = found.data;

        const imageSource = found.base + packPath(tileset_data.image);
        if (!imageSource) {
            console.error('Tileset data is missing the image path.');
            return null;
        }

        const tilesetImage = await new Promise((resolve, reject) => {
            const img = new Image();
            img.onload = () => resolve(img);
            img.onerror = () => reject(new Error(`Failed to load image at ${imageSource}`));
            img.src = imageSource;
        });

        const tileset = new Tileset(jsonPath, tileset_data, tilesetImage, firstgid);

        return tileset;
    }
}

export class TileFactory {
    constructor() {
        this.tileLookup = new Map();
        this.tilesets = [];
        this.animatedTiles = [];
    }

    add(tileset) {
        this.tilesets.push(tileset);
    }

    getTileByGlobalTileId(globalTileId) {
        const flips = flipsOf(globalTileId);
        const id = flips ? (globalTileId >>> 0) & GID_MASK : globalTileId;
        // the tileset that has the id (asking each in turn warned on every miss)
        const tileset = this.tilesets.find(t => id >= t.firstgid && id < t.firstgid + t.tilecount);
        const tile = tileset ? tileset.getTileByGlobalTileId(id) : null;
        if (!tile) {
            if (id !== 0) {
                console.warn(`Tile with global tile id "${id}" was not found in tile factory.`);
            }
            return null;
        }
        return flips ? this.flippedTile(globalTileId, tile, flips) : tile;
    }

    /** One view per flipped global id, so the same id always gives the same tile object. */
    flippedTile(globalTileId, tile, flips) {
        if (!this.flippedTiles) {
            this.flippedTiles = new Map();
        }
        if (!this.flippedTiles.has(globalTileId)) {
            this.flippedTiles.set(globalTileId, flipped(tile, flips));
        }
        return this.flippedTiles.get(globalTileId);
    }

    getTilesetByGlobalTileId(globalTileId) {
        globalTileId = (globalTileId >>> 0) & GID_MASK;
        for (const tileset of this.tilesets) {
            const tile = tileset.tiles.get(globalTileId - tileset.firstgid);
            if (tile) {
                return tileset;
            }
        }
        return null;
    }

    getTilesetBySource(source) {
        for (const tileset of this.tilesets) {
            if (tileset.source === source) {
                return tileset;
            }
        }
        return null;
    }

    getTileByTypeAndState(type, state) {
        for (const tileset of this.tilesets) {
            const tile = tileset.getTileByTypeAndState(type, state);
            if (tile) {
                return tile;
            }
        }
        return null;
    }

    getTilesetByTile(tile) {
        for (const tileset of this.tilesets) {
            if (tileset.has(tile)) {
                return tileset;
            }
        }
        return null;
    }

    /**
     * @param {string} pack the asset pack the level names (map property `pack`), for the message
     */
    static async create(tilesetsDescription, pathPrefix = "", pack = "") {
        const tileFactory = new TileFactory();
        const tilesetPromises = tilesetsDescription.map(ts => {
            return Tileset.create(ts.source, ts.firstgid, pathPrefix);
        });
        const loadedTilesets = await Promise.all(tilesetPromises);
        // a tileset no pack has would leave walls without rules: refuse the level (bug B24)
        const missing = tilesetsDescription.filter((ts, i) => !loadedTilesets[i]).map(ts => ts.source);
        if (missing.length > 0) {
            throw new MissingTilesetError(missing, pack);
        }
        loadedTilesets.forEach(tileset => {
            tileFactory.add(tileset);
        });
        return tileFactory;
    }
}

/** A level names tilesets that no asset pack has. The message is the one the student sees. */
export class MissingTilesetError extends Error {
    constructor(sources, pack = "") {
        super(missingTilesetMessage(sources, pack));
        this.name = 'MissingTilesetError';
        this.sources = sources;
        this.pack = pack;
    }
}

/** Same wording as the simulator (dungeoncoder/sim.py, missing_tileset_message). */
export function missingTilesetMessage(sources, pack = "") {
    const needs = pack ? `This level needs the asset pack "${pack}": get it (the exercise sheet says how) and add it ` : 'Add the asset pack ';
    return `Missing tileset ${sources.join(', ')}: no asset pack has it. `
        + `${needs}to the setting dungeonCoder.assetPacks (outside VS Code: DC_ASSET_PACKS).`;
}
