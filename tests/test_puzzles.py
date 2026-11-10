"""The puzzle library: structure, exactness, agreement with simulation, cross-checks.

No test states the answer of a `practice_pending` puzzle: those are checked only against
simulation and by type, so reading this file spoils nothing I am still practising.
"""

from __future__ import annotations

import itertools
import math
from fractions import Fraction as F

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ev_lab.prob.dist import fair_die
from ev_lab.prob.montecarlo import assert_agrees, rng_for, run_mc
from ev_lab.prob.stopping import value_iteration
from ev_lab.puzzles import (
    ballot_problem,
    birthday_23,
    broken_stick_triangle,
    coupon_collector_die,
    die_one_reroll,
    die_reroll_cost,
    expected_max_of_draws,
    expected_max_three_dice,
    expected_max_two_dice,
    first_ace_position,
    fixed_points_permutation,
    four_cards_four_suits,
    gamblers_ruin_biased,
    meeting_window,
    monty_hall,
    monty_hall_four_doors,
    penney_game,
    random_walk_duration,
    red_black_stopping,
    rolls_until_six,
    rolls_until_two_sixes,
    rope_loops,
    st_petersburg_capped,
    three_cards_red_face,
    three_dice_sum_ten,
    two_headed_coin,
)
from ev_lab.puzzles.base import TAGS, Puzzle
from ev_lab.puzzles.patterns import pattern_chain
from ev_lab.puzzles.registry import all_puzzles, get_puzzle

PUZZLES = all_puzzles()
PRACTICE = {"two_dice_six", "die_one_reroll", "tosses_until_hh", "market_hidden_integer"}

# ---- structure -------------------------------------------------------------------------


def test_library_size_and_unique_ids() -> None:
    assert len(PUZZLES) >= 25
    assert len({p.id for p in PUZZLES}) == len(PUZZLES)


def test_the_four_practice_problems_are_pending_and_listed_first() -> None:
    assert {p.id for p in PUZZLES if p.practice_pending} == PRACTICE
    assert {p.id for p in PUZZLES[:4]} == PRACTICE


def test_every_tag_and_every_difficulty_is_covered() -> None:
    for tag in TAGS:
        assert sum(tag in p.tags for p in PUZZLES) >= 2, tag
    for level in (1, 2, 3):
        assert sum(p.difficulty == level for p in PUZZLES) >= 4, level


@pytest.mark.parametrize("p", PUZZLES, ids=lambda p: p.id)
def test_puzzle_is_well_formed(p: Puzzle) -> None:
    assert set(p.tags) <= set(TAGS)
    assert len(p.statement) > 40 and p.statement.rstrip().endswith(("?", "."))
    assert "{answer}" in p.explanation
    assert 3 <= len([s for s in p.explanation.replace("\n", " ").split(". ") if s]) <= 12
    assert get_puzzle(p.id) is p


def test_unknown_puzzle_id() -> None:
    with pytest.raises(KeyError):
        get_puzzle("no_such_puzzle")


# ---- exactness and agreement with simulation -------------------------------------------


@pytest.mark.parametrize("p", PUZZLES, ids=lambda p: p.id)
def test_exact_answer_is_a_fraction(p: Puzzle) -> None:
    assert type(p.solve()) is F  # not a float, not a numpy scalar


@pytest.mark.parametrize("p", PUZZLES, ids=lambda p: p.id)
def test_exact_agrees_with_monte_carlo(p: Puzzle) -> None:
    mc = run_mc(p.simulate, 60_000, rng_for(20261109, f"test:{p.id}"))
    assert mc.se > 0
    assert_agrees(p.solve(), mc, tol_se=4.0, label=p.id)


def test_simulators_are_reproducible() -> None:
    p = get_puzzle("coupon_collector_die")
    a = run_mc(p.simulate, 5_000, rng_for(1, p.id))
    b = run_mc(p.simulate, 5_000, rng_for(1, p.id))
    assert a == b


# ---- reference values (docs/sources.md) ------------------------------------------------


def test_reference_values_from_the_specification() -> None:
    assert rolls_until_six.solve() == 6
    harmonic_6 = sum((F(1, k) for k in range(1, 7)), F(0))
    assert coupon_collector_die.solve() == 6 * harmonic_6 == F(147, 10)
    assert round(float(birthday_23.solve()), 4) == 0.5073
    assert round(float(birthday_23.solve()), 6) == 0.507297  # digits given by the source
    assert monty_hall.solve() == F(2, 3)
    assert fixed_points_permutation.solve() == 1


