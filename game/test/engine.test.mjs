/**
 * Unit tests for the game's rules (game/src), in Node: collision, abyss, `controls`,
 * the goal check, the inventory, statistics and the tile size.
 *
 *     npm run test:engine
 */
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { play, step, turn, advance } from './helpers.mjs';

test('collision: a wall stops the hero, floor lets it pass', async () => {
    const game = await play(['#####', '#H.##', '#####']);
    assert.equal(game.hero.isCollisionInFront(), false);
    assert.equal(step(game), true);
    assert.deepEqual(game.character.currentCell(), [2, 1]);
    assert.equal(game.hero.isCollisionInFront(), true);
    assert.equal(step(game), false);
    assert.deepEqual(game.character.currentCell(), [2, 1]);
});

test('collision: outside the level counts as a wall', async () => {
    const game = await play(['H.'], { start: 'west' });
    assert.equal(game.hero.isCollisionInFront(), true);
    assert.equal(step(game), false);
});

test('turning: four left turns go north, west, south, east; only north is sensed', async () => {
    const game = await play(['###', '#H#', '###'], { start: 'north' });
    const seen = [];
    for (let i = 0; i < 4; i++) {
        seen.push([game.character.getDirection(), game.hero.isFacingNorth()]);
        turn(game);
    }
    assert.deepEqual(seen, [['north', true], ['west', false], ['south', false], ['east', false]]);
    assert.equal(game.character.getDirection(), 'north');
});

test('moving: a second move during a step is refused', async () => {
    const game = await play(['#####', '#H..#', '#####']);
    assert.equal(game.hero.move(), true);
    assert.equal(game.hero.isMoving(), true);
    assert.equal(game.hero.move(), false);
    advance(game.level, 600);
    assert.equal(game.hero.isMoving(), false);
    assert.deepEqual(game.character.currentCell(), [2, 1]);
});

test('abyss: it is sensed, and stepping into it means falling, then death', async () => {
    const game = await play(['####', '#H~#', '####']);
    assert.equal(game.hero.isAbyssInFront(), true);
    assert.equal(game.hero.isCollisionInFront(), false);
    assert.equal(game.hero.move(), true);
    assert.equal(game.character.isFalling(), true);
    assert.equal(game.character.isDead(), false);
    assert.equal(game.hero.getStatistics().game_over, true);
    advance(game.level, 3100);
    assert.equal(game.character.isDead(), true);
});

test('controls: a switch opens the door it controls', async () => {
    const game = await play(['#####', '#H.D.', '#s###'], { controls: [[[1, 2], [3, 1]]] });
    step(game);
    assert.equal(game.hero.isCollisionInFront(), true, 'the closed door blocks');
    turn(game, 2);
    step(game);                                  // back to the start, facing west
    turn(game);                                  // south: the switch
    assert.equal(game.hero.isSwitchInFront(), true);
    assert.equal(game.hero.interact(), true);
    turn(game);                                  // east
    step(game);
    assert.equal(game.hero.isCollisionInFront(), false, 'the open door lets the hero pass');
    assert.equal(step(game), true);
    assert.deepEqual(game.character.currentCell(), [3, 1]);
});

test('interact: true only if an object reacted (D4)', async () => {
    const game = await play(['####', '#Ht#', '####']);
    assert.equal(game.hero.isTorchInFront(), true);
    assert.equal(game.hero.interact(), true);
    turn(game);                                  // north: a wall
    assert.equal(game.hero.interact(), false);
});

test('goal: reached only when the step is finished, not while the hero is still walking (B11)', async () => {
    const game = await play(['####', '#HZ#', '####']);
    assert.equal(game.level.isHeroOnGoal(), false);
    game.hero.move();
    let early = false;
    for (let t = 0; t < 480; t += 1000 / 60) {   // a step takes 500 ms
        game.level.update(1000 / 60);
        early = early || game.level.isHeroOnGoal() || game.level.isComplete();
    }
    assert.equal(early, false);
    advance(game.level, 200);
    assert.equal(game.level.isHeroOnGoal(), true);
    assert.equal(game.level.isComplete(), true);
});

