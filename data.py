PLAYER_COLORS = {"Player 1": "#f08c53", 
                 "Player 2": "#66e691"}

rows, cols = 4, 4
cell_size = "min(22vw, 22vh)"

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