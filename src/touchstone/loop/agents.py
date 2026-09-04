"""P3.4 -- the three roles the loop calls, and the two tools the critic holds.

`mine.py` takes its agents as callables and holds no model. They come from here: the router
and its rubric (D-086 SS B), the curator that reads a failed session and proposes a predicate
(D-086 SS C), and the critic that attacks it with `run_predicate` and `attempt_budget` in
hand (D-085, D-089, D-092).

This is the third module to reach the SDK, and `test_only_the_seam_and_the_doctor_may_reach_a_
model` is set equality so that fact has to be argued rather than added. The argument is
D-107's, one level along: that guard protects the GATING path, `predicate.evaluate()` is what
gates, and `test_no_model_in_gating_path` walks it and still finds no model. What is here is
the PROPOSING path, and D-086 SS A already priced it out loud -- inside the loop every branch
is a model's, and the mechanical boundary that survives is `admission`, outside it.

Two things are deliberately absent, and both are absences rather than omissions:

    D-087's suite check. The exact half runs the admitted suite's predicates against the
    trace; the judged half puts the suite index in the curator's prompt. Both take a suite of
    ADMITTED cases as input, and admission is backlog because the loop is what produces one
    (D-086 SS D). Writing either now means writing it against a shape nothing emits.

    The answer key. `corpus.Session.anomalous` is derived from tau2's `reward_info`, and
    rubric criterion 1 asks the router to reach the same verdict from the transcript alone --
    so the disagreement between them IS the router's measured error rate (D-082 SS B). Put
    the flag in the prompt and that number measures nothing. `_transcript` reads `messages`
    and nothing else, and `test_no_prompt_carries_the_answer_key` is what holds it there.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
from typing import TYPE_CHECKING, Any

from touchstone import config
from touchstone.gate import extract
from touchstone.loop import corpus, mine

if TYPE_CHECKING:
    from collections.abc import Mapping

    from touchstone.gate.predicate import Predicate

__all__ = [
    "CRITIC",
    "CURATOR",
    "RUBRIC",
    "Verdict",
    "asked",
    "critic",
    "curator",
    "ran",
    "route",
    "router",
    "shape",
]

# Tool results are cut to this. Measured 2026-09-01 over all 13,095 in the corpus, because 800
# was a guess and it cut 60.6% of them while the longest is 3,370 characters. A curator
# proposing over a truncated render while `run_predicate` judges the full messages is the
# mismatch the failed-tool render exists to prevent, and `ArgumentIn` reads what was being cut.
# So the bound sits above the corpus maximum and never fires here; it stays for a swapped
# specimen (D-062). Uncut, transcripts run 12.2 KB median, 21 KB p95, 106 KB max.
_CUT = 4000

RUBRIC = """You screen one agent session and decide whether it is worth mining for an eval gate.

Answer with one JSON object and nothing else. No prose, no code fence.

  {"criterion_1": bool, "criterion_2": bool, "criterion_3": bool, "criterion_4": bool,
   "why": "<one sentence, and it must hold for whichever criterion you answered NO>"}

  1. Is this session anomalous -- did the agent get something wrong?
  2. Does the failure map to something written down: the policy below, or a tool's own
     contract? A NO here is the cheapest refusal there is, and it costs nothing later.
  3. Is the failure visible in the process, not only in the end state? An agent that reached
     the right database state by a route the policy forbids is a YES.
  4. Is the violation specific enough to write a machine-checkable rule over? "Refunded
     outside the stated window" is. "Unhelpful" is not.

You are not deciding whether the loop proceeds. All four have to hold for that, and combining
them is not your job -- answer each one on its own, including when an earlier NO makes a later
criterion feel moot.
"""

CURATOR = """You read one failed agent session and write the rule it broke, as one predicate.

Deciding what is worth encoding is your job, not only translating. A failure that is real and
that the policy never speaks to is not one this loop can gate; say so rather than reaching for
the nearest rule. A rule too vague to check is worse than none, because it fires on correct
work and every case it fails becomes someone's afternoon.

