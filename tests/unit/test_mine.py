"""The inner loop's exits, and the one check D-090 and D-091 both name as due with this file.

The loop is three model calls around a mechanical test, so almost nothing here can be checked
by running it for real -- a live trace tells you what one critic did on one session, not what
the graph does when a critic misbehaves. What IS checkable is every door the trace can leave
by, driven with stub agents, and that is what this file is.

The load-bearing one is `test_a_critic_that_never_calls_a_tool_still_stops`. D-090 C and
D-091 C each specify it in the same words and each say it is unwritten because `loop/mine.py`
does not exist. It does now.

No corpus load. `run_predicate` is the only function here that reads the 934, and the two
tests that touch it substitute a set of three -- 91 MB of JSON would put the whole suite over
its 2 s budget for a fact about three sessions.
"""

import asyncio

import pytest

from touchstone.config import MAX_ATTEMPTS
from touchstone.gate.predicate import Predicate, RequiresPriorTool
from touchstone.loop import corpus, mine
from touchstone.loop.mine import Attempt, Record, Ruling, State, attempt_budget, run_predicate

AUTH = Predicate(
    rule="a lookup must follow authentication",
    source="policy.md:3",
    check=RequiresPriorTool(tool="get_order_details", prior=("get_user_details",)),
)


def session(sid: str, authenticated: bool) -> corpus.Session:
    """One session that either authenticates before the lookup or does not.

    One call per assistant message, because `RequiresPriorTool` reads message order and two
    calls in one message are not ordered with respect to each other. That is the evaluator
    being correct about a parallel call, and a fixture that batched them tested nothing.
    """
    names = ["get_user_details"] if authenticated else []
    names.append("get_order_details")
    return corpus.Session(
        id=sid,
        task_id="1",
        trial=0,
        agent="stub",
        anomalous=not authenticated,
        termination_reason="user_stop",
        messages=[
            m
            for n, name in enumerate(names)
            for m in (
                {"role": "assistant", "content": "", "tool_calls": [{"id": str(n), "name": name}]},
                {"role": "tool", "id": str(n)},
            )
        ],
    )


def state(record: Record, decision: str | None) -> State:
    """A lap's worth of state, which is all `_reason` reads."""
    return {
        "session": session("t", authenticated=False),
        "record": record,
        "candidate": None,
        "argument": None,
        "decision": decision,
        "enhance": True,
    }


async def _yes(_: corpus.Session) -> bool:
    return True


async def _propose(_: State) -> Predicate:
    return AUTH


async def _bounce(_: State) -> Ruling:
    """The critic D-091 C describes: it argues forever and never touches its tools."""
    return Ruling("bounce", "try again")


def run(
    *,
    router: mine.Router = _yes,
    curator: mine.Curator = _propose,
    critic: mine.Critic = _bounce,
) -> Record:
    """Drive one anomalous session through the graph with stubs. Returns its record."""
    target = session("t", authenticated=False)
    return asyncio.run(mine.mine(target, router=router, curator=curator, critic=critic))


def test_a_critic_that_never_calls_a_tool_still_stops() -> None:
    """D-090 C invariant 3 and D-091 C invariant 3, in the words both decisions used.

    The graph's edge and the critic's tool call one function, so a critic that ignores its
    budget entirely is stopped by the same arithmetic that would have advised it. Asserted on
    the exact count, not on termination: a loop that stopped at one attempt would also finish.
    """
    record = run()
    assert record.dispatches == MAX_ATTEMPTS
    assert record.exit_reason == "budget_exhausted"
    assert record.attempts == []


def test_the_router_can_end_a_trace_before_any_agent_runs() -> None:
    """A SKIP costs nothing. If it dispatched the curator once, selection would be advisory."""

    async def no(_: corpus.Session) -> bool:
        return False

    record = run(router=no)
    assert record.exit_reason == "skipped"
    assert record.dispatches == 0


def test_a_router_that_enhances_a_clean_session_ends_before_the_curator() -> None:
    """DEF-079. The key scores this target clean, so it is in the set `run_predicate` scans.

    Any predicate that fires on it is therefore its own counterexample, `holds` can never be
    true, and the five laps a bounce-forever critic would spend could not have ended any other
    way. The router made the error and the record names it, rather than reading as a curator
    that ran out of attempts. Asserted on the dispatch count too: an exit that still paid for
    the laps would be a relabelling and not a fix.
    """
    target = session("clean", authenticated=True)
    record = asyncio.run(mine.mine(target, router=_yes, curator=_propose, critic=_bounce))
    assert record.exit_reason == "misrouted"
    assert record.dispatches == 0


def test_a_hand_over_ends_the_trace() -> None:
    """The one exit that produces a candidate. Everything else is a finding about the policy.

    The critic files a holding attempt first, because that is what a real one does: it calls
    `run_predicate`, reads `holds`, and only then hands over. A hand-over with nothing behind
    it is the next test.
    """

    async def hand_over(s: State) -> Ruling:
        s["record"].attempts.append(Attempt(AUTH, fired_on_target=True, counterexample=None))
        return Ruling("hand_over")

    record = run(critic=hand_over)
    assert record.exit_reason == "handed_over"
    assert record.dispatches == 1
    assert record.waved_through == 0


