"""Mental math: generators against an independent calculation, adaptive weights, sessions."""

from __future__ import annotations

import re
from decimal import Decimal
from fractions import Fraction as F
from pathlib import Path

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from ev_lab.practice_log import LogHeaderError, read_rows
from ev_lab.trainer import math_log
from ev_lab.trainer.adaptive import PastAnswer, category_weights, pick_category
from ev_lab.trainer.io import ScriptedIO
from ev_lab.trainer.math_session import run_math_session
from ev_lab.trainer.mental_math import CATEGORIES, LEVELS, TITLES, Question, generate

# ---- generators vs an independent calculation ------------------------------------------


def _independent_answer(q: Question) -> Decimal | F:
    """Recompute the answer from the question *text* alone, by a different route."""
    t = q.text
    if q.category in ("mul_2x2", "mul_3x1", "decimal_mul"):
        a, b = t.split(" x ")
        return Decimal(a) * Decimal(b)
    if q.category == "division":
        a, b = re.fullmatch(r"(\d+) / (\d+) \(to 2 decimals\)", t).groups()  # type: ignore[union-attr]
        return F(int(a), int(b))
    if q.category == "squares":
        n = int(t.removesuffix("^2"))
        return F(sum(2 * k + 1 for k in range(n)))  # n^2 = sum of the first n odd numbers
    if q.category == "frac_pct":
        if t.endswith("as a percentage"):
            n, d = t.split(" ")[0].split("/")
            return Decimal(int(n)) * 100 / Decimal(int(d))
        return F(Decimal(t.split("%")[0])) / 100
    if q.category == "pct_change":
        a, b = re.fullmatch(r"(\d+) -> (\d+): percentage change", t).groups()  # type: ignore[union-attr]
        return (Decimal(b) / Decimal(a) - 1) * 100
    if q.category == "seq_sum":
        nums = [int(x) for x in re.findall(r"\d+", t.split("(")[0])]
        first, second, last = nums[0], nums[1], nums[-1]
        if nums[:3] == [1, 2, 4]:  # geometric: 1 + 2 + 4 + ... + last
            total, term = 0, 1
            while term <= last:
                total, term = total + term, term * 2
            return F(total)
        terms = list(range(first, last + 1, second - first))
        if "terms)" in t:
            assert len(terms) == int(re.search(r"\((\d+) terms\)", t).group(1))  # type: ignore[union-attr]
        return F(sum(terms))
    raise AssertionError(q.category)


@settings(max_examples=150, deadline=None)
@given(
    st.sampled_from(sorted(CATEGORIES)),
    st.sampled_from(LEVELS),
    st.integers(min_value=0, max_value=2**32 - 1),
)
def test_generated_answer_matches_independent_calculation(
    category: str, level: int, seed: int
) -> None:
    q = generate(np.random.default_rng(seed), category, level)
    assert q.category == category and q.level == level
    assert isinstance(q.answer, F) and isinstance(q.tolerance, F)
    other = _independent_answer(q)
    if isinstance(other, F):
        assert q.answer == other
    else:  # Decimal: 28 significant digits, compare far below any tolerance
        assert abs(Decimal(q.answer.numerator) / Decimal(q.answer.denominator) - other) < Decimal(
            "1e-20"
        )
    assert q.is_correct(q.answer)


def test_every_category_has_a_title_and_all_levels_work() -> None:
    assert set(CATEGORIES) == set(TITLES) and len(CATEGORIES) == 8
    rng = np.random.default_rng(0)
    for category in CATEGORIES:
        for level in LEVELS:
            generate(rng, category, level)
    with pytest.raises(ValueError, match="level"):
        generate(rng, "squares", 4)


def test_same_seed_same_questions() -> None:
    a = [generate(np.random.default_rng(5), c, 2) for c in CATEGORIES]
    b = [generate(np.random.default_rng(5), c, 2) for c in CATEGORIES]
    assert a == b


def test_tolerances_by_category() -> None:
    rng = np.random.default_rng(3)
    for category in ("mul_2x2", "mul_3x1", "decimal_mul", "squares", "seq_sum"):
        q = generate(rng, category, 2)
        assert q.tolerance == 0 and not q.is_correct(q.answer + F(1, 1000))
    q = Question("division", 2, "100 / 7 (to 2 decimals)", F(100, 7), F(1, 100))
    assert q.is_correct(F("14.29")) and q.is_correct(F("14.28"))  # rounded or truncated
    assert not q.is_correct(F("14.3")) and not q.is_correct(F("14.27"))
    assert generate(rng, "pct_change", 1).tolerance == F(1, 10)
    assert generate(rng, "pct_change", 3).tolerance == F(1, 2)


# ---- adaptive weights ------------------------------------------------------------------

CATS = ["a", "b", "c"]


def test_no_history_means_equal_weights() -> None:
    w = category_weights([], CATS, window=50)
    assert w == {"a": 2.0, "b": 2.0, "c": 2.0}


