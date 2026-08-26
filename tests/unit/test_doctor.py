"""The one piece of `doctor` that is logic rather than I/O — and the one that had the bug.

`model_usage` can carry more than one model, and in isolation mode the CLI's housekeeping
call on haiku sorts first. Reading position instead of name reported a correctly pinned
model as a failed pin (D-035). These two cases are that bug, frozen.
"""

import pytest

from touchstone import config
from touchstone.doctor import _cerebras, metric_check, model_check, specimen_check, tracing_check

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


URI = "file:///tmp/mlruns"


def test_a_span_that_round_trips_passes() -> None:
    assert tracing_check("abc123", "abc123", URI).status == "pass"


def test_nothing_read_back_fails() -> None:
    # The failure that has no symptom: the run scores, the store stays empty. On
    # mlflow-skinny 3.15.1 the file store is refused unless MLFLOW_ALLOW_FILE_STORE is
    # set, and the export is async on top of that — two ways to write nothing quietly.
    check = tracing_check("abc123", None, URI)
    assert check.status == "fail"
    assert "MLFLOW_ALLOW_FILE_STORE" in check.note


def test_someone_elses_trace_is_not_ours() -> None:
    # `search_traces(max_results=1)` returns the newest trace, which is only ours because
    # we just wrote it. Comparing the marker is what turns that assumption into a check.
    check = tracing_check("abc123", "def456", URI)
    assert check.status == "fail"
    assert "abc123" in check.detail and "def456" in check.detail


def test_metric_check_names_the_first_disagreement_rather_than_a_count() -> None:
    """D-099 — the copy in `loop/score.py` is only safe while something reports it drifting."""
    check = metric_check(["pass_hat_k(2,1,1) 0.0 != 0.5"])
    assert check.status == "fail"
    assert "pass_hat_k(2,1,1)" in check.detail, "a bare count leaves nowhere to start"
    assert metric_check([]).status == "pass"
