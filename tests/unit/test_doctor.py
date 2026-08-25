"""The one piece of `doctor` that is logic rather than I/O — and the one that had the bug.

`model_usage` can carry more than one model, and in isolation mode the CLI's housekeeping
call on haiku sorts *first*. Reading position instead of name reported a correctly pinned
model as a failed pin (D-035). These two cases are that bug, frozen.
"""

import pytest

from touchstone import config
from touchstone.doctor import _cerebras, model_check, specimen_check

HOUSEKEEPING = "claude-haiku-4-5-20251001"


def test_pinned_model_is_found_even_when_it_is_not_first() -> None:
    usage = {HOUSEKEEPING: {"outputTokens": 11}, config.MODEL: {"outputTokens": 4}}
    check = model_check(usage, 0.0036)
    assert check.status == "pass"
    assert HOUSEKEEPING in check.note  # reported, not hidden — it is real spend


def test_only_the_pinned_model_needs_no_note() -> None:
    check = model_check({config.MODEL: {"outputTokens": 4}}, 0.0030)
    assert check.status == "pass"
    assert check.note == ""


def test_a_pin_that_did_not_take_fails() -> None:
    check = model_check({HOUSEKEEPING: {"outputTokens": 11}}, 0.0006)
    assert check.status == "fail"


def test_no_model_at_all_fails() -> None:
    assert model_check({}, 0.0).status == "fail"


def test_absent_cerebras_key_is_a_pass_not_a_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    # D-067: Anthropic only. Absent is the correct state; it warned here until 2026-08-20.
    monkeypatch.delenv("CEREBRAS_API_KEY", raising=False)
    assert _cerebras().status == "pass"


def test_a_set_cerebras_key_warns(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CEREBRAS_API_KEY", "sk-whatever")
    assert _cerebras().status == "warn"


def test_the_measured_specimen_passes() -> None:
    # P1.0's two numbers, measured against tau2 at a2c024725189.
    check = specimen_check(config.TAU2_RETAIL_TASKS, config.TAU2_RETAIL_POLICY_BYTES)
    assert check.status == "pass"


def test_a_different_task_count_fails() -> None:
    # The whole point: reachable is not the same as right. A tree that resolves and
    # holds a different corpus makes every downstream number about something else.
    check = specimen_check(113, config.TAU2_RETAIL_POLICY_BYTES)
    assert check.status == "fail"
    assert "113" in check.detail  # what was found, not just that it was wrong


def test_an_edited_policy_fails() -> None:
    assert specimen_check(config.TAU2_RETAIL_TASKS, 6698).status == "fail"
