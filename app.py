import solara
import reacton.ipywidgets as w
import ipywidgets as widgets 
import random

from data import (
    dice_and_rule_values, die_face,
    PLAYER_COLORS as INITIAL_COLORS,
    rows, cols, cell_size,
)

# ── helpers (unchanged) ────────────────────────────────────────────────
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

def count_adjacent_same_owner(owner_matrix, r, c, player):
    cnt = 0
    for dr in [-1, 0, 1]:
        for dc in [-1, 0, 1]:
            if dr == dc == 0:
                continue
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and owner_matrix[nr][nc] == player:
                cnt += 1
    return cnt

def count_total_points(grid, owner_matrix):
    p1_score = 0
    p2_score = 0
    counted_pairs: set[tuple[tuple[int, int], tuple[int, int]]] = set()

    for r in range(rows):
        for c in range(cols):
            owner = owner_matrix[r][c]
            if not owner:
                continue

            # base value of the tile itself
            base = dice_and_rule_values.get(grid[r][c], 0)
            if owner == "Player 1":
                p1_score += base
            else:
                p2_score += base

            # adjacency bonus (look only up/left/diagonals to avoid double-counting)
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

# ── MAIN COMPONENT ─────────────────────────────────────────────────────
@solara.component
def GameGrid():
    # game state
    grid, set_grid = solara.use_state(random_grid(possible_values))
    owner_matrix, set_owner_matrix = solara.use_state(
        [[None for _ in range(cols)] for _ in range(rows)]
    )
    player, set_player = solara.use_state("Player 1")

    # ► editable colours
    player_colors, set_player_colors = solara.use_state(dict(INITIAL_COLORS))

    def set_player_color(name):
        return lambda new: set_player_colors({**player_colors, name: new})

    # --- callbacks ----------------------------------------------------
    def on_refresh(_=None):
        set_grid(random_grid(possible_values))
        set_owner_matrix([[None] * cols for _ in range(rows)])

    def on_tile_click(r, c):
        current = player
        p1_tiles, p2_tiles = count_controlled_tiles(owner_matrix)
        if owner_matrix[r][c] is None and (p1_tiles if current == "Player 1" else p2_tiles) >= 6:
            return
        new = [list(row) for row in owner_matrix]
        new[r][c] = None if new[r][c] else current
        set_owner_matrix(new)

    # --- derived scores ----------------------------------------------
    p1_score, p2_score = count_total_points(grid, owner_matrix)
    p1_tiles, p2_tiles = count_controlled_tiles(owner_matrix)

    # ──────────────────────────────────────────────────────────────────
    #                              UI
    # ──────────────────────────────────────────────────────────────────
    with solara.Card(
        "Player selection",
        style={
            "position": "absolute",
            "top": "10px",
            "left": "10px",
            "background": player_colors[player],
            "color": "#fff",
            "border": "2px solid #fff",
        },
    ):
        # 1️⃣ whose-turn toggle (unchanged)
        solara.ToggleButtonsSingle(
            value=player,
            values=list(player_colors.keys()),
            on_value=set_player,
            style={"padding-bottom": "10px", "background": player_colors[player]},
        )

        # 2️⃣ two side-by-side “player columns”
        with solara.GridFixed(columns=2, column_gap="16px", row_gap="4px"):
            # ----- PLAYER 1 --------------------------------------------------
            with solara.Div(
                    style={
                        "background": player_colors["Player 1"],
                        "padding": "10px",
                        "spacing": "10px",
                        "borderRadius": "8px",
                        "color": "#fff",     # white text for contrast
                        "display": "flex",
                        "flexDirection": "column",
                        "alignItems": "center",
                    }):
                solara.Markdown("**Player 1**", style={"fontSize": "1vw"})
                w.ColorPicker(
                    value=player_colors["Player 1"],
                    on_value=set_player_color("Player 1"),
                    description="",
                    layout=widgets.Layout(width="100px"),
                )
                solara.Markdown(f"Points: **{p1_score}**", style={"fontSize": "0.9vw"})
                solara.Markdown(f"Tiles: **{p1_tiles}**", style={"fontSize": "0.9vw"})

            # ----- PLAYER 2 --------------------------------------------------
            with solara.Div(
                    style={
                        "background": player_colors["Player 2"],
                        "padding": "6px",
                        "borderRadius": "8px",
                        "color": "#fff",
                        "display": "flex",
                        "flexDirection": "column",
                        "alignItems": "center",
                    }):
                solara.Markdown("**Player 2**", style={"fontSize": "1vw"})
                w.ColorPicker(
                    value=player_colors["Player 2"],
                    on_value=set_player_color("Player 2"),
                    description="",
                    layout=widgets.Layout(width="100px"),
                )
                solara.Markdown(f"Points: **{p2_score}**", style={"fontSize": "0.9vw"})
                solara.Markdown(f"Tiles: **{p2_tiles}**", style={"fontSize": "0.9vw"})

        # 3️⃣ refresh button (optional – move/keep as you like)
        solara.Button("🔄 New board", on_click=on_refresh, style={"marginTop": "6px"})

    # playing grid
    with solara.Column(style={"width": "98vw", "height": "98vh",
                              "justifyContent": "center", "alignItems": "center"}):
        with solara.GridFixed(columns=cols):
            for r in range(rows):
                for c in range(cols):
                    val = grid[r][c].strip()
                    pts = dice_and_rule_values.get(val, 0)
                    owner = owner_matrix[r][c]
                    bg = player_colors[owner] if owner else card_bg_color(val)

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
                                    "fontSize": "2vw" if is_dice_face(val) else "1vw",
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
                                    "fontSize": "1vw",
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