def test_a_hand_over_the_check_does_not_support_is_not_a_door() -> None:
    """D-064 keeps the verdict mechanical, so the critic's word alone cannot end the loop.

    Here the candidate fired on the target and also on a clean session, so it does not hold,
    and the critic hands over anyway. The lap goes round again and the count rises — the same
    treatment `force_terminated` gets in D-094: the net stays whatever the expected value is,
    and a non-zero count is a bug report against a prompt rather than a category.
    """

    async def waves(s: State) -> Ruling:
        s["record"].attempts.append(Attempt(AUTH, fired_on_target=True, counterexample="other"))
        return Ruling("hand_over")

    record = run(critic=waves)
    assert record.exit_reason == "budget_exhausted", "it ran out rather than handing over"
    assert record.dispatches == MAX_ATTEMPTS
    assert record.waved_through == MAX_ATTEMPTS


def test_an_earlier_candidate_that_held_does_not_wave_the_current_one_through() -> None:
    """The check is matched on the CANDIDATE, and this is the case that needs it.

    A critic is free to call no tool this lap. Reading `attempts[-1]` would then hand over on
    evidence about the predicate before it — a real risk here, because the curator is told
    what its last candidate got wrong and is expected to send a different one.
    """
    other = Predicate(rule="something else", source="policy.md:9", check=AUTH.check)
    record = Record(session_id="t")
    record.attempts.append(Attempt(other, fired_on_target=True, counterexample=None))

    lap = state(record, "hand_over")
    lap["candidate"] = AUTH
    assert mine.held(record, other), "the earlier one did hold"
    assert not mine.held(record, AUTH), "and it says nothing about this one"
    assert mine._reason(lap) is None


def test_an_early_give_up_ends_the_trace_and_names_the_rule() -> None:
    """D-089 B: giving up costs naming the rule you went looking for and did not find."""

    async def gives_up(s: State) -> Ruling:
        s["record"].attempts.append(Attempt(AUTH, fired_on_target=False, counterexample=None))
        attempt_budget(s["record"], "a confirmation rule policy.md does not state")
        return Ruling("bounce", "no rule to encode")

    record = run(critic=gives_up)
    assert record.exit_reason == "gave_up"
    assert record.rule_searched_for is not None
    assert record.dispatches == 1


def test_a_give_up_with_nothing_run_is_refused() -> None:
    """The refusal D-091 B put in the tool rather than in the prompt.

    D-082 wants at least one predicate result behind every unmineable, and this is where that
    is enforced. A field in a structured answer could not have refused anything.
    """
    record = Record(session_id="t")
    assert attempt_budget(record, "a rule I did not look for") == "refused"
    assert record.gave_up is False
    assert record.rule_searched_for is None


def test_a_refusal_does_not_buy_an_attempt() -> None:
    """D-091 C invariant 2, asserted because the tempting fix for the line above is to reset."""
    record = Record(session_id="t", dispatches=3)
    attempt_budget(record, "a rule")
    attempt_budget(record)
    assert record.dispatches == 3


def test_a_critic_told_to_exit_that_bounces_anyway_is_force_terminated() -> None:
    """D-094 C. The value of this edge is that it fires only on disobedience.

    Under D-093 it fired on every exhausted trace and meant nothing. Here a count above zero
    sends someone to a prompt, so it has to be distinguishable from an ordinary exhaustion.
    """
    record = Record(session_id="t", dispatches=MAX_ATTEMPTS)
    assert attempt_budget(record) == "exit"
    assert mine._reason(state(record, "bounce")) == "force_terminated"


def test_a_critic_told_to_exit_that_complies_is_an_ordinary_exhaustion() -> None:
    """The other half, and without it the test above passes on a rule that never says no."""
    record = Record(session_id="t", dispatches=MAX_ATTEMPTS)
    attempt_budget(record)
    assert mine._reason(state(record, None)) == "budget_exhausted"


def test_a_predicate_that_holds_needs_both_halves(monkeypatch: pytest.MonkeyPatch) -> None:
    """The stopping rule, and the cheat it exists to catch.

    A predicate that merely quoted the failing session would fire on the target and meet the
    first clean session that looks like it. Silence is checked against the whole control set,
    so the second half is what makes the first one mean anything.
    """
    monkeypatch.setattr(corpus, "clean", lambda: (session("c1", authenticated=True),))
    attempt = run_predicate(AUTH, session("t", authenticated=False))
    assert attempt.fired_on_target is True
    assert attempt.counterexample is None
    assert attempt.holds is True


def test_a_predicate_that_fires_on_a_clean_session_hands_back_that_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The counterexample is an id, not a count: attempt i+1 is shown what attempt i got wrong."""
    monkeypatch.setattr(corpus, "clean", lambda: (session("c9", authenticated=False),))
    attempt = run_predicate(AUTH, session("t", authenticated=False))
    assert attempt.counterexample == "c9"
    assert attempt.holds is False
