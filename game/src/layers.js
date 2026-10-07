/**
 * Base class for all level layers.
 */
export class BaseLayer {
    /**
     * @param {Array<Object>} layerDescription Raw layer description from Tiled Level JSON
     */
    constructor(layerDescription) {
        const {
            height = 0,
            id,
            name = "",
            opacity = 1,
            properties = [],
            type,
            visible = true,
            width = 0,
            x = 0,
            y = 0
        } = layerDescription;

        this.name = name;
        this.id = id;
        this.type = type;
        this.opacity = opacity;
        this.visible = visible;
        this.properties = properties;
        this.height = height;
        this.width = width;
        this.x = x;
        this.y = y;
    }

    /**
     * Helper to get a boolean custom property with a default value.
     * @param {string} name The name of the property.
     * @param {boolean} defaultValue The default value if the property is not found or not boolean.
     * @returns {boolean} The boolean value of the property.
     */
    getBooleanProperty(name, defaultValue = false) {
        if (this.properties) {
            const prop = this.properties.find(p => p.name === name);
            if (prop && prop.type === 'bool') {
                return prop.value;
            }
        }
        return defaultValue;
    }
}

/**
 * Represents a tile layer in the level.
 * Extends BaseLayer to include tile-specific properties.
 */
export class TileLayer extends BaseLayer {
    /**
     * @param {Array<Object>} layerDescription Raw layer description from Tiled Level JSON
     * @param {import('./tiles.js').TileFactory} tileFactory Tile Factory that was generated from the Tiled Level JSON
     */
    constructor(layerDescription, tileFactory) {
        super(layerDescription);

        const  {
            data,
            width,
            height
        } = layerDescription;

        this.rows = height;
        this.cols = width;
        this.tileMap = [];

        for (let rowIndex = 0; rowIndex < this.rows; rowIndex++) {
            this.tileMap[rowIndex] = [];
            for (let colIndex = 0; colIndex < this.cols; colIndex++) {
                this.tileMap[rowIndex][colIndex] = tileFactory.getTileByGlobalTileId(data[colIndex + (rowIndex * this.cols)]);
            }
        }
    }

    /**
     * Gets the tile ID at a specific column and row.
     * @param {number} row The row index (0-based).
     * @param {number} col The column index (0-based).
     * @returns {number | undefined} The tile ID, or undefined if out of bounds.
     */
    getTileAt(row, col) {
        if (col < 0 || col >= this.width || row < 0 || row >= this.height) {
            console.warn(`Accessing tile outside bounds: (${col}, ${row}) on layer "${this.name}"`);
            return undefined; // Or throw an error
        }
        return this.tileMap[row][col];
    }

    replaceTile(col, row, newTile) {
        this.tileMap[row][col] = newTile;
    }
}

export class ObjectLayer extends BaseLayer {
    constructor(layerDescription, tileFactory, objectFactory) {
        super(layerDescription);

        const  {
            draworder,
            id,
            name,
            objects,
            opacity,
            type,
            visible,
            x,
            y
        } = layerDescription;

        this.visible = visible;
        this.objects = [];
        objects.forEach((objectDescription) => {
            // a Region rectangle only describes level variants (dungeoncoder/variants.py);
            // the Python client removes them, a level opened directly may still have them
            if (objectDescription.type !== "Region") {
                this.objects.push(objectFactory.create(objectDescription, tileFactory));
            }
        });
    }

    update(deltaTime) {
        this.objects.forEach((object) => {
            object.update(deltaTime);
        });
    }
}