test('inventory: pick up, carry, drop; items are seen only on the own field', async () => {
    const game = await play(['#####', '#H*.#', '#####']);
    assert.deepEqual(game.hero.getItemsAtHeroPosition(), []);
    assert.equal(game.hero.pickup('Sweets'), false);
    step(game);
    assert.deepEqual(game.hero.getItemsAtHeroPosition(), ['Sweets']);
    assert.equal(game.hero.pickup('Sweets'), true);
    assert.deepEqual(game.hero.getInventory(), ['Sweets']);
    assert.deepEqual(game.hero.getItemsAtHeroPosition(), []);
    step(game);
    assert.equal(game.hero.drop('Sweets'), true);
    assert.deepEqual(game.hero.getInventory(), []);
    assert.deepEqual(game.hero.getItemsAtHeroPosition(), ['Sweets']);
    assert.equal(game.hero.drop('Sweets'), false);
});

test('inventory: inventory_size limits what the hero can carry', async () => {
    const game = await play(['#####', '#H**#', '#####'], { properties: { inventory_size: 1 } });
    step(game);
    assert.equal(game.hero.pickup('Sweets'), true);
    step(game);
    assert.equal(game.hero.isInventoryFull(), true);
    assert.equal(game.hero.pickup('Sweets'), false);
});

test('win conditions: all_sweets keeps the level open on the goal until everything is collected', async () => {
    const game = await play(['#####', '#H*Z#', '#####'], { properties: { win: 'all_sweets' } });
    step(game);
    step(game);
    assert.equal(game.level.isHeroOnGoal(), true);
    assert.equal(game.level.isComplete(), false);
    assert.equal(game.level.unmetWinConditions().length, 1);
    turn(game, 2);
    step(game);
    game.hero.pickup('Sweets');
    turn(game, 2);
    step(game);
    assert.equal(game.level.isComplete(), true);
});

test('statistics: moves, bumps, turns, interactions, pickups and sensor calls are counted', async () => {
    const game = await play(['####', '#H*#', '####']);
    step(game);                                  // move
    step(game);                                  // bump
    turn(game);
    game.hero.isCollisionInFront();
    game.hero.interact();
    game.hero.pickup('Sweets');
    const s = game.hero.getStatistics();
    assert.deepEqual([s.moves, s.bumps, s.turns, s.sensor_calls, s.interactions, s.pickups], [1, 1, 1, 1, 1, 1]);
});

test('tile size: on 32 px tiles one step is 32 px and the rules are the same', async () => {
    const game = await play(['#####', '#H.~#', '#####'], { size: 32 });
    const x = game.character.x;
    assert.equal(step(game), true);
    assert.equal(game.character.x, x + 32);
    assert.deepEqual(game.character.currentCell(), [2, 1]);
    assert.equal(game.hero.isAbyssInFront(), true);
});

test('flip flags: a mirrored tile keeps its rules (wall, abyss, goal), only the picture is mirrored', async () => {
    const { Level } = await import('../src/level.js');
    const { levelData } = await import('./helpers.mjs');
    const data = levelData(['#####', '#H~Z#', '#####']);
    const H = 0x80000000, V = 0x40000000, D = 0x20000000;
    const [floor, walls, objects] = data.layers;
    walls.data = walls.data.map(gid => (gid ? gid + H + V : 0));
    floor.data = floor.data.map(gid => (gid ? gid + D : 0));
    const goal = objects.objects.find(o => o.gid === 1 + 16);
    goal.gid += H;
    const level = await Level.create(data);
    const hero = level.character;
    assert.equal(level.tileFactory.getTileByGlobalTileId(walls.data[0]).flipH, true);
    assert.equal(level.tileFactory.getTileByGlobalTileId(walls.data[0]).flipV, true);
    const { CharacterInterface } = await import('../src/character.js');
    const { Statistics } = await import('../src/statistics.js');
    const face = new CharacterInterface({ fog: null }, level, hero, new Statistics());
    assert.equal(face.isAbyssInFront(), true);              // the mirrored abyss is still an abyss
    turn({ hero: face }, 1);                                // north: a mirrored wall
    assert.equal(face.isCollisionInFront(), true);
    assert.ok(level.objectFactory.gameObjects.some(o => o.type === 'Goal' && o.tile.flipH === true));
});

