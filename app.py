import solara
import random

from data import dice_and_rule_values, die_face, PLAYER_COLORS, rows, cols, cell_size


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

def random_grid(possible_values):
    selected = random.sample(possible_values, rows * cols)
    return [selected[i*cols:(i+1)*cols] for i in range(rows)]

def count_adjacent_same_owner(owner_matrix, r, c, player):
    count = 0
    for dr in [-1, 0, 1]:
        for dc in [-1, 0, 1]:
            if dr == 0 and dc == 0:
                continue  # Skip the center
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                if owner_matrix[nr][nc] == player:
                    count += 1
    return count

def count_total_points(grid, owner_matrix):
    p1_score = p2_score = 0
    already_counted = set()
    for r in range(rows):
        for c in range(cols):
            owner = owner_matrix[r][c]
            if owner:
                val = grid[r][c]
                base_pts = dice_and_rule_values.get(val, 0)
                if owner == "Player 1":
                    p1_score += base_pts
                else:
                    p2_score += base_pts

                # Only look up/left/up-left/up-right to avoid double-counting
                for dr, dc in [(-1, 0), (0, -1), (-1, -1), (-1, 1)]:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        if owner_matrix[nr][nc] == owner:
                            # Make a tuple that represents the unordered pair
                            pair = tuple(sorted([(r, c), (nr, nc)]))
                            if pair not in already_counted:
                                if owner == "Player 1":
                                    p1_score += 1
                                else:
                                    p2_score += 1
                                already_counted.add(pair)
    return p1_score, p2_score

def count_controlled_tiles(owner_matrix):
    p1_tiles = 0
    p2_tiles = 0
    for row in owner_matrix:
        for owner in row:
            if owner == "Player 1":
                p1_tiles += 1
            elif owner == "Player 2":
                p2_tiles += 1
    return p1_tiles, p2_tiles


# --- Main grid component ---
@solara.component
def GameGrid():
    grid, set_grid = solara.use_state(random_grid(possible_values))
    player, set_player = solara.use_state("Player 1")

    owner_matrix, set_owner_matrix = solara.use_state(
        [[None for _ in range(cols)] for _ in range(rows)])
    
    p1_score, p2_score = count_total_points(grid, owner_matrix)
    p1_tiles, p2_tiles = count_controlled_tiles(owner_matrix)

    
    def on_refresh(_=None):
        set_grid(random_grid(possible_values))
        set_owner_matrix([[None]*cols for _ in range(rows)])

    def on_tile_click(r, c):
        # Count current player's tiles
        current_player = player  # "Player 1" or "Player 2"
        p1_tiles, p2_tiles = count_controlled_tiles(owner_matrix)
        player_tiles = p1_tiles if current_player == "Player 1" else p2_tiles

        # Don't allow if already at 6 tiles
        if owner_matrix[r][c] is None and player_tiles >= 6:
            return  # Ignore click

        new = [list(row) for row in owner_matrix]
        new[r][c] = None if new[r][c] is not None else player
        set_owner_matrix(new)

    with solara.Card(
        "Player Selection",
        style={
            "position": "absolute",
            "top": "10px",
            "left": "10px",
            "background": PLAYER_COLORS[player],  # Set to current player's color
            "color": "#fff",  # Make text white for contrast
            "border": "2px solid #fff",
        }
    ):
        solara.ToggleButtonsSingle(
            value=player,
            values=list(PLAYER_COLORS.keys()),
            on_value=set_player,
            style={"border":"2px solid #fff"}  # white border for contrast
        )
        solara.Markdown(" ", style={"padding-top":"10px"})

        with solara.GridFixed(columns=3):
            solara.Markdown("Player 1", style={"font-size":"1vw", "fontWeight":"bold"})
            solara.Markdown(f"{p1_score}", style={"font-size":"1vw", "fontWeight":"bold"})
            solara.Markdown(f"({p1_tiles})", style={"font-size":"1vw", "fontWeight":"bold"})

            solara.Markdown("Player 2", style={"font-size":"1vw", "fontWeight":"bold"})
            solara.Markdown(f"{p2_score}", style={"font-size":"1vw", "fontWeight":"bold"})
            solara.Markdown(f"({p2_tiles})", style={"font-size":"1vw", "fontWeight":"bold"})


    with solara.Column(style={"width":"98vw","height":"98vh","justifyContent":"center","alignItems":"center"}):
        with solara.GridFixed(columns=cols):
            for r in range(rows):
                for c in range(cols):
                    val = grid[r][c].strip()
                    pts = dice_and_rule_values.get(val, 0)
                    owner = owner_matrix[r][c]
                    bg = PLAYER_COLORS[owner] if owner else card_bg_color(val)

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
                                    "margin": "10px"
                               },
                            ),
                            solara.Text(
                                str(pts),
                                style={
                                    "position": "absolute",
                                    "bottom": "10px",
                                    "fontSize": "1vw",
                                    "color": "#333", "fontWeight": "bold",
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