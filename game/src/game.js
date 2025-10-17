const TILE_SIZE = 16;
export const GAME_WIDTH = 480; 
export const GAME_HEIGHT = 320;
const FONT_SIZE = 12;

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

class Tile {
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

    hasAnimation() {
        return (this.animationDescription?.length ?? 0) > 0;
    }

    /**
     * Draws the tile onto a 2D rendering context.
     * @param {CanvasRenderingContext2D} ctx The 2D rendering context of the canvas.
     * @param {number} destX The X-coordinate (pixel) on the canvas to draw the tile.
     * @param {number} destY The Y-coordinate (pixel) on the canvas to draw the tile.
     * @param {number} [destWidth=this.width] The optional width to draw the tile (defaults to original tile width).
     * @param {number} [destHeight=this.height] The optional height to draw the tile (defaults to original tile height).
     */
    draw(ctx, destX, destY, destWidth = this.width, destHeight = this.height) {
        if (!this.visible)
            return;
        
        destY -= this.height; // tiled coordinates are bottom left corner
        ctx.drawImage(
            this.image,
            this.x,
            this.y,
            this.width,
            this.height,
            destX + this.x_offset,         
            destY + this.y_offset,        
            destWidth,  
            destHeight  
        );
    }
}

class AnimationFrame {
    constructor(tile, duration) {
        this.tile = tile;
        this.duration = duration;
    }
}

class AnimatedTile {
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

    draw(ctx, destX, destY, destWidth = this.width, destHeight = this.height) {
        const tile = this.getCurrentTile();
        destY -= this.height; // tiled coordinates are bottom left corner
        ctx.drawImage(
            tile.image,
            tile.x,    
            tile.y,    
            tile.width,
            tile.height,
            destX + tile.x_offset,         
            destY + tile.y_offset,     
            destWidth,  
            destHeight  
        );
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

class Tileset {

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

        for (const [id, tile] of tileset.tiles) {
            if (tile instanceof AnimatedTile) {
                tile.initializeAnimations(tileset);
            }
        }

        return tileset;
    }
}

class TileFactory {
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

/**
 * Base class for all level layers.
 */
class BaseLayer {
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
class TileLayer extends BaseLayer {
    /**
     * @param {Array<Object>} layerDescription Raw layer description from Tiled Level JSON
     * @param {TileFactory} tileFactory Tile Factory that was generated from the Tiled Level JSON
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

    /**
     * Draws the tile layer onto a 2D rendering context.
     * @param {CanvasRenderingContext2D} ctx The 2D rendering context of the canvas.
     */
    draw(ctx, levelTileWidth, levelTileHeight) {
        if (!this.visible || this.opacity <= 0) {
            return;
        }

        ctx.globalAlpha = this.opacity;

        this.tileMap.forEach((row, rowIndex) => {
            row.forEach((tile, colIndex) => {
                if (tile) {
                    const destX = colIndex * levelTileWidth;
                    const destY = rowIndex * levelTileHeight + levelTileHeight; // Compute tiled coordinates here, i.e. bottom left
                    tile.draw(ctx, destX, destY);
                }
            });
        });

        ctx.globalAlpha = 1.0;
    }
}

class ObjectLayer extends BaseLayer {
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
            this.objects.push(objectFactory.create(objectDescription, tileFactory));
        });
    }

    update(deltaTime) {
        this.objects.forEach((object) => {
            object.update(deltaTime);
        });
    }

    draw(ctx, levelTileWidth, levelTileHeight) {
        if (this.visible) {
            this.objects.forEach((object) =>  {
                object.draw(ctx);
            });
        }
    }
}

