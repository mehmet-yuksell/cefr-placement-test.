"""Simulate synthetic examinees to check the test algorithm.

Usage:
    python tools/simulate.py --n 2000 --seed 42 [--length 28] [--mode adaptive]
                             [--theta-sd 1.2] [--retakes 200] [--bank-dir DIR]

True abilities are drawn from N(0, theta-sd). Three scenarios are run:

* ideal: responses follow exactly the provisional parameters used for scoring;
* misspecified: each item's true b is its stored b + U(-0.5, 0.5) and its
  true a is U(0.7, 1.4), while scoring keeps the stored values;
* oracle ceiling: every item sits exactly at the examinee's information peak
  (no bank, no content rules), an upper bound for this length and model.

A retake study then gives the same examinees three consecutive attempts and
counts repeated items. All figures describe the algorithm under idealised
assumptions, not real-world validity. Exit status is 1 if within-one-level
agreement in the ideal scenario is below 95%.
"""

from __future__ import annotations

import argparse
import random
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean

from placement import engine
from placement.bank import DEFAULT_BANK_DIR, ItemBank, load_bank
from placement.config import (
    CEFR_LEVELS,
    DEFAULT_GUESSING,
    INFO_PEAK_OFFSET,
    TEST_LENGTH,
)
from placement.exposure import summarise_exposure
from placement.scoring import (
    ScoredResponse,
    borderline_with,
    eap,
    level_for_theta,
    level_probabilities,
    most_likely_level,
    p_correct,
)

WITHIN_ONE_GATE = 0.95


@dataclass
class ScenarioStats:
    """Aggregated outcome of one simulated scenario."""

    name: str
    lengths: list[int] = field(default_factory=list)
    ses: list[float] = field(default_factory=list)
    errors: list[float] = field(default_factory=list)
    confusion: Counter[tuple[str, str]] = field(default_factory=Counter)
    borderline: int = 0
    exposure: Counter[str] = field(default_factory=Counter)
    flags: Counter[str] = field(default_factory=Counter)
    # (true theta, theta estimate, SE, headline level) per examinee
    records: list[tuple[float, float, float, str]] = field(default_factory=list)

    def add(self, true_theta: float, responses: list[ScoredResponse]) -> None:
        """Score one simulated test and accumulate its statistics."""
        est = eap(responses)
        level = most_likely_level(level_probabilities(est.posterior))
        self.lengths.append(len(responses))
        self.ses.append(est.se)
        self.errors.append(est.theta - true_theta)
        self.confusion[(level_for_theta(true_theta), level)] += 1
        self.borderline += borderline_with(est.theta, est.se, level) is not None
        self.records.append((true_theta, est.theta, est.se, level))

    def borderline_profile(self, factor: float) -> tuple[float, float, float]:
        """For a borderline factor: (borderline rate, exact rate of clear results, coverage).

        Coverage counts a result as right when the true level is the headline,
        or, for borderline results, the named neighbouring level.
        """
        flagged = clear_hits = clear = covered = 0
        for true_theta, theta, se, level in self.records:
            truth = level_for_theta(true_theta)
            neighbour = borderline_with(theta, se, level, factor)
            if neighbour is None:
                clear += 1
                clear_hits += truth == level
                covered += truth == level
            else:
                flagged += 1
                covered += truth in (level, neighbour)
        return flagged / self.n, clear_hits / clear if clear else 0.0, covered / self.n

    def level_exact(self, level: str) -> float:
        """Exact agreement among examinees whose true level is ``level``."""
        row = [self.confusion[(level, est)] for est in CEFR_LEVELS]
        return self.confusion[(level, level)] / sum(row) if sum(row) else 0.0

    @property
    def n(self) -> int:
        return len(self.lengths)

    def agreement(self, max_distance: int) -> float:
        """Share of examinees classified within ``max_distance`` levels."""
        hits = sum(
            count
            for (true, est), count in self.confusion.items()
            if abs(CEFR_LEVELS.index(true) - CEFR_LEVELS.index(est)) <= max_distance
        )
        return hits / self.n


def answer_probability(theta: float, true_params: tuple[float, float, float]) -> float:
    a, b, c = true_params
    return p_correct(theta, b, a, c)


