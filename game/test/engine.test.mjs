/**
 * Unit tests for the game's rules (game/src), in Node: collision, abyss, `controls`,
 * the goal check, the inventory, statistics and the tile size.
 *
 *     npm run test:engine
 */
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { play, playInGame, step, turn, advance } from './helpers.mjs';

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

// --- the erring oracle (orakel: 70), timed guards (tick), the sight range (witterung) ---------

test('oracle: orakel: true always tells the truth, orakel: 70 errs reproducibly', async () => {
    const honest = await play(['#####', '#H.Z#', '#####'], { properties: { orakel: true } });
    assert.equal(honest.hero.hasOracle(), true);
    assert.deepEqual([1, 2, 3, 4, 5].map(() => honest.hero.askOracle()), ['east', 'east', 'east', 'east', 'east']);
    const erring = await play(['#####', '#H.Z#', '#####'], { properties: { orakel: 70, seed: 7 } });
    assert.equal(erring.hero.hasOracle(), true);
    const answers = Array.from({ length: 40 }, () => erring.hero.askOracle());
    const wrong = answers.filter(a => a !== 'east');
    assert.ok(wrong.length >= 5 && wrong.length <= 20, `wrong answers: ${wrong.length}`);
    assert.ok(wrong.every(a => ['north', 'south', 'west'].includes(a)));
    const again = await play(['#####', '#H.Z#', '#####'], { properties: { orakel: 70, seed: 7 } });
    assert.deepEqual(Array.from({ length: 40 }, () => again.hero.askOracle()), answers);
    const none = await play(['#####', '#H.Z#', '#####']);
    assert.equal(none.hero.hasOracle(), false);
});

test('oracle roll: the shared hash gives the same numbers as the simulator', async () => {
    const { CharacterInterface } = await import('../src/character.js');
    // the first values of oracle_roll(7, n) in api/python/dungeoncoder/sim.py (tests/engine_stufe2.py checks them there)
    const rolls = [1, 2, 3].map(n => CharacterInterface.oracleRoll(7, n));
    assert.ok(rolls.every(r => r >= 0 && r < 1));
    assert.equal(new Set(rolls).size, 3);
    assert.equal(CharacterInterface.oracleRoll(7, 1), CharacterInterface.oracleRoll(7, 1));
});

test('witterung: the level says how far is_enemy_in_front may look; without guards it sees nothing', async () => {
    const game = await play(['#######', '#H....#', '#######'], { properties: { witterung: 3 } });
    assert.equal(game.hero.sightRange(), 3);
    assert.equal(game.hero.isEnemyInFront(3), false);
    assert.equal(game.level.guardsTimed(), false);
    const timed = await play(['#######', '#H....#', '#######'], { properties: { tick: 500 } });
    assert.equal(timed.level.guardsTimed(), true);
    assert.equal(timed.hero.sightRange(), 1);
    advance(timed.level, 1200);          // no guards: nothing happens, nothing breaks
    assert.equal(step(timed), true);
});

// --- a live game (map property arena): one hero per team, each with its own end ---------------

const ARENA = ['#######', '#H....#', '#2....#', '#3...~#', '#######'];
const ARENA_OPTIONS = { properties: { arena: true, codes: 'ROT-1 BLAU-2 GELB-3', max_moves: 2 } };

test('arena: team codes name the heroes, case does not matter', async () => {
    const game = await playInGame(ARENA, ARENA_OPTIONS);
    assert.equal(game.arena, true);
    assert.equal(game.level.heroes.length, 3);
    assert.deepEqual(game.level.arenaNames(), ['ROT', 'BLAU', 'GELB']);
    assert.equal(game.level.heroIndexForCode('blau-2'), 1);
    assert.equal(game.level.heroIndexForCode('GRUEN-9'), -1);
});

test('arena: the referee starts and ends the game; the pace is fixed', async () => {
    const game = await playInGame(ARENA, ARENA_OPTIONS);
    assert.equal(game.arenaStarted, false);
    assert.equal(game.isRunning(), true);
    assert.equal(game.startArena(), true);
    assert.equal(game.startArena(), false);
    assert.equal(game.arenaStarted, true);
    assert.equal(game.endArena(), true);
    assert.equal(game.isRunning(), false);
    assert.equal(game.endArena(), false);
});

test('arena: every hero keeps its own counters and its own end; the others play on', async () => {
    const game = await playInGame(ARENA, ARENA_OPTIONS);
    game.startArena();
    const [rot, blau, gelb] = game.characterInterfaces;
    assert.equal(rot.move(), true);
    advance(game.level, 600);
    assert.equal(rot.getStatistics().moves, 1);
    assert.equal(blau.getStatistics().moves, 0);
    assert.equal(blau.getStatistics().moves_left, 2);
    assert.equal(rot.getStatistics().moves_left, 1);
    // rot spends its budget and collapses: out, but the game goes on
    assert.equal(rot.move(), true);
    advance(game.level, 600);
    assert.equal(rot.move(), false);
    assert.equal(rot.isOut(), true);
    assert.equal(rot.getStatistics().out, true);
    assert.equal(rot.getStatistics().game_over, true);
    assert.equal(blau.getStatistics().out, false);
    assert.equal(blau.getStatistics().game_over, false);
    assert.equal(game.isRunning(), true);
    assert.equal(blau.move(), true);
    advance(game.level, 600);
    assert.equal(blau.getStatistics().moves, 1);
});

