"""The three cases `quota_exhausted` distinguishes, and the one it deliberately does not act on.

Then the ledger, which distinguishes nothing and is not allowed to (D-091 SS E).

Uses the SDK's own `RateLimitInfo` and `ResultMessage` rather than stand-ins: the fields that
decide these are optional upstream, and a hand-rolled double is exactly the thing that would
not know that. `usage` is `dict[str, Any]` there, so its values are not all counts.
"""

from __future__ import annotations

import pytest
from claude_agent_sdk import RateLimitInfo, ResultMessage

from touchstone import config
from touchstone.loop import budget


@pytest.fixture(autouse=True)
def _no_reading(monkeypatch: pytest.MonkeyPatch) -> None:
    """Both readings are module state, so each test starts from before the first call."""
    monkeypatch.setattr(budget, "_last", None)
    monkeypatch.setattr(budget, "_spent", {})


def see(monkeypatch: pytest.MonkeyPatch, **fields: object) -> None:
    monkeypatch.setattr(budget, "_last", RateLimitInfo(**fields))


def test_before_the_first_call_there_is_room() -> None:
    """Refusing to start on no reading would mean never starting."""
    assert budget.reading() is None
    assert not budget.quota_exhausted()


def test_below_the_reserve_there_is_room(monkeypatch: pytest.MonkeyPatch) -> None:
    see(monkeypatch, status="allowed", utilization=config.QUOTA_STOP_UTILIZATION - 0.01)
    assert not budget.quota_exhausted()


def test_at_the_reserve_there_is_not(monkeypatch: pytest.MonkeyPatch) -> None:
    """The boundary is inclusive -- the direction that stops rather than the one that spends."""
    see(monkeypatch, status="allowed", utilization=config.QUOTA_STOP_UTILIZATION)
    assert budget.quota_exhausted()


def test_rejected_is_final_whatever_the_number_says(monkeypatch: pytest.MonkeyPatch) -> None:
    """The vendor's own verdict outranks our reserve, including when the number disagrees."""
    see(monkeypatch, status="rejected", utilization=0.0)
    assert budget.quota_exhausted()


def test_a_warning_with_no_number_is_taken_at_its_word(monkeypatch: pytest.MonkeyPatch) -> None:
    """`utilization` is optional upstream. Absent, the status is the only reading there is."""
    see(monkeypatch, status="allowed_warning")
    assert budget.quota_exhausted()


def test_allowed_with_no_number_still_has_room(monkeypatch: pytest.MonkeyPatch) -> None:
    see(monkeypatch, status="allowed")
    assert not budget.quota_exhausted()


def test_a_warning_below_the_reserve_does_not_stop_the_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """Deliberate, and the reason the constant exists.

    The vendor never says at what fraction it warns, so where a number is available it is the
    number that decides.
    """
    see(monkeypatch, status="allowed_warning", utilization=0.10)
    assert not budget.quota_exhausted()


def test_observe_is_what_the_stream_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    """The events arrive on transitions only, so the reading has to survive between calls."""
    monkeypatch.setattr(budget, "_last", None)
    budget.observe(RateLimitInfo(status="rejected"))
    assert budget.quota_exhausted()
    assert budget.reading() is not None


def test_a_fresh_trace_has_attempts_left() -> None:
    assert not budget.attempts_exhausted(0)


def test_the_last_attempt_is_still_an_attempt() -> None:
    assert not budget.attempts_exhausted(config.MAX_ATTEMPTS - 1)


def test_the_cap_stops_the_loop() -> None:
    assert budget.attempts_exhausted(config.MAX_ATTEMPTS)


def test_overshooting_the_cap_still_stops() -> None:
    """`>=`, not `==`. A caller that counted wrong should be stopped, not waved through."""
    assert budget.attempts_exhausted(config.MAX_ATTEMPTS + 3)


def cost(**fields: object) -> ResultMessage:
    """A finished call, with the four required fields defaulted to something uninteresting."""
    return ResultMessage(
        **{
            "subtype": "success",
            "duration_ms": 0,
            "duration_api_ms": 0,
            "is_error": False,
            "num_turns": 1,
            "session_id": "s",
            **fields,
        }  # type: ignore[arg-type]
    )


def test_a_role_that_has_not_been_asked_is_absent_rather_than_zero() -> None:
    """An empty row and no row are different findings, the same way an empty harvest is."""
    budget.spent("critic", cost())
    assert "curator" not in budget.ledger()


def test_two_calls_by_one_role_are_one_row() -> None:
    budget.spent("critic", cost(duration_ms=100, total_cost_usd=0.5))
    budget.spent("critic", cost(duration_ms=200, total_cost_usd=0.25))
    row = budget.ledger()["critic"]
    assert (row["calls"], row["duration_ms"], row["usd"]) == (2, 300, 0.75)


def test_roles_are_not_pooled() -> None:
    budget.spent("router", cost())
    budget.spent("critic", cost())
    assert sorted(budget.ledger()) == ["critic", "router"]


def test_turns_is_the_maximum_and_not_the_total() -> None:
    """The number a cap is pinned to. A sum would say six calls of one turn had reached it."""
    for turns in (1, 6, 2):
        budget.spent("critic", cost(num_turns=turns))
    assert budget.ledger()["critic"]["turns"] == 6


def test_tokens_are_summed_under_whatever_key_the_sdk_reported() -> None:
    """Not a fixed list of names -- a renamed usage field would otherwise read as zero."""
    budget.spent("critic", cost(usage={"input_tokens": 10, "cache_read_input_tokens": 4}))
    budget.spent("critic", cost(usage={"input_tokens": 5, "output_tokens": 7}))
    assert budget.ledger()["critic"]["tokens"] == {
        "input_tokens": 15,
        "cache_read_input_tokens": 4,
        "output_tokens": 7,
    }


def test_a_usage_value_that_is_not_a_count_is_left_out() -> None:
    """`usage` is `dict[str, Any]` upstream, and summing a nested breakdown would raise."""
    budget.spent("critic", cost(usage={"input_tokens": 3, "server_tool_use": {"web": 1}}))
    assert budget.ledger()["critic"]["tokens"] == {"input_tokens": 3}


def test_a_call_with_no_cost_reported_still_counts_as_a_call() -> None:
    """`total_cost_usd` and `usage` are both optional upstream, and a missing price is not free."""
    budget.spent("router", cost(total_cost_usd=None, usage=None))
    assert budget.ledger()["router"]["calls"] == 1


def test_the_ledger_cannot_be_edited_through_what_it_returns() -> None:
    """A caller writing a header holds a copy, tokens included, or the header edits the run."""
    budget.spent("critic", cost(usage={"input_tokens": 10}))
    got = budget.ledger()
    got["critic"]["calls"] = 99
    got["critic"]["tokens"]["input_tokens"] = 99
    assert budget.ledger()["critic"] == {
        "calls": 1, "turns": 1, "duration_ms": 0, "usd": 0.0, "tokens": {"input_tokens": 10}
    }


def test_forget_starts_a_new_harvest_rather_than_adding_to_the_last() -> None:
    budget.spent("critic", cost())
    budget.forget()
    assert budget.ledger() == {}


def test_the_ledger_decides_nothing() -> None:
    """D-091 SS E: `quota_exhausted` still answers from `utilization` alone, spend or no spend."""
    budget.spent("critic", cost(total_cost_usd=10_000.0, num_turns=999))
    assert not budget.quota_exhausted()
