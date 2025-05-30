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

# --- Main grid component ---
@solara.component
def GameGrid():
    grid, set_grid = solara.use_state(random_grid(possible_values))
    player, set_player = solara.use_state("Player 1")

    owner_matrix, set_owner_matrix = solara.use_state(
        [[None for _ in range(cols)] for _ in range(rows)])
    
    p1_score = p2_score = 0
    for r in range(rows):
        for c in range(cols):
            owner = owner_matrix[r][c]
            if owner:
                val = grid[r][c]
                pts = dice_and_rule_values.get(val, 0)
                if owner == "Player 1":
                    p1_score += pts
                else:
                    p2_score += pts
    
    def on_refresh(_=None):
        set_grid(random_grid(possible_values))
        set_owner_matrix([[None]*cols for _ in range(rows)])

    def on_tile_click(r, c):
        new = [list(row) for row in owner_matrix]
        new[r][c] = None if new[r][c] is not None else player
        set_owner_matrix(new)

    with solara.Card("Grid controls", style={"position":"absolute","top":"2vh","left":"10px"}):
        solara.Button("REFRESH", on_click=on_refresh, style={"border":"2px solid #ccc"})

    with solara.Card("Player Selection", style={"position":"absolute","top":"22vh","left":"10px"}):
        solara.ToggleButtonsSingle(value=player, values=list(PLAYER_COLORS.keys()), on_value=set_player, style={"border":"2px solid #ccc"})
        solara.Markdown(" ", style={"padding-top":"10px"})
        with solara.HBox():
            solara.Markdown(f"{p1_score}", style={"font-size":"1.25vw", "fontWeight":"bold", "color":PLAYER_COLORS['Player 1']})
            solara.Markdown(" ", style={"font-size":"1.25vw", "fontWeight":"bold"})
            solara.Markdown(" ", style={"font-size":"1.25vw", "fontWeight":"bold"})
            solara.Markdown(" ", style={"font-size":"1.25vw", "fontWeight":"bold"})
            solara.Markdown(f"{p2_score}", style={"font-size":"1.25vw", "fontWeight":"bold", "color":PLAYER_COLORS['Player 2']})

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
                                    "fontSize": "40pt" if is_dice_face(val) else "24pt",
                                    "color": "#333" if is_dice_face(val) else "#2b6bb5",
                                    "fontWeight": "normal" if is_dice_face(val) else "bold",
                                    "alignSelf": "flex-start",
                                    "margin": "10px",
                                    "lineHeight": "1em",
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
                                    "width": "2em", "height": "2em",
                                    "display": "flex", "alignItems": "center", "justifyContent": "center",
                                },
                            ),
                        ],
                    )

@solara.component
def Page():
    GameGrid()