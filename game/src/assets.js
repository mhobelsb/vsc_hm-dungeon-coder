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