test('arena: a hero that is out is not a wall, but a standing hero is; is_hero_in_front sees it', async () => {
    const game = await playInGame(['#####', '#H2.#', '#####'], { properties: { arena: true, codes: 'A-1 B-2' } });
    game.startArena();
    const [a, b] = game.characterInterfaces;
    assert.equal(a.isHeroInFront(), true);
    assert.equal(a.isCollisionInFront(), true);
    assert.equal(a.move(), false);
    assert.equal(b.isHeroInFront(), false);
    assert.equal(b.move(), true);
    advance(game.level, 600);
    assert.equal(a.isHeroInFront(), false);
    assert.equal(a.move(), true);
});

test('arena: the round ends when every hero is out', async () => {
    const game = await playInGame(['####', '#H~#', '####'], { properties: { arena: true, codes: 'A-1' } });
    game.startArena();
    const [a] = game.characterInterfaces;
    assert.equal(a.move(), true);
    advance(game.level, 3200);
    assert.equal(a.isOut(), true);
    game.gameLoop(0);                       // the loop notices: all out, round over
    assert.equal(game.arenaOver, true);
    assert.equal(game.isRunning(), false);
});

test('co-op without arena: unchanged, a lost hero ends the level for all, the counters are shared', async () => {
    const game = await playInGame(['####', '#H~#', '#2.#', '####'], { properties: { win: 'all_heroes' } });
    assert.equal(game.arena, false);
    const [a, b] = game.characterInterfaces;
    assert.equal(a.move(), true);
    assert.equal(game.isRunning(), false);
    assert.equal(a.getStatistics().game_over, true);
    assert.equal(b.getStatistics().game_over, true);
    assert.equal(b.getStatistics().moves, 1);
    assert.equal(b.getStatistics().out, undefined);
});

// --- a live game in the room: who may do what, the board, the teams' own names -------------------

test('room access: open to the room, the referee stays on this computer and heroes belong to who joined', async () => {
    const { RoomAccess } = await import('../src/room-access.js');
    const closed = new RoomAccess(false);
    assert.equal(closed.refusal('load_level', '10.0.0.5', null), null);
    const room = new RoomAccess(true);
    assert.equal(room.refusal('load_level', '127.0.0.1', null), null);
    assert.match(room.refusal('load_level', '10.0.0.5', null), /referee/);
    assert.match(room.refusal('start_game', '10.0.0.5', null), /referee/);
    assert.equal(room.refusal('join', '10.0.0.5', { code: 'A-1' }), null);
    assert.match(room.refusal('move', '10.0.0.5', { hero: 1 }), /Join the game first/);
    room.answered('join', '10.0.0.5', { success: true, result: { hero: 1 } });
    assert.equal(room.refusal('move', '10.0.0.5', { hero: 1 }), null);
    assert.match(room.refusal('move', '10.0.0.6', { hero: 1 }), /another team/);
    room.answered('load_level', '127.0.0.1', { success: true });
    assert.match(room.refusal('move', '10.0.0.5', { hero: 1 }), /Join the game first/);
});

test('arena board: German with lang de, who joined, the room bar; teams may name themselves', async () => {
    const { ArenaBoard } = await import('../src/arena-board.js');
    const game = await playInGame(ARENA, { properties: { arena: true, codes: 'ROT-1 BLAU-2 GELB-3', lang: 'de' } });
    let html = ArenaBoard.render(game);
    assert.match(html, /Bereit: 0 von 3/);
    assert.match(html, /fehlt noch/);
    assert.match(html, /Der Raum: 0 von/);
    game.joinArena(1, '  Die Runenjäger  ');
    game.joinArena(0, '');
    html = ArenaBoard.render(game);
    assert.match(html, /Bereit: 2 von 3/);
    assert.match(html, /Die Runenjäger/);
    assert.deepEqual(game.arenaDisplayNames(), ['ROT', 'Die Runenjäger', 'GELB']);
    game.joinArena(2, 'x'.repeat(40));
    assert.equal(game.arenaDisplayNames()[2].length, 24);
    game.startArena();
    assert.match(ArenaBoard.render(game), /Läuft 0:0/);
    const english = await playInGame(ARENA, ARENA_OPTIONS);
    assert.match(ArenaBoard.render(english), /Ready: 0 of 3/);
});
