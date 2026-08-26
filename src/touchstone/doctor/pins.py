"""Whether the pinned world still agrees with what was measured — P1.0 and D-099.

Two independent pins, one shape. Each is a pure comparison plus a private wrapper that
does the I/O, so the decision tests without τ²'s 1.71 s import:

    specimen    the corpus a run would load — task count and policy size
    metrics     our copies of `pass_hat_k` and `is_successful`, and the termination
                vocabulary, against upstream's own

Both exist because a silent disagreement here does not break a run; it makes every number
the run produces describe something other than what the version table says it does.
"""

from __future__ import annotations

import json

from .. import config
from .result import Check


def specimen_check(tasks: int, policy_bytes: int) -> Check:
    """Compare a resolved specimen against the measured pin — the logic half of P1.0.

    Split from `_tau2_data` so it tests without τ²'s 1.71 s import. The convention through
    this module: I/O in the private wrapper, the decision here.

    Args:
        tasks: How many tasks retail's `tasks.json` actually holds.
        policy_bytes: The on-disk size of retail's `policy.md`.

    Returns:
        A pass only when both match `config`'s measured values.
    """
    detail = f"retail: {tasks} tasks, policy {policy_bytes} B"
    if (tasks, policy_bytes) != (config.TAU2_RETAIL_TASKS, config.TAU2_RETAIL_POLICY_BYTES):
        return Check(
            "fail", "tau2 data", detail,
            f"expected {config.TAU2_RETAIL_TASKS} and {config.TAU2_RETAIL_POLICY_BYTES} B — "
            "a different specimen makes every number here about a different corpus",
        )
    return Check("pass", "tau2 data", detail)


def _tau2_data() -> Check:
    """Assert the specimen a run would actually load — P1.0.

    Reads τ²'s own constants rather than re-deriving the path — τ² resolves its data
    directory once at import and only warns, and the default fallback is broken under a venv
    install (DEF-051). The import is local so `doctor` can report that it failed.

    Returns:
        A pass only when both retail files are on disk AND match the measured pin.
    """
    try:
        from tau2.domains.retail.utils import RETAIL_POLICY_PATH, RETAIL_TASK_SET_PATH
    except ImportError as exc:
        return Check(
            "fail", "tau2 data", f"tau2 not importable — {exc}",
            "the specimen is pinned in pyproject's [tool.uv.sources]",
        )

    if missing := [p for p in (RETAIL_TASK_SET_PATH, RETAIL_POLICY_PATH) if not p.exists()]:
        return Check(
            "fail",
            "tau2 data",
            f"{len(missing)} of 2 files missing under {RETAIL_POLICY_PATH.parent}",
            "set TAU2_DATA_DIR to the checkout's data/ directory — τ² only warns",
        )

    return specimen_check(
        len(json.loads(RETAIL_TASK_SET_PATH.read_text())),
        RETAIL_POLICY_PATH.stat().st_size,
    )


def metric_check(disagreements: list[str]) -> Check:
    """Report whether our copied metrics still agree with upstream's — the logic half of D-099.

    `loop/score.py` copies the two metrics rather than importing them (D-099); this is what
    notices the copy drifting, and it costs nothing because `doctor` imports τ² anyway.
    Agreement is checked by behaviour — matching source text can hide changed arithmetic.

    Args:
        disagreements: One string per input where the two implementations differ.

    Returns:
        A pass only when every sampled input agrees.
    """
    if disagreements:
        return Check(
            "fail", "metrics", f"{len(disagreements)} disagreement(s): {disagreements[0]}",
            "loop/score.py copies upstream's metrics (D-099) — the copy has drifted from the pin",
        )
    return Check("pass", "metrics", "metrics and termination vocabulary agree with the pin")


def _metrics() -> Check:
    """Run our copies against τ²'s over a small exhaustive grid — D-099.

    Exhaustive over the shape, not a sample of it. Every `(trials, successes, k)` with
    `trials ≤ 5` is checked, which includes the `k < num_trials` rows where the plausible
    re-derivation ("passed every attempt") diverges — the corpus we develop against has 4
    trials on every task, so a spot check at `k == num_trials` would agree with a wrong copy.

    Returns:
        A pass only when every grid point and every tolerance point matches.
    """
    try:
        from tau2.data_model.simulation import TerminationReason
        from tau2.metrics.agent_metrics import is_successful as up_successful
        from tau2.metrics.agent_metrics import pass_hat_k as up_pass_hat_k
    except ImportError as exc:
        return Check(
            "fail", "metrics", f"tau2 not importable — {exc}",
            "the specimen is pinned in pyproject's [tool.uv.sources]",
        )

    from touchstone.loop.schema import TERMINATION_REASONS
    from touchstone.loop.score import is_successful, pass_hat_k

    bad: list[str] = []
    for trials in range(1, 6):
        for successes in range(trials + 1):
            for k in range(1, trials + 1):
                ours, theirs = pass_hat_k(trials, successes, k), up_pass_hat_k(trials, successes, k)
                if ours != theirs:
                    bad.append(f"pass_hat_k({trials},{successes},{k}) {ours} != {theirs}")
    # The tolerance is the whole content of `is_successful`, so the points that matter are the
    # ones just inside and just outside it — 1.0 alone would agree with a bare `== 1.0`.
    for reward in (0.0, 0.5, 0.9999, 1 - 1e-7, 1.0, 1 + 1e-7, 1.001):
        if is_successful(reward) != up_successful(reward):
            bad.append(f"is_successful({reward}) disagrees")

    # A misspelt reason passes mypy and every test; only upstream's enum catches it (D-100).
    mine, upstream = set(TERMINATION_REASONS), {r.value for r in TerminationReason}
    if mine != upstream:
        bad.append(f"termination reasons differ: ours-only {sorted(mine - upstream)}, "
                   f"upstream-only {sorted(upstream - mine)}")
    return metric_check(bad)
