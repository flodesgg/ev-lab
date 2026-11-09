"""Small zero-sum matrix games used in tests and in the report (row player's payoffs)."""

from __future__ import annotations

from fractions import Fraction

Matrix = tuple[tuple[Fraction | int, ...], ...]

ROCK_PAPER_SCISSORS: Matrix = ((0, -1, 1), (1, 0, -1), (-1, 1, 0))
# rock beating scissors pays double
BIASED_RPS: Matrix = ((0, -1, 2), (1, 0, -1), (-2, 1, 0))
MATCHING_PENNIES: Matrix = ((1, -1), (-1, 1))
# solved by hand in tests: row (3/7, 4/7), column (2/7, 5/7), value 1/7
HAND_2X2: Matrix = ((3, -1), (-2, 1))
# the third row is strictly worse than the first, so it gets probability 0
DOMINATED_ROW: Matrix = ((3, -1), (-2, 1), (2, -2))

GAMES: dict[str, Matrix] = {
    "rock-paper-scissors": ROCK_PAPER_SCISSORS,
    "biased rock-paper-scissors": BIASED_RPS,
    "matching pennies": MATCHING_PENNIES,
    "hand-solved 2x2": HAND_2X2,
    "dominated third row": DOMINATED_ROW,
}
REGRET_GAMES = ("rock-paper-scissors", "biased rock-paper-scissors")
