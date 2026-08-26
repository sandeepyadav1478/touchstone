"""The published shape of `results/<version>.json` — docs/05 §6, as types.

Its own module because it is a vocabulary, not a step: `score` writes these, `doctor`'s
`metric_check` reads `TERMINATION_REASONS` to diff the pinned ten against τ²'s live enum, and
`touchstone score` will assemble the envelope around `Scored`. A shape three callers agree on
that lives inside one of them is a shape the other two import a step to reach.

Nothing here imports τ² — same 1.56 s reason as `score` itself.
"""

from __future__ import annotations

from typing import Literal, TypedDict


class TerminationReasons(TypedDict):
    """all ten, always, even AT zero — `tau2/data_model/simulation.py:1254`, declaration order.

    A key that appears only when it fires cannot be read as "never fired": the reader cannot
    tell it from "not recorded", and the two mean opposite things about a run.

    A total `TypedDict` is why that is now a type error rather than a convention. Omit one
    and `mypy` refuses the construction — the rule moved out of this docstring and into the
    checker. The tuple below is derived from these annotations, so there is one list of ten
    in the project and no way for a key to exist in one place and not the other.
    """

    user_stop: int
    agent_stop: int
    max_steps: int
    timeout: int
    too_many_errors: int
    agent_error: int
    user_error: int
    infrastructure_error: int
    context_window_exceeded: int
    unexpected_error: int


TERMINATION_REASONS = tuple(TerminationReasons.__annotations__)


class Case(TypedDict):
    """One task's row — docs/05 §6 `cases[]`.

    `db_scored` is a separate denominator from `trials`: a simulation that died before the
    evaluator ran is a trial that happened and a DB check that did not.
    """

    id: str
    trials: int
    success_k: int
    db_passed: int
    db_scored: int


class Aggregate(TypedDict):
    """The arithmetic half of docs/05 §6 `aggregate`.

    The span-derived keys are deliberately absent from this type, not optional in it.
    `cost_per_success_usd`, `tool_calls_mean`, `p95_latency_s`, `budget_exceeded` and
    `void_attempts` have no producer until `touchstone run` exists (P1.6). Declaring them
    `NotRequired` would let a caller read a key that nothing has ever written.
    """

    k: int
    trials: int
    tasks: int
    reward_mean: float
    pass_hat_1: float
    pass_hat_k: float
    reward_breakdown_zeroed: dict[str, int]
    #: A `Literal`, so the other published convention cannot be written here by accident.
    infra_error_convention: Literal["counted_as_failed"]
    infra_errors: int
    undersampled_tasks: list[str]
    termination_reasons: TerminationReasons


class Scored(TypedDict):
    """What `score()` returns — the two halves of the results file it can fill on its own.

    Not the whole file. `benchmark_hash`, `domain` and `tau2_commit` come from
    `suite/benchmark/manifest.json`, and `model`/`provider`/`auth` are facts about a run, so the
    envelope is assembled by the `touchstone score` command. A scorer that reaches for a manifest
    is a scorer that cannot be tested without one.
    """

    aggregate: Aggregate
    cases: list[Case]

#: The one τ² counts as "the run never happened". We count it as a failed trial — see `score`.
INFRA = "infrastructure_error"