def run_engine(
    bank: ItemBank,
    theta: float,
    true_params: dict[str, tuple[float, float, float]],
    rng: random.Random,
    *,
    seed: int,
    mode: str,
    length: int,
    seen: dict[str, int] | None = None,
    routing: dict[str, int] | None = None,
) -> engine.TestState:
    """Administer one test to a simulated examinee with ability ``theta``."""
    state = engine.new_test(bank, seed=seed, mode=mode, length=length, seen=seen, routing_weights=routing)
    while (item := engine.current_item(state, bank)) is not None:
        correct = rng.random() < answer_probability(theta, true_params[item.id])
        engine.record_answer(state, bank, item.id, correct)
    return state


def simulate_bank_scenario(
    name: str,
    bank: ItemBank,
    thetas: list[float],
    true_params: dict[str, tuple[float, float, float]],
    rng: random.Random,
    mode: str,
    length: int,
    routing: dict[str, int] | None = None,
) -> ScenarioStats:
    """Run every examinee through the engine with the given true parameters."""
    stats = ScenarioStats(name)
    for index, theta in enumerate(thetas):
        state = run_engine(bank, theta, true_params, rng, seed=index, mode=mode, length=length, routing=routing)
        stats.add(theta, engine.scored_responses(state, bank))
        stats.exposure.update(state.selected)
        stats.flags.update(state.flags)
    return stats


def simulate_oracle(thetas: list[float], rng: random.Random, length: int) -> ScenarioStats:
    """Every item at the examinee's own information peak: an upper bound."""
    stats = ScenarioStats("oracle ceiling")
    for theta in thetas:
        b = theta - INFO_PEAK_OFFSET
        responses = [
            ScoredResponse(b=b, correct=rng.random() < p_correct(theta, b)) for _ in range(length)
        ]
        stats.add(theta, responses)
    return stats


def simulate_retakes(
    bank: ItemBank,
    thetas: list[float],
    true_params: dict[str, tuple[float, float, float]],
    rng: random.Random,
    mode: str,
    length: int,
    attempts: int = 3,
) -> list[tuple[float, float]]:
    """Per attempt: (mean repeated items, share of examinees with any repeat)."""
    repeats: list[list[int]] = [[] for _ in range(attempts)]
    for index, theta in enumerate(thetas):
        seen: dict[str, int] = {}
        for attempt in range(1, attempts + 1):
            state = run_engine(
                bank, theta, true_params, rng, seed=10_000 * attempt + index, mode=mode, length=length, seen=seen
            )
            repeats[attempt - 1].append(sum(1 for i in state.selected if i in seen))
            seen.update(dict.fromkeys(state.selected, attempt))
    return [(mean(r), sum(1 for x in r if x) / len(r)) for r in repeats]


def format_stats(stats: ScenarioStats) -> list[str]:
    """Human-readable lines for one scenario."""
    lines = [
        f"## {stats.name} (n = {stats.n})",
        f"mean test length         {mean(stats.lengths):.1f}",
        f"exact CEFR agreement     {stats.agreement(0):.1%}",
        f"within one level         {stats.agreement(1):.1%}",
        f"mean SE                  {mean(stats.ses):.3f}",
        f"RMSE of theta            {mean(e * e for e in stats.errors) ** 0.5:.3f}",
        f"mean bias of theta       {mean(stats.errors):+.3f}",
        f"labelled borderline      {stats.borderline / stats.n:.1%}",
        "confusion matrix (rows = true level, columns = estimated level):",
        "        " + "".join(f"{lvl:>6}" for lvl in CEFR_LEVELS) + "   exact",
    ]
    for true in CEFR_LEVELS:
        row = [stats.confusion[(true, est)] for est in CEFR_LEVELS]
        total = sum(row)
        exact = f"{row[CEFR_LEVELS.index(true)] / total:6.1%}" if total else "     -"
        lines.append(f"  {true:<6}" + "".join(f"{c:>6}" for c in row) + f"  {exact}")
    if stats.flags:
        lines.append("relaxation events (tests affected): " + ", ".join(f"{k}={v}" for k, v in sorted(stats.flags.items())))
    return lines


def parse_routing(text: str) -> dict[str, int] | None:
    """Parse ``A1:1,A2:2,...`` into routing weights (None when empty)."""
    if not text.strip():
        return None
    weights = {}
    for part in text.split(","):
        level, _, weight = part.partition(":")
        if level.strip() not in CEFR_LEVELS:
            raise SystemExit(f"unknown level in --routing: {level!r}")
        weights[level.strip()] = int(weight)
    return weights


