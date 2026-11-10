// Hand evaluator for 5, 6 or 7 cards. Offline study only.
//
// Same integer values as the Python evaluators (src/ev_lab/cards/evaluator.py):
//
//     value = category * 13^5 + up to five tiebreaker ranks as base-13 digits
//
// so a higher value always means a better hand, and the three implementations (Python
// oracle, numpy, C++) can be compared with ==.
//
// A card is an integer 0..51: rank = card / 4 (0 = deuce .. 12 = ace), suit = card % 4.
//
// Method: describe the hand by 13-bit rank masks and look the pieces up in tables with
// 8192 entries.
//     m1, m2, m3, m4   ranks present at least once / twice / three times / four times
//     fm               ranks of the flush suit, when five or more cards share a suit
#pragma once

#include <array>
#include <cstdint>

namespace evlab {

constexpr int kMasks = 1 << 13;
constexpr std::int32_t kBase = 371293;  // 13^5
constexpr std::int32_t kWeight[5] = {28561, 2197, 169, 13, 1};  // 13^4 .. 13^0

enum Category : std::int32_t {
  kHighCard = 0,
  kPair,
  kTwoPair,
  kTrips,
  kStraight,
  kFlush,
  kFullHouse,
  kQuads,
  kStraightFlush,
};

struct Tables {
  std::array<std::int8_t, kMasks> high{};       // index of the highest set bit (0 if none)
  std::array<std::int8_t, kMasks> popcount{};
  std::array<std::int8_t, kMasks> straight{};   // high rank of the best straight, or -1
  std::array<std::int32_t, kMasks> top5{};      // top five ranks at tiebreaker digits 0..4
  std::array<std::int32_t, kMasks> kick3{};     // top three ranks at digits 1..3 (after a pair)
  std::array<std::int32_t, kMasks> kick2{};     // top two ranks at digits 1..2 (after trips)

  Tables() {
    const int wheel = (1 << 12) | 0b1111;  // A-2-3-4-5: the ace plays low
    for (int mask = 0; mask < kMasks; ++mask) {
      int ranks[13];
      int count = 0;
      for (int r = 12; r >= 0; --r) {
        if (mask >> r & 1) ranks[count++] = r;
      }
      high[mask] = static_cast<std::int8_t>(count ? ranks[0] : 0);
      popcount[mask] = static_cast<std::int8_t>(count);

      int best = -1;
      for (int top = 12; top >= 4 && best < 0; --top) {
        const int run = 0b11111 << (top - 4);
        if ((mask & run) == run) best = top;
      }
      if (best < 0 && (mask & wheel) == wheel) best = 3;  // the five is the high card
      straight[mask] = static_cast<std::int8_t>(best);

      std::int32_t t5 = 0, k3 = 0, k2 = 0;
      for (int i = 0; i < count && i < 5; ++i) t5 += ranks[i] * kWeight[i];
      for (int i = 0; i < count && i < 3; ++i) k3 += ranks[i] * kWeight[i + 1];
      for (int i = 0; i < count && i < 2; ++i) k2 += ranks[i] * kWeight[i + 1];
      top5[mask] = t5;
      kick3[mask] = k3;
      kick2[mask] = k2;
    }
  }
};

inline const Tables& tables() {
  static const Tables instance;
  return instance;
}

// Value of `n` cards (5 <= n <= 7): the best five-card hand among them.
inline std::int32_t evaluate(const int* cards, int n) {
  const Tables& t = tables();
  int m1 = 0, m2 = 0, m3 = 0, m4 = 0;
  int suit_mask[4] = {0, 0, 0, 0};
  for (int i = 0; i < n; ++i) {
    const int bit = 1 << (cards[i] >> 2);
    m4 |= m3 & bit;  // order matters: promote from the highest count down
    m3 |= m2 & bit;
    m2 |= m1 & bit;
    m1 |= bit;
    suit_mask[cards[i] & 3] |= bit;
  }

  int fm = 0;
  for (int s = 0; s < 4; ++s) {
    if (t.popcount[suit_mask[s]] >= 5) fm = suit_mask[s];
  }

  // A straight flush needs five *suited* consecutive cards: test the flush mask.
  if (fm && t.straight[fm] >= 0) return kStraightFlush * kBase + t.straight[fm] * kWeight[0];

  if (m4) {
    const int quad = t.high[m4];
    return kQuads * kBase + quad * kWeight[0] + t.high[m1 & ~(1 << quad)] * kWeight[1];
  }

  if (m3) {
    const int trip = t.high[m3];
    const int pairs = m2 & ~(1 << trip);  // includes a second, lower set of trips
    if (pairs) return kFullHouse * kBase + trip * kWeight[0] + t.high[pairs] * kWeight[1];
  }

  if (fm) return kFlush * kBase + t.top5[fm];  // top five of the suit, even with 6 or 7

  if (t.straight[m1] >= 0) return kStraight * kBase + t.straight[m1] * kWeight[0];

  if (m3) {
    const int trip = t.high[m3];
    return kTrips * kBase + trip * kWeight[0] + t.kick2[m1 & ~(1 << trip)];
  }

  if (m2) {
    const int pair1 = t.high[m2];
    const int lower = m2 & ~(1 << pair1);
    if (lower) {
      const int pair2 = t.high[lower];
      // with three pairs the third pair's rank competes for the kicker
      const int kicker = t.high[m1 & ~(1 << pair1) & ~(1 << pair2)];
      return kTwoPair * kBase + pair1 * kWeight[0] + pair2 * kWeight[1] + kicker * kWeight[2];
    }
    return kPair * kBase + pair1 * kWeight[0] + t.kick3[m1 & ~(1 << pair1)];
  }

  return t.top5[m1];
}

}  // namespace evlab
