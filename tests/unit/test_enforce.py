"""P3.1 — the gate on the call path.

Nothing here imports τ², for the reason `test_score.py` states: the import costs 1.71 s
against a two-second suite. The last test reads τ²'s source as TEXT instead, because
`enforce.py`'s docstring makes three claims about upstream code and an unguarded claim about
someone else's file is the one that rots without anybody noticing.
"""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
from typing import Any

import pytest

from touchstone.gate import enforce
from touchstone.gate.predicate import ArgumentIn, Predicate, RequiresPriorTool

AUTH = Predicate(
    rule="orders are read only after the user is identified",
    source="policy.md:3",
    check=RequiresPriorTool(tool="get_order_details", prior=("get_user_details",)),
)
REASON = Predicate(
    rule="a cancellation states one of two reasons",
    source="policy.md:20",
    check=ArgumentIn(
        tool="cancel_pending_order", argument="reason", allowed=("no longer needed",)
    ),
)


class Env:
    """The half of `tau2.environment.Environment` the gate touches, and nothing else.

    A stand-in rather than the real class because importing τ² is what this suite refuses to
    do. What makes the stand-in honest is the last test in this file, which checks the real
    method's signature against the one `arm` binds over it.
    """

    def __init__(self, raises: str | None = None) -> None:
        self.seen: list[tuple[str, str, dict[str, Any]]] = []
        self.raises = raises

    def make_tool_call(
        self, tool_name: str, requestor: str = "assistant", **kwargs: Any
    ) -> str:
        """Record the call, then behave like a domain tool that may or may not raise."""
        self.seen.append((tool_name, requestor, kwargs))
        if tool_name == self.raises:
            raise ValueError("the environment refused this itself")
        return "ok"


def test_a_call_breaking_an_admitted_rule_never_reaches_the_environment() -> None:
    env = Env()
    state = enforce.arm(env, [AUTH])

    with pytest.raises(ValueError, match=r"policy\.md:3"):
        env.make_tool_call("get_order_details", order_id="#1")

    assert env.seen == [], "the gate raised but the write happened anyway"
    assert len(state.refused) == 1
    assert state.refused[0].tool == "get_order_details"


def test_the_same_call_goes_through_once_its_prior_has_succeeded() -> None:
    env = Env()
    state = enforce.arm(env, [AUTH])

    env.make_tool_call("get_user_details", user_id="u1")
    assert env.make_tool_call("get_order_details", order_id="#1") == "ok"

    assert state.refused == []
    assert [name for name, _, _ in env.seen] == ["get_user_details", "get_order_details"]


def test_a_refused_call_cannot_serve_as_another_rule_s_prior() -> None:
    """The history is accepted calls only, and this is the reason it has to be.

    `get_user_details` is refused here by a second rule, so it never ran. If the gate recorded
    attempts rather than executions, that refusal would still satisfy `AUTH`'s prior and the
    order lookup would sail through on the strength of a call the environment never saw.
    """
    blocked = Predicate(
        rule="the user lookup is itself gated, for this test",
        source="policy.md:9",
        check=ArgumentIn(tool="get_user_details", argument="user_id", allowed=("u2",)),
    )
    env = Env()
    state = enforce.arm(env, [AUTH, blocked])

    with pytest.raises(ValueError, match=r"policy\.md:9"):
        env.make_tool_call("get_user_details", user_id="u1")
    with pytest.raises(ValueError, match=r"policy\.md:3"):
        env.make_tool_call("get_order_details", order_id="#1")

    assert env.seen == []
    assert len(state.refused) == 2


def test_a_call_the_environment_itself_rejected_is_not_a_prior_either() -> None:
    env = Env(raises="get_user_details")
    enforce.arm(env, [AUTH])

    with pytest.raises(ValueError, match="the environment refused this itself"):
        env.make_tool_call("get_user_details", user_id="u1")
    with pytest.raises(ValueError, match=r"policy\.md:3"):
        env.make_tool_call("get_order_details", order_id="#1")

    assert [name for name, _, _ in env.seen] == ["get_user_details"]


def test_a_user_tool_call_is_not_gated() -> None:
    """The user simulator is a population no rule was measured on.

    Every predicate is mined from assistant calls, so gating the user's tools would enforce a
    rule against evidence that does not exist.
    """
    env = Env()
    state = enforce.arm(env, [AUTH])

    assert env.make_tool_call("get_order_details", requestor="user", order_id="#1") == "ok"

    assert env.seen == [("get_order_details", "user", {"order_id": "#1"})]
    assert state.refused == []
    assert state.accepted == [], "a user call was recorded into the assistant's trajectory"


def test_tier_1_refuses_without_any_admitted_predicate() -> None:
    """The suite is empty for most of this project's life and the gate is not therefore off."""
    env = Env()
    state = enforce.arm(env)

    with pytest.raises(ValueError, match=r"policy\.md:132"):
        env.make_tool_call(
            "exchange_delivered_order_items",
            order_id="#1",
            item_ids=["111"],
            new_item_ids=["111"],
        )

    assert env.seen == []
    assert state.refused[0].violations[0].constraint == "self_swap"


