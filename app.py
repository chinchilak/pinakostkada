from nicegui import ui
import random
import json
import os

from data import (
    dice_and_rule_values, die_face,
    PLAYER_COLORS,
    TILE_COLORS,
    rows, cols, cell_size,
    DEFAULT_DICE_FONT_SCALE,
    DEFAULT_TEXT_FONT_SCALE,
)

SETTINGS_FILE = "game_settings.json"

# ------------- Persistent Settings Helpers ------------------


def load_settings(default_names, default_colors, default_dice_scale, default_text_scale):
    if not os.path.exists(SETTINGS_FILE):
        return default_names, default_colors, default_dice_scale, default_text_scale

    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return default_names, default_colors, default_dice_scale, default_text_scale

    names = data.get("player_names", {}) or {}
    colors = data.get("player_colors", {}) or {}
    dice_scale = data.get("dice_font_scale", default_dice_scale)
    text_scale = data.get("text_font_scale", default_text_scale)

    for k, v in default_names.items():
        names.setdefault(k, v)
    for k, v in default_colors.items():
        colors.setdefault(k, v)

    return names, colors, dice_scale, text_scale


def save_settings(state):
    data = {
        "player_names": state.player_names,
        "player_colors": state.player_colors,
        "dice_font_scale": state.dice_font_scale,
        "text_font_scale": state.text_font_scale,
    }
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        # silent fail is fine for this small tool
        pass


# ----------------- Game Logic Utilities ---------------------

possible_values = list(dice_and_rule_values.keys())


def is_dice_face(value: str) -> bool:
    return all(part.isdigit() for part in value.split())


def dice_string_to_faces(s: str) -> str:
    return " ".join(die_face[n] for n in s.split()) if is_dice_face(s) else s


def card_bg_color(value: str) -> str:
    if is_dice_face(value):
        parts = value.split()
        if len(parts) == 2:
            return TILE_COLORS["pair"]
        elif len(parts) == 3:
            return TILE_COLORS["triple"]
    return TILE_COLORS["other"]


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

        defaults_names = {"Player 1": "Player 1", "Player 2": "Player 2"}
        defaults_colors = dict(PLAYER_COLORS)

        (
            self.player_names,
            self.player_colors,
            self.dice_font_scale,
            self.text_font_scale,
        ) = load_settings(
            defaults_names,
            defaults_colors,
            DEFAULT_DICE_FONT_SCALE,
            DEFAULT_TEXT_FONT_SCALE,
        )

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

    def _has_four_in_line(self, player: str) -> bool:
        directions = [(1, 0), (0, 1), (1, 1), (1, -1)]
        for r in range(rows):
            for c in range(cols):
                if self.owner[r][c] != player:
                    continue
                for dr, dc in directions:
                    ok = True
                    for k in range(1, 4):  # need 3 more = total 4
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
        # If a "last turn" is pending for someone, only that player may act
        if self.pending_last_turn_for and player != self.pending_last_turn_for:
            return False
        # no more than 6 rounds per player
        if self.rounds[player] >= 6:
            return False
        return True

    def play(self, r, c) -> str:
        """
        Called when current player clicks a tile.
        Returns:
          'placed'  -> tile placed, round counted
          'removed' -> own tile removed
          'blocked' -> illegal
        """
        current = self.player

        if not self._can_player_act(current):
            return "blocked"

        owner = self.owner[r][c]

        # own tile: allow removing without ending the round
        if owner == current:
            self.owner[r][c] = None
            return "removed"

        # opponent tile: cannot change
        if owner is not None and owner != current:
            return "blocked"

        # empty tile: place and finish the round
        if owner is None:
            self.owner[r][c] = current
            self.rounds[current] += 1   # this is a full round
            self._after_turn(current)
            return "placed"

        return "blocked"

    def pass_turn(self):
        """Player chooses to pass: counts as a round without placing."""
        current = self.player
        if not self._can_player_act(current):
            return
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

    reason_html = (
        f"Reason: {game.win_reason}" if game.win_reason else ""
    )
    go_detail.set_content(
        f"<div style='font-size:1.2em; font-weight:bold; "
        f"text-shadow:1px 1px 2px rgba(0,0,0,0.4); margin-bottom:12px;'>{reason_html}</div>"
    )

    game_over_dialog.open()


