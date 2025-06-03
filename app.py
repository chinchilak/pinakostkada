import solara
import reacton.ipywidgets as w
import ipywidgets as widgets
import random

from data import (
    dice_and_rule_values, die_face,
    PLAYER_COLORS as INITIAL_COLORS,
    rows, cols, cell_size,
)

# ── helpers ───────────────────────────────────────────────────────────
possible_values = list(dice_and_rule_values.keys())

def is_dice_face(s: str) -> bool:
    return all(part.isdigit() for part in s.split())

def dice_string_to_faces(s: str) -> str:
    if is_dice_face(s):
        return " ".join(die_face[n] for n in s.split())
    return s

def card_bg_color(value: str) -> str:
    if is_dice_face(value):
        parts = value.split()
        if len(parts) == 2:
            return "#d4edda"
        elif len(parts) == 3:
            return "#d1ecf1"
    return "#f8d7da"

def random_grid(values):
    sel = random.sample(values, rows * cols)
    return [sel[i * cols:(i + 1) * cols] for i in range(rows)]

def count_total_points(grid, owner_matrix):
    p1_score = 0
    p2_score = 0
    counted_pairs: set[tuple[tuple[int, int], tuple[int, int]]] = set()
    for r in range(rows):
        for c in range(cols):
            owner = owner_matrix[r][c]
            if owner is None:
                continue
            base = dice_and_rule_values.get(grid[r][c], 0)
            if owner == "Player 1":
                p1_score += base
            else:
                p2_score += base
            for dr, dc in [(-1, 0), (0, -1), (-1, -1), (-1, 1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols and owner_matrix[nr][nc] == owner:
                    pair = tuple(sorted(((r, c), (nr, nc))))
                    if pair not in counted_pairs:
                        if owner == "Player 1":
                            p1_score += 1
                        else:
                            p2_score += 1
                        counted_pairs.add(pair)
    return p1_score, p2_score

def count_controlled_tiles(owner_matrix):
    p1 = sum(cell == "Player 1" for row in owner_matrix for cell in row)
    p2 = sum(cell == "Player 2" for row in owner_matrix for cell in row)
    return p1, p2

# ── MAIN COMPONENT ────────────────────────────────────────────────────
@solara.component
def GameGrid():
    grid, set_grid = solara.use_state(random_grid(possible_values))
    owner_matrix, set_owner_matrix = solara.use_state([[None] * cols for _ in range(rows)])
    player, set_player = solara.use_state("Player 1")
    player_colors, set_player_colors = solara.use_state(dict(INITIAL_COLORS))
    font_scale, set_font_scale = solara.use_state(1.0)  # master scale

    # callbacks -------------------------------------------------------
    def set_player_color(name):
        return lambda new: set_player_colors({**player_colors, name: new})

    def on_refresh(_=None):
        set_grid(random_grid(possible_values))
        set_owner_matrix([[None] * cols for _ in range(rows)])

    def on_tile_click(r, c):
        p1_tiles, p2_tiles = count_controlled_tiles(owner_matrix)
        if owner_matrix[r][c] is None and ((player == "Player 1" and p1_tiles >= 6) or (player == "Player 2" and p2_tiles >= 6)):
            return
        nm = [list(row) for row in owner_matrix]
        nm[r][c] = None if nm[r][c] else player
        set_owner_matrix(nm)

    # derived ----------------------------------------------------------
    p1_score, p2_score = count_total_points(grid, owner_matrix)
    p1_tiles, p2_tiles = count_controlled_tiles(owner_matrix)

    # style helpers ----------------------------------------------------
    card_font = f"{1.0 * font_scale}em"
    card_heading = f"{1.2 * font_scale}em"

    # layout -----------------------------------------------------------
    with solara.Row(gap="24px", style={"padding": "16px", "alignItems": "flex-start"}):
        # ░░ CONFIG ░░
        with solara.Card("Game settings", style={"minWidth": "240px", "background": player_colors[player], "color": "#fff", "border": "2px solid #fff"}):
            # scale slider first so user sees it
            w.FloatSlider(
                value=font_scale,
                min=0.5,
                max=3.0,
                step=0.1,
                description=f"Scale ×{font_scale:.1f}",
                on_value=set_font_scale,
                layout=widgets.Layout(width="100%"),
                
            )

            solara.ToggleButtonsSingle(
                value=player,
                values=list(player_colors.keys()),
                on_value=set_player,
                style={"margin": "20px"},
            )

            with solara.GridFixed(columns=2, column_gap="12px", row_gap="4px"):
                for p_name, p_color, p_pts, p_tiles in [
                    ("Player 1", player_colors["Player 1"], p1_score, p1_tiles),
                    ("Player 2", player_colors["Player 2"], p2_score, p2_tiles),
                ]:
                    with solara.Div(style={"background": p_color, "padding": "8px", "borderRadius": "8px", "color": "#fff", "display": "flex", "flexDirection": "column", "alignItems": "center", "fontSize": card_font}):
                        solara.Markdown(f"**{p_name}**", style={"fontSize": card_heading})
                        w.ColorPicker(value=p_color, on_value=set_player_color(p_name), description="", layout=widgets.Layout(width="100px"))
                        solara.Markdown(f"Points: **{p_pts}**", style={"fontSize": card_font})
                        solara.Markdown(f"Tiles: **{p_tiles}**", style={"fontSize": card_font})

            solara.Button("🔄 New board", on_click=on_refresh, style={"marginTop": "20px"})

        # ░░ GRID ░░
        with solara.Column(style={"justifyContent": "center", "alignItems": "center"}):
            with solara.GridFixed(columns=cols):
                for r in range(rows):
                    for c in range(cols):
                        val = grid[r][c].strip()
                        pts = dice_and_rule_values.get(val, 0)
                        owner = owner_matrix[r][c]
                        bg = player_colors[owner] if owner else card_bg_color(val)
                        dice_font = f"{2 * font_scale}vw" if is_dice_face(val) else f"{1 * font_scale}vw"
                        pts_font = f"{1 * font_scale}vw"
                        solara.Button(
                            label="",
                            on_click=lambda r=r, c=c: on_tile_click(r, c),
                            style={
                                "position": "relative",
                                "padding": "10px",
                                "margin": "0",
                                "background": bg,
                                "border": "2px solid #fff",
                                "borderRadius": "10px",
                                "width": cell_size,
                                "height": cell_size,
                                "display": "flex",
                                "flexDirection": "column",
                            },
                            children=[
                                solara.Text(
                                    dice_string_to_faces(val),
                                    style={
                                        "fontSize": dice_font,
                                        "color": "#333" if is_dice_face(val) else "#2b6bb5",
                                        "fontWeight": "normal" if is_dice_face(val) else "bold",
                                        "alignSelf": "flex-start",
                                        "margin": "10px",
                                    },
                                ),
                                solara.Text(
                                    str(pts),
                                    style={
                                        "position": "absolute",
                                        "bottom": "10px",
                                        "fontSize": pts_font,
                                        "color": "#333",
                                        "fontWeight": "bold",
                                        "background": "#fff",
                                        "border": "2px solid #888",
                                        "borderRadius": "50%",
                                        "width": "2vw",
                                        "height": "2vw",
                                        "display": "flex",
                                        "alignItems": "center",
                                        "justifyContent": "center",
                                    },
                                ),
                            ],
                        )

@solara.component
def Page():
    GameGrid()