test('a tileset no asset pack has refuses the level with a message (bug B24)', async () => {
    const { Level } = await import('../src/level.js');
    const { MissingTilesetError } = await import('../src/tiles.js');
    const { levelData } = await import('./helpers.mjs');
    const data = levelData(['####', '#HZ#', '####']);
    data.tilesets[0] = { ...data.tilesets[0], source: '../tilesets/gibt_es_nicht.json' };
    await assert.rejects(Level.create(data), error => error instanceof MissingTilesetError
        && error.sources.length === 1 && /gibt_es_nicht.*dungeonCoder\.assetPacks/.test(error.message));
    // a level that names its asset pack (map property pack, G5): the message says which pack to get
    data.properties = [{ name: 'pack', type: 'string', value: 'dungeon-coder-assets' }];
    await assert.rejects(Level.create(data), error => error instanceof MissingTilesetError
        && error.pack === 'dungeon-coder-assets' && /needs the asset pack "dungeon-coder-assets"/.test(error.message));
});

test('start inventory: the item tiles come from the pack manifest (pack.json "items", gap G3)', async () => {
    const game = await play(['#####', '#H.Z#', '#####'], { properties: { hero_inventory: 'Pebble*3, Crystal' } });
    assert.deepEqual(game.hero.getInventory(), ['Pebble', 'Pebble', 'Pebble', 'Crystal']);
    // the demo pack names its own tiles: pebble local 20, white crystal local 18 (tools/make_demo_pack.py)
    const pebble = game.character.inventory[0];
    assert.equal(pebble.tile, game.level.tileFactory.getTileByGlobalTileId(1 + 20));
    assert.equal(game.hero.drop('Pebble'), true);
    assert.deepEqual(game.hero.getItemsAtHeroPosition(), ['Pebble']);
    // an item type no pack names isn't given (the game warns), the others are
    const other = await play(['#####', '#H.Z#', '#####'], { properties: { hero_inventory: 'Feder*2, Pebble' } });
    assert.deepEqual(other.hero.getInventory(), ['Pebble']);
});

test('the bundled assets name the same items for the game and for the Python package (sim, map builder)', async () => {
    const { readFile } = await import('node:fs/promises');
    const read = async (path) => JSON.parse(await readFile(new URL(path, import.meta.url), 'utf8'));
    const game = await read('../assets/pack.json');
    const python = await read('../../api/python/dungeoncoder/packs/items.json');
    assert.deepEqual(python.items, game.items);
});

test('sensing (DC-T1j): a sensor marks the cell it looked at, with its answer', async () => {
    const { Sensing } = await import('../src/sensing.js');
    const { Level } = await import('../src/level.js');
    const { CharacterInterface } = await import('../src/character.js');
    const { Statistics } = await import('../src/statistics.js');
    const { levelData } = await import('./helpers.mjs');
    const level = await Level.create(levelData(['#####', '#Hs.#', '#####']));
    const sensing = new Sensing();
    const hero = new CharacterInterface({ fog: null, sensing }, level, level.character, new Statistics());
    assert.equal(hero.isSwitchInFront(), true);
    assert.deepEqual([...sensing.marks.values()].map(m => [m.col, m.row, m.positive]), [[2, 1, true]]);
    assert.equal(hero.isAbyssInFront(), false);
    assert.equal(sensing.marks.get('2,1').positive, false);
    sensing.update(Sensing.FLASH_MS + 1);
    assert.equal(sensing.marks.size, 0);
    const off = new Sensing(false);
    off.mark(1, 1, true);
    assert.equal(off.marks.size, 0);
});

