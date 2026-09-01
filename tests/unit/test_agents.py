"""The three roles, checked at the two places a model is not involved.

Almost everything in `agents.py` is a prompt, and a prompt is not testable here -- what it
produces costs quota, and the run that spends it is the measurement, not this. What IS
testable is the pair of boundaries either side of the model: what goes into a prompt, and what
comes back out of one becomes.

So: the transcript that goes in, the verdict arithmetic that is ours rather than the router's,
and the round trip that says the critic argues with the same predicate the curator emitted.

No tau2 import. `policy()` reads the specimen's data directory, which costs 1.71 s at import,
and the whole unit suite has 2 s.
"""

import asyncio
import json

import pytest

from touchstone.gate.extract import parse
from touchstone.gate.predicate import Predicate, RequiresPriorTool
from touchstone.loop import agents, corpus, mine

AUTH = Predicate(
    rule="a lookup must follow authentication",
    source="policy.md:10",
    check=RequiresPriorTool(tool="get_order_details", prior=("get_user_details",)),
)


def session() -> corpus.Session:
    """A session carrying every field the answer key writes and one ordinary exchange."""
    return corpus.Session(
        id="s1",
        task_id="1",
        trial=0,
        agent="stub",
        anomalous=True,
        termination_reason="agent_error",
        messages=[
            {"role": "user", "content": "cancel my order"},
            {
                "role": "assistant",
                "content": "on it",
                "tool_calls": [{"id": "0", "name": "cancel", "arguments": {"id": "W1"}}],
            },
            {"role": "tool", "id": "0", "content": "done", "error": False},
        ],
    )


def test_the_transcript_carries_the_exchange_and_not_the_verdict() -> None:
    """The positive half of `test_no_prompt_carries_the_answer_key`.

    That guard reads the AST and would keep passing if `_transcript` stopped rendering
    anything at all. This one names what has to be there as well as what must not be.
    """
    rendered = agents._transcript(session())
    assert "user: cancel my order" in rendered
    assert 'assistant calls cancel({"id": "W1"})' in rendered
    assert "tool[ok]: done" in rendered
    assert "agent_error" not in rendered
    assert "anomalous" not in rendered


def test_a_failed_tool_result_is_rendered_as_failed() -> None:
    """Success is a field the shapes read, so hiding it would show less than the check does.

    `RequiresPriorTool` is satisfied only by a prior call the environment answered without an
    error, and a transcript that rendered both the same way would have the curator proposing
    over one trajectory and `run_predicate` judging over another.
    """
    s = session()
    s.messages[2]["error"] = True
    assert "tool[error]: done" in agents._transcript(s)


def test_long_content_is_cut_and_says_so() -> None:
    """A silent truncation reads as an agent that stopped mid-sentence."""
    cut = agents._cut("x" * 5000)
    assert cut.startswith("x" * agents._CUT)
    assert cut.endswith(f"[...{5000 - agents._CUT} more]")


def test_enhance_needs_all_four_criteria() -> None:
    """D-086 §B is four criteria, not a score, and the composition is not the router's.

    Asserted one criterion at a time: a model asked for a fifth judgement can answer NO to
    criterion 2 and still reach ENHANCE, and that is the failure this arithmetic removes.
    """
    yes = agents.Verdict(anomalous=True, stated=True, in_process=True, specific=True, why="")
    assert yes.enhance
    for field in ("anomalous", "stated", "in_process", "specific"):
        assert not agents.Verdict(**{**vars(yes), field: False}).enhance, field


def test_the_critic_argues_with_what_the_curator_emitted() -> None:
    """`_shape` is the candidate as JSON, and it has to parse back to the same predicate.

    The critic is handed a rendering, not the object, so the rendering is where the two can
    drift. A field dropped here is a field the critic never objects to and the suite still
    carries -- and `parse` is the closed-set boundary that catches it, so the round trip runs
    through it rather than comparing dictionaries.
    """
    assert parse(json.dumps(agents.shape(AUTH))) == AUTH


def test_a_curator_that_found_no_shape_costs_no_model_call() -> None:
    """The curator returning None is an answer (D-106), not a gap to hand the critic.

    Attacking nothing would spend a call and come back with the observation that there is
    nothing there. Nothing is monkeypatched here on purpose: if the short circuit went away
    this test would try to reach a model, which is the loudest failure available.
    """
    state: mine.State = {
        "session": session(),
        "record": mine.Record(session_id="s1"),
        "candidate": None,
        "argument": None,
        "decision": None,
        "enhance": True,
    }
    ruling = asyncio.run(agents.critic(state))
    assert ruling.decision == "bounce"
    assert ruling.argument is not None


def test_the_rubric_hash_moves_when_a_criterion_does() -> None:
    """The bookkeeping D-041 requires beside every agreement figure.

    Editing a criterion makes every earlier score a different claim measured against a
    different rubric, so the hash is what tells two runs apart. The count is asserted with it
    because a criterion silently dropped changes the hash correctly and the rubric wrongly.
    """
    assert len(agents.RUBRIC_HASH) == 12
    assert agents.RUBRIC.count("criterion_") == 4


def lookup(sid: str, *, authenticated: bool) -> corpus.Session:
    """A session that looks an order up, having authenticated first or not.

    One call per assistant message: `RequiresPriorTool` orders on message index, so two calls
    in one message are not ordered with respect to each other.
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


def _state(record: mine.Record) -> mine.State:
    """One lap's working set, at the point the critic has its two tools in hand."""
    return {
        "session": lookup("t", authenticated=False),
        "record": record,
        "candidate": AUTH,
        "argument": None,
        "decision": None,
        "enhance": True,
    }


def test_running_a_predicate_files_the_result_rather_than_reporting_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The line D-085 B drew: the graph reads a recorded call, never a model's account of one.

    The tool both answers the critic and appends to the record, and only the second half is
    load-bearing -- a critic that misreports what it saw still cannot change what the edge
    routes on. So the assertion is on the record, and the reply is checked for agreeing.

    `corpus.clean` is stubbed because the real one loads 91 MB. It returns the authenticating
    session, which is what makes the silence half of `holds` mean something here.
    """
    monkeypatch.setattr(corpus, "clean", lambda: (lookup("c1", authenticated=True),))
    record = mine.Record(session_id="t")

    reply = agents.ran(_state(record), AUTH)

    assert len(record.attempts) == 1
    assert record.attempts[0].holds
    assert reply == {"fired_on_target": True, "counterexample": None, "holds": True}


def test_giving_up_is_refused_before_anything_has_run_and_costs_no_attempt() -> None:
    """D-082's floor, at the one place it can fire: every unmineable carries a run behind it.

    Three calls, because what each does to the record is the point. The empty string must not
    be read as a give-up -- a model that sends `""` has named no rule, and naming one is the
    price (D-089 D) -- and the refusal must not buy an attempt back.

    The attempt is filed by hand rather than run: `run_predicate` would load the corpus, and
    what the third call turns on is only that the list is non-empty.
    """
    record = mine.Record(session_id="t")
    state = _state(record)

    assert agents.asked(state, "  ") == mine.CONTINUE
    assert agents.asked(state, "no such rule") == mine.REFUSED
    assert not record.gave_up
    assert record.dispatches == 0

    record.attempts.append(mine.Attempt(predicate=AUTH, fired_on_target=True, counterexample=None))
    assert agents.asked(state, "no such rule") == mine.RECORDED
    assert record.gave_up
    assert record.rule_searched_for == "no such rule"
