"""The closed set of shapes a mined rule may take, and the mechanical check of one.

Tier 1 (`tier1.py`) checks one proposed call in isolation. This checks a whole session, and
that difference is the point: D-105 measured tier 1 silent on the adopted corpus because the
retail tools already raise on everything a single call can get wrong. What they cannot see is
order -- an unauthenticated lookup, a write nobody confirmed -- and docs/02 measured 371
sessions that pass the DB check with a failed `action_check`, plus 56 with an unconfirmed
write. Those are trajectory failures, so a trajectory is what a predicate reads.

Two shapes, and no more until one is measured to be needed:

    RequiresPriorTool    a call must follow a SUCCESSFUL call to one of these
    ArgumentIn           an argument may only take one of these values

There were three. `RequiresUserAssent` was retired by D-109 after being measured rather than
argued: it was the only shape that matched TEXT rather than structure, and the only one that
was broken. `scripts/measure-assent-window.py` carries the numbers.

They are data, never code. The curator runs with `allowed_tools=[]` (docs/03 SS5) so it emits a
field rather than calling anything, and a field that arrives as Python source would put model
output on the execution path that D-064 exists to keep mechanical. The cost is expressiveness:
a rule these three cannot say is a rule this loop cannot mine, and `scripts/measure-predicate.py`
is where that shows up as a shape nothing fires on.

The write/read split is NOT a list here. `tau2.environment.toolkit.ToolKit.tool_mutates_state`
(`toolkit.py:202`) already carries it, and D-065 picked the same source for the enforcement
point -- a second copy is a second thing to get wrong when a domain changes.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from touchstone.gate.tier1 import Violation


@dataclass(frozen=True)
class RequiresPriorTool:
    """`tool` may only be called after one of `prior` has returned without an error.

    Retail's policy opens with authentication, and states it survives the user volunteering
    the id: "This has to be done even when the user already provides the user id."
    """

    tool: str
    prior: tuple[str, ...]


@dataclass(frozen=True)
class ArgumentIn:
    """`argument` of `tool` may only take a value in `allowed`.

    Case- and whitespace-insensitive: policy states the cancellation reasons as prose
    ("either 'no longer needed' or 'ordered by mistake'") and an agent that capitalises one
    has not broken the rule the policy wrote down.
    """

    tool: str
    argument: str
    allowed: tuple[str, ...]


Check = RequiresPriorTool | ArgumentIn


@dataclass(frozen=True)
class Predicate:
    """One check, plus where the rule it encodes is written down.

    `source` is not decoration. docs/02 SS5 allows a gate only against something stated, so a
    predicate that cannot name a line of policy is one the loop must refuse -- and refusing it
    needs the citation to be a field rather than a habit.
    """

    rule: str
    source: str
    check: Check


def _calls(messages: Sequence[Mapping[str, Any]]) -> list[tuple[int, Mapping[str, Any]]]:
    """Every assistant-issued tool call, with the index of the message carrying it."""
    return [
        (i, call)
        for i, m in enumerate(messages)
        for call in (m.get("tool_calls") or [])
        if call.get("requestor", "assistant") == "assistant"
    ]


def _succeeded(messages: Sequence[Mapping[str, Any]]) -> set[str]:
    """The ids of tool calls the environment answered without an error."""
    return {
        str(m.get("id"))
        for m in messages
        if m.get("role") == "tool" and not m.get("error")
    }


def evaluate(predicate: Predicate, messages: Sequence[Mapping[str, Any]]) -> list[Violation]:
    """Every place in this session where `predicate` is broken. Mechanical, no model.

    Empty is not approval -- it means this one rule was not broken, which is the answer for
    almost every session and almost every rule. The verdict a loop draws from silence comes
    from the control set in `scripts/measure-predicate.py`, never from one call to this.

    Calls the environment rejected are reported too. A refused call is still an attempt to
    break the rule, and the caller decides whether to count it -- the measurement splits on
    it, so this stays the honest superset rather than pre-judging.
    """
    check = predicate.check
    ok = _succeeded(messages) if isinstance(check, RequiresPriorTool) else set()
    out: list[Violation] = []

    for i, call in _calls(messages):
        if call.get("name") != check.tool:
            continue
        detail = _broken(check, messages, i, call, ok)
        if detail is not None:
            out.append(Violation(type(check).__name__, predicate.source, detail))
    return out


def _broken(
    check: Check,
    messages: Sequence[Mapping[str, Any]],
    i: int,
    call: Mapping[str, Any],
    ok: set[str],
) -> str | None:
    """The reason this call breaks `check`, or None if it does not."""
    if isinstance(check, RequiresPriorTool):
        earlier = {
            c.get("name")
            for j, c in _calls(messages)
            if j < i and str(c.get("id")) in ok
        }
        if earlier.isdisjoint(check.prior):
            return f"{check.tool} called with no successful {' or '.join(check.prior)} before it"
        return None

    value = (call.get("arguments") or {}).get(check.argument)
    if value is None:
        return None
    if str(value).strip().lower() not in {a.strip().lower() for a in check.allowed}:
        return f"{check.tool}.{check.argument} was {value!r}, not one of {check.allowed}"
    return None