class GameObject {
    /**
     * @param {Array<Object>} objectDescription Raw object from Tiled Level JSON
     * @param {TileFactory} tileFactory Tile Factory that was generated from the Tiled Level JSON
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

    draw(ctx, destX = this.x, destY = this.y, destWidth = this.width, destHeight = this.height) {
        if (this.visible) {
            this.tile.draw(ctx, destX, destY, destWidth, destHeight);
        }
    }
}

class Torch extends GameObject {
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

    interact(level) {
        this.toggleState();
    }

    toggleState() {
        if (this.isBurning()) {
            this.off();
        } else {
            this.on();
        }
    }

    on() {
        this.setState("burning");
    }

    off() {
        this.setState("off");
    }
}

class TwoWaySwitch extends GameObject {
    static STATES = ["left", "right"];

    constructor(objectDescription, tileFactory) {
        super(objectDescription, tileFactory, "Switch", TwoWaySwitch.STATES);
    }

    isLeft() {
        return this.getState() === "left";
    }

    isRight() {
        return this.getState() === "right";
    }

    toggleState() {
        if (this.isLeft()) {
            this.right();
        } else {
            this.left();
        }
    }

    interact(level) {
        this.toggleState();
        if (this.getProperty('controls')) {
            const propertyControls = this.getProperty('controls');
            let object = null;
            if (propertyControls) {
                object = level.getObjectById(propertyControls.value);
            } else {
                console.warn(`Switch has no property controls set.`);
            }
            if (object) {
                if (typeof object.interact === 'function') {
                    object.interact(level);
                } else {
                    console.log(`Error: the switch cannot interact with the object with ID "${propertyControls.value}.`)
                }
            } else {
                console.warn(`Object with ID "${propertyControls.value}" not found.`);
            }
        }
    }

    left() {
        this.setState("left");
    }

    right() {
        this.setState("right");
    }
}

class Door extends GameObject {
    static STATES = ["open", "closed"];

    constructor(objectDescription, tileFactory, name=Door.name) {
        super(objectDescription, tileFactory, name, Door.STATES);
    }

    isOpen() {
        return this.getState() === "open";
    }

    toggleState() {
        if (this.isOpen()) {
            this.close();
        } else {
            this.open();
        }
    }

    interact(level) {
        this.toggleState();
    }

    open() {
        this.setState("open");
    }

    close() {
        this.setState("closed");
    }
}

class VerticalDoor extends Door {
    constructor(objectDescription, tileFactory, name=VerticalDoor.name) {
        super(objectDescription, tileFactory, name);
    }
}

class Grille extends Door {
    constructor(objectDescription, tileFactory, name=Grille.name) {
        super(objectDescription, tileFactory, name);
    }
}

class VerticalGrille extends Door {
    constructor(objectDescription, tileFactory, name=VerticalGrille.name) {
        super(objectDescription, tileFactory, name);
    }
}

class Chest extends GameObject {
    static STATES = ["open", "closed"];

    constructor(objectDescription, tileFactory) {
        super(objectDescription, tileFactory, Chest.name, Chest.STATES);
    }

    isOpen() {
        return this.getState() === "open";
    }

    toggleState() {
        if (this.isOpen()) {
            this.close();
        } else {
            this.open();
        }
    }

    interact(level) {
        this.toggleState();
    }

    open() {
        this.setState("open");
    }

    close() {
        this.setState("closed");
    }
}

class Jug extends GameObject {
    static STATES = ["unbroken", "broken"];

    constructor(objectDescription, tileFactory) {
        super(objectDescription, tileFactory, Jug.name, Jug.STATES);
    }

    isBroken() {
        return this.getState() === "broken";
    }

    toggleState() {
        if (!this.isBroken()) {
            this.break();
        } else {
            // cannot repair
        }
    }

    interact(level) {
        this.toggleState();
    }

    break() {
        this.setState("broken");
    }
}

class Goal extends GameObject {
    static STATES = ["default"];

    constructor(objectDescription, tileFactory) {
        super(objectDescription, tileFactory, Goal.name, Goal.STATES);
    }

    interact(level) {
    }
}

class Character extends GameObject {
    static STATES = ["walking", "standing"];
    static DIRECTIONS = ["south", "east", "north", "west"];

    static generateCombinedStrings(array1, array2) {
        const combined = [];
        for (var i = 0; i < 15; i++) {
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

    constructor(objectDescription, tileFactory) {
        const all_states = Character.generateCombinedStrings(Character.STATES, Character.DIRECTIONS);
        super(objectDescription, tileFactory, Character.name, all_states);
        // Movement Properties
        this.targetX = this.x;        // Target pixel x-coordinate for current movement
        this.targetY = this.y;        // Target pixel y-coordinate for current movement
        this.movementProgress = 0;    // 0.0 to 1.0, progress along the current tile move
        this.moveDuration = 1000 / 2; // Duration in ms to move one tile
        this.setName("Alina");
        this.setTypeNumber(7);
    }

    setName(name) {
        this.heroName = name;
    }

    setTypeNumber(typeNumber) {
        this.typeNumber = typeNumber;
        this.setStateAndDirection(this.getState(), this.getDirection());
    }

    isMoving() {
        return this.getState() === "walking";
    }

    isFacingNorth() {
        return this.getDirection() === "north";
    }

    turnLeft() {
        const direction = this.getDirection();
        const state = this.getState();

        if (this.isMoving()) {
            return false;
        }
    
        let newDirection = "north";
        switch (direction) {
            case "north":
                newDirection = "west";
                break;
            case "west":
                newDirection = "south";
                break;
            case "south":
                newDirection = "east";
                break;
            case "east":
                newDirection = "north";
                break;
        }

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

    isCollisionInFront(level, newDirection = this.direction) {
        const newTargetXY = this.getPositionInDirection(newDirection, true);
        return level.isCollision(newTargetXY[0], newTargetXY[1]);
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
            this.targetX = newTargetXY[0];
            this.targetY = newTargetXY[1];
            this.movementProgress = 0;
            this.setStateAndDirection("walking", newDirection);
            
            // Store the exact pixel coordinates where this current movement starts
            this.currentMoveStartX = this.x;
            this.currentMoveStartY = this.y;
            
            return true;
        }
    }

    interact(level) {
        const position = this.getPositionInDirection(this.getDirection(), true);
        const object =  level.getObjectAtPosition(position[0], position[1]);
        if (object) {
            if (typeof object.interact === 'function') {
                object.interact(level);
            } else {
                console.log(`You cannot interact with the object with ID "${object.id}".`)
            }
        } else {
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

    draw(ctx) {
        // For debugging
        ctx.fillStyle = 'black';
        ctx.fillRect(this.x, this.y, 1, 1);

        const newTargetXY = this.getPositionInDirection(this.getDirection(), true);
        ctx.fillStyle = 'red';
        ctx.fillRect(newTargetXY[0], newTargetXY[1], 1, 1);

        super.draw(ctx);
    }

    update(deltaTime) {

        if (this.isMoving()) {
            this.movementProgress += deltaTime; // Accumulate time for movement
            const progressRatio = Math.min(1, this.movementProgress / this.moveDuration);

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

class GameObjectFactory {
    static OBJECT_MAP = new Map([
        ["Torch", Torch],
        ["Switch", TwoWaySwitch],
        ["Door", Door],
        ["VerticalDoor", VerticalDoor],
        ["Grille", Grille],
        ["VerticalGrille", VerticalGrille],
        ["Character", Character],
        ["Chest", Chest],
        ["Jug", Jug],
        ["Goal", Goal]
    ]);

    constructor() {
        this.gameObjects = [];
    }
    
    create(objectDescription, tileFactory) {
        let classConstructor = GameObject;
        const {
            gid,
            type = ""
        } = objectDescription;

        let objectType = type;
        if (objectType === "") {
            const tile = tileFactory.getTileByGlobalTileId(gid);
            if (!tile) {
                console.warn(`Object with invalid tile id "${gid}" found.`);
                objectType = "";
            } else {
                objectType = tile.type;
            }
        }

        if (GameObjectFactory.OBJECT_MAP.has(objectType)) {
            classConstructor = GameObjectFactory.OBJECT_MAP.get(objectType);
        } else {
            console.warn(`Object with type "${objectType}" not defined in Object Map. Check object layer in your level.`)
        }
        const gameObject = new classConstructor(objectDescription, tileFactory, classConstructor.name);
        this.gameObjects.push(gameObject);
        return gameObject;
    }

    getObjectByName(name) {
        for (const object of this.gameObjects) {
            if (object.name === name) {
                return object;
            }
        }

        console.error(`GameObject with name "${name}" not found.`);
        return null;
    }

    getObjectByType(type) {
        for (const object of this.gameObjects) {
            if (object.type === type) {
                return object;
            }
        }

        console.error(`GameObject with type "${type}" not found.`);
        return null;
    }

    getObjectById(id) {
        for (const object of this.gameObjects) {
            if (object.id === id) {
                return object;
            }
        }

        console.error(`GameObject with ID "${id}" not found.`);
        return null;
    }

    getObjectAtPosition(x, y) {
        for (const object of this.gameObjects) {
            if (object.isAtPosition(x, y)) {
                return object;
            }
        }
        return null;
    }
}

/**
 * Represents a complete Tiled level, containing multiple layers.
 */
class Level {
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

