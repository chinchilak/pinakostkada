# ── GAME CONFIG ──────────────────────────────────────────────────────

# Player ownership colors
PLAYER_COLORS = {
    "Player 1": "#f08c53",   # orange
    "Player 2": "#66e691",   # lime-green
}

# Grid configuration
rows, cols = 4, 4
cell_size = "min(22vw, 22vh)"


DEFAULT_DICE_FONT_SCALE = 1.3
DEFAULT_TEXT_FONT_SCALE = 1.0


# ── VISUAL TILE RULES ────────────────────────────────────────────────
# Colors for tiles depending on what kind of value they represent:
TILE_COLORS = {
    "pair":   "#d4edda",   # light green
    "triple": "#d1ecf1",   # light blue
    "other":  "#f8d7da",   # light red
}

# Dice-face unicode glyphs
die_face = {
    "1": "\u2680",
    "2": "\u2681",
    "3": "\u2682",
    "4": "\u2683",
    "5": "\u2684",
    "6": "\u2685",
}


# ── GAME RULE VALUES ─────────────────────────────────────────────────
dice_and_rule_values = {
    # Pairs
    "1 1": 1, "2 2": 1, "3 3": 1, "4 4": 1, "5 5": 1, "6 6": 1,

    # Triplets
    "1 1 1": 1, "2 2 2": 1, "3 3 3": 1, "4 4 4": 1, "5 5 5": 1, "6 6 6": 1,

    # Specials
    "<= 9": 2, ">= 26": 2,
    "12 / 13 / 14": 2, "21 / 22 / 23": 2,
    "A A  B B": 2, "A A A  B B": 3,
    "A A A A": 3, "A A A A A": 4,
    "A B C D E": 3, "A +1 +2 +3": 2,
    "A +1 +2 +3 +4": 3, "1, 3, 5": 2, "2, 4, 6": 2,
}
