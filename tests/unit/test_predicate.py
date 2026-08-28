"""The predicate evaluator: what each shape fires on, and what it refuses to guess at."""

from __future__ import annotations

from typing import Any

import pytest

from touchstone.gate.predicate import (
    ArgumentIn,
    Predicate,
    RequiresPriorTool,
    RequiresUserAssent,
    evaluate,
)

AUTH = ("find_user_id_by_email",)


def call(name: str, cid: str = "1", requestor: str = "assistant", **arguments: Any) -> dict:
    """One assistant message carrying one tool call."""
    return {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {"id": cid, "name": name, "arguments": arguments, "requestor": requestor}
        ],
    }


def result(cid: str = "1", error: bool = False) -> dict:
    """The environment's answer to that call."""
    return {"role": "tool", "id": cid, "content": "ok", "error": error}


def said(text: str) -> dict:
    """One user turn."""
    return {"role": "user", "content": text, "tool_calls": None}


def prior(tool: str = "cancel_pending_order") -> Predicate:
    return Predicate("auth first", "retail/policy.md:10", RequiresPriorTool(tool, AUTH))


def assent(tool: str = "cancel_pending_order") -> Predicate:
    return Predicate("confirm first", "retail/policy.md:16",
                     RequiresUserAssent(tool, ("yes", "go ahead")))


def test_a_write_with_no_prior_lookup_fires() -> None:
    v = evaluate(prior(), [call("cancel_pending_order")])
    assert len(v) == 1
    assert v[0].rule == "retail/policy.md:10"


def test_a_write_after_a_successful_lookup_is_silent() -> None:
    messages = [call("find_user_id_by_email", "a"), result("a"), call("cancel_pending_order", "b")]
    assert evaluate(prior(), messages) == []


def test_a_lookup_that_errored_does_not_count_as_prior() -> None:
    # The distinction the check exists for: the call was made, the id was never located, and
    # a name-order scan of the transcript cannot tell those apart.
    messages = [
        call("find_user_id_by_email", "a"),
        result("a", error=True),
        call("cancel_pending_order", "b"),
    ]
    assert len(evaluate(prior(), messages)) == 1


def test_a_later_lookup_does_not_excuse_an_earlier_write() -> None:
    messages = [call("cancel_pending_order", "a"), call("find_user_id_by_email", "b"), result("b")]
    assert len(evaluate(prior(), messages)) == 1


def test_a_write_with_no_assent_in_the_message_before_it_fires() -> None:
    messages = [said("I want to cancel order W1"), call("cancel_pending_order")]
    assert len(evaluate(assent(), messages)) == 1


def test_a_write_after_agreement_is_silent() -> None:
    messages = [said("I want to cancel"), {"role": "assistant", "content": "Confirm?"},
                said("Yes, go ahead"), call("cancel_pending_order")]
    assert evaluate(assent(), messages) == []


def test_only_the_most_recent_user_turn_is_read() -> None:
    # A yes given to an earlier, different action is not assent to this one — the whole rule
    # is that confirmation is per-action, so a wider window would silently excuse the second.
    messages = [said("yes"), {"role": "assistant", "content": "done"},
                said("now change my address too"), call("cancel_pending_order")]
    assert len(evaluate(assent(), messages)) == 1


def test_an_argument_outside_the_allowed_set_fires_and_case_does_not_matter() -> None:
    check = ArgumentIn("cancel_pending_order", "reason", ("no longer needed",))
    p = Predicate("two reasons", "retail/policy.md:90", check)
    assert len(evaluate(p, [call("cancel_pending_order", reason="changed my mind")])) == 1
    assert evaluate(p, [call("cancel_pending_order", reason="No Longer Needed")]) == []


def test_an_absent_argument_is_not_a_violation() -> None:
    # A missing argument is the environment's error to raise, and guessing here would report
    # a policy breach for what is actually a malformed call.
    p = Predicate("two reasons", "retail/policy.md:90",
                  ArgumentIn("cancel_pending_order", "reason", ("no longer needed",)))
    assert evaluate(p, [call("cancel_pending_order")]) == []


def test_a_call_the_user_made_is_not_the_agents_to_answer_for() -> None:
    messages = [call("cancel_pending_order", requestor="user")]
    assert evaluate(prior(), messages) == []


@pytest.mark.parametrize(
    "messages",
    [
        [],
        [{"role": "assistant"}],
        [{"role": "assistant", "tool_calls": None}],
        [{"role": "user", "content": None}, call("cancel_pending_order")],
        [{"role": "tool"}, call("cancel_pending_order")],
    ],
)
def test_a_malformed_transcript_returns_no_opinion_rather_than_raising(messages: list) -> None:
    for p in (prior(), assent()):
        evaluate(p, messages)
