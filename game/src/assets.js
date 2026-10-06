/**
 * Asset packs (D8a). A pack is a folder like game/assets/: tilesets/*.json, images/*,
 * optionally a pack.json manifest. Levels name their tilesets as "../tilesets/x.json";
 * the engine looks for them in the configured packs first (VS Code setting
 * dungeonCoder.assetPacks, or DC_ASSET_PACKS for the dev server), then in the
 * extension's own assets folder. So the public extension can ship a free demo pack,
 * while course art comes from a private pack on the student's disk.
 */

/** The base URLs to search, each ending in "/": configured packs, then the bundled assets. */
export function assetBases(pathPrefix = "") {
    const configured = Array.isArray(window.DcAssetPackUris) ? window.DcAssetPackUris : [];
    return [...configured.map(u => (u.endsWith("/") ? u : u + "/")), pathPrefix + "assets/"];
}

/** "../tilesets/x.json" -> "tilesets/x.json" (a path inside a pack). */
export function packPath(levelRelative) {
    return levelRelative.replace(/^(\.\.\/)+/, "");
}

/**
 * Loads a JSON file from the first base that has it.
 * @returns {Promise<{base: string, data: object}|null>}
 */
export async function loadFromPacks(relativePath, pathPrefix = "") {
    for (const base of assetBases(pathPrefix)) {
        try {
            const response = await fetch(base + relativePath);
            if (response.ok) {
                return { base, data: await response.json() };
            }
        } catch (e) {
            // not in this pack: try the next one
        }
    }
    console.error(`Could not load ${relativePath} from any asset pack (${assetBases(pathPrefix).join(", ")}).`);
    return null;
}

/** An Image that tries each base in turn until one loads (screens, title images). */
export function imageFromPacks(relativePath, pathPrefix = "") {
    const bases = assetBases(pathPrefix);
    const image = new Image();
    let i = 0;
    image.onerror = () => {
        i += 1;
        if (i < bases.length) {
            image.src = bases[i] + relativePath;
        } else {
            console.error(`Could not load image ${relativePath} from any asset pack.`);
        }
    };
    image.src = bases[0] + relativePath;
    return image;
}

/**
 * The tiles of the items the engine creates itself (the start inventory, map property
 * `hero_inventory`), from the packs' manifests: pack.json may name them as
 *     "items": {"Pebble": {"tileset": "x.json", "tile": 20}, "Crystal": {...}}
 * The first pack that names an item wins (the same order as for tilesets).
 * @returns {Promise<Object<string, {source: string, local: number}>>} item type -> level-relative tileset and local id
 */
export async function loadItemTiles(pathPrefix = "") {
    const items = {};
    for (const base of assetBases(pathPrefix)) {
        let manifest = null;
        try {
            const response = await fetch(base + "pack.json");
            manifest = response.ok ? await response.json() : null;
        } catch (e) {
            // a pack without a manifest names no items
        }
        for (const [type, spec] of Object.entries(manifest?.items ?? {})) {
            if (!(type in items) && spec && typeof spec.tileset === "string" && Number.isInteger(spec.tile)) {
                items[type] = { source: "../tilesets/" + spec.tileset, local: spec.tile };
            }
        }
    }
    return items;
}