Write the rule the session actually broke. The nearest rule that happens to fire is a
different rule, and the suite will carry your description of it, not the one you meant.

"""

CRITIC = """You attack one candidate predicate before it can reach the suite.

You have two tools.

  run_predicate       runs the candidate against the session it was written for and against
                      every session the benchmark scored clean. It answers whether it fired on
                      the target, and names the first clean session it also fired on. It takes
                      no arguments: the candidate is the one in front of you.
  attempt_budget      with no argument, answers whether there is another attempt left.
                      With `rule_searched_for`, gives up on this session for good -- name the
                      stated rule you went looking for and did not find. It refuses a give-up
                      when nothing has been run yet.

Run the cheap refusals first. A candidate that quotes a task id, or encodes a rule the policy
does not state, needs no run to be sent back, and a run spent on it is a run not available
later. The policy is below and it is line-numbered: `source` names a line, so read that line
and check it says what the candidate claims. A citation that does not support the rule is the
same refusal as an unstated rule, and it is cheaper than either.

Then answer with one JSON object and nothing else. No prose, no code fence.

  {"decision": "hand_over" | "bounce", "argument": "<what is wrong with it, specifically>"}

  hand_over   the predicate fires on this session and on no clean one. You have watched that
              happen. Inferring it from reading the predicate is not the same claim.
  bounce      back to the curator with a finding it can act on. Never "this seems weak": a
              vague objection spends one of the attempts and teaches the curator nothing.

If `attempt_budget` tells you there is no attempt left, stop. Answering `bounce` after that is
recorded as a force-termination against this prompt, not as an ordinary exhaustion.
"""

# D-041 requires it beside every score: edit a criterion and every past agreement figure is a
# different claim measured against a different rubric.
RUBRIC_HASH = sha256(RUBRIC.encode()).hexdigest()[:12]

CRITIC_TOOLS = ("mcp__loop__run_predicate", "mcp__loop__attempt_budget")


@dataclass(frozen=True)
class Verdict:
    """The router's four answers, and the composition it does not get to make.

    `enhance` is ours because it is arithmetic, and a model asked for a fifth judgement can
    reach ENHANCE while answering NO to one of the four. `anomalous` is criterion 1 and is
    read on its own: against `corpus.Session.anomalous`, over the 1,712, it is
    `criterion_1_agreement` and no other number here is reportable without it (D-082 SS B).
    """

    anomalous: bool
    stated: bool
    in_process: bool
    specific: bool
    why: str

    @property
    def enhance(self) -> bool:
        """All four, which is what D-086 SS B's table means by criteria rather than a score."""
        return self.anomalous and self.stated and self.in_process and self.specific


@lru_cache(maxsize=1)
def policy() -> str:
    """Retail's policy, line-numbered, so a citation can be checked rather than believed.

    D-106 makes `source` a required field and the loop refuses a predicate that cannot name a
    line. Numbering it here is what makes the requirement answerable: without it the model is
    being asked to cite a line it was never shown.
    """
    lines = corpus.policy_text().splitlines()
    return "\n".join(f"{i:>4}  {line}" for i, line in enumerate(lines, 1))


def _cut(text: str) -> str:
    """Long content, shortened, saying so where it was cut."""
    return text if len(text) <= _CUT else f"{text[:_CUT]} [...{len(text) - _CUT} more]"


def _tag(item: Mapping[str, Any]) -> str:
    """A call or result's id, rendered so the two can be paired, or nothing when it has none."""
    return f" #{item['id']}" if item.get("id") else ""