def test_a_call_breaking_two_rules_reports_both() -> None:
    """One rule, reported, is a refusal somebody satisfies and gets refused again."""
    unauthenticated = Predicate(
        rule="a cancellation follows the user being identified",
        source="policy.md:3",
        check=RequiresPriorTool(
            tool="cancel_pending_order", prior=("get_user_details",)
        ),
    )
    env = Env()
    state = enforce.arm(env, [REASON, unauthenticated])

    with pytest.raises(ValueError, match=r"refused by touchstone") as raised:
        env.make_tool_call("cancel_pending_order", order_id="#1", reason="changed my mind")

    assert len(state.refused[0].violations) == 2
    assert "policy.md:20" in str(raised.value)
    assert "policy.md:3" in str(raised.value)
    assert "changed my mind" in str(raised.value)


def test_arming_an_armed_environment_raises_rather_than_nesting() -> None:
    env = Env()
    enforce.arm(env, [AUTH])

    with pytest.raises(RuntimeError, match="already armed"):
        enforce.arm(env, [AUTH])


def test_arming_one_environment_leaves_another_alone() -> None:
    """The evaluator's gold environment is a different object, and this is what that buys."""
    gated, gold = Env(), Env()
    enforce.arm(gated, [AUTH])

    assert gold.make_tool_call("get_order_details", order_id="#1") == "ok"
    with pytest.raises(ValueError, match=r"policy\.md:3"):
        gated.make_tool_call("get_order_details", order_id="#1")


def _tau2() -> Path:
    """τ²'s package directory, without importing it. Same resolution as `check-diagram.py`."""
    declared = Path("/home/sandeep/synergies/tau2-bench/src/tau2")
    if declared.exists():
        return declared
    spec = importlib.util.find_spec("tau2")
    if spec is None or spec.origin is None:
        pytest.skip("no tau2 checkout and no installed package")
    return Path(spec.origin).parent


def test_the_upstream_shape_enforce_py_describes_is_still_the_upstream_shape() -> None:
    """Three claims `enforce.py` makes about τ², checked against τ²'s source.

    They are the reasons the gate is armed per instance rather than on the class, so if any of
    them stops being true the design's justification has gone and the docstring is fiction.
    Read as text at the pinned commit; nothing here imports τ².
    """
    environment = ast.parse((_tau2() / "environment" / "environment.py").read_text())
    functions = {
        node.name: node
        for node in ast.walk(environment)
        if isinstance(node, ast.FunctionDef)
    }

    # 1. `gated` has to be substitutable for the method it is bound over.
    args = functions["make_tool_call"].args
    assert [a.arg for a in args.args] == ["self", "tool_name", "requestor"]
    assert args.kwarg is not None
    assert args.kwarg.arg == "kwargs"

    # 2. An instance attribute only intercepts anything if the caller goes through `self`.
    calls = {
        ast.unparse(node.func)
        for node in ast.walk(functions["get_response"])
        if isinstance(node, ast.Call)
    }
    assert "self.make_tool_call" in calls

    # 3. The evaluator replays gold actions through the same method and swallows the error,
    #    which is why a class-level gate would corrupt a score in silence rather than fail.
    evaluator = (_tau2() / "evaluator" / "evaluator_env.py").read_text()
    assert evaluator.count("gold_environment.make_tool_call(") == 2
    guarded = [
        node
        for node in ast.walk(ast.parse(evaluator))
        if isinstance(node, ast.Try)
        and any("make_tool_call" in ast.unparse(stmt) for stmt in node.body)
    ]
    assert len(guarded) == 2, "the gold-action calls are no longer inside a try"
    for node in guarded:
        caught = [stmt for handler in node.handlers for stmt in handler.body]
        handlers = ast.unparse(ast.Module(body=caught, type_ignores=[]))
        assert "raise" not in handlers, "the evaluator now re-raises — reread enforce.py"


def test_the_simulation_builds_its_environment_where_the_gate_attaches() -> None:
    """The fourth claim: `build_environment` is the orchestrator's constructor and only that.

    `loop.run.install_gate` rebinds it, so this is what makes the arming per-instance in
    practice rather than only in principle. Two halves, and the second is the load-bearing one:
    the evaluator builds its gold environment from the registry directly, so it never comes
    through here. The day it does, this run gates the gold actions and the reward is wrong in
    silence — the failure `enforce.py`'s header is entirely about.
    """
    tree = ast.parse((_tau2() / "runner" / "build.py").read_text())
    callers = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        for call in ast.walk(node)
        if isinstance(call, ast.Call) and getattr(call.func, "id", "") == "build_environment"
    }
    assert callers == {"build_text_orchestrator", "build_voice_orchestrator"}

    # Every file that CALLS it, not every file that names it: `run.py` and `runner/__init__.py`
    # re-export the name and neither invokes it, so a check on the bare name would fail on
    # upstream's own public surface.
    calling = sorted(
        path.relative_to(_tau2()).as_posix()
        for path in _tau2().rglob("*.py")
        if "build_environment(" in path.read_text()
    )
    assert calling == ["runner/build.py"], f"{calling} also builds through the gated constructor"
