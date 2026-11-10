"""The web trainer: the step-wise math drill, the JSON app and the HTTP mapping.

No sockets are opened: requests go straight to `respond` / `TrainerApp.handle`.
"""

from __future__ import annotations

import csv
import json
from fractions import Fraction as F
from pathlib import Path

import numpy as np
import pytest
import yaml

from ev_lab.context import start
from ev_lab.puzzles.registry import get_puzzle
from ev_lab.trainer.math_drill import MathDrill
from ev_lab.trainer.mental_math import Question
from ev_lab.web.app import ApiError, TrainerApp
from ev_lab.web.server import HOST, INDEX, respond

REPO = Path(__file__).resolve().parents[1]


class Clock:
    """A clock the test moves by hand."""

    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


# ---- MathDrill ----------------------------------------------------------------------------


def _drill(clock: Clock, questions: int = 3, limit: float = 60.0):  # type: ignore[no-untyped-def]
    logged: list[tuple[Question, str, bool, float]] = []
    drill = MathDrill(
        questions=questions,
        seconds_limit=limit,
        level=1,
        rng=np.random.default_rng(1),
        weights={"squares": 1.0},
        clock=clock,
        log=lambda q, a, ok, s: logged.append((q, a, ok, s)),
    )
    return drill, logged


def test_drill_grades_times_and_finishes() -> None:
    clock = Clock()
    drill, logged = _drill(clock)
    assert drill.number == 1 and drill.remaining() == 60.0 and not drill.finished
    first = drill.current
    assert first is not None
    clock.now += 4.0
    graded = drill.submit(str(first.answer))
    assert (graded.status, graded.correct, graded.correct_answer) == (
        "graded",
        True,
        str(first.answer),
    )
    assert logged[0][2] is True and logged[0][3] == pytest.approx(4.0)
    assert drill.number == 2 and drill.remaining() == pytest.approx(56.0)
    assert drill.submit("abc").status == "invalid" and len(logged) == 1  # asked again
    assert drill.submit("").correct is False  # skipped: logged as wrong
    assert drill.submit("0").correct is False
    assert drill.finished and drill.current is None
    assert drill.summary.ended == "all questions answered"
    assert (drill.summary.answered, drill.summary.correct) == (3, 1)
    with pytest.raises(RuntimeError):
        drill.submit("1")


def test_drill_discards_an_answer_after_the_deadline() -> None:
    clock = Clock()
    drill, logged = _drill(clock, limit=10.0)
    clock.now += 10.5
    assert drill.submit("1").status == "late"
    assert drill.finished and logged == [] and drill.summary.ended == "time is up"
    assert drill.summary.seconds_used == 10.0


def test_drill_can_be_stopped() -> None:
    drill, _ = _drill(Clock())
    drill.stop()
    assert drill.finished and drill.summary.ended == "stopped early"


# ---- the app ------------------------------------------------------------------------------


@pytest.fixture
def app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TrainerApp:
    raw = yaml.safe_load((REPO / "config.yaml").read_text())
    raw["monte_carlo"]["trials"] = 2000
    raw["trainer"]["math"]["presets"]["tiny"] = {"questions": 2, "minutes": 1}
    raw["trainer"]["daily"]["math_preset"] = "tiny"
    (tmp_path / "config.yaml").write_text(yaml.safe_dump(raw))
    monkeypatch.chdir(tmp_path)
    return TrainerApp(start(Path("config.yaml")), seed=5, clock=Clock())


def test_overview(app: TrainerApp) -> None:
    o = app.handle("GET", "/api/overview")
    assert o["default_preset"] == "tiny" and o["presets"]["tiny"] == {"questions": 2, "minutes": 1}
    assert set(o["quantities"]) == {"sum3", "max2", "product2", "heads10", "range3"}
    assert o["stats"]["math_answers"] == 0 and o["stats"]["puzzles_total"] >= 25