    /**
     * Draws all layers of the level onto a 2D rendering context.
     * Layers are drawn in the order they appear in the Tiled JSON.
     * @param {CanvasRenderingContext2D} ctx The 2D rendering context of the canvas.
     */
    draw(ctx) {
        if (!ctx) {
            console.warn("Cannot draw tile layers: ctx not provided.");
            return;
        }

        this.layers.forEach(layer => {
            layer.draw(ctx, this.tileWidth,this.tileHeight);
        });
    }

    getObjectByName(name) {
        return this.objectFactory.getObjectByName(name);
    }

    getObjectByType(type) {
        return this.objectFactory.getObjectByType(type);
    }

    getObjectAtPosition(x, y) {
        return this.objectFactory.getObjectAtPosition(x, y);
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
            } else if (layer instanceof ObjectLayer) {
                const object = this.objectFactory.getObjectAtPosition(x, y);
                if (object) {
                    return object.isCollision();
                }
            }
        }

        return false; // No collision detected
    }
}

class KeyBoardInput {
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

class CharacterInterface {
    constructor(game, level, character) {
        this.game = game;
        this.level = level;
        this.character = character;
    }

    move() {
        return this.character.move(this.character.getDirection(), this.level);
    }

    configure(name, typeNumber) {
        this.character.setName(name);
        this.character.setTypeNumber(typeNumber);
        return true;
    }

