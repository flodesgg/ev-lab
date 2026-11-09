"""Exact toolkit: distributions, linear algebra, Markov chains, stopping, geometry, MC."""

from __future__ import annotations

import itertools
from fractions import Fraction as F

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from ev_lab.prob.dist import Dist, convolve, fair_die, joint, sum_of
from ev_lab.prob.exact import exact
from ev_lab.prob.geometry import UNIT_SQUARE, area, clip
from ev_lab.prob.linalg import SingularMatrixError, identity, inverse, matmul, solve
from ev_lab.prob.markov import AbsorbingChain
from ev_lab.prob.montecarlo import (
    FloatArray,
    McResult,
    agrees,
    assert_agrees,
    rng_for,
    run_mc,
)
from ev_lab.prob.stopping import StoppingSolution, value_iteration

# ---- exact gate ------------------------------------------------------------------------


@pytest.mark.parametrize("bad", [0.5, np.float64(0.5), np.int64(1), True, "1/2", None])
def test_exact_refuses_anything_but_int_and_fraction(bad: object) -> None:
    with pytest.raises(TypeError, match="exact arithmetic only"):
        exact(bad)


def test_dist_refuses_float_probabilities() -> None:
    with pytest.raises(TypeError):
        Dist({"a": 0.5, "b": 0.5})  # type: ignore[dict-item]


def test_dist_refuses_float_outcomes_in_expectation() -> None:
    with pytest.raises(TypeError):
        Dist({0.5: F(1)}).expect()


# ---- Dist ------------------------------------------------------------------------------


def test_probabilities_must_sum_to_one() -> None:
    with pytest.raises(ValueError, match="sum to"):
        Dist({1: F(1, 2), 2: F(1, 3)})
    with pytest.raises(ValueError, match="negative"):
        Dist({1: F(3, 2), 2: F(-1, 2)})


def test_die_mean_and_variance_by_hand() -> None:
    die = fair_die()
    assert die.expect() == F(21, 6)
    # E[X^2] - E[X]^2 = 91/6 - 49/4
    assert die.variance() == F(91, 6) - F(49, 4)
    assert all(isinstance(p, F) for _, p in die.items())


def test_map_merges_outcomes() -> None:
    parity = fair_die().map(lambda x: x % 2)
    assert parity == Dist({0: F(1, 2), 1: F(1, 2)})


def test_sum_of_two_dice_matches_brute_force_count() -> None:
    two = sum_of(fair_die(), 2)
    for total in range(2, 13):
        count = sum(1 for a, b in itertools.product(range(1, 7), repeat=2) if a + b == total)
        assert two[total] == F(count, 36)
    assert two == convolve(fair_die(), fair_die())
    assert two[13] == 0


def test_joint_is_all_tuples_equally_likely() -> None:
    j = joint(fair_die(), fair_die(), fair_die())
    assert len(j) == 216
    assert j[(1, 2, 3)] == F(1, 216)


def test_condition_renormalises() -> None:
    even = fair_die().condition(lambda x: x % 2 == 0)
    assert even == Dist.uniform([2, 4, 6])
    with pytest.raises(ValueError, match="probability 0"):
        fair_die().condition(lambda x: x > 6)


def test_bind_is_law_of_total_probability() -> None:
    # urn A (prob 1/3) has 1 red of 2; urn B (prob 2/3) has 1 red of 4
    urn = Dist({"A": F(1, 3), "B": F(2, 3)})
    red = urn.bind(
        lambda u: Dist(
            {True: F(1, 2), False: F(1, 2)} if u == "A" else {True: F(1, 4), False: F(3, 4)}
        )
    )
    assert red[True] == F(1, 3) * F(1, 2) + F(2, 3) * F(1, 4)


def test_uniform_counts_repeats() -> None:
    assert Dist.uniform("aab") == Dist({"a": F(2, 3), "b": F(1, 3)})


@given(st.lists(st.integers(min_value=1, max_value=50), min_size=1, max_size=6))
def test_from_weights_sums_to_one_and_expectation_is_linear(weights: list[int]) -> None:
    d = Dist.from_weights(dict(enumerate(weights)))
    assert sum((p for _, p in d.items()), F(0)) == 1
    assert d.expect(lambda x: 3 * x + 2) == 3 * d.expect() + 2
    assert d.variance(lambda x: 3 * x + 2) == 9 * d.variance()
    assert sum_of(d, 3).expect() == 3 * d.expect()
    assert sum_of(d, 3).variance() == 3 * d.variance()


# ---- linear algebra --------------------------------------------------------------------


def test_solve_hand_example() -> None:
    # x + 2y = 5, 3x + 4y = 6  ->  x = -4, y = 9/2
    assert solve([[1, 2], [3, 4]], [[5], [6]]) == [[F(-4)], [F(9, 2)]]


