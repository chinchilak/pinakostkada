import solara
import random


def card_bg_color(value):
    if is_dice_face(value):
        if len(value.split()) == 2:
            return "#d4edda"  # light green
        elif len(value.split()) == 3:
            return "#d1ecf1"  # light blue
    return "#f8d7da"  # light red for specials

def is_dice_face(s: str) -> bool:
    return all(part.isdigit() for part in s.split())

def dice_string_to_faces(s):
    if is_dice_face(s):
        return " ".join(die_face[n] for n in s.split())
    return s

def random_grid():
    selected_values = random.sample(possible_values, rows * cols)
    return [selected_values[i*cols:(i+1)*cols] for i in range(rows)]

rows, cols = 4, 4
die_face = {"1": "\u2680", "2": "\u2681", "3": "\u2682", "4": "\u2683", "5": "\u2684", "6": "\u2685"}
cell_size = "min(22vw, 22vh)"

dice_and_rule_values = {
    # Pairs
    "1 1": 1, 
    "2 2": 1, 
    "3 3": 1, 
    "4 4": 1, 
    "5 5": 1, 
    "6 6": 1,
    # Triplets
    "1 1 1": 1, 
    "2 2 2": 1, 
    "3 3 3": 1, 
    "4 4 4": 1, 
    "5 5 5": 1, 
    "6 6 6": 1,
    # Special rules (assign manually)
    "<= 9": 2,
    ">= 26": 2,
    "12 / 13 / 14": 2,
    "21 / 22 / 23": 2,
    "A A  B B": 2,
    "A A A  B B": 3,
    "A A A A": 3,
    "A A A A A": 4,
    "A B C D E": 3,
    "A +1 +2 +3": 2,
    "A +1 +2 +3 +4": 3,
    "1, 3, 5": 2,
    "2, 4, 6": 2,}

possible_values = list(dice_and_rule_values.keys())

if len(possible_values) < rows * cols:
    raise ValueError("Not enough unique values for the grid. Add more special rules!")


@solara.component
def GameGrid():
    with solara.Column(
        style={
            "width": "98vw",
            "height": "98vh",
            "justifyContent": "center",
            "alignItems": "center"
        }
    ):
        with solara.GridFixed(columns=cols):
            for row in range(rows):
                for col in range(cols):
                    value = value = random_grid()[row][col]
                    points = dice_and_rule_values[value]
                    with solara.Card(
                        style={
                            "border": "2px solid #fff",
                            "background": card_bg_color(value),
                            "color": "#333",
                            "borderRadius": "10px",
                            "width": cell_size,
                            "height": cell_size,
                            "display": "flex",
                            "alignItems": "flex-start",
                            "justifyContent": "flex-start",
                            "position": "relative",
                        }
                    ):
                        solara.Text(
                            dice_string_to_faces(value),
                            style={
                                "position": "absolute",
                                "fontSize": "40pt" if is_dice_face(value) else "24pt",
                                "left": "10px",
                                "top": "20px",
                                "textAlign": "left",
                                "color": "#333" if is_dice_face(value) else "#2b6bb5",
                                "fontWeight": "normal" if is_dice_face(value) else "bold",
                            }
                        )
                        solara.Text(
                            str(points),
                            style={
                                "position": "absolute",
                                "right": "10px",
                                "bottom": "10px",
                                "fontSize": "18pt",
                                "color": "#333",
                                "fontWeight": "bold",
                                "background": "#fff",
                                "border": "2px solid #888",
                                "borderRadius": "50%",
                                "width": "2em",
                                "height": "2em",
                                "display": "flex",
                                "alignItems": "center",
                                "justifyContent": "center",
                                "boxShadow": "0 0 4px #ccc",
                                "pointerEvents": "none",
                                "userSelect": "none",
                            }
                        )

@solara.component
def Page():
    solara.Title("4x4 Dice Grid - With Static Dict")
    GameGrid()
