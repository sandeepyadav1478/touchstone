"""The `policy.md:20` reading D-108 leans on, checked without touching the corpus.

`measure-control-set.py` self-checks its other two signals: it prints them beside docs/02's
recorded 407 and 371 and says REPRODUCED or CONFLICT, so a break there is loud. The policy rule
has no such anchor -- 627 of 934 is a number with nothing to disagree with -- and it is the one
D-108 §D rests on, so it is checked here instead.

No τ² import. The script defers `measure-tier1` and `measure-predicate` into `census()` for
exactly this reason; importing the file is free and the specimen's 1.71 s never gets paid.
"""

import importlib.util

from touchstone.config import ROOT

_spec = importlib.util.spec_from_file_location(
    "measure_control_set", ROOT / "scripts" / "measure-control-set.py"
)
# Two asserts, not one composite, so a renamed script says which half is missing (D-100).
assert _spec is not None, "scripts/measure-control-set.py is not where this test expects it"
assert _spec.loader is not None, "scripts/measure-control-set.py resolved without a loader"
control = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(control)

breaks = control.breaks_one_call_at_a_time


def call(name: str = "get_order_details") -> dict[str, str]:
    """One assistant tool call, in the shape `predicate.py` already reads them in."""
    return {"name": name, "requestor": "assistant"}


def test_a_bare_tool_call_breaks_nothing() -> None:
    """The compliant shape: one call, no prose beside it."""
    assert breaks([{"role": "assistant", "content": "", "tool_calls": [call()]}]) == (False, False)


def test_narrating_beside_a_call_is_the_first_half() -> None:
    """policy.md:20's second sentence, and the half that fires on 353 of the clean 934."""
    msg = {"role": "assistant", "content": "Let me look that up.", "tool_calls": [call()]}
    assert breaks([msg]) == (True, False)


def test_two_calls_in_one_message_is_the_second_half() -> None:
    """policy.md:20's first sentence, and the half that fires on the other 353.

    The corpus does this with the SAME tool twice, so the check counts calls, not distinct names.
    """
    msg = {"role": "assistant", "content": "", "tool_calls": [call(), call()]}
    assert breaks([msg]) == (False, True)


def test_prose_with_no_call_is_not_a_violation() -> None:
    """The agent is allowed to talk. Only talking WHILE calling is the stated failure."""
    assert breaks([{"role": "assistant", "content": "Anything else?"}]) == (False, False)


def test_whitespace_is_not_prose() -> None:
    """A blank `content` beside a call is how the corpus writes a clean call, not a violation.

    Without the strip this returns True on most of the corpus and the 353 becomes meaningless.
    """
    assert breaks([{"role": "assistant", "content": "  \n ", "tool_calls": [call()]}]) == (
        False,
        False,
    )


def test_the_user_may_do_both_freely() -> None:
    """The rule is addressed to the agent. Only assistant messages are read."""
    msgs = [{"role": "user", "content": "yes please", "tool_calls": [call(), call()]}]
    assert breaks(msgs) == (False, False)


def test_a_session_is_flagged_by_any_message_in_it() -> None:
    """The signal is per-session, not per-message -- that is what makes 627 a count of sessions."""
    msgs = [
        {"role": "assistant", "content": "", "tool_calls": [call()]},
        {"role": "user", "content": "ok"},
        {"role": "assistant", "content": "Cancelling now.", "tool_calls": [call()]},
    ]
    assert breaks(msgs) == (True, False)
