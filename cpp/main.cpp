// Command-line front end for the C++ hand evaluator. Used by the Python tests and reports.
//
//   ev_eval eval K        read hands from stdin (K card integers per hand, whitespace
//                         separated), print one value per line
//   ev_eval counts K      enumerate every K-card hand (K = 5, 6 or 7) and print the nine
//                         category counts, high card first, then "seconds <elapsed>"
//   ev_eval bench N       evaluate N pseudo-random 7-card hands, print hands per second
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>

#include "evaluator.hpp"

namespace {

using Clock = std::chrono::steady_clock;

double seconds_since(Clock::time_point start) {
  return std::chrono::duration<double>(Clock::now() - start).count();
}

int run_eval(int k) {
  std::vector<int> cards(static_cast<std::size_t>(k));
  std::vector<char> seen(52);
  while (true) {
    for (int i = 0; i < k; ++i) {
      if (std::scanf("%d", &cards[static_cast<std::size_t>(i)]) != 1) {
        if (i == 0) return 0;  // clean end of input
        std::fprintf(stderr, "error: incomplete hand at end of input\n");
        return 2;
      }
    }
    std::fill(seen.begin(), seen.end(), 0);
    for (int c : cards) {
      if (c < 0 || c > 51) {
        std::fprintf(stderr, "error: card %d is not in 0..51\n", c);
        return 2;
      }
      if (seen[static_cast<std::size_t>(c)]) {
        std::fprintf(stderr, "error: duplicate card %d in a hand\n", c);
        return 2;
      }
      seen[static_cast<std::size_t>(c)] = 1;
    }
    std::printf("%d\n", evlab::evaluate(cards.data(), k));
  }
}

// Visit every k-subset of 0..51 in increasing order.
void enumerate(int k, int start, int depth, int* cards, std::int64_t* counts) {
  if (depth == k) {
    ++counts[evlab::evaluate(cards, k) / evlab::kBase];
    return;
  }
  for (int c = start; c <= 52 - (k - depth); ++c) {
    cards[depth] = c;
    enumerate(k, c + 1, depth + 1, cards, counts);
  }
}

int run_counts(int k) {
  std::int64_t counts[9] = {0};
  int cards[7];
  const auto start = Clock::now();
  enumerate(k, 0, 0, cards, counts);
  for (int i = 0; i < 9; ++i) std::printf("%lld\n", static_cast<long long>(counts[i]));
  std::printf("seconds %.3f\n", seconds_since(start));
  return 0;
}

int run_bench(long long n) {
  // xorshift64: a fixed, self-contained generator so the benchmark needs no input
  std::uint64_t state = 0x9E3779B97F4A7C15ULL;
  auto next = [&state]() {
    state ^= state << 13;
    state ^= state >> 7;
    state ^= state << 17;
    return state;
  };
  std::vector<int> hands(static_cast<std::size_t>(n) * 7);
  for (long long h = 0; h < n; ++h) {
    int deck[52];
    for (int i = 0; i < 52; ++i) deck[i] = i;
    for (int i = 0; i < 7; ++i) {  // partial Fisher-Yates shuffle
      const int j = i + static_cast<int>(next() % static_cast<std::uint64_t>(52 - i));
      const int tmp = deck[i];
      deck[i] = deck[j];
      deck[j] = tmp;
      hands[static_cast<std::size_t>(h * 7 + i)] = deck[i];
    }
  }
  const auto start = Clock::now();
  std::int64_t checksum = 0;
  for (long long h = 0; h < n; ++h) {
    checksum += evlab::evaluate(&hands[static_cast<std::size_t>(h * 7)], 7);
  }
  const double elapsed = seconds_since(start);
  std::printf("hands %lld\nseconds %.6f\nchecksum %lld\n", n, elapsed,
              static_cast<long long>(checksum));
  return 0;
}

}  // namespace

int main(int argc, char** argv) {
  if (argc == 3) {
    const long long arg = std::atoll(argv[2]);
    if (std::strcmp(argv[1], "eval") == 0 && arg >= 5 && arg <= 7) return run_eval(static_cast<int>(arg));
    if (std::strcmp(argv[1], "counts") == 0 && arg >= 5 && arg <= 7) return run_counts(static_cast<int>(arg));
    if (std::strcmp(argv[1], "bench") == 0 && arg >= 1) return run_bench(arg);
  }
  std::fprintf(stderr, "usage: ev_eval eval K | counts K | bench N   (K = 5, 6 or 7)\n");
  return 2;
}
