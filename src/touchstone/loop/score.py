"""Turn a τ² results file into `results/<version>.json` — P1.5, with no model call.

[D-007] is unchanged; what changed is whose answer key it reads. τ²'s evaluator is mechanical —
a database diff and a replayed action sequence — so scoring is arithmetic over a file someone
else's orchestrator wrote, and arithmetic is reproducible in a way a judge is not.

Two success definitions, reported side by side, and conflating them is the whole risk.

- `reward` is τ²'s composite, and we publish it unmodified (invariant 16). On today's
  retail tasks it legitimately contains an `NL_ASSERTION` judge — 112 of 114 declare one.
- `reward_breakdown["DB"]` is the mechanical component and the only thing touchstone gates
  on ([D-069]). It is written on every task by `evaluator_env.py:153`.

We gate on a component; we do not get to publish a different headline.

Nothing here imports τ². The package costs 1.56 s to import — its `__init__` chain builds
the whole registry — and phase 1's gate is the unit suite under 2 s. The two upstream functions
this needs are four lines between them and are copied with their file and line, which
`doctor`'s `metric_check` then asserts still agree with the pin. Re-deriving a metric is how
two projects end up publishing the same word for different arithmetic.

The shape it writes is `loop.schema` — `doctor` and the `score` command read those types too,
so they are not this step's to own.
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Any, cast

from touchstone.loop.schema import (
    INFRA,
    TERMINATION_REASONS,
    Case,
    Scored,
    TerminationReasons,
)


def is_successful(reward: float) -> bool:
    """Copied verbatim from `tau2/metrics/agent_metrics.py:12`.

    The tolerance is upstream's and it is not decoration. `reward` is a product of
    component floats, so an exactly-1.0 comparison fails on rounding that no one can see.
    """
    return (1 - 1e-6) <= reward <= (1 + 1e-6)


def pass_hat_k(num_trials: int, success_count: int, k: int) -> float:
    """Copied verbatim from `tau2/metrics/agent_metrics.py:113` (arXiv 2406.12045).

    Not "the fraction that passed every attempt" — it is the probability that k trials drawn
    without replacement all pass; the two coincide only at `k == num_trials` (D-099).
    `pass^k`, never `pass@k`: the familiar name means at least one of k, a weaker gate.

    Args:
        num_trials: Trials actually run for one task.
        success_count: How many of them succeeded.
        k: How many trials to draw.

    Returns:
        The pass^k metric for one task.

    Raises:
        ValueError: When fewer than `k` trials were run — upstream's behaviour, kept.
    """
    if num_trials < k:
        raise ValueError(f"Number of trials {num_trials} is less than k {k}.")
    return math.comb(success_count, k) / math.comb(num_trials, k)


def db_component(sim: dict[str, Any]) -> float | None:
    """The mechanical component, or `None` when the simulation carries no breakdown at all.

    `None` is not 0.0. A missing breakdown means the evaluator did not run — an infra
    error, a crash — and scoring that as a failed DB check would blame the agent for the
    harness. It is counted as a failed trial (that is the leaderboard convention) but never
    as a failed DB check, and the two counts are reported separately.
    """
    return ((sim.get("reward_info") or {}).get("reward_breakdown") or {}).get("DB")


def score(simulations: list[dict[str, Any]], k: int) -> Scored:
    """Aggregate one τ² results file's simulations. Pure, deterministic, no I/O, no model.

    Infra errors count as failed — the leaderboard convention, the opposite of τ²'s own
    `get_metrics_df` (`agent_metrics.py:145`). `infra_error_convention` records which, in the
    results file, because a number without its convention is not comparable.
    `k` is never inferred per task; undersampled tasks are named, not averaged in at a
    different strictness.

    Args:
        simulations: The `simulations` list of a τ² results file, already loaded.
        k: How many trials pass^k draws — `config.K`.

    Returns:
        The `aggregate` and `cases` halves of `results/<version>.json` (docs/05 §6).
    """
    by_task: dict[str, list[dict[str, Any]]] = {}
    for sim in simulations:
        by_task.setdefault(str(sim["task_id"]), []).append(sim)

    rewards = [float((s.get("reward_info") or {}).get("reward") or 0.0) for s in simulations]
    terminations = Counter(str(s.get("termination_reason")) for s in simulations)

    # Which component killed the reward — counted only where the composite actually failed.
    # A component at 0.0 on a run that still scored 1.0 is arithmetically impossible (the
    # composite is a product), so this cannot double-count; it can only stay honest if the
    # guard is here rather than assumed.
    zeroed: Counter[str] = Counter()
    for sim in simulations:
        info = sim.get("reward_info") or {}
        if is_successful(float(info.get("reward") or 0.0)):
            continue
        for name, value in sorted((info.get("reward_breakdown") or {}).items()):
            if value == 0.0:
                zeroed[name] += 1

    cases: list[Case] = []
    hat_k: list[float] = []
    hat_1: list[float] = []
    undersampled: list[str] = []
    # Length-then-lexicographic, not `key=int` — and the asymmetry with
    # `scripts/freeze-benchmark.py` is deliberate. Only `airline` and `retail` have all-digit
    # task ids; `telecom`'s look like `[mobile_data_issue]user_abroad_…[PERSONA:Hard]`. The
    # freezer must crash on those, because a different sort there is a silently different
    # benchmark. Ordering a results table is presentation, so it must not crash — and on decimal
    # ids this key agrees with numeric order, which is what the manifest froze.
    for task_id in sorted(by_task, key=lambda t: (len(t), t)):
        sims = by_task[task_id]
        wins = sum(
            is_successful(float((s.get("reward_info") or {}).get("reward") or 0.0)) for s in sims
        )
        db_values = [v for v in (db_component(s) for s in sims) if v is not None]
        hat_1.append(wins / len(sims))
        if len(sims) >= k:
            hat_k.append(pass_hat_k(len(sims), wins, k))
        else:
            undersampled.append(task_id)
        cases.append({
            "id": task_id,
            "trials": len(sims),
            "success_k": wins,
            "db_passed": sum(is_successful(v) for v in db_values),
            "db_scored": len(db_values),
        })

    return {
        "aggregate": {
            "k": k,
            "trials": len(simulations),
            "tasks": len(by_task),
            "reward_mean": _mean(rewards),
            "pass_hat_1": _mean(hat_1),
            "pass_hat_k": _mean(hat_k),
            "reward_breakdown_zeroed": dict(sorted(zeroed.items())),
            "infra_error_convention": "counted_as_failed",
            "infra_errors": terminations.get(INFRA, 0),
            "undersampled_tasks": undersampled,
            # The one `cast` here, and it is safe by construction rather than by assertion:
            # `TERMINATION_REASONS` IS this TypedDict's key list, so the comprehension cannot
            # produce a key the type does not declare or miss one it does.
            "termination_reasons": cast(
                "TerminationReasons", cast(object, {r: terminations.get(r, 0) for r in TERMINATION_REASONS})
            ),
        },
        "cases": cases,
    }


def _mean(values: list[float]) -> float:
    """An empty mean is `0.0`, not a crash and not `None` — but see the caller.

    It reads as a real zero in the results file, which is why `trials`, `tasks` and
    `undersampled_tasks` sit beside every mean here: a rate with no denominator visible is
    the failure this project has paid for most often.
    """
    return sum(values) / len(values) if values else 0.0