def main(argv: list[str] | None = None) -> int:
    """Run all scenarios, print the report and return the exit status."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--n", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--length", type=int, default=TEST_LENGTH)
    parser.add_argument("--mode", choices=("adaptive", "fixed"), default="adaptive")
    parser.add_argument("--theta-sd", type=float, default=1.2)
    parser.add_argument("--retakes", type=int, default=200, help="examinees in the 3-attempt study (0 = skip)")
    parser.add_argument("--bank-dir", type=Path, default=DEFAULT_BANK_DIR)
    parser.add_argument("--borderline-factors", default="",
                        help="comma-separated SE factors to compare for the borderline label, e.g. 0.5,0.35,0.25")
    parser.add_argument("--routing", default="",
                        help="routing-stage level weights to try, e.g. A1:1,A2:2,B1:2,B2:3,C1:1,C2:1")
    args = parser.parse_args(argv)
    routing = parse_routing(args.routing)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    bank = load_bank(args.bank_dir)
    master = random.Random(args.seed)
    thetas = [master.gauss(0.0, args.theta_sd) for _ in range(args.n)]
    nominal = {i.id: (i.discrimination_a, i.difficulty_b, i.guessing_c) for i in bank.items}
    shifted = {
        i.id: (master.uniform(0.7, 1.4), i.difficulty_b + master.uniform(-0.5, 0.5), DEFAULT_GUESSING)
        for i in bank.items
    }

    ideal = simulate_bank_scenario(
        "ideal", bank, thetas, nominal, random.Random(f"{args.seed}:ideal"), args.mode, args.length, routing
    )
    misspecified = simulate_bank_scenario(
        "misspecified", bank, thetas, shifted, random.Random(f"{args.seed}:mis"), args.mode, args.length, routing
    )
    oracle = simulate_oracle(thetas, random.Random(f"{args.seed}:oracle"), args.length)

    print(f"# Simulation: n={args.n}, seed={args.seed}, length={args.length}, mode={args.mode}, "
          f"true theta ~ N(0, {args.theta_sd}), bank={len(bank)} items / {len(bank.passages)} passages")
    if routing:
        print(f"routing weights: {routing}")
    print("These figures describe the algorithm under idealised assumptions, not real-world validity.\n")
    for stats in (ideal, misspecified, oracle):
        print("\n".join(format_stats(stats)))
        print()
    factors = [float(f) for f in args.borderline_factors.split(",") if f.strip()]
    if factors:
        print("## borderline factor comparison (ideal scenario)")
        print("factor  borderline  exact(all)  exact(clear results)  coverage")
        for factor in factors:
            rate, clear_exact, coverage = ideal.borderline_profile(factor)
            print(f"{factor:<6.2f}  {rate:>10.1%}  {ideal.agreement(0):>10.1%}  {clear_exact:>20.1%}  {coverage:>8.1%}")
        print()

    summary = summarise_exposure(ideal.exposure, (i.id for i in bank.items), ideal.n)
    print("## item exposure (ideal scenario)")
    print(f"max exposure rate        {summary.max_rate:.1%}")
    print(f"median exposure rate     {summary.median_rate:.1%}")
    print(f"items never used         {summary.unused_share:.1%}")
    print("most exposed             " + ", ".join(f"{i} {r:.0%}" for i, r in summary.most_exposed))

    if args.retakes:
        retake_thetas = thetas[: args.retakes]
        rows = simulate_retakes(
            bank, retake_thetas, nominal, random.Random(f"{args.seed}:retake"), args.mode, args.length
        )
        print(f"\n## retakes: {len(retake_thetas)} examinees x 3 consecutive attempts")
        for attempt, (mean_repeats, share) in enumerate(rows, start=1):
            print(f"attempt {attempt}: mean repeated items {mean_repeats:.1f}, examinees with any repeat {share:.0%}")

    within_one = ideal.agreement(1)
    verdict = "PASS" if within_one >= WITHIN_ONE_GATE else "FAIL"
    print(f"\nGATE within-one-level >= {WITHIN_ONE_GATE:.0%} (ideal): {within_one:.1%} -> {verdict}")
    print(f"exact agreement {ideal.agreement(0):.1%} vs oracle ceiling {oracle.agreement(0):.1%}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
