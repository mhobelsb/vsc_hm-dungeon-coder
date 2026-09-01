// Extracted from Game so both game.js and rendering/game-renderer.js can
// reference the same state values without an import cycle between them.
export const GAME_STATE = {
    WAITING_FOR_LEVEL: "WAITING",
    PLAYING: "PLAYING",
    LEVEL_COMPLETE: "LEVEL_COMPLETE",
    GAME_OVER: "GAME_OVER"
};