    turnLeft() {
        return this.character.turnLeft();
    }

    isFacingNorth() {
        return this.character.isFacingNorth();
    }

    isMoving() {
        return this.character.isMoving();
    }

    interact() {
        return this.character.interact(this.level);
    }



}

export class Game {
    static GAME_STATE = {
        WAITING_FOR_LEVEL: "WAITING", 
        PLAYING: "PLAYING",
        LEVEL_COMPLETE: "LEVEL_COMPLETE"
    };

    constructor(canvas, pathPrefix) {
        this.lastFrameTimeMs = 0;
        this.lastFpsUpdateTime = 0;
        this.framesThisSecond = 0;
        this.updatesThisSecond = 0;
        this.accumulatedTime = 0;
        this.animationFrameId = null;
        this.FIXED_TIME_STEP = 1000 / 60;
        this.goal = null;
        this.level = null;
        this.entryScreenImage = null;
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.inputManager = new KeyBoardInput();
        this.currentGameState = Game.GAME_STATE.WAITING_FOR_LEVEL;
        this.remainingTime = 5000;
        this.character = null;
        this.characterInterface = null;
        this.pathPrefix = pathPrefix;
    }

    async loadLevel(levelData) {
        this.level = await Level.create(levelData, this.pathPrefix);
        this.character = this.level.getObjectByName("MainCharacter");
        this.characterInterface = new CharacterInterface(this, this.level, this.character);
        this.inputManager.setCharacter(this.character);
        console.log("Level successfully loaded.");
        this.currentGameState = Game.GAME_STATE.PLAYING;
        this.remainingTime = 5000;
    }

