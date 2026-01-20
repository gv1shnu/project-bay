// Avatar styles from DiceBear
const AVATAR_STYLES = [
    'lorelei',      // Anime faces
    'adventurer',   // Cute anime adventurers
    'notionists',   // Clean minimalist
    'big-smile',    // Cartoon with grins
    'pixel-art',    // Retro pixelated
    'thumbs',       // Playful emojis
    'bottts',       // Friendly robots
]

// Get consistent avatar URL for a username (same user always gets same style)
export function getAvatarUrl(seed: string): string {
    // Simple hash to pick style
    let hash = 0
    for (let i = 0; i < seed.length; i++) {
        hash = seed.charCodeAt(i) + ((hash << 5) - hash)
    }
    const styleIndex = Math.abs(hash) % AVATAR_STYLES.length
    const style = AVATAR_STYLES[styleIndex]

    return `https://api.dicebear.com/7.x/${style}/svg?seed=${seed}`
}