# ---------------- Settings Modal ----------------------------

with ui.dialog() as setup_dialog, ui.card().style("min-width: 360px;"):
    ui.markdown("### ⚙ Game Setup")

    # player name + color rows with reliable on_change saving
    for p in ["Player 1", "Player 2"]:
        with ui.row().style("align-items:center; gap:8px; margin-bottom:6px;"):
            ui.label(p).style("width:80px;font-weight:bold;")

            def handle_name_change(e, player=p):
                game.player_names[player] = e.value
                save_settings(game)
                refresh_ui()

            ui.input(
                value=game.player_names[p],
                on_change=handle_name_change,
            ).style("flex:1;")

            def handle_color_change(e, player=p):
                game.player_colors[player] = e.value
                save_settings(game)
                refresh_ui()

            ui.color_input(
                value=game.player_colors[p],
                on_change=handle_color_change,
            ).style("width:70px;")

    ui.separator()

    ui.label("Dice size")
    def on_dice_size_change(e):
        game.dice_font_scale = e.value
        save_settings(game)
        refresh_ui()

    ui.slider(
        min=0.7,
        max=1.8,
        step=0.1,
        value=game.dice_font_scale,
        on_change=on_dice_size_change,
    ).props("label-always")

    ui.label("Text size")
    def on_text_size_change(e):
        game.text_font_scale = e.value
        save_settings(game)
        refresh_ui()

    ui.slider(
        min=0.7,
        max=1.8,
        step=0.1,
        value=game.text_font_scale,
        on_change=on_text_size_change,
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

    active = player == game.player and not game.game_over

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

        with ui.column().style("align-items:center; margin-top:8px; gap:6px;"):

            def stat_row(label, value):
                with ui.row().style(
                    "width:170px; justify-content:space-between; font-size:1.1em; padding:2px 0;"
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
            stat_row("Rounds:", f"{rounds} ({tiles})")

        if active and not game.game_over:
            def do_pass():
                game.pass_turn()
                refresh_ui()
                if game.game_over:
                    show_game_over()

            ui.button("Pass", on_click=do_pass).style(
                "margin-top:12px; font-weight:bold;"
            )


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
    badge_size = f"{2 * game.text_font_scale}vw"
    pts_fs = f"{0.9 * game.text_font_scale}vw"

    with ui.column().classes("items-center").style("gap:8px;"):
        with ui.grid(columns=cols).style("gap:4px;"):
            for r in range(rows):
                for c in range(cols):
                    v = game.grid[r][c].strip()
                    pts = dice_and_rule_values.get(v, 0)
                    owner = game.owner[r][c]

                    bg = game.player_colors.get(owner, card_bg_color(v)) if owner else card_bg_color(v)

                    def click(row=r, col=c):
                        if game.game_over:
                            return
                        _ = game.play(row, col)
                        refresh_ui()
                        if game.game_over:
                            show_game_over()

                    tile = ui.element("div").style(
                        f"background:{bg}; width:{cell_size}; height:{cell_size}; "
                        "border:2px solid white; border-radius:10px; position:relative; cursor:pointer;"
                    ).on("click", click)

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
                            ui.label(str(pts)).style(f"font-size:{pts_fs}; font-weight:bold;")

        ui.button("⚙ Setup", on_click=setup_dialog.open).props("flat dense")


# ---------------- Final Page Layout ------------------------

with ui.column().classes("items-center").style(
    "width:100%; min-height:100vh; justify-content:center;"
):
    with ui.row().classes("items-center justify-center").style(
        "gap:24px; max-width:90vw; margin:auto;"
    ):
        left_panel()
        board()
        right_panel()

ui.run(host='0.0.0.0', port=8080)