def test_coupon_collector_matches_the_source_example_for_50() -> None:
    # Wikipedia's worked example: n = 50 gives 224.9603
    assert round(float(coupon_collector_die.expected_rolls(50)), 4) == 224.9603


# ---- independent cross-checks (a second method for the same number) ---------------------


@pytest.mark.parametrize("n", [1, 2, 3, 4, 5, 6])
def test_fixed_point_distribution_matches_brute_force(n: int) -> None:
    counts = dict.fromkeys(range(n + 1), 0)
    for perm in itertools.permutations(range(n)):
        counts[sum(i == x for i, x in enumerate(perm))] += 1
    dist = fixed_points_permutation.fixed_point_distribution(n)
    for k, c in counts.items():
        assert dist[k] == F(c, math.factorial(n))
    assert dist.expect() == 1


def test_ballot_matches_brute_force_over_all_counting_orders() -> None:
    a, b = ballot_problem.A_VOTES, ballot_problem.B_VOTES
    good = total = 0
    for b_positions in itertools.combinations(range(a + b), b):
        lead, ok = 0, True
        for i in range(a + b):
            lead += -1 if i in b_positions else 1
            ok = ok and lead > 0
        good += ok
        total += 1
    assert ballot_problem.solve() == F(good, total)


@given(st.integers(1, 12), st.integers(0, 11))
def test_ballot_theorem_formula(a: int, b: int) -> None:
    if a > b:
        assert ballot_problem.always_ahead(a, b) == F(a - b, a + b)


def test_reroll_cost_matches_value_iteration() -> None:
    cost = die_reroll_cost.COST
    v = value_iteration(list(range(1, 7)), float, lambda _s: fair_die(), cost=float(cost))
    game_value = sum(v.values()) / 6  # the first roll is free
    assert float(die_reroll_cost.solve()) == pytest.approx(game_value, abs=1e-9)
    # the optimal threshold is the first face you would not pay to re-roll
    threshold, _ = die_reroll_cost.best_threshold(cost)
    assert [v[f] == f for f in range(1, 7)] == [f >= threshold for f in range(1, 7)]


def test_reroll_with_zero_cost_and_with_huge_cost() -> None:
    assert die_reroll_cost.best_threshold(F(0)) == (6, F(6))
    assert die_reroll_cost.best_threshold(F(100)) == (1, F(7, 2))


def _red_black_plain(r: int, b: int) -> F:
    """Direct recursion for the expected future gain, written without the toolkit."""
    if r == 0:
        return F(0)
    if b == 0:
        return F(r)
    go_on = (r * (1 + _red_black_plain(r - 1, b)) + b * (-1 + _red_black_plain(r, b - 1))) / F(
        r + b
    )
    return max(F(0), go_on)


def test_red_black_small_decks() -> None:
    # one red, one black, by hand: draw; red first (1/2) -> stop with +1; black first -> end at 0
    assert red_black_stopping.value(1, 1) == F(1, 2)
    assert red_black_stopping.value(3, 0) == 3
    assert red_black_stopping.value(0, 3) == 0
    for r, b in [(2, 2), (3, 2), (2, 4), (4, 4)]:
        assert red_black_stopping.value(r, b) == _red_black_plain(r, b)


def test_more_rerolls_are_worth_more() -> None:
    values = [die_one_reroll.value(rolls) for rolls in (1, 2, 3, 4)]
    assert values[0] == F(7, 2)
    assert values == sorted(values) and len(set(values)) == 4


def test_four_suits_matches_counting_hands() -> None:
    assert four_cards_four_suits.solve() == F(13**4, math.comb(52, 4))


def test_first_ace_matches_the_gap_symmetry_argument() -> None:
    # aces split the other cards into (aces + 1) gaps of equal expected size
    assert first_ace_position.solve() == F(52 - 4, 4 + 1) + 1
    small = first_ace_position.first_ace_distribution(5, 2)
    brute = [min(c) + 1 for c in itertools.combinations(range(5), 2)]
    assert small.expect() == F(sum(brute), len(brute))


def test_max_of_draws_matches_brute_force() -> None:
    brute = [max(c) for c in itertools.combinations(range(1, 9), 3)]
    assert expected_max_of_draws.max_distribution(8, 3).expect() == F(sum(brute), len(brute))


