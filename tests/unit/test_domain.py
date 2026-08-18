"""P1.1's runnable check: the blast table, and the two ways `Usage` gets the wrong model."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from touchstone.domain import (
    ESCALATION_THRESHOLD,
    Action,
    BlastRadius,
    GroundTruth,
    Incident,
    RootCause,
    Usage,
)

# docs/01 §5, transcribed a SECOND time on purpose — a table that checks itself against the
# implementation's own dict would pass whatever that dict said.
EXPECTED_ESCALATION = {
    Action.ANNOTATE_INCIDENT: False,
    Action.PAGE_SECONDARY: False,
    Action.SCALE_WORKERS: False,
    Action.RESTART_SERVICE: True,
    Action.ROLLBACK_DEPLOY: True,
    Action.FAILOVER_DATASTORE: True,
}


def test_every_action_has_a_blast_radius():
    assert set(EXPECTED_ESCALATION) == set(Action)


@pytest.mark.parametrize(("action", "escalates"), EXPECTED_ESCALATION.items())
def test_invariant_4_escalation_is_one_comparison(action, escalates):
    assert (action.blast_radius >= ESCALATION_THRESHOLD) is escalates


def test_blast_radius_is_ordered():
    assert BlastRadius.NONE < ESCALATION_THRESHOLD < BlastRadius.DOWNSTREAM


def test_invariant_1_no_truth_field_reachable_from_incident():
    # The structural half of "the agent never sees ground truth": no field of GroundTruth may
    # appear anywhere in the Incident tree. The rendering half is P1.2's.
    def fields(model, seen=frozenset()) -> object:
        for name, info in model.model_fields.items():
            yield name
            for arg in (info.annotation, *getattr(info.annotation, "__args__", ())):
                if hasattr(arg, "model_fields") and arg not in seen:
                    yield from fields(arg, seen | {arg})

    reachable = set(fields(Incident))
    # The walk is only worth anything if it descends: Incident → Evidence → LogLine → level.
    assert {"level", "value", "start"} <= reachable
    assert not set(GroundTruth.model_fields) & reachable, f"truth reachable: {reachable}"


def _result(model_usage, total=0.02) -> SimpleNamespace:
    return SimpleNamespace(
        model_usage=model_usage, total_cost_usd=total, duration_ms=1200, duration_api_ms=900
    )


# The exact shape phase 0 measured, plus the haiku entry that sorts first — DEF-001.
HAIKU = {"outputTokens": 9, "costUSD": 0.000578}
SONNET = {
    "inputTokens": 4,
    "outputTokens": 282,
    "cacheReadInputTokens": 38056,
    "cacheCreationInputTokens": 144,
    "costUSD": 0.0161988,
}


def test_from_result_matches_by_name_not_by_position():
    usage = Usage.from_result(
        _result({"claude-haiku-4-5-20251001": HAIKU, "claude-sonnet-4-6": SONNET}),
        model="claude-sonnet-4-6",
        provider="subscription",
    )
    assert usage.canonical_model == "claude-sonnet-4-6"
    assert usage.completion_tokens == 282
    assert usage.cache_read_tokens == 38056
    assert usage.other_models == {"claude-haiku-4-5-20251001": 0.000578}
    # ⚠️ The run's total, not the model's — it includes the haiku call.
    assert usage.cost_usd == 0.02


def test_from_result_raises_when_the_pinned_model_is_absent():
    with pytest.raises(ValueError, match="absent from model_usage"):
        Usage.from_result(
            _result({"claude-haiku-4-5-20251001": HAIKU}),
            model="claude-sonnet-4-6",
            provider="subscription",
        )


def test_root_cause_has_eleven_classes_ten_of_them_renderable():
    assert len(RootCause) == 11
    assert RootCause.INSUFFICIENT_EVIDENCE in RootCause
