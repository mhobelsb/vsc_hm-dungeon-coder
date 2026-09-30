import { GameObject, Torch, TwoWaySwitch, Door, VerticalDoor, PatternDoor, Grille, VerticalGrille, Chest, Jug, Goal, Item, Guard } from './game-objects.js';
import { Character } from './character.js';

export class GameObjectFactory {
    static OBJECT_MAP = new Map([
        ["Torch", Torch],
        ["Switch", TwoWaySwitch],
        ["Door", Door],
        ["VerticalDoor", VerticalDoor],
        ["PatternDoor", PatternDoor],
        ["Grille", Grille],
        ["VerticalGrille", VerticalGrille],
        ["Character", Character],
        ["Chest", Chest],
        ["Jug", Jug],
        ["Goal", Goal],
        ["Crystal", Item],
        ["Pebble", Item],
        ["Guard", Guard]
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
                objectType = "Unknown Object";
            } else {
                objectType = tile.type;
            }
        }

        if (GameObjectFactory.OBJECT_MAP.has(objectType)) {
            classConstructor = GameObjectFactory.OBJECT_MAP.get(objectType);
        } else {
            console.warn(`Object with type "${objectType}" not defined in Object Map. Check object layer in your level.`);
        }
        const gameObject = new classConstructor(objectDescription, tileFactory, objectType);
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

    getObjectsAtPosition(x, y) {
        let objects = [];
        for (const object of this.gameObjects) {
            if (object.isAtPosition(x, y)) {
                objects.push(object);
            }
        }
        return objects;
    }
}