def _transcript(session: corpus.Session) -> str:
    """One session as the model sees it: messages, in order, and nothing derived from a reward.

    Tool calls are rendered with their arguments and each result with whether it errored,
    because order and success are exactly what the three predicate shapes read. A render that
    dropped either would be showing the model less than the check it is proposing.

    Each call and each result carries its id for the same reason, one field along (DEF-078).
    `predicate._succeeded` pairs a result to its call BY id, and 657 of the corpus's 1,712
    sessions have a message that calls more than one tool -- 994 such messages, up to 47 calls
    in one. Untagged, their results arrive as a run of `tool[ok]` and `tool[error]` lines that
    can only be paired by counting, so the reader is guessing at exactly the field the check
    reads. Measured 2026-09-01: all 13,870 calls carry an id and every one is answered.
    """
    out = []
    for m in session.messages:
        role = str(m.get("role", "?"))
        content = _cut(str(m.get("content") or "").strip())
        if role == "tool":
            out.append(f"tool{_tag(m)}[{'error' if m.get('error') else 'ok'}]: {content}")
            continue
        if content:
            out.append(f"{role}: {content}")
        for call in m.get("tool_calls") or []:
            args = json.dumps(call.get("arguments") or {}, sort_keys=True)
            out.append(f"{role} calls {call.get('name')}({_cut(args)}){_tag(call)}")
    return "\n".join(out)


async def route(session: corpus.Session) -> Verdict:
    """The rubric, run once over one session. Every criterion, not just the verdict."""
    answer = extract.json_object(
        await extract.ask(
            "router",
            f"{RUBRIC}\nThe policy, line-numbered:\n\n{policy()}\n",
            f"The session:\n\n{_transcript(session)}\n",
            max_turns=config.AGENT_TURNS,
        )
    )
    return Verdict(
        anomalous=bool(answer.get("criterion_1")),
        stated=bool(answer.get("criterion_2")),
        in_process=bool(answer.get("criterion_3")),
        specific=bool(answer.get("criterion_4")),
        why=str(answer.get("why") or ""),
    )


async def router(session: corpus.Session) -> bool:
    """ENHANCE or SKIP, which is all the graph needs. `route` is what a measurement calls."""
    return (await route(session)).enhance


async def curator(state: mine.State) -> Predicate | None:
    """Propose a predicate for this session, or None where no shape fits.

    On attempt 2 and after it is handed the critic's argument and the transcript of the clean
    session its last candidate fired on -- the id alone names the failure without showing it,
    and the whole point of a counterexample is that the next attempt can read what it got
    wrong (D-085 SS F).

    The counterexample is looked up BY the last candidate and not as `attempts[-1]`, for the
    reason D-110 gives for `mine.held`. `state["candidate"]` still holds the previous lap's
    proposal here -- `curate` overwrites it with this call's return -- and the critic is free
    to bounce without calling `run_predicate` (D-086 C prices exactly that), so the newest
    attempt on the record can belong to a candidate two laps old. Showing that one back would
    tell the curator its last proposal fired on a session it never ran against.
    """
    parts = [f"The session:\n\n{_transcript(state['session'])}\n"]
    if state["argument"]:
        parts.append(f"The critic sent your last candidate back:\n\n{state['argument']}\n")
    last = next(
        (a for a in reversed(state["record"].attempts) if a.predicate == state["candidate"]), None
    )
    if last is not None and last.counterexample:
        parts.append(
            "It also fired on this session, which the benchmark scored clean. Whatever it is "
            f"keying on is not the rule:\n\n{_by_id(last.counterexample)}\n"
        )
    prompt = "\n".join(parts)
    system = f"{CURATOR}{extract.SYSTEM}\nThe policy, line-numbered:\n\n{policy()}\n"
    return extract.parse(await extract.ask("curator", system, prompt, max_turns=config.AGENT_TURNS))


