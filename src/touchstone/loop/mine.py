"""P3.4 -- the inner loop, and the only stage in this project that runs more than once.

Everything else measures: one candidate, one pass, one verdict. This takes ONE session the
router marked ENHANCE and works it repeatedly, up to `config.MAX_ATTEMPTS`, until it has a
predicate that fires on that session and is silent on every clean one. The outer loop asks
whether a version is better; this makes the thing that answers.

Nothing here holds a model. The three agents arrive as callables, which is not an abstraction
kept for later -- D-090 and D-091 both name the same check as the one to write with this file,
and it needs a critic that always bounces and never calls a tool:

    a stub critic terminates in exactly MAX_ATTEMPTS attempts

The exits are D-093's and D-094's, and which one fired is the number that matters. A cap that
ran out and a critic that gave up at attempt 2 produce the same artefact otherwise, and
D-089's whole mitigation is that the give-up rate can be watched.

    handed_over        a candidate reached the gauntlet -- the critic said so AND the check
                       agreed. Both, because the critic is a model and D-064 keeps the verdict
                       mechanical; a hand-over it cannot support is counted in `waved_through`
                       and costs an attempt like any other bounce. The candidate itself is on
                       the record, because admission cannot recover it: a critic may run a
                       predicate that holds, bounce it anyway and hand over a different one a
                       lap later, leaving two holding attempts and nothing saying which of
                       them the hand-over was about
    budget_exhausted   the edge fired at the cap -- the honest failure
    gave_up            the critic gave up early and the tool accepted it
    force_terminated   an agent was told to exit and continued. Expected value: 0, and a
                       count above it is a bug report against a prompt, never a category
    skipped            the router never entered the loop. Not in D-094's table, because a
                       trace that did not enter cannot have left by one of its four doors
    misrouted          the router said ENHANCE about a session the answer key scores clean.
                       Also outside D-094: no attempt is spent, because the target is itself
                       in the set `run_predicate` scans, so every candidate is its own
                       counterexample and no verdict is reachable (DEF-079). A router error,
                       counted as one rather than as a curator that ran out of attempts

The cap is read by `budget.attempts_exhausted()` and by nothing here -- the edge and the
critic's tool call the one function, so no second place knows the number (D-091 C).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Literal, TypedDict

from touchstone.gate.predicate import Predicate, evaluate
from touchstone.loop import corpus
from touchstone.loop.budget import attempts_exhausted

__all__ = [
    "Attempt",
    "Record",
    "Ruling",
    "attempt_budget",
    "build",
    "held",
    "mine",
    "run_predicate",
    "spend",
]

ExitReason = Literal[
    "handed_over", "budget_exhausted", "gave_up", "force_terminated", "skipped", "misrouted"
]

CONTINUE, EXIT, REFUSED, RECORDED = "continue", "exit", "refused", "recorded"


@dataclass(frozen=True)
class Attempt:
    """One candidate and what the mechanical check returned for it.

    Both halves are kept, not just the verdict: an attempt that missed the target teaches the
    curator something different from one that fired on a clean session, and the counterexample
    is the payload the next attempt is handed.
    """

    predicate: Predicate
    fired_on_target: bool
    counterexample: str | None

    @property
    def holds(self) -> bool:
        """docs/02 section 5's stopping rule: fires on the failure, silent on what passes."""
        return self.fired_on_target and self.counterexample is None


@dataclass(frozen=True)
class Ruling:
    """What the critic returns: where the lap goes, and what the curator is told.

    Two fields because D-082 C2 has two hand-backs and only one of them is the counterexample.
    The other is the critic's own objection, and it has to reach the curator or the bounce
    costs an attempt and teaches nothing -- D-086 C's "never this seems weak" is a rule about
    a payload that has to exist to be judged.

    `argument` is None on a hand-over. The counterexample is not here: it is already in
    `Record.attempts`, written by the tool that produced it, and copying it into the model's
    return value would make the graph read a model's account of a mechanical result.
    """

    decision: str
    argument: str | None = None


