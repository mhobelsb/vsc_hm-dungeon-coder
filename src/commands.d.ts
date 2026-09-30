// GENERATED FILE - do not edit by hand.
// Source: api/openapi.yaml, via tools/generate-commands.mjs (npm run generate).
//
// Ambient typing for the plain-JS, generated config modules under game/src/
// (commands.js, api-config.js), so extension.ts can import them without
// pulling the untyped game/ tree into TypeScript's compilation graph (no
// `allowJs`).
declare module '*commands.js' {
    export const COMMANDS: {
        readonly MOVE: 'move';
        readonly TURN_LEFT: 'turn_left';
        readonly INTERACT: 'interact';
        readonly CONFIGURE: 'configure';
        readonly SET_PACE: 'set_pace';
        readonly PICKUP: 'pickup';
        readonly DROP: 'drop';
        readonly GET_ITEMS_AT_POSITION: 'get_items_at_position';
        readonly IS_ENEMY_IN_FRONT: 'is_enemy_in_front';
        readonly ASK_ORACLE: 'ask_oracle';
        readonly READ_ITEM_VALUE: 'read_item_value';
        readonly PEEK_ITEM_VALUE: 'peek_item_value';
        readonly GET_INVENTORY: 'get_inventory';
        readonly IS_COLLISION_IN_FRONT: 'is_collision_in_front';
        readonly IS_FACING_NORTH: 'is_facing_north';
        readonly IS_AT_GOAL: 'is_at_goal';
        readonly IS_TORCH_IN_FRONT: 'is_torch_in_front';
        readonly IS_SWITCH_IN_FRONT: 'is_switch_in_front';
        readonly IS_ABYSS_IN_FRONT: 'is_abyss_in_front';
        readonly GET_STATISTICS: 'get_statistics';
        readonly LOAD_LEVEL: 'load_level';
        readonly RESET_LEVEL: 'reset_level';
        readonly IS_MOVING: 'is_moving';
    };
    export const COMMAND_LIST: readonly string[];
    export const ROUTES: readonly { method: 'get' | 'post'; path: string; command: string; body: boolean }[];
}

declare module '*api-config.js' {
    export const API_HOST: string;
    export const API_PORT: number;
    export const API_BASE_URL: string;
}