def test_inverse_times_matrix_is_identity() -> None:
    a = [[F(2), F(1), F(0)], [F(1), F(3), F(1)], [F(0), F(1), F(4)]]
    assert matmul(inverse(a), a) == identity(3)


def test_singular_matrix_is_reported() -> None:
    with pytest.raises(SingularMatrixError):
        inverse([[1, 2], [2, 4]])


def test_solve_needs_a_pivot_swap() -> None:
    assert solve([[0, 1], [1, 0]], [[2], [3]]) == [[F(3)], [F(2)]]


# ---- Markov chains ---------------------------------------------------------------------


def test_three_state_chain_solved_by_hand() -> None:
    # A -> A 2/3, A -> B 1/3;  B -> A 3/4, B -> C 1/4;  C absorbing.
    # E_A = 1 + (2/3)E_A + (1/3)E_B and E_B = 1 + (3/4)E_A  give  E_A = 16, E_B = 13.
    chain = AbsorbingChain({"A": {"A": F(2, 3), "B": F(1, 3)}, "B": {"A": F(3, 4), "C": F(1, 4)}})
    assert chain.transient == ["A", "B"] and chain.absorbing == ["C"]
    assert chain.expected_steps("A") == 16
    assert chain.expected_steps("B") == 13
    assert chain.expected_steps("C") == 0
    assert chain.absorption_probs("A") == {"C": F(1)}
    # visits to A before absorption, from A: N[A][A] = 12 (and 4 visits to B: 12 + 4 = 16)
    assert chain.expected_visits("A", "A") == 12
    assert chain.expected_visits("A", "B") == 4


def test_fair_walk_on_four_points_solved_by_hand() -> None:
    # States 0..3, 0 and 3 absorbing. From 1: h1 = h2/2, h2 = 1/2 + h1/2 -> h1 = 1/3.
    # Steps: t1 = 1 + t2/2, t2 = 1 + t1/2 -> t1 = t2 = 2.
    half = F(1, 2)
    chain = AbsorbingChain({1: {0: half, 2: half}, 2: {1: half, 3: half}, 0: {0: 1}})
    assert chain.absorbing == [0, 3]
    assert chain.absorption_probs(1) == {0: F(2, 3), 3: F(1, 3)}
    assert chain.expected_steps(1) == 2
    assert chain.absorption_probs(3) == {0: F(0), 3: F(1)}


def test_chain_validation() -> None:
    with pytest.raises(ValueError, match="sum to"):
        AbsorbingChain({"A": {"A": F(1, 2), "B": F(1, 3)}})
    with pytest.raises(ValueError, match="never reach"):
        AbsorbingChain({"A": {"B": 1}, "B": {"A": 1}, "C": {"D": 1}})
    with pytest.raises(TypeError):
        AbsorbingChain({"A": {"B": 0.5, "A": 0.5}})  # type: ignore[dict-item]


def test_chain_matches_simulation() -> None:
    chain = AbsorbingChain({"A": {"A": F(2, 3), "B": F(1, 3)}, "B": {"A": F(3, 4), "C": F(1, 4)}})

    def simulate(rng: np.random.Generator, n: int) -> FloatArray:
        out = np.zeros(n)
        for i in range(n):
            state, steps = "A", 0
            while state != "C":
                u = rng.random()
                state = ("A" if u < 2 / 3 else "B") if state == "A" else ("A" if u < 0.75 else "C")
                steps += 1
            out[i] = steps
        return out

    assert_agrees(chain.expected_steps("A"), run_mc(simulate, 20_000, rng_for(1, "chain")))


# ---- optimal stopping ------------------------------------------------------------------


def _d4_game(rolls: int) -> StoppingSolution[int]:
    return StoppingSolution(rolls - 1, lambda _t, face: face, lambda _t, _face: fair_die(4))


def _d4_value(rolls: int) -> F:
    game = _d4_game(rolls)
    return fair_die(4).expect(lambda face: game.value(0, face))


def test_two_step_game_solved_by_hand() -> None:
    # Four-sided die, one optional re-roll. A re-roll is worth E = 5/2, so keep 3 and 4:
    # value = (3 + 4)/4 + (2/4)(5/2) = 3.
    game = _d4_game(2)
    assert game.continuation(0, 1) == F(5, 2)
    assert [game.should_stop(0, face) for face in (1, 2, 3, 4)] == [False, False, True, True]
    assert fair_die(4).expect(lambda face: game.value(0, face)) == 3
    assert game.should_stop(1, 1)  # at the horizon you must stop


