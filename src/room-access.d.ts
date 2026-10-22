// Typing for the plain-JS module game/src/room-access.js (shared by the extension and the dev server),
// so extension.ts can import it without allowJs. Keep it in step with that file.
declare module '*room-access.js' {
    export class RoomAccess {
        constructor(exposed?: boolean);
        exposed: boolean;
        static isLoopback(address: unknown): boolean;
        refusal(command: string, address: unknown, params: any): string | null;
        answered(command: string, address: unknown, response: any): void;
    }
}