def test_expected_max_of_dice_matches_tail_sum() -> None:
    for dice in (1, 2, 3):
        tail = sum((1 - F(k, 6) ** dice for k in range(6)), F(0))
        assert expected_max_two_dice.expected_max(dice) == tail


def test_gamblers_ruin_matches_closed_form() -> None:
    p = gamblers_ruin_biased.P_WIN
    r = (1 - p) / p
    k, n = gamblers_ruin_biased.START, gamblers_ruin_biased.TARGET
    assert gamblers_ruin_biased.solve() == (1 - r**k) / (1 - r**n)
    fair = gamblers_ruin_biased.ruin_chain(F(1, 2), 10)
    assert fair.absorption_probs(3)[10] == F(3, 10)


def test_fair_walk_duration_is_product_of_distances() -> None:
    assert random_walk_duration.solve() == random_walk_duration.UP * random_walk_duration.DOWN


def test_run_of_two_successes_formula() -> None:
    p = F(1, 6)
    assert rolls_until_two_sixes.solve() == 1 / p + 1 / p**2


def test_two_headed_coin_matches_bayes_by_odds() -> None:
    odds = F(1, 99) * 2**5
    assert two_headed_coin.solve() == odds / (1 + odds)


def test_rope_loops_small_case_by_hand() -> None:
    # one rope: always one loop. two ropes: first tie closes a loop with prob 1/3, then 1 more.
    assert rope_loops.expected_loops(1) == 1
    assert rope_loops.expected_loops(2) == F(4, 3)


def test_pattern_chain_single_symbol_and_symmetry() -> None:
    assert pattern_chain(["H"]).expected_steps("") == 2
    assert pattern_chain(["HT"]).expected_steps("") == pattern_chain(["TH"]).expected_steps("")
    race = pattern_chain(["HT", "TH"]).absorption_probs("")
    assert race == {"HT": F(1, 2), "TH": F(1, 2)} or race == {"TH": F(1, 2), "HT": F(1, 2)}


def test_shortcuts_quoted_in_explanations_hold() -> None:
    """Each explanation names a shortcut; the computed answer must equal what it implies.
    (Library puzzles only: nothing here concerns a practice_pending puzzle.)"""
    assert monty_hall_four_doors.solve() == F(3, 4) * F(1, 2)
    assert penney_game.solve() == 1 - F(1, 2) ** 2  # opponent needs the first two tosses HH
    assert three_cards_red_face.solve() == F(2, 3)  # two of the three red faces
    assert meeting_window.solve() == 1 - F(3, 4) ** 2
    assert broken_stick_triangle.solve() == 2 * F(1, 2) * F(1, 2) ** 2  # two triangles, legs 1/2
    assert st_petersburg_capped.solve() == st_petersburg_capped.CAP_TOSS + 1
    assert expected_max_three_dice.solve() == sum((1 - F(k, 6) ** 3 for k in range(6)), F(0))
    triples = [t for t in itertools.product(range(1, 7), repeat=3) if sum(t) == 10]
    assert three_dice_sum_ten.solve() == F(len(triples), 216)

    def unordered(total: int) -> int:
        rolls = itertools.product(range(1, 7), repeat=3)
        return len({tuple(sorted(t)) for t in rolls if sum(t) == total})

    assert unordered(9) == unordered(10)  # Galileo's observation in the explanation
    m, n = expected_max_of_draws.DRAWN, expected_max_of_draws.CARDS
    assert expected_max_of_draws.solve() == F(m * (n + 1), m + 1) == n - F(n - m, m + 1)
    assert math.comb(23, 2) == 253  # "23 people form 253 pairs"
    assert rope_loops.solve() == sum((F(1, 2 * k - 1) for k in range(1, 11)), F(0))


@pytest.mark.slow
@pytest.mark.parametrize("p", PUZZLES, ids=lambda p: p.id)
def test_no_simulator_is_biased_across_independent_seeds(p: Puzzle) -> None:
    """A single run can pass by luck. Over many seeds the z-scores of unbiased code average
    to zero: their mean times sqrt(number of seeds) is itself a standard normal draw."""
    exact = p.solve()
    seeds = 25
    zs = [
        run_mc(p.simulate, 100_000, rng_for(4242, f"bias-test:{p.id}:{k}")).z(exact)
        for k in range(seeds)
    ]
    assert abs(sum(zs) / seeds) * math.sqrt(seeds) < 4.0, p.id