async def critic(state: mine.State) -> mine.Ruling:
    """Attack the candidate, with the mechanical check and the budget as tools.

    An unparseable answer raises rather than becoming a bounce. A critic that cannot produce
    its verdict would otherwise burn the remaining attempts and be reported as an ordinary
    exhaustion, and D-094 SS C's whole argument is that the exit reasons have to stay
    distinguishable to be worth counting.

    The policy goes in for the same reason the router and the curator get it: two of the three
    cheap refusals the prompt asks for first are judgements about what the policy says, and
    D-106 makes `source` a required citation the critic is the only reader of. Until
    2026-09-01 it was the one role that had to make those calls without the document.
    """
    candidate = state["candidate"]
    if candidate is None:
        return mine.Ruling("bounce", "the curator found no shape that fits this session")

    prompt = (
        f"The candidate:\n\n{json.dumps(shape(candidate), indent=2)}\n\n"
        f"The session it was written for:\n\n{_transcript(state['session'])}\n"
    )
    answer = extract.json_object(
        await extract.ask(
            "critic",
            f"{CRITIC}\nThe policy, line-numbered:\n\n{policy()}\n",
            prompt,
            max_turns=config.CRITIC_TURNS,
            allowed_tools=CRITIC_TOOLS,
            servers=_server(state, candidate),
        )
    )
    decision = "hand_over" if answer.get("decision") == "hand_over" else "bounce"
    return mine.Ruling(decision, str(answer.get("argument") or "") or None)


def shape(predicate: Predicate) -> dict[str, Any]:
    """A predicate as the curator emitted it, so the critic argues with what was proposed."""
    check = predicate.check
    return {
        "kind": type(check).__name__,
        "rule": predicate.rule,
        "source": predicate.source,
        **{k: list(v) if isinstance(v, tuple) else v for k, v in vars(check).items()},
    }


def _by_id(session_id: str) -> str:
    """One session by id. The corpus is already loaded by the time a counterexample exists."""
    return next(_transcript(s) for s in corpus.load() if s.id == session_id)


def ran(state: mine.State, candidate: Predicate) -> dict[str, Any]:
    """The body of `run_predicate`, outside the decorator so it can be run without one.

    `holds` is sent rather than left to be inferred. It is the stopping rule and it is an AND
    of the other two fields, so a critic that reconstructed it could get it wrong in the one
    direction that matters -- reading a fired-on-target as a pass while a counterexample sits
    beside it.
    """
    attempt = mine.spend(state["record"], candidate, state["session"])
    return {
        "fired_on_target": attempt.fired_on_target,
        "counterexample": attempt.counterexample,
        "holds": attempt.holds,
    }


def asked(state: mine.State, rule_searched_for: str | None) -> str:
    """The body of `attempt_budget`. An empty rule is a question, never a give-up.

    The tool has one optional argument and two jobs, so the argument arriving empty is the
    ambiguous case: a model that sends `""` has not named a rule, and D-089 SS D makes naming
    one the price of giving up. Reading it as a give-up would let the price be paid in
    whitespace.
    """
    return mine.attempt_budget(state["record"], (rule_searched_for or "").strip() or None)


def _server(state: mine.State, candidate: Predicate) -> dict[str, Any]:
    """The critic's two tools, bound to this session's record.

    In-process, so what the graph reads afterwards is a recorded call and never the model's
    account of one -- which is the line D-085 SS B drew and D-086 SS A left standing for the
    record even after the decision moved to the critic.
    """
    from claude_agent_sdk import create_sdk_mcp_server, tool

    @tool("run_predicate", "Run the candidate against the target and the clean sessions.", {})
    async def run(_: dict[str, Any]) -> dict[str, Any]:
        return _said(json.dumps(ran(state, candidate)))

    @tool(
        "attempt_budget",
        "Ask whether an attempt is left, or give up on this session for good.",
        {
            "type": "object",
            "properties": {
                "rule_searched_for": {
                    "type": "string",
                    "description": "The stated rule you looked for and did not find. Giving up.",
                }
            },
            "required": [],
        },
    )
    async def spend(args: dict[str, Any]) -> dict[str, Any]:
        return _said(asked(state, args.get("rule_searched_for")))

    return {"loop": create_sdk_mcp_server("loop", tools=[run, spend])}


def _said(text: str) -> dict[str, Any]:
    """A tool result in the shape the SDK expects."""
    return {"content": [{"type": "text", "text": text}]}
