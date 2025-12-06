from nicegui import ui
import random
import json
import os

SETTINGS_FILE = "game_settings.json"

# ----------------- Config load/save -------------------------

DEFAULT_CONFIG = {
    "player_names": {"Player 1": "Player 1", "Player 2": "Player 2"},
    "player_colors": {"Player 1": "#f08c53", "Player 2": "#66e691"},
    "tile_colors": {
        "pair": "#d4edda",
        "triple": "#d1ecf1",
        "other": "#f8d7da",
    },
    "fonts": {
        "dice_font_scale": 1.3,
        "text_font_scale": 1.0,
        "badge_scale": 1.0,
        "badge_text_scale": 1.4,
    },
    "board": {
        "rows": 4,
        "cols": 4,
        "cell_size": "min(22vw, 22vh)",
    },
}


def _merge_config(data: dict, base: dict) -> dict:
    """Recursively merge base defaults into data."""
    result = dict(data) if isinstance(data, dict) else {}
    for k, v in base.items():
        if isinstance(v, dict):
            result[k] = _merge_config(result.get(k, {}), v)
        else:
            result.setdefault(k, v)
    return result


def load_config() -> dict:
    if not os.path.exists(SETTINGS_FILE):
        return dict(DEFAULT_CONFIG)
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        return dict(DEFAULT_CONFIG)
    return _merge_config(raw, DEFAULT_CONFIG)


def save_config(cfg: dict) -> None:
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


config = load_config()

# expose board globals for helper functions
rows = config["board"]["rows"]
cols = config["board"]["cols"]
cell_size = config["board"]["cell_size"]

# ----------------- Game logic constants ---------------------

# dice-face unicode mapping
die_face = {
    "1": "\u2680",
    "2": "\u2681",
    "3": "\u2682",
    "4": "\u2683",
    "5": "\u2684",
    "6": "\u2685",
}

# scoring/rules
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
    # Specials
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
    "2, 4, 6": 2,
}

possible_values = list(dice_and_rule_values.keys())

# ----------------- Helper functions -------------------------


def is_dice_face(value: str) -> bool:
    return all(part.isdigit() for part in value.split())


def dice_string_to_faces(s: str) -> str:
    return " ".join(die_face[n] for n in s.split()) if is_dice_face(s) else s


def card_bg_color(value: str) -> str:
    colors = config["tile_colors"]
    if is_dice_face(value):
        parts = value.split()
        if len(parts) == 2:
            return colors["pair"]
        elif len(parts) == 3:
            return colors["triple"]
    return colors["other"]


def random_grid(values):
    shuffled = random.sample(values, rows * cols)
    return [shuffled[i * cols:(i + 1) * cols] for i in range(rows)]