test('call log (DC-T1j): one line per call, as Python writes values', async () => {
    const { CallLog } = await import('../src/call-log.js');
    const ok = (result, success = true, message = '') => ({ result: { success, result, message } });
    assert.equal(CallLog.describe('move', null, ok(true)), 'move()  ✓');
    assert.equal(CallLog.describe('move', null, ok(false, false, 'Moving failed. Way is blocked.')), 'move()  ✗ blocked');
    assert.equal(CallLog.describe('is_switch_in_front', null, ok(false)), 'is_switch_in_front()  → False');
    assert.equal(CallLog.describe('get_items_at_position', null, ok(['Sweets'])), "get_items_at_position()  → ['Sweets']");
    assert.equal(CallLog.describe('pickup', { name: 'Sweets', hero: 1 }, ok(true)), "heroes[1]: pickup('Sweets')  ✓");
    assert.equal(CallLog.describe('is_moving', null, ok(false)), null);
    const log = new CallLog(null);
    for (let i = 0; i < 12; i++) {
        log.add('turn_left', null, ok(true));
    }
    assert.equal(log.entries.length, CallLog.LENGTH);
    log.add('load_level', {}, ok(true));
    assert.deepEqual(log.entries, ['— level loaded —']);
});

test('co-op (DC-T3c): Hero2 is a second hero, heroes block each other, all_heroes', async () => {
    const { Level } = await import('../src/level.js');
    const { CharacterInterface } = await import('../src/character.js');
    const { Statistics } = await import('../src/statistics.js');
    const { levelData, advance } = await import('./helpers.mjs');
    const data = levelData(['######', '#H..Z#', '#...Z#', '######'], { properties: { win: 'all_heroes' } });
    const objects = data.layers[2].objects;
    const main = objects.find(o => o.name === 'MainCharacter');
    objects.push({ ...main, id: 99, name: 'Hero2', y: main.y + 16 });
    const level = await Level.create(data);
    assert.equal(level.heroes.length, 2);
    const statistics = new Statistics();
    const [a, b] = level.heroes.map(h => new CharacterInterface({ fog: null }, level, h, statistics));
    b.turnLeft();                       // east -> north: hero 1 is in front
    assert.equal(b.isCollisionInFront(), true);
    assert.equal(b.move(), false);
    for (let i = 0; i < 3; i++) {
        b.turnLeft();
    }
    for (let i = 0; i < 3; i++) {
        a.move();
        b.move();
        advance(level, 600);
    }
    assert.deepEqual(level.unmetWinConditions(), []);
    assert.equal(level.isComplete(), true);
});

test('variants: a Region rectangle never becomes a game object', async () => {
    const { Level } = await import('../src/level.js');
    const { levelData } = await import('./helpers.mjs');
    const data = levelData(['#####', '#H.s#', '#####']);
    data.layers[2].objects.push({ id: 50, name: 'region1', type: 'Region', x: 16, y: 16, width: 48, height: 16, visible: false });
    const level = await Level.create(data);
    assert.equal(level.objectFactory.gameObjects.some(o => o.type === 'Region'), false);
});

test('call log (show_calls): off unless the level switches it on; L still toggles it', async () => {
    const { CallLog } = await import('../src/call-log.js');
    const element = { hidden: false };
    const log = new CallLog(element);
    const plain = await play(['#####', '#H.Z#', '#####']);
    log.showFor(plain.level);
    assert.equal(element.hidden, true);
    const shown = await play(['#####', '#H.Z#', '#####'], { properties: { show_calls: true } });
    log.showFor(shown.level);
    assert.equal(element.hidden, false);
    log.toggle();
    assert.equal(element.hidden, true);
    const off = await play(['#####', '#H.Z#', '#####'], { properties: { show_calls: false } });
    log.toggle();
    log.showFor(off.level);                 // each level load decides anew
    assert.equal(element.hidden, true);
});
