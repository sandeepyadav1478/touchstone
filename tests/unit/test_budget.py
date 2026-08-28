"""The three cases `quota_exhausted` distinguishes, and the one it deliberately does not act on.

Uses the SDK's own `RateLimitInfo` rather than a stand-in: the field that decides this is
optional upstream, and a hand-rolled double is exactly the thing that would not know that.
"""

from __future__ import annotations

import pytest
from claude_agent_sdk import RateLimitInfo

from touchstone import config
from touchstone.loop import budget


@pytest.fixture(autouse=True)
def _no_reading(monkeypatch: pytest.MonkeyPatch) -> None:
    """The reading is module state, so each test starts from before the first call."""
    monkeypatch.setattr(budget, "_last", None)


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