def test_more_rolls_never_hurt_and_no_reroll_is_the_mean() -> None:
    values = [_d4_value(k) for k in (1, 2, 3, 4)]
    assert values[0] == F(5, 2)
    assert values == sorted(values)
    assert all(isinstance(v, F) for v in values)


def test_stopping_matches_brute_force_over_all_threshold_policies() -> None:
    # 3 rolls of a d4: a policy is a keep-threshold for roll 1 and for roll 2.
    die = fair_die(4)

    def policy_value(t1: int, t2: int) -> F:
        last = die.expect()
        second = die.expect(lambda f: f if f >= t2 else last)
        return die.expect(lambda f: f if f >= t1 else second)

    best = max(policy_value(a, b) for a in range(1, 6) for b in range(1, 6))
    game = _d4_game(3)
    assert die.expect(lambda f: game.value(0, f)) == best


def test_value_iteration_free_rerolls_reach_the_maximum() -> None:
    v = value_iteration(list(range(1, 5)), float, lambda _s: fair_die(4), cost=0.0, tol=1e-12)
    assert all(abs(x - 4.0) < 1e-9 for x in v.values())


def test_value_iteration_expensive_rerolls_mean_stop_at_once() -> None:
    v = value_iteration(list(range(1, 5)), float, lambda _s: fair_die(4), cost=10.0)
    assert v == {1: 1.0, 2: 2.0, 3: 3.0, 4: 4.0}


# ---- geometry --------------------------------------------------------------------------


def test_area_of_unit_square_and_half() -> None:
    assert area(UNIT_SQUARE) == 1
    below_diagonal = clip(UNIT_SQUARE, -1, 1, 0)  # y <= x
    assert area(below_diagonal) == F(1, 2)
    assert area(clip(UNIT_SQUARE, 1, 0, F(1, 3))) == F(1, 3)  # x <= 1/3
    assert area(clip(UNIT_SQUARE, 1, 1, F(1, 2))) == F(1, 8)  # corner triangle
    assert area(clip(UNIT_SQUARE, 1, 0, -1)) == 0  # empty


@given(
    st.fractions(min_value=-2, max_value=2),
    st.fractions(min_value=-2, max_value=2),
    st.fractions(min_value=-2, max_value=2),
)
def test_a_line_splits_the_square_into_two_parts_of_total_area_one(a: F, b: F, c: F) -> None:
    if a == 0 and b == 0:
        return
    assert area(clip(UNIT_SQUARE, a, b, c)) + area(clip(UNIT_SQUARE, -a, -b, -c)) == 1


# ---- Monte Carlo checker ---------------------------------------------------------------


def _die_sim(rng: np.random.Generator, n: int) -> FloatArray:
    return rng.integers(1, 7, n).astype(np.float64)


def test_mc_estimate_and_standard_error() -> None:
    mc = run_mc(_die_sim, 100_000, rng_for(7, "die"))
    assert mc.n == 100_000
    # sd of a die is sqrt(35/12); SE = sd / sqrt(n)
    assert mc.se == pytest.approx((35 / 12) ** 0.5 / 100_000**0.5, rel=0.02)
    assert agrees(F(7, 2), mc)
    assert_agrees(F(7, 2), mc)


def test_mc_detects_a_wrong_exact_answer() -> None:
    mc = run_mc(_die_sim, 100_000, rng_for(7, "die"))
    assert not agrees(F(36, 10), mc)  # 3.6 instead of 3.5 is about 18 SE away
    with pytest.raises(AssertionError, match="SE") as err:
        assert_agrees(F(36, 10), mc, label="die")
    assert "3.6" not in str(err.value) and "18/5" not in str(err.value)  # no values leaked


def test_same_seed_same_result_and_names_give_different_streams() -> None:
    a = run_mc(_die_sim, 1000, rng_for(7, "die"))
    b = run_mc(_die_sim, 1000, rng_for(7, "die"))
    c = run_mc(_die_sim, 1000, rng_for(7, "other"))
    d = run_mc(_die_sim, 1000, rng_for(8, "die"))
    assert a == b
    assert a != c and a != d


def test_exact_value_must_be_a_fraction() -> None:
    mc = McResult(estimate=3.5, se=0.01, n=100)
    with pytest.raises(TypeError, match="must be a Fraction"):
        agrees(3.5, mc)  # type: ignore[arg-type]


def test_zero_standard_error_requires_equality() -> None:
    constant = McResult(estimate=1.0, se=0.0, n=100)
    assert agrees(F(1), constant)
    assert not agrees(F(99, 100), constant)


def test_simulator_must_return_a_vector() -> None:
    with pytest.raises(ValueError, match="1-D"):
        run_mc(lambda _rng, n: np.zeros((n, 2)), 10, rng_for(1, "x"))
