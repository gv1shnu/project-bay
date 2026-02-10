/**
 * utils/avatar.ts — Deterministic avatar URL generation.
 *
 * Generates consistent avatar URLs using the DiceBear API.
 * Same username → always the same avatar style and appearance.
 * This avoids needing users to upload profile pictures.
 */

// Available DiceBear avatar styles — each produces a different art style
const AVATAR_STYLES = [
    'lorelei',          // Minimalist line-drawn faces
    'adventurer',       // Colorful cartoon faces
    'pixel-art',        // 8-bit retro pixel style
    'bottts',           // Robot/bot faces
    'avataaars',        // Cartoon people (like Bitmoji)
    'big-ears',         // Characters with big ears
    'micah',            // Modern illustrated faces
] as const;


/**
 * Generate a deterministic avatar URL for a username.
 *
 * The style is picked by hashing the username into a number,
 * so the same username always maps to the same avatar style.
 *
 * @param username - The user's username
 * @returns A DiceBear API URL that returns an SVG avatar
 */
export const getAvatarUrl = (username: string): string => {
    // Simple hash: sum of all character codes → mod by number of styles
    const hash = username.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
    const styleIndex = hash % AVATAR_STYLES.length;
    const style = AVATAR_STYLES[styleIndex];

    // DiceBear API generates an SVG avatar based on style + seed (username)
    return `https://api.dicebear.com/7.x/${style}/svg?seed=${encodeURIComponent(username)}`;
};
