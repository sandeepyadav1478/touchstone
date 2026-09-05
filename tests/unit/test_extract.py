"""The parse boundary: every way a model answer can be wrong, and the one way it can be right.

No SDK call anywhere in here. `parse` is pure by design so the half of `extract` that can be
tested for free is the half that decides whether an answer is usable at all.

One exception at the end, and it reads the source rather than running it: `ask` cannot be
called without a model, but the ORDER of what it does after the stream ends is a property of
the file, and that order is where the cost ledger is either kept or lost (D-091 SS E).
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from touchstone.gate import extract as extract_module
from touchstone.gate.extract import parse
from touchstone.gate.predicate import ArgumentIn, RequiresPriorTool, evaluate


def answer(**fields: object) -> str:
    base = {"rule": "a stated rule", "source": "policy.md:1"}
    return json.dumps({**base, **fields})


def test_a_prior_tool_answer_becomes_the_shape_it_names() -> None:
    got = parse(answer(kind="RequiresPriorTool", tool="cancel", prior=["find_user_id_by_email"]))
    assert got is not None
    assert got.check == RequiresPriorTool(tool="cancel", prior=("find_user_id_by_email",))
    assert got.source == "policy.md:1"


def test_an_argument_answer_becomes_the_shape_it_names() -> None:
    got = parse(answer(kind="ArgumentIn", tool="cancel", argument="reason", allowed=["a", "b"]))
    assert got is not None
    assert got.check == ArgumentIn(tool="cancel", argument="reason", allowed=("a", "b"))


def test_every_list_becomes_a_tuple() -> None:
    """The shapes are frozen dataclasses and a list field defeats that quietly."""
    got = parse(answer(kind="RequiresPriorTool", tool="t", prior=["a", "b"]))
    assert got is not None
    assert isinstance(got.check.prior, tuple)


def test_json_wrapped_in_prose_still_parses() -> None:
    """A model told to emit bare JSON sometimes narrates first. That is a slip, not a refusal."""
    body = answer(kind="RequiresPriorTool", tool="t", prior=["a"])
    got = parse(f"Here is the predicate:\n\n```json\n{body}\n```\n\nHope that helps.")
    assert got is not None
    assert got.check.tool == "t"


def test_declining_to_encode_is_an_answer_not_an_error() -> None:
    """A capability failure has no stated rule behind it, so there is nothing to translate."""
    assert parse('{"kind": null, "why": "the policy states no rule about this"}') is None


@pytest.mark.parametrize("kind", ["RequiresTwoTools", "RequiresUserAssent"])
def test_an_unknown_shape_is_refused_rather_than_accommodated(kind: str) -> None:
    """The set being closed is the guarantee. Waving a third shape through would lose it.

    `RequiresUserAssent` is here because a RETIRED name is the one a model is most likely to
    emit -- it was in the prompt, and D-109 took it out of the prompt and out of the code on
    the same day. Refusing an invented kind and silently accepting a dead one would read the
    same in every test above this line.
    """
    with pytest.raises(ValueError, match="the set is closed"):
        parse(answer(kind=kind, tool="t"))


def test_a_missing_field_names_the_field() -> None:
    with pytest.raises(ValueError, match="prior"):
        parse(answer(kind="RequiresPriorTool", tool="t"))


@pytest.mark.parametrize("blank", ["", "   "])
@pytest.mark.parametrize("field", ["rule", "source"])
def test_an_empty_citation_is_refused(field: str, blank: str) -> None:
    """D-106 makes `source` a field precisely so a predicate cannot arrive without one."""
    body = {"rule": "r", "source": "s", "kind": "RequiresPriorTool", "tool": "t", "prior": ["a"]}
    body[field] = blank
    with pytest.raises(ValueError, match=field):
        parse(json.dumps(body))


def test_an_answer_with_no_json_at_all_raises() -> None:
    with pytest.raises(ValueError, match="no JSON object"):
        parse("I could not work out what rule you mean.")


def test_a_json_array_is_not_an_answer() -> None:
    with pytest.raises((TypeError, ValueError)):
        parse('["RequiresPriorTool"]')


def test_extra_keys_are_ignored() -> None:
    """A model that adds its reasoning as a field has not answered wrongly."""
    got = parse(answer(kind="RequiresPriorTool", tool="t", prior=["a"], confidence="high"))
    assert got is not None


def test_a_parsed_answer_is_one_evaluate_can_run() -> None:
    """The point of the whole boundary: model text in, a working mechanical check out."""
    got = parse(answer(kind="RequiresPriorTool", tool="cancel", prior=["auth"]))
    assert got is not None
    messages = [
        {"role": "assistant", "tool_calls": [{"id": "1", "name": "cancel", "arguments": {}}]},
    ]
    assert len(evaluate(got, messages)) == 1


def test_the_seam_charges_a_failed_call_before_it_raises() -> None:
    """`ask` reaches the SDK, so its ORDER is what is checkable here without a model.

    The cost is filed between the stream ending and the error raise, and the direction is the
    whole point: a call that came back an error spent the five-hour window exactly as an
    answered one did, and those are the calls a turn cap set too low produces (config.py:54).
    A ledger that only counted the successes would understate the thing it exists to tune.

    The bare `raise` inside the stream's own `except` is deliberately not covered -- that path
    never received a `ResultMessage`, so there is nothing to charge.
    """
    tree = ast.parse(Path(extract_module.__file__).read_text())
    ask = next(
        n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef) and n.name == "ask"
    )
    charged = [
        n.lineno
        for n in ast.walk(ask)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "spent"
    ]
    raised = [
        n.lineno
        for n in ast.walk(ask)
        if isinstance(n, ast.Raise)
        and isinstance(n.exc, ast.Call)
        and getattr(n.exc.func, "id", "") == "RuntimeError"
    ]
    assert len(charged) == 1, f"one call to budget.spent, found {len(charged)}"
    assert len(raised) == 1, f"one RuntimeError raise, found {len(raised)}"
    assert charged[0] < raised[0], "a failed call must be charged before ask raises"
