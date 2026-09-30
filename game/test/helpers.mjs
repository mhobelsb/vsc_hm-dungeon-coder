/**
 * Runs the game's logic modules (game/src) in Node, without a browser: for unit tests.
 * Tilesets are read from the demo asset pack (packs/demo) on disk; pictures are not
 * loaded (the rules only need a tileset's JSON).
 *
 *     npm run test:engine
 */
import { readFile } from 'node:fs/promises';

const PACK = new URL('../../packs/demo/', import.meta.url);

// what game/src/assets.js and tiles.js expect from a browser
globalThis.window = { DcAssetPackUris: [PACK.href] };
globalThis.fetch = async (url) => {
    try {
        const text = await readFile(new URL(url), 'utf8');
        return { ok: true, json: async () => JSON.parse(text) };
    } catch {
        return { ok: false };
    }
};
globalThis.Image = class {
    set src(value) {
        this.source = value;
        queueMicrotask(() => this.onload && this.onload());
    }
    get src() {
        return this.source;
    }
};
// the engine reports every constructed object and refused action on the console
console.log = () => {};
console.warn = () => {};
const consoleError = console.error;
console.error = (...args) => {          // a test level without a goal is fine
    if (!/^GameObject with type "Goal" not found/.test(String(args[0]))) {
        consoleError(...args);
    }
};

const { Level } = await import('../src/level.js');
const { CharacterInterface } = await import('../src/character.js');
const { Statistics } = await import('../src/statistics.js');

const DIRECTIONS = ['north', 'east', 'south', 'west'];
// local tile ids in the demo pack (tools/make_demo_pack.py); the floor tileset starts at gid 1
const OBJECT_TILES = { Z: 16, T: 4, t: 5, s: 6, d: 8, D: 10, C: 12, J: 14, '*': 17 };
const HERO_FIRST_GID = 25;

/**
 * A level on the demo tiles from rows of symbols:
 * # wall, . floor, ~ abyss, H hero, Z goal, T/t torch, s switch, D vertical door, d door,
 * C chest, J jug, * sweets.
 * @param {string[]} rows
 * @param {{start?: string, size?: number, properties?: object, controls?: Array<[number[], number[]]>}} options
 *   controls: pairs of cells [[x, y], [x, y]]: the object on the first operates the one on the second
 */
export function levelData(rows, { start = 'east', size = 16, properties = {}, controls = [] } = {}) {
    const prefix = size === 32 ? 'demo32' : 'demo';
    const height = rows.length, width = Math.max(...rows.map(r => r.length));
    const floor = [], walls = [], objects = [], idAt = new Map();
    for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
            const c = rows[y][x] ?? ' ';
            floor.push(c === ' ' ? 0 : (c === '~' ? 4 : 2));
            walls.push(c === '#' ? 3 : 0);
            const base = { height: size, width: size, rotation: 0, type: '', visible: true, x: x * size, y: (y + 1) * size };
            if (c === 'H') {
                objects.push({ ...base, id: objects.length + 1, name: 'MainCharacter', gid: HERO_FIRST_GID + 7 * 8 + DIRECTIONS.indexOf(start) * 2 });
            } else if (c in OBJECT_TILES) {
                objects.push({ ...base, id: objects.length + 1, name: '', gid: 1 + OBJECT_TILES[c] });
                idAt.set(`${x},${y}`, objects.length);
            }
        }
    }
    for (const [from, to] of controls) {
        objects[idAt.get(from.join(',')) - 1].properties = [{ name: 'controls', type: 'object', value: idAt.get(to.join(',')) }];
    }
    const layer = (id, name, data, collision) => ({
        data, height, width, id, name, opacity: 1, type: 'tilelayer', visible: true, x: 0, y: 0,
        ...(collision ? { properties: [{ name: 'collision', type: 'bool', value: true }] } : {}),
    });
    return {
        height, width, infinite: false, orientation: 'orthogonal', renderorder: 'right-down', tileheight: size, tilewidth: size,
        type: 'map', version: '1.10', nextlayerid: 4, nextobjectid: objects.length + 1,
        properties: Object.entries(properties).map(([name, value]) =>
            ({ name, type: typeof value === 'boolean' ? 'bool' : (Number.isInteger(value) ? 'int' : 'string'), value })),
        tilesets: [{ firstgid: 1, source: `../tilesets/${prefix}_tiles.json` }, { firstgid: HERO_FIRST_GID, source: `../tilesets/${prefix}_hero.json` }],
        layers: [layer(1, 'Floor', floor, false), layer(2, 'Walls', walls, true),
            { draworder: 'topdown', id: 3, name: 'Objects', objects, opacity: 1, type: 'objectgroup', visible: true, x: 0, y: 0 }],
    };
}

/** A loaded level with the hero's interface, as the game wires them (no fog). */
export async function play(rows, options) {
    const level = await Level.create(levelData(rows, options));
    const statistics = new Statistics();
    const hero = new CharacterInterface({ fog: null }, level, level.character, statistics);
    return { level, hero, character: level.character, statistics };
}

/** Lets game time pass in the game's fixed steps (60 per second). */
export function advance(level, milliseconds) {
    const step = 1000 / 60;
    for (let t = 0; t < milliseconds; t += step) {
        level.update(step);
    }
}

/** move() and wait until the step is done (a step takes 500 ms at pace 1). */
export function step(game) {
    const moved = game.hero.move();
    advance(game.level, 600);
    return moved;
}

export function turn(game, times = 1) {
    for (let i = 0; i < times; i++) {
        game.hero.turnLeft();
    }
}