@dataclass
class Record:
    """Everything one trace produced. Written by the tools and the edge, read by the caller.

    Mutable and passed by reference through the graph state on purpose. The tools run in this
    process, so what lands here is the recorded call rather than a model's account of one --
    which is the line D-085 B drew and the reason `attempt_budget` is a tool at all.
    """

    session_id: str
    attempts: list[Attempt] = field(default_factory=list)
    dispatches: int = 0
    told_to_exit: bool = False
    gave_up: bool = False
    waved_through: int = 0
    rule_searched_for: str | None = None
    exit_reason: ExitReason | None = None
    handed_over: Predicate | None = None


def run_predicate(predicate: Predicate, session: corpus.Session) -> Attempt:
    """The critic's evidence, and the one mechanical step left inside the loop (D-086 A).

    Silence is checked against the 934 rather than sampled, and it short-circuits on the first
    clean session that fires because that session IS the counterexample -- a second one would
    be a longer answer to a question already answered.

    The target is not in the set being scanned, but that is the graph's doing and not this
    function's: `selected` leaves by `misrouted` before any curator call when the router marks
    a clean session ENHANCE (DEF-079). Called directly with one, a predicate that fires on the
    target returns the target as its own counterexample.

    Ceiling, and it is docs/02's: silent on the corpus is a claim about the sessions that were
    run, never about the domain. The slower control that was supposed to catch the difference
    was deleted with `open` to `locked`, so a cleared predicate rests on this and nothing else.
    """
    return Attempt(
        predicate=predicate,
        fired_on_target=bool(evaluate(predicate, session.messages)),
        counterexample=next(
            (s.id for s in corpus.clean() if evaluate(predicate, s.messages)), None
        ),
    )


def held(record: Record, candidate: Predicate | None) -> bool:
    """Did the MECHANICAL check pass this candidate? The other half of a hand-over.

    The critic's `decision` is a model's word and D-064 keeps the verdict mechanical, so the
    word alone cannot be what ends the loop. `run_predicate` already computed the answer and
    the critic was even sent it; this is the graph reading the recorded result instead of the
    account of it, which is the same line D-085 SS B drew for the tools.

    Matched on the CANDIDATE and not on the last attempt, and that is the whole subtlety: a
    critic is free to call no tool this lap, and `attempts[-1]` would then be the PREVIOUS
    candidate's result. One that held would wave the current one through on evidence about a
    different predicate. Searching by equality also covers the ordinary case where the critic
    ran the tool and then something else.
    """
    return any(a.predicate == candidate and a.holds for a in record.attempts)


def spend(record: Record, predicate: Predicate, session: corpus.Session) -> Attempt:
    """Run a candidate and file the result. The body of the critic's `run_predicate` tool."""
    attempt = run_predicate(predicate, session)
    record.attempts.append(attempt)
    return attempt


def attempt_budget(record: Record, rule_searched_for: str | None = None) -> str:
    """The critic's only interface to the budget, and the body of its second tool.

    Asked without an argument it answers whether there is room, from the same function the
    edge routes on -- so the critic is never TOLD the cap in a prompt, where it would be a
    word that does not change when the constant does.

    Asked with one it is a give-up, and it refuses when nothing has been run: D-082 wants at
    least one `run_predicate` result behind every unmineable, and a tool is the only place
    that check can fire at the moment of giving up. Refusing costs an attempt and never buys
    one -- nothing here touches the counter.
    """
    if rule_searched_for is None:
        record.told_to_exit = attempts_exhausted(record.dispatches)
        return EXIT if record.told_to_exit else CONTINUE
    if not record.attempts:
        return REFUSED
    record.gave_up = True
    record.rule_searched_for = rule_searched_for
    return RECORDED


class State(TypedDict):
    """What travels the graph. `record` is the durable half; the rest is one lap's working set."""

    session: corpus.Session
    record: Record
    candidate: Predicate | None
    argument: str | None
    decision: str | None
    enhance: bool | None


Router = Callable[[corpus.Session], Awaitable[bool]]
Curator = Callable[[State], Awaitable[Predicate | None]]
Critic = Callable[[State], Awaitable[Ruling]]


