"""P3.1 -- enforcement: refuse a tool call before the write happens.

D-065's second mode. Shadow judges a finished session and never acts; this sits on the call
path and raises, so the write does not happen. The gate is the same one either way -- tier 1
(`tier1.check`) on the proposed call, and the admitted suite (`predicate.evaluate`) on the
trajectory it would extend -- because D-065's `wrong if` is that shadow and enforce diverge,
and two implementations of one check is the way to guarantee they do.

    ARMED PER ENVIRONMENT INSTANCE, NEVER ON THE CLASS. This is the design, not a detail.

`Environment.make_tool_call` is the single path every tool execution passes through, which is
what makes it the chokepoint and also what makes patching the CLASS wrong: the evaluator
replays the task's gold actions through the very same method on its own environment
(`evaluator_env.py:107` and `:314`) to build the reference state a run is scored against. A
class-level gate would refuse a gold action -- and both call sites wrap it in
`except Exception: logger.warning(...)`, so the refusal would not raise, would not fail, and
would not appear in the results. It would produce a wrong reference DB and a wrong reward with
nothing anywhere saying so. `get_response` is no safer: `set_state` replays message history
through it (`environment.py:390`) for the same gold environment.

So the scope is one object: `arm(environment)` binds an instance attribute, `self.make_tool_call`
finds it, and the evaluator's environment is a different object that was never armed. The
separation is by construction rather than by a flag somebody has to remember to set.

Three more things that are decisions rather than mechanics:

    requestor   only `assistant` is gated. Every predicate is mined from assistant calls --
                `predicate._calls` filters on exactly that -- so gating the user simulator's
                tools would enforce a rule against a population no rule was measured on.
    refusal     a raise, because `get_response` (`environment.py:475`) already turns an
                exception into `ToolMessage(error=True)`. The agent is told why and may retry,
                and the refusal lands in the transcript rather than in a side channel.
    history     accepted calls only. A refused call did not execute, so counting it would let
                a rejected attempt satisfy the `prior` half of another rule.

NO MODEL, at any point. The predicates arrive already extracted and already admitted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from touchstone.gate import tier1
from touchstone.gate.predicate import evaluate

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from touchstone.gate.predicate import Predicate
    from touchstone.gate.tier1 import Violation

__all__ = ["Armed", "Refusal", "arm", "refuses"]


@dataclass(frozen=True)
class Refusal:
    """One call the gate stopped, and every rule that stopped it.

    The whole list rather than the first: a call can break two rules, and a refusal reported as
    one of them is a refusal somebody fixes halfway.
    """

    tool: str
    arguments: Mapping[str, Any]
    violations: tuple[Violation, ...]


@dataclass
class Armed:
    """The gate's state for one environment: what it let through, and what it did not.

    Mutable and held by the closure `arm` installs, so a caller can read the outcome of a run
    without the gate having to write a file or the orchestrator having to hand anything back.
    """

    predicates: tuple[Predicate, ...]
    accepted: list[tuple[str, Mapping[str, Any]]] = field(default_factory=list)
    refused: list[Refusal] = field(default_factory=list)


def _trace(
    accepted: Sequence[tuple[str, Mapping[str, Any]]],
    tool: str,
    arguments: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """The accepted calls plus the proposed one, in the message shape `evaluate` reads.

    Synthesised rather than taken from the orchestrator, which holds the real trajectory: the
    gate is armed on an environment and an environment has no trajectory, and reaching up to
    the orchestrator for one would couple the gate to a class it does not otherwise touch.
    What `evaluate` actually reads is narrow -- names, arguments, ids, and which results
    errored -- and all four are here.

    Ids are the accepted call's index, which has to be unique: `_succeeded` keys on the id, so
    two calls sharing one would let a successful call vouch for a failed one.
    """
    messages: list[dict[str, Any]] = []
    for i, (name, args) in enumerate(accepted):
        call = {"id": str(i), "name": name, "arguments": dict(args), "requestor": "assistant"}
        messages.append({"tool_calls": [call]})
        messages.append({"role": "tool", "id": str(i), "error": False})
    proposed = {
        "id": "proposed",
        "name": tool,
        "arguments": dict(arguments),
        "requestor": "assistant",
    }
    messages.append({"tool_calls": [proposed]})
    return messages


def refuses(
    tool: str,
    arguments: Mapping[str, Any],
    accepted: Sequence[tuple[str, Mapping[str, Any]]],
    predicates: Sequence[Predicate],
) -> list[Violation]:
    """Every rule this call would break. Empty means let it through. Pure, so it is testable.

    `evaluate` judges a whole session and this wants one call, and the difference costs
    nothing because the history is violation-free by induction: every call in `accepted`
    cleared this same gate before it was appended, and neither shape can be broken later by
    something appended after it. `RequiresPriorTool` reads only the prefix before its call and
    `ArgumentIn` reads only the call. So anything `evaluate` returns here is about the
    proposed call, and filtering by position would be filtering on an invariant.

    Tier 1 runs first and, on the adopted corpus, never fires: D-105 measured it silent, and
    the nine firings on the wider set are all on calls the environment itself rejected. It is
    kept because that is a fact about retail's tools, not about the check -- a specimen whose
    tools validate less brings it back, and a gate deleted for being quiet is a gate nobody
    notices is missing.
    """
    out = list(tier1.check(tool, arguments))
    trace = _trace(accepted, tool, arguments)
    for predicate in predicates:
        out.extend(evaluate(predicate, trace))
    return out


def _why(violations: Sequence[Violation]) -> str:
    """The refusal as the agent reads it: what was broken, and where it is written down.

    The citation goes in on purpose. An agent told only that a call was refused can do nothing
    but retry it; one told which line of the policy refused it can satisfy the rule instead,
    and that difference is what separates a gate from a rate limit.
    """
    return "refused by touchstone: " + "; ".join(
        f"{v.detail} ({v.rule})" for v in violations
    )


def arm(environment: Any, predicates: Sequence[Predicate] = ()) -> Armed:
    """Put the gate in front of one environment's tool calls. Returns the state it fills in.

    Refuses to arm an already-armed environment rather than nesting. A second wrapper would
    run the gate twice, count every refusal twice and record every accepted call twice, and
    the trajectory being wrong is worse than the double-count: a duplicated prior satisfies
    nothing extra, but a duplicated argument list is a second chance to match.
    """
    if getattr(environment.make_tool_call, "_touchstone", False):
        raise RuntimeError("this environment is already armed")

    upstream = environment.make_tool_call
    state = Armed(tuple(predicates))

    def gated(tool_name: str, requestor: str = "assistant", **kwargs: Any) -> Any:
        if requestor != "assistant":
            return upstream(tool_name, requestor=requestor, **kwargs)
        broken = refuses(tool_name, kwargs, state.accepted, state.predicates)
        if broken:
            state.refused.append(Refusal(tool_name, dict(kwargs), tuple(broken)))
            raise ValueError(_why(broken))
        result = upstream(tool_name, requestor=requestor, **kwargs)
        state.accepted.append((tool_name, dict(kwargs)))
        return result

    gated._touchstone = True  # type: ignore[attr-defined]
    environment.make_tool_call = gated
    return state
