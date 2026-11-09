"""Which category to ask next: weak and slow categories come up more often.

Rule (docs/decisions.md D-019), per category, over its last `window` answers:
    accuracy = (correct + 1) / (answers + 2)          smoothed, so 0 answers -> 0.5
    slowness = clip(median seconds / overall median seconds - 1, 0, 1)
    weight   = 1 + 2 * (1 - accuracy) + slowness      between 1 and 4
A category is drawn with probability weight / sum of weights. Every category keeps a
weight of at least 1, so nothing disappears from practice.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from statistics import median

import numpy as np


@dataclass(frozen=True)
class PastAnswer:
    category: str
    correct: bool
    seconds: float


def category_weights(
    history: Sequence[PastAnswer], categories: Sequence[str], window: int
) -> dict[str, float]:
    recent = {c: [a for a in history if a.category == c][-window:] for c in categories}
    all_seconds = [a.seconds for rows in recent.values() for a in rows]
    overall = median(all_seconds) if all_seconds else 0.0
    weights: dict[str, float] = {}
    for c in categories:
        rows = recent[c]
        accuracy = (sum(a.correct for a in rows) + 1) / (len(rows) + 2)
        slowness = 0.0
        if rows and overall > 0:
            slowness = min(1.0, max(0.0, median(a.seconds for a in rows) / overall - 1.0))
        weights[c] = 1.0 + 2.0 * (1.0 - accuracy) + slowness
    return weights


def pick_category(rng: np.random.Generator, weights: dict[str, float]) -> str:
    names = list(weights)
    p = np.array([weights[n] for n in names], dtype=np.float64)
    return names[int(rng.choice(len(names), p=p / p.sum()))]
