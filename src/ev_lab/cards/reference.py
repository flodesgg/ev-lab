"""Reference category counts for all 5-card and all 7-card (best five of seven) hands.

Standard combinatorics results; source checked 2026-11-09 (docs/sources.md): Wikipedia,
"Poker probability", frequency tables for 5-card and 7-card hands. The code must reproduce
them; if it does not, the bug is in the code.

Index 0 = high card ... 8 = straight flush (royal flushes included).
"""

from __future__ import annotations

FIVE_CARD_TOTAL = 2_598_960
FIVE_CARD_COUNTS = (1_302_540, 1_098_240, 123_552, 54_912, 10_200, 5_108, 3_744, 624, 40)

SEVEN_CARD_TOTAL = 133_784_560
SEVEN_CARD_COUNTS = (
    23_294_460,
    58_627_800,
    31_433_400,
    6_461_620,
    6_180_020,
    4_047_644,
    3_473_184,
    224_848,
    41_584,
)