def test_weak_and_slow_categories_get_more_weight() -> None:
    history = (
        [PastAnswer("a", True, 5.0)] * 20  # accurate, normal speed
        + [PastAnswer("b", False, 5.0)] * 20  # inaccurate
        + [PastAnswer("c", True, 15.0)] * 20  # accurate but slow
    )
    w = category_weights(history, CATS, window=50)
    assert w["b"] > w["c"] > w["a"]
    # by hand: a = 1 + 2(1 - 21/22); b = 1 + 2(1 - 1/22); c = a + min(1, 15/5 - 1)
    assert w["a"] == pytest.approx(1 + 2 / 22)
    assert w["b"] == pytest.approx(1 + 42 / 22)
    assert w["c"] == pytest.approx(1 + 2 / 22 + 1.0)
    assert all(1.0 <= x <= 4.0 for x in w.values())


def test_only_the_recent_window_counts() -> None:
    history = [PastAnswer("a", False, 5.0)] * 100 + [PastAnswer("a", True, 5.0)] * 10
    assert category_weights(history, ["a"], window=10)["a"] == pytest.approx(1 + 2 / 12)


def test_pick_category_follows_the_weights() -> None:
    rng = np.random.default_rng(11)
    picks = [pick_category(rng, {"a": 1.0, "b": 3.0}) for _ in range(4000)]
    assert picks.count("b") / 4000 == pytest.approx(0.75, abs=0.03)


# ---- timed session ---------------------------------------------------------------------


class FakeClock:
    """Each question takes `step` seconds: the clock advances whenever it is read."""

    def __init__(self, step: float) -> None:
        self.now, self.step = 0.0, step

    def __call__(self) -> float:
        self.now += self.step
        return self.now


def _run(answers: list[str], questions: int, limit: float, step: float = 1.0):  # type: ignore[no-untyped-def]
    io = ScriptedIO(answers)
    logged: list[tuple[Question, str, bool, float]] = []
    summary = run_math_session(
        questions=questions,
        seconds_limit=limit,
        level=1,
        rng=np.random.default_rng(42),
        weights={"squares": 1.0},
        io=io,
        clock=FakeClock(step),
        log=lambda q, a, ok, s: logged.append((q, a, ok, s)),
    )
    return summary, logged, io


def _square_answers(count: int) -> list[str]:
    rng = np.random.default_rng(42)
    out = []
    for _ in range(count):
        pick_category(rng, {"squares": 1.0})
        out.append(str(generate(rng, "squares", 1).answer))
    return out


def test_session_all_correct() -> None:
    summary, logged, io = _run(_square_answers(3), questions=3, limit=600)
    assert (summary.answered, summary.correct, summary.ended) == (3, 3, "all questions answered")
    assert [ok for _, _, ok, _ in logged] == [True, True, True]
    assert all(s > 0 for _, _, _, s in logged)
    assert any("right" in line for line in io.transcript)
    assert "Correct: 3/3 (100%)" in "\n".join(summary.lines())


def test_wrong_answer_shows_the_right_one_immediately() -> None:
    right = _square_answers(1)[0]
    summary, logged, io = _run(["1"], questions=1, limit=600)
    assert summary.correct == 0 and logged[0][1] == "1"
    assert any("wrong" in line and right in line for line in io.transcript)


def test_enter_skips_and_garbage_is_asked_again() -> None:
    answers = _square_answers(2)
    _, logged, io = _run(["", "abc", answers[1]], questions=2, limit=600)
    assert [(a, ok) for _, a, ok, _ in logged] == [("", False), (answers[1], True)]
    assert any("not a number" in line for line in io.transcript)


def test_session_stops_when_time_is_up() -> None:
    # every clock read costs 10 s and the limit is 45 s: only the first answer is in time
    summary, logged, _ = _run(_square_answers(5), questions=5, limit=45, step=10)
    assert summary.ended == "time is up"
    assert summary.answered == len(logged) == 1
    assert summary.seconds_used <= 45


def test_late_answer_is_discarded() -> None:
    summary, logged, io = _run(_square_answers(1), questions=1, limit=25, step=10)
    assert summary.answered == 0 and logged == []
    assert any("not counted" in line for line in io.transcript)


def test_end_of_input_stops_the_session() -> None:
    summary, _, _ = _run(_square_answers(1), questions=5, limit=600)
    assert summary.ended == "stopped early" and summary.answered == 1


# ---- the log ---------------------------------------------------------------------------


def test_math_log_rows_and_header(tmp_path: Path) -> None:
    q = Question("division", 2, "100 / 7 (to 2 decimals)", F(100, 7), F(1, 100))
    math_log.log_answer(tmp_path, "s1", q, "14.29", True, 3.21)
    math_log.log_answer(tmp_path, "s1", q, "", False, 9.0)
    rows = read_rows(tmp_path / math_log.FILE_NAME, math_log.HEADER)
    assert rows[0]["category"] == "division" and rows[0]["correct_answer"] == "14.2857"
    assert (
        rows[0]["answer"] == "14.29" and rows[0]["correct"] == "1" and rows[0]["seconds"] == "3.2"
    )
    assert math_log.history(tmp_path) == [
        PastAnswer("division", True, 3.2),
        PastAnswer("division", False, 9.0),
    ]
    (tmp_path / math_log.FILE_NAME).write_text("wrong,header\n1,2\n")
    with pytest.raises(LogHeaderError):
        math_log.log_answer(tmp_path, "s1", q, "1", False, 1.0)