def _reason(state: State) -> ExitReason | None:
    """Which door this lap leaves by, or None to go round again. Pure, so it can be tested.

    Order is the decision. A give-up the tool accepted outranks everything, because it is
    already recorded; a hand-over outranks the cap, because a candidate that held on the last
    attempt held. `force_terminated` sits above the cap so that an agent which was told to
    exit and bounced anyway is reported as disobedience rather than as an ordinary exhaustion.

    The compliant half of that needs no branch. `attempt_budget` sets `told_to_exit` from
    `attempts_exhausted` and `dispatches` only ever rises, so a trace that was told to exit is
    still over the cap on the last line and is exhausted there -- one door, reached two ways.
    """
    record = state["record"]
    if record.gave_up:
        return "gave_up"
    if state["decision"] == "hand_over" and held(record, state["candidate"]):
        return "handed_over"
    if record.told_to_exit and state["decision"] == "bounce":
        return "force_terminated"
    return "budget_exhausted" if attempts_exhausted(record.dispatches) else None


def build(*, router: Router, curator: Curator, critic: Critic) -> Any:
    """The compiled graph: route, then curator and critic until an edge says stop.

    Imported here rather than at module scope. langgraph costs 0.617 s and the three functions
    above are the ones most callers want; the unit suite has a 2 s budget for all of it, and a
    test of `_reason` should not pay for a graph library it never builds.

    ponytail: LangGraph's default recursion limit of 25 is left alone. The loop stops on its
    own edge well inside it at five attempts, and raising the cap past about eleven would need
    this set -- but deriving it here would put a second reader on the cap D-091 keeps to one.
    """
    from langgraph.graph import END, START, StateGraph

    async def route(state: State) -> dict[str, Any]:
        return {"enhance": await router(state["session"])}

    async def curate(state: State) -> dict[str, Any]:
        state["record"].dispatches += 1
        return {"candidate": await curator(state)}

    async def criticise(state: State) -> dict[str, Any]:
        ruling = await critic(state)
        return {"decision": ruling.decision, "argument": ruling.argument}

    def settle(state: State) -> str:
        # The write and the route come out of one call, which is what D-093 C means by the
        # edge owning `exit_reason`: a field written anywhere else was written by something
        # that did not decide, and the two get conflated again the first time they disagree.
        # `waved_through` is written here for the same reason -- it is the edge disagreeing
        # with the critic, so the edge is the only thing that can count it.
        if state["decision"] == "hand_over" and not held(state["record"], state["candidate"]):
            state["record"].waved_through += 1
        state["record"].exit_reason = _reason(state)
        if state["record"].exit_reason == "handed_over":
            state["record"].handed_over = state["candidate"]
        return END if state["record"].exit_reason else "curate"

    def selected(state: State) -> str:
        if not state["enhance"]:
            state["record"].exit_reason = "skipped"
            return END
        # DEF-079: a clean target sits in the set `run_predicate` scans, so nothing can hold.
        # The key is read here and never in a prompt, and only after the router has answered.
        if not state["session"].anomalous:
            state["record"].exit_reason = "misrouted"
            return END
        return "curate"

    graph = StateGraph(State)
    graph.add_node("route", route)
    graph.add_node("curate", curate)
    graph.add_node("criticise", criticise)
    graph.add_edge(START, "route")
    graph.add_conditional_edges("route", selected, {"curate": "curate", END: END})
    graph.add_edge("curate", "criticise")
    graph.add_conditional_edges("criticise", settle, {"curate": "curate", END: END})
    return graph.compile()


async def mine(
    session: corpus.Session, *, router: Router, curator: Curator, critic: Critic
) -> Record:
    """Work one session and return its record, whichever door it left by.

    An unmineable is a result and not an error (D-081): a trace nobody can write a rule for is
    a finding about the policy, not a bug in the curator. The caller reads `exit_reason` to
    tell the four apart, and reports the `gave_up` share beside any unmineable count -- a rate
    that cannot be decomposed is not a signal.
    """
    state: State = {
        "session": session,
        "record": Record(session_id=session.id),
        "candidate": None,
        "argument": None,
        "decision": None,
        "enhance": None,
    }
    final: State = await build(router=router, curator=curator, critic=critic).ainvoke(state)
    return final["record"]
