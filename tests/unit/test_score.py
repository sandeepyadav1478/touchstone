"""P1.5 — the scorer, checked against arithmetic rather than against itself.

Nothing here imports τ². `from tau2.metrics.agent_metrics import pass_hat_k` costs
1.563 s measured, against a 2-second gate for the whole suite. The two copied functions are
checked here against hand-computed combinatorics; that they still match upstream is
`doctor`'s job, which already pays the import once.

The corpus this was developed against has binary rewards, so `reward_mean` and `pass_hat_1`
came out equal to sixteen digits. That is an identity of that data — every reward 0.0 or 1.0,
every task at 4 trials — not of the metrics, and a test that only ever saw that corpus would not
notice the two being swapped. The fixtures below are therefore fractional and ragged on purpose.
"""

from __future__ import annotations

import math
from typing import Any

import pytest

from touchstone.loop.schema import TERMINATION_REASONS
from touchstone.loop.score import db_component, is_successful, pass_hat_k, score


def sim(
    task_id: str,
    reward: float,
    *,
    db: float | None = 1.0,
    nl: float | None = None,
    termination: str = "user_stop",
    info: bool = True,
) -> dict[str, Any]:
    """One simulation record, shaped like τ²'s but carrying only the fields scoring reads."""
    breakdown = {"DB": db} if db is not None else {}
    if nl is not None:
        breakdown["NL_ASSERTION"] = nl
    return {
        "task_id": task_id,
        "termination_reason": termination,
        "reward_info": {"reward": reward, "reward_breakdown": breakdown} if info else None,
    }


def test_pass_hat_k_is_a_hypergeometric_draw_not_an_all_passed_fraction() -> None:
    # 2 of 4 passed. "Passed every attempt" would be 0-or-1; the metric is a probability.
    assert pass_hat_k(4, 2, 1) == 0.5
    assert pass_hat_k(4, 2, 2) == math.comb(2, 2) / math.comb(4, 2) == pytest.approx(1 / 6)
    assert pass_hat_k(4, 2, 3) == 0.0  # cannot draw 3 winners from 2
    # At k == num_trials the two definitions coincide — which is why testing only k=n hides the
    # difference, and why the k=2 row above is the one that matters.
    assert pass_hat_k(4, 4, 4) == 1.0


def test_pass_hat_k_refuses_a_k_it_cannot_draw() -> None:
    # Upstream raises rather than clamping, and we keep that: a silently clamped k reports a
    # different, easier metric under the same column name.
    with pytest.raises(ValueError, match="less than k"):
        pass_hat_k(2, 1, 3)


def test_success_uses_upstreams_tolerance() -> None:
    assert is_successful(1.0)
    assert is_successful(1.0 - 1e-7)
    assert is_successful(1.0 + 1e-7)
    assert not is_successful(0.9999)
    assert not is_successful(0.0)


def test_infrastructure_errors_count_as_failed_trials_and_say_so() -> None:
    """The convention is the finding. τ²'s own `get_metrics_df` filters these out."""
    sims = [sim("1", 1.0), sim("1", 0.0, termination="infrastructure_error", info=False)]
    agg = score(sims, k=1)["aggregate"]
    assert agg["trials"] == 2, "a filtered infra error would leave 1 — that is the other convention"
    assert agg["pass_hat_1"] == 0.5
    assert agg["infra_errors"] == 1
    assert agg["infra_error_convention"] == "counted_as_failed"


def test_a_missing_breakdown_is_not_a_failed_db_check() -> None:
    """`None` is not 0.0. The evaluator not running is not the agent corrupting the database."""
    crashed = sim("1", 0.0, termination="infrastructure_error", info=False)
    assert db_component(crashed) is None
    case = score([sim("1", 1.0), crashed], k=1)["cases"][0]
    assert case["trials"] == 2, "it still counts as a trial"
    assert (case["db_passed"], case["db_scored"]) == (1, 1), "but not as a DB denominator"


def test_all_ten_termination_reasons_are_present_at_zero() -> None:
    agg = score([sim("1", 1.0)], k=1)["aggregate"]
    assert list(agg["termination_reasons"]) == list(TERMINATION_REASONS)
    assert len(TERMINATION_REASONS) == 10
    assert agg["termination_reasons"]["timeout"] == 0, "absent ≠ never fired"


def test_reward_mean_is_not_the_success_rate() -> None:
    """The composite is published unmodified (invariant 16) — fractional rewards stay fractional."""
    agg = score([sim("1", 0.5), sim("1", 1.0)], k=1)["aggregate"]
    assert agg["reward_mean"] == 0.75
    assert agg["pass_hat_1"] == 0.5, "0.5 is not a pass, however close the mean looks"


def test_only_a_failed_run_attributes_a_zeroed_component() -> None:
    sims = [
        sim("1", 0.0, db=0.0, nl=1.0),  # DB killed it
        sim("2", 0.0, db=1.0, nl=0.0),  # the judge killed it
        sim("3", 1.0, db=1.0, nl=1.0),  # nothing killed it
    ]
    assert score(sims, k=1)["aggregate"]["reward_breakdown_zeroed"] == {"DB": 1, "NL_ASSERTION": 1}


def test_undersampled_tasks_are_named_rather_than_scored_at_a_softer_k() -> None:
    sims = [sim("1", 1.0), sim("1", 1.0), sim("2", 1.0)]
    agg = score(sims, k=2)["aggregate"]
    assert agg["undersampled_tasks"] == ["2"]
    assert agg["pass_hat_k"] == 1.0, "task 2 is excluded, not averaged in at k=1"
    assert agg["tasks"] == 2, "it is still a task, and the denominator still says so"


def test_cases_are_ordered_the_way_the_manifest_froze_them() -> None:
    sims = [sim(i, 1.0) for i in ("100", "9", "12", "5")]
    assert [c["id"] for c in score(sims, k=1)["cases"]] == ["5", "9", "12", "100"]
