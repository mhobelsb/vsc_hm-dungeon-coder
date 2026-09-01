import { AnimatedTile, TileFactory } from './tiles.js';
import { TileLayer, ObjectLayer } from './layers.js';
import { GameObjectFactory } from './game-object-factory.js';
import { Torch } from './game-objects.js';

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
        this.goal = this.getObjectByType("Goal");
    }

    static async create(levelData, pathPrefix = "") {
        if (!levelData) return;

        const tileFactory = await TileFactory.create(levelData.tilesets, pathPrefix);
        const level = new Level(levelData, tileFactory);

        return level;
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

    isComplete() {
        if (this.character && this.goal) {
            if (this.character.x == this.goal.x && this.character.y == this.goal.y) {
                return true;
            }
        }

        return false;
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