    start() {
            this.entryScreenImage = new Image();
            this.entryScreenImage.src = this.pathPrefix + 'assets/images/dungeon_coder.png'; // Replace with your image URL or path
            this.entryScreenImage.onload = () => {
            };
            this.entryScreenImage.onerror = () => {
                console.error("Error loading image.");
            };
    
        if (!this.animationFrameId) {
            this.animationFrameId = requestAnimationFrame(this.gameLoop.bind(this));
            console.log("Game loop started.");
        }
    }

    drawDarkOverlay(ctx, canvasWidth, canvasHeight) {
        const opacity = 1 - this.level.getBrightness();
        ctx.fillStyle = `rgba(0, 0, 0, ${opacity})`;
        ctx.fillRect(0, 0, canvasWidth, canvasHeight);
    }

    getCharacterInterface() {
        return this.characterInterface;
    }

    isComplete() {
        return this.level.isComplete();
    }

    gameLoop(currentTime) {
        const deltaTimeMs = currentTime - this.lastFrameTimeMs;
        this.lastFrameTimeMs = currentTime;
        this.accumulatedTime += deltaTimeMs;

        while (this.accumulatedTime >= this.FIXED_TIME_STEP) {
            if (this.currentGameState === Game.GAME_STATE.PLAYING)  {
                if (this.level) {
                    this.level.update(this.FIXED_TIME_STEP);
                }
            }
            this.updatesThisSecond++;
            this.accumulatedTime -= this.FIXED_TIME_STEP;
        }

        const centerX = GAME_WIDTH / 2;
        const centerY = GAME_HEIGHT / 2;
        switch(this.currentGameState) {
            case Game.GAME_STATE.WAITING_FOR_LEVEL:
                this.ctx.drawImage(this.entryScreenImage, 0, 0, GAME_WIDTH, GAME_HEIGHT);
                this.ctx.fillStyle = 'black';
                this.ctx.fillRect(10, GAME_HEIGHT- 30, GAME_WIDTH -20, 20);

                this.ctx.fillStyle = 'green';
                this.ctx.font = `${FONT_SIZE}px Arial`;
                this.ctx.textAlign = 'center';
                this.ctx.textBaseline = 'middle';
                this.ctx.fillText('Use the Python API to connect and load a level!', centerX, GAME_HEIGHT - 20);
                break;
            case Game.GAME_STATE.PLAYING:
                this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
                this.level.draw(this.ctx);
                this.drawDarkOverlay(this.ctx, this.canvas.width, this.canvas.height);
                if (this.level.isComplete()) {
                    this.currentGameState =  Game.GAME_STATE.LEVEL_COMPLETE;
                }
                break;
            case Game.GAME_STATE.LEVEL_COMPLETE:
                this.ctx.globalAlpha = 0.7;
                this.ctx.fillStyle = 'black';
                this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
                this.ctx.globalAlpha = 1.0;

                this.ctx.fillStyle = 'green';
                this.ctx.font = `${FONT_SIZE}px Arial`;
                this.ctx.textAlign = 'center';
                this.ctx.textBaseline = 'middle';
                this.ctx.fillText(`Level Completed! Continue in ${Math.ceil(this.remainingTime / 1000)}s.`, centerX, centerY);
                this.remainingTime -= deltaTimeMs;
                if (this.remainingTime <= 0) {
                    this.currentGameState = Game.GAME_STATE.WAITING_FOR_LEVEL;
                }
                break;
        }

        this.framesThisSecond++;
        this.inputManager.update(deltaTimeMs, this.level);
        this.animationFrameId = requestAnimationFrame(this.gameLoop.bind(this));
    }
}