def test_math_session_never_sends_the_answer_before_the_attempt(app: TrainerApp) -> None:
    clock: Clock = app.clock  # type: ignore[assignment]
    s = app.handle("POST", "/api/math/start", {"preset": "tiny", "level": 1})
    assert (s["number"], s["total"], s["remaining"], s["done"]) == (1, 2, 60.0, False)
    assert set(s) == {"done", "number", "total", "remaining", "question", "summary", "focus"}
    clock.now += 3.0
    bad = app.handle("POST", "/api/math/answer", {"answer": "nonsense"})
    assert bad["status"] == "invalid" and bad["number"] == 1 and bad["correct_answer"] == ""
    wrong = app.handle("POST", "/api/math/answer", {"answer": "-1"})
    assert wrong["status"] == "graded" and wrong["correct"] is False and wrong["correct_answer"]
    assert wrong["number"] == 2 and wrong["remaining"] == 57.0
    last = app.handle("POST", "/api/math/answer", {"answer": ""})
    assert last["done"] and "Answered 2 of 2" in last["summary"][0]
    rows = _rows(Path("practice/math_log.csv"))
    assert [r["correct"] for r in rows] == ["0", "0"] and rows[0]["answer"] == "-1"
    assert rows[0]["seconds"] == "3.0" and len({r["session_id"] for r in rows}) == 1
    with pytest.raises(ApiError, match="no math session"):
        app.handle("POST", "/api/math/answer", {"answer": "1"})


def test_math_time_limit_and_stop(app: TrainerApp) -> None:
    clock: Clock = app.clock  # type: ignore[assignment]
    app.handle("POST", "/api/math/start", {})
    clock.now += 61.0
    late = app.handle("POST", "/api/math/answer", {"answer": "5"})
    assert late["status"] == "late" and late["done"] and "time is up" in late["summary"][0]
    assert not Path("practice/math_log.csv").exists()  # the late answer was not logged
    app.handle("POST", "/api/math/start", {})
    assert "stopped early" in app.handle("POST", "/api/math/stop")["summary"][0]
    with pytest.raises(ApiError, match="unknown preset"):
        app.handle("POST", "/api/math/start", {"preset": "nope"})
    with pytest.raises(ApiError, match="level"):
        app.handle("POST", "/api/math/start", {"level": 7})


def test_quiz_reveals_the_solution_only_after_an_answer(app: TrainerApp) -> None:
    clock: Clock = app.clock  # type: ignore[assignment]
    shown = app.handle("POST", "/api/quiz/next")
    puzzle = get_puzzle(shown["id"])
    assert puzzle.practice_pending and shown["reason"] == "practice problem, not tried yet"
    assert set(shown) == {
        "id",
        "title",
        "statement",
        "difficulty",
        "tags",
        "kind",
        "max_width",
        "reason",
    }
    exact = puzzle.solve()
    assert format(float(exact), ".6g") not in json.dumps(shown)  # nothing leaked
    clock.now += 42.0
    if puzzle.kind == "market":
        body = {"bid": str(exact - 1), "ask": str(exact + 1)}
        with pytest.raises(ApiError, match="bid"):
            app.handle("POST", "/api/quiz/answer", {"bid": "x", "ask": "3"})
    else:
        body = {"answer": str(exact)}
        with pytest.raises(ApiError, match="answer"):
            app.handle("POST", "/api/quiz/answer", {"answer": "x"})
    result = app.handle("POST", "/api/quiz/answer", body)
    assert result["correct"] is True and result["seconds"] == 42.0
    assert result["explanation"] and result["exact"] and "SE" in result["monte_carlo"]
    assert "(in 1 d)" in result["next_review"]
    rows = _rows(Path("practice/puzzle_log.csv"))
    assert [(r["puzzle_id"], r["correct"], r["seconds"]) for r in rows] == [
        (puzzle.id, "1", "42.0")
    ]
    with pytest.raises(ApiError, match="no puzzle is open"):  # one attempt per showing
        app.handle("POST", "/api/quiz/answer", body)
    assert app.handle("POST", "/api/quiz/next")["id"] != puzzle.id  # the next pending one