def count_total_points(grid, owner_matrix):
    score_p1 = score_p2 = 0
    counted = set()

    for r in range(rows):
        for c in range(cols):
            owner = owner_matrix[r][c]
            if owner is None:
                continue
            base = dice_and_rule_values.get(grid[r][c], 0)
            if owner == "Player 1":
                score_p1 += base
            else:
                score_p2 += base

            # adjacency bonus
            for dr, dc in [(-1, 0), (0, -1), (-1, -1), (-1, 1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols and owner_matrix[nr][nc] == owner:
                    pair = tuple(sorted(((r, c), (nr, nc))))
                    if pair not in counted:
                        if owner == "Player 1":
                            score_p1 += 1
                        else:
                            score_p2 += 1
                        counted.add(pair)

    return score_p1, score_p2


def count_tiles(owner_matrix):
    """Return (tiles_p1, tiles_p2)."""
    return (
        sum(cell == "Player 1" for row in owner_matrix for cell in row),
        sum(cell == "Player 2" for row in owner_matrix for cell in row),
    )


# -------------------- Game State ----------------------------


class GameState:
    def __init__(self):
        self.grid = random_grid(possible_values)
        self.owner = [[None] * cols for _ in range(rows)]
        self.player = "Player 1"  # whose turn it is

        # rounds per player (turns, including pass)
        self.rounds = {"Player 1": 0, "Player 2": 0}

        # game-end state
        self.game_over = False
        self.winner = None  # "Player 1", "Player 2", or None for tie
        self.win_reason = ""
        self.pending_last_turn_for = None  # who still gets a last turn due to 21+ rule

        # history stack for undo
        self.history: list[dict] = []

        # settings from config
        self.player_names = dict(config["player_names"])
        self.player_colors = dict(config["player_colors"])
        # tile colors stay in config; we just read from there for backgrounds
        self.dice_font_scale = config["fonts"]["dice_font_scale"]
        self.text_font_scale = config["fonts"]["text_font_scale"]
        self.badge_scale = config["fonts"]["badge_scale"]
        self.badge_text_scale = config["fonts"]["badge_text_scale"]

    # ---- core operations ----

    def reset_board(self):
        self.grid = random_grid(possible_values)
        self.owner = [[None] * cols for _ in range(rows)]
        self.player = "Player 1"
        self.rounds = {"Player 1": 0, "Player 2": 0}
        self.game_over = False
        self.winner = None
        self.win_reason = ""
        self.pending_last_turn_for = None
        self.history.clear()

    def _save_snapshot(self):
        """Save current state so we can undo the last full turn."""
        self.history.append(
            {
                "owner": [row[:] for row in self.owner],
                "rounds": dict(self.rounds),
                "player": self.player,
                "game_over": self.game_over,
                "winner": self.winner,
                "win_reason": self.win_reason,
                "pending_last_turn_for": self.pending_last_turn_for,
            }
        )

    def undo_last(self):
        """Undo the last completed turn (place or pass)."""
        if not self.history:
            return
        snap = self.history.pop()
        self.owner = [row[:] for row in snap["owner"]]
        self.rounds = dict(snap["rounds"])
        self.player = snap["player"]
        self.game_over = snap["game_over"]
        self.winner = snap["winner"]
        self.win_reason = snap["win_reason"]
        self.pending_last_turn_for = snap["pending_last_turn_for"]

    def _has_four_in_line(self, player: str) -> bool:
        directions = [(1, 0), (0, 1), (1, 1), (1, -1)]
        for r in range(rows):
            for c in range(cols):
                if self.owner[r][c] != player:
                    continue
                for k in range(1, 4):  # need 3 more = total 4
                    nr, nc = r + directions[0][0] * 0, c + directions[0][1] * 0
                for dr, dc in directions:
                    ok = True
                    for k in range(1, 4):
                        nr, nc = r + dr * k, c + dc * k
                        if not (0 <= nr < rows and 0 <= nc < cols):
                            ok = False
                            break
                        if self.owner[nr][nc] != player:
                            ok = False
                            break
                    if ok:
                        return True
        return False

    def _check_four_winner(self):
        p1 = self._has_four_in_line("Player 1")
        p2 = self._has_four_in_line("Player 2")
        if p1 and not p2:
            return "Player 1"
        if p2 and not p1:
            return "Player 2"
        if p1 and p2:
            return None
        return None

    def _decide_winner_by_score(self, reason: str):
        p1, p2 = count_total_points(self.grid, self.owner)
        self.game_over = True
        self.win_reason = reason
        if p1 > p2:
            self.winner = "Player 1"
        elif p2 > p1:
            self.winner = "Player 2"
        else:
            self.winner = None  # tie

    def _after_turn(self, last_player: str):
        """Evaluate win conditions after last_player finished their turn."""
        if self.game_over:
            return

        # 1) check 4-in-a-row instant win
        four_winner = self._check_four_winner()
        if four_winner is not None:
            self.game_over = True
            if four_winner:
                self.winner = four_winner
                self.win_reason = "4 tiles in a line"
            else:
                self.winner = None
                self.win_reason = "Both have 4-in-a-line"
            return

        p1_score, p2_score = count_total_points(self.grid, self.owner)

        # 2) handle pending last turn due to 21+ rule
        if self.pending_last_turn_for:
            if last_player == self.pending_last_turn_for:
                self.pending_last_turn_for = None
                self._decide_winner_by_score("21+ reached, last turn played")
                return
        else:
            # if someone just crossed 21+ this turn, trigger last turn for the opponent
            if p1_score >= 21 or p2_score >= 21:
                self.pending_last_turn_for = (
                    "Player 2" if last_player == "Player 1" else "Player 1"
                )

        # 3) rounds limit: once both played 6 rounds, higher score wins
        if self.rounds["Player 1"] >= 6 and self.rounds["Player 2"] >= 6:
            self._decide_winner_by_score("Both played 6 rounds")
            return

        if self.game_over:
            return

        # 4) choose next player
        if self.pending_last_turn_for:
            self.player = self.pending_last_turn_for
        else:
            self.player = "Player 2" if last_player == "Player 1" else "Player 1"

    def _can_player_act(self, player: str) -> bool:
        if self.game_over:
            return False
        if self.pending_last_turn_for and player != self.pending_last_turn_for:
            return False
        if self.rounds[player] >= 6:
            return False
        return True

    def play(self, r, c) -> str:
        current = self.player

        if not self._can_player_act(current):
            return "blocked"

        owner = self.owner[r][c]

        if owner == current:
            self.owner[r][c] = None
            return "removed"

        if owner is not None and owner != current:
            return "blocked"

        if owner is None:
            self._save_snapshot()
            self.owner[r][c] = current
            self.rounds[current] += 1
            self._after_turn(current)
            return "placed"

        return "blocked"

    def pass_turn(self):
        current = self.player
        if not self._can_player_act(current):
            return
        self._save_snapshot()
        self.rounds[current] += 1
        self._after_turn(current)


game = GameState()


def refresh_ui():
    board.refresh()
    left_panel.refresh()
    right_panel.refresh()


# ---------------- Global Dark Theme -------------------------

ui.add_head_html("""
<style>
  body {
    background-color: #000000;
  }
</style>
""")


# ---------------- Game Over Dialog (gold overlay) -----------

with ui.dialog() as game_over_dialog, ui.card().style(
    "min-width: 420px; max-width: 520px; "
    "background: linear-gradient(135deg, #f9e79f, #f1c40f, #b7950b); "
    "border-radius: 18px; "
    "border: 3px solid #ffffff; "
    "box-shadow: 0 0 32px rgba(255, 255, 255, 0.95); "
    "color: #1b1b1b; text-align: center; padding: 24px;"
):
    go_title = ui.html(
        "<div style='font-size:2.0em; font-weight:bold; "
        "text-shadow:1px 1px 3px rgba(0,0,0,0.5); margin-bottom:8px;'>"
        "🏆 Game over</div>",
        sanitize=False,
    )
    go_detail = ui.html(
        "<div style='font-size:1.2em; font-weight:bold; "
        "text-shadow:1px 1px 2px rgba(0,0,0,0.4); margin-bottom:12px;'></div>",
        sanitize=False,
    )

    def new_game():
        game.reset_board()
        refresh_ui()
        game_over_dialog.close()

    ui.separator().style("margin: 8px 0 12px 0;")

    with ui.row().style("justify-content:center; gap:12px;"):
        ui.button("New game", on_click=new_game).style(
            "font-weight:bold; padding:8px 18px; "
            "background:#1b1b1b; color:#f9e79f;"
        )
        ui.button("Close", on_click=game_over_dialog.close).props("flat").style(
            "font-weight:bold; padding:8px 16px; color:#1b1b1b;"
        )


def show_game_over():
    if not game.game_over:
        return

    if game.winner:
        winner_name = game.player_names[game.winner]
        go_title.set_content(
            f"<div style='font-size:2.0em; font-weight:bold; "
            f"text-shadow:1px 1px 3px rgba(0,0,0,0.5); margin-bottom:8px;'>"
            f"🏆 {winner_name} wins!</div>"
        )
    else:
        go_title.set_content(
            "<div style='font-size:2.0em; font-weight:bold; "
            "text-shadow:1px 1px 3px rgba(0,0,0,0.5); margin-bottom:8px;'>"
            "🤝 It's a tie!</div>"
        )

    reason_html = f"Reason: {game.win_reason}" if game.win_reason else ""
    go_detail.set_content(
        f"<div style='font-size:1.2em; font-weight:bold; "
        f"text-shadow:1px 1px 2px rgba(0,0,0,0.4); margin-bottom:12px;'>{reason_html}</div>"
    )

    game_over_dialog.open()


# ---------------- Settings Modal ----------------------------

with ui.dialog() as setup_dialog, ui.card().style("min-width: 360px;"):
    ui.markdown("### ⚙ Game Setup")

    # player name + color rows
    for p in ["Player 1", "Player 2"]:
        with ui.row().style("align-items:center; gap:8px; margin-bottom:6px;"):
            ui.label(p).style("width:80px;font-weight:bold;")

            def handle_name_change(e, player=p):
                game.player_names[player] = e.value
                config["player_names"][player] = e.value
                save_config(config)
                refresh_ui()

            ui.input(
                value=game.player_names[p],
                on_change=handle_name_change,
            ).style("flex:1;")

            def handle_color_change(e, player=p):
                game.player_colors[player] = e.value
                config["player_colors"][player] = e.value
                save_config(config)
                refresh_ui()

            ui.color_input(
                value=game.player_colors[p],
                on_change=handle_color_change,
            ).style("width:70px;")

    ui.separator()

    # DICE SIZE SLIDER
    ui.label("Dice size")
    def on_dice_size_change(e):
        game.dice_font_scale = e.value
        config["fonts"]["dice_font_scale"] = e.value
        save_config(config)
        refresh_ui()

    ui.slider(
        min=0.7,
        max=4.0,
        step=0.1,
        value=game.dice_font_scale,
        on_change=on_dice_size_change,
    ).props("label-always")

    # TEXT SIZE SLIDER
    ui.label("Text size")
    def on_text_size_change(e):
        game.text_font_scale = e.value
        config["fonts"]["text_font_scale"] = e.value
        save_config(config)
        refresh_ui()

    ui.slider(
        min=0.7,
        max=4.0,
        step=0.1,
        value=game.text_font_scale,
        on_change=on_text_size_change,
    ).props("label-always")

    # BADGE SIZE SLIDER
    ui.label("Badge size")
    def on_badge_change(e):
        game.badge_scale = e.value
        config["fonts"]["badge_scale"] = e.value
        save_config(config)
        refresh_ui()

    ui.slider(
        min=0.5,
        max=4.0,
        step=0.1,
        value=game.badge_scale,
        on_change=on_badge_change,
    ).props("label-always")

    # BADGE TEXT SIZE SLIDER
    ui.label("Badge text size")
    def on_badge_text_change(e):
        game.badge_text_scale = e.value
        config["fonts"]["badge_text_scale"] = e.value
        save_config(config)
        refresh_ui()

    ui.slider(
        min=0.5,
        max=4.0,
        step=0.1,
        value=game.badge_text_scale,
        on_change=on_badge_text_change,
    ).props("label-always")

    ui.separator()

    def reset():
        game.reset_board()
        refresh_ui()

    ui.button("Reset board", on_click=reset).props("outline")
    ui.button("Close", on_click=setup_dialog.close)


# ---------------- Player Panels -----------------------------


def render_player(player: str):
    score_p1, score_p2 = count_total_points(game.grid, game.owner)
    t1, t2 = count_tiles(game.owner)

    score, tiles = (score_p1, t1) if player == "Player 1" else (score_p2, t2)
    rounds = game.rounds[player]
    name = game.player_names[player]
    color = game.player_colors[player]

    active = player == game.player

    border = "#FFFFFF" if active else "#000000"
    glow = "0 0 18px rgba(255,255,255,0.9)" if active else "none"

    with ui.card().style(
        f"""
        background:{color};
        padding:18px;
        border-radius:14px;
        border:4px solid {border};
        box-shadow:{glow};
        color:white;
        text-align:center;
        """
    ):
        ui.html(
            f"<div style='font-size:1.6em; font-weight:bold; "
            f"text-shadow:2px 2px 4px rgba(0,0,0,0.9);'>{name}</div>",
            sanitize=False,
        )

        ui.separator()

        with ui.column().style("align-items:center; margin-top:8px; gap:10px;"):

            def stat_row(label, value):
                with ui.row().style(
                    "width:190px; justify-content:space-between; font-size:1.35em; padding:4px 0;"
                ):
                    ui.html(
                        f"<span style='font-weight:bold; text-shadow:2px 2px 4px rgba(0,0,0,0.8);'>{label}</span>",
                        sanitize=False,
                    )
                    ui.html(
                        f"<span style='font-weight:bold; text-shadow:2px 2px 4px rgba(0,0,0,0.8);'>{value}</span>",
                        sanitize=False,
                    )

            stat_row("Points:", score)
            stat_row("Rounds:", rounds)
            stat_row("Tiles:", tiles)

        if active:
            with ui.row().style(
                "margin-top:12px; width:100%; display:flex; justify-content:space-between;"
            ):
                # Pass on the left (if game not over)
                if not game.game_over:
                    def do_pass():
                        game.pass_turn()
                        refresh_ui()
                        if game.game_over:
                            show_game_over()

                    ui.button("Pass", on_click=do_pass).style(
                        "font-weight:bold; min-width:80px;"
                    )
                else:
                    ui.label("").style("width:80px;")

                # Undo on the right (if history exists)
                if game.history:
                    def do_undo():
                        game.undo_last()
                        try:
                            game_over_dialog.close()
                        except Exception:
                            pass
                        refresh_ui()

                    ui.button("Undo", on_click=do_undo).style(
                        "font-weight:bold; min-width:80px;"
                    )
                else:
                    ui.label("").style("width:80px;")


@ui.refreshable
def left_panel():
    render_player("Player 1")


@ui.refreshable
def right_panel():
    render_player("Player 2")


# ---------------- Game Board -------------------------------


@ui.refreshable
def board():
    dice_fs = f"{1.4 * game.dice_font_scale}vw"
    text_fs = f"{1.4 * game.text_font_scale}vw"
    badge_size = f"{2.4 * game.badge_scale}vw"
    pts_fs = f"{1.4 * game.badge_text_scale}vw"

    with ui.column().classes("items-center").style("gap:8px;"):
        with ui.grid(columns=cols).style("gap:4px;"):
            for r in range(rows):
                for c in range(cols):
                    v = game.grid[r][c].strip()
                    pts = dice_and_rule_values.get(v, 0)
                    owner = game.owner[r][c]

                    bg = (
                        game.player_colors.get(owner, card_bg_color(v))
                        if owner
                        else card_bg_color(v)
                    )

                    def click(row=r, col=c):
                        if game.game_over:
                            return
                        _ = game.play(row, col)
                        refresh_ui()
                        if game.game_over:
                            show_game_over()

                    tile = (
                        ui.element("div")
                        .style(
                            f"background:{bg}; width:{cell_size}; height:{cell_size}; "
                            "border:2px solid white; border-radius:10px; position:relative; cursor:pointer;"
                        )
                        .on("click", click)
                    )

                    with tile:
                        fs = dice_fs if is_dice_face(v) else text_fs
                        ui.label(dice_string_to_faces(v)).style(
                            f"position:absolute; left:10px; top:10px; font-size:{fs}; font-weight:bold;"
                        )
                        with ui.element("div").style(
                            f"position:absolute; bottom:10px; right:10px; width:{badge_size}; height:{badge_size}; "
                            "background:white; border-radius:50%; border:2px solid grey; "
                            "display:flex;align-items:center;justify-content:center;"
                        ):
                            ui.label(str(pts)).style(
                                f"font-size:{pts_fs}; font-weight:bold;"
                            )

        ui.button("⚙ Setup", on_click=setup_dialog.open).props("flat dense")


# ---------------- Final Page Layout ------------------------

with ui.column().classes("items-center").style(
    "width:100%; min-height:100vh; justify-content:center;"
):
    with ui.row().classes("items-start justify-center").style(
        "gap:24px; max-width:90vw; margin:auto;"
    ):
        left_panel()
        board()
        right_panel()

ui.run(host="0.0.0.0", port=8080)
