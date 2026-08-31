// Ambient typing for the plain-JS, generated config modules under game/src/
// (commands.js, api-config.js), so extension.ts can import them without
// pulling the untyped game/ tree into TypeScript's compilation graph (no
// `allowJs`).
declare module '*commands.js' {
    export const COMMANDS: {
        readonly LOAD_LEVEL: 'load_level';
        readonly RESET_LEVEL: 'reset_level';
        readonly MOVE: 'move';
        readonly INTERACT: 'interact';
        readonly TURN_LEFT: 'turn_left';
        readonly IS_MOVING: 'is_moving';
        readonly CONFIGURE: 'configure';
        readonly IS_FACING_NORTH: 'is_facing_north';
        readonly IS_AT_GOAL: 'is_at_goal';
        readonly IS_COLLISION_IN_FRONT: 'is_collision_in_front';
        readonly IS_ABYSS_IN_FRONT: 'is_abyss_in_front';
        readonly IS_TORCH_IN_FRONT: 'is_torch_in_front';
        readonly IS_SWITCH_IN_FRONT: 'is_switch_in_front';
        readonly GET_ITEMS_AT_POSITION: 'get_items_at_position';
        readonly GET_INVENTORY: 'get_inventory';
        readonly PICKUP: 'pickup';
        readonly DROP: 'drop';
        readonly SET_PACE: 'set_pace';
    };
    export const COMMAND_LIST: readonly string[];
}

declare module '*api-config.js' {
    export const API_HOST: string;
    export const API_PORT: number;
    export const API_BASE_URL: string;
}