def test_market_game_end_to_end(app: TrainerApp) -> None:
    s = app.handle("POST", "/api/market/start", {"quantity": "sum3"})
    assert (s["title"], s["rounds"], s["round"], s["public"], s["max_width"]) == (
        "Sum of three dice", 3, 1, "nothing", "3",
    )  # fmt: skip
    assert "x" not in s and "review" not in s  # nothing about the hidden value yet
    wide = app.handle("POST", "/api/market/quote", {"bid": "5", "ask": "15"})
    assert wide["status"] == "invalid" and "too wide" in wide["error"] and wide["round"] == 1
    fair = F(21, 2)
    while True:
        half = F(s["max_width"]) / 2
        s = app.handle(
            "POST", "/api/market/quote", {"bid": str(fair - half), "ask": str(fair + half)}
        )
        assert s["status"] == "ok" and s["trade"]
        if s["done"]:
            break
        fair = sum(int(part.split("= ")[1]) for part in s["public"].split(", ")) + F(7, 2) * (
            3 - len(s["public"].split(", "))
        )
    assert len(s["review"]) == 3 and all(r["contains_fair"] == "yes" for r in s["review"])
    assert s["review"][0]["fair_value"] == "10.5" and s["review"][0]["public"] == "nothing"
    rows = _rows(Path("practice/market_log.csv"))
    assert len(rows) == 3 and {r["x"] for r in rows} == {str(s["x"])}
    assert f"{sum(float(r['pnl']) for r in rows):+.2f}" == s["total_pnl"]
    with pytest.raises(ApiError, match="no market game"):
        app.handle("POST", "/api/market/quote", {"bid": "1", "ask": "2"})
    with pytest.raises(ApiError, match="unknown quantity"):
        app.handle("POST", "/api/market/start", {"quantity": "nope"})


def test_stats_and_figures(app: TrainerApp) -> None:
    empty = app.handle("POST", "/api/stats")
    assert empty["figures"] == [] and empty["stats"]["practice_days"] == 0
    assert app.figure_path("math_accuracy.png") is None
    app.handle("POST", "/api/math/start", {})
    app.handle("POST", "/api/math/answer", {"answer": "1"})
    app.handle("POST", "/api/math/answer", {"answer": "1"})
    after = app.handle("POST", "/api/stats")
    assert after["stats"]["math_answers"] == 2 and after["stats"]["streak"] == 1
    assert after["figures"] == ["math_accuracy.png", "math_speed.png"]
    assert app.figure_path("math_accuracy.png") is not None
    assert app.figure_path("../../config.yaml") is None  # only the two known files


# ---- HTTP mapping -------------------------------------------------------------------------


def test_http_mapping(app: TrainerApp) -> None:
    status, kind, body = respond(app, "GET", "/", b"")
    assert status == 200 and kind.startswith("text/html") and b"ev-lab trainer" in body
    status, kind, body = respond(app, "GET", "/api/overview", b"")
    assert status == 200 and kind == "application/json" and "presets" in json.loads(body)
    status, _, body = respond(app, "POST", "/api/math/start", b'{"preset": "nope"}')
    assert status == 400 and "unknown preset" in json.loads(body)["error"]
    assert respond(app, "POST", "/api/math/start", b"{not json")[0] == 400
    assert respond(app, "POST", "/api/math/start", b"[1, 2]")[0] == 400
    assert respond(app, "GET", "/api/nope", b"")[0] == 404
    assert respond(app, "GET", "/figures/math_accuracy.png", b"")[0] == 404
    assert respond(app, "GET", "/figures/../../config.yaml", b"")[0] == 404


def test_page_is_local_and_self_contained() -> None:
    assert HOST == "127.0.0.1"
    page = INDEX.read_text()
    assert "http://" not in page and "https://" not in page  # no external resource at all
    assert "<script src" not in page and "<link" not in page
    for route in ("/api/overview", "/api/math/start", "/api/math/answer", "/api/math/stop",
                  "/api/quiz/next", "/api/quiz/answer", "/api/market/start",
                  "/api/market/quote", "/api/stats"):  # fmt: skip
        assert route in page, route
