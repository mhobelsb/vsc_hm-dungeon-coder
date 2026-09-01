export const TILE_SIZE = 16;

async function loadJson(filePath) {
  try {
    const response = await fetch(filePath);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
  } catch (e) {
    console.error(`Could not load JSON from ${filePath}: ${e}`);
    return null;
  }
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
            if (globalTileId != 0) {
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
                if (tileState === state)
                    return tile;
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
        const correctedPath = pathPrefix + jsonPath.replace('..', 'assets');
        const tileset_data = await loadJson(correctedPath);
        if (!tileset_data) {
            return null;
        }

        const imageSource = pathPrefix + tileset_data.image.replace('..', 'assets');
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
        for (const tileset of this.tilesets) {
            const tile = tileset.getTileByGlobalTileId(globalTileId);
            if (tile) {
                return tile;
            }
        }
        return null;
    }

    getTilesetByGlobalTileId(globalTileId) {
        for (const tileset of this.tilesets) {
            const tile = tileset.getTileByGlobalTileId(globalTileId);
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

    static async create(tilesetsDescription, pathPrefix = "") {
        const tileFactory = new TileFactory();
        const tilesetPromises = tilesetsDescription.map(ts => {
            return Tileset.create(ts.source, ts.firstgid, pathPrefix);
        });
        const loadedTilesets = await Promise.all(tilesetPromises);
        loadedTilesets.forEach(tileset => {
            tileFactory.add(tileset);
        });
        return tileFactory;
    }
}
