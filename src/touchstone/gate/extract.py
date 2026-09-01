"""P2.2 -- the model's half of the gate: a stated policy line becomes one of three shapes.

The division of labour is D-064's and it is the whole point of the phase. The model TRANSLATES:
it reads a rule someone already wrote down and picks the shape that encodes it. It never
decides whether an agent did well, and it never sees a reward. The verdict is
`predicate.evaluate()`, which is arithmetic over a transcript and has no model in it.

Which is why the answer is a JSON object rather than Python. D-106: the shapes are a closed
set of three, the curator runs with `allowed_tools=[]` so it emits a field and not a program,
and exec'ing model-authored source would put a model back on the path D-064 keeps mechanical.
`parse()` is the boundary that enforces that -- an unknown `kind` is refused rather than
accommodated, because the set being closed is the guarantee.

This module reaches the SDK, which `test_only_the_seam_and_the_doctor_may_reach_a_model` used
to forbid outside `adapter` and `doctor`. The argument for widening it is D-107: that guard
protects the GATING path, and this is the proposing path -- the module it hands its answer to,
`predicate.py`, is now walked by `test_no_model_in_gating_path` and still has no model in it.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import fields
from typing import TYPE_CHECKING, Any

from touchstone import config
from touchstone.gate.predicate import ArgumentIn, Predicate, RequiresPriorTool, RequiresUserAssent
from touchstone.loop import budget

if TYPE_CHECKING:
    from touchstone.gate.predicate import Check

__all__ = ["SYSTEM", "ask", "extract", "json_object", "parse"]

_SHAPES: dict[str, type[Check]] = {
    c.__name__: c for c in (RequiresPriorTool, RequiresUserAssent, ArgumentIn)
}

SYSTEM = """You translate a written policy rule into one machine-checkable predicate.

Answer with one JSON object and nothing else. No prose, no code fence.

  {"kind": <one of the shapes below>, "rule": <one sentence>, "source": <where it is written>}

plus that shape's own fields:

  RequiresPriorTool   "tool": str, "prior": [str]
      `tool` may only be called after one of `prior` returned without an error.

  RequiresUserAssent  "tool": str, "phrases": [str]
      `tool` may only be called after a user message containing one of `phrases`.

  ArgumentIn          "tool": str, "argument": str, "allowed": [str]
      `argument` of `tool` may only take a value in `allowed`.

Rules you must follow:

  - Encode only what the policy states. If it does not say it, it is not a rule.
  - "source" must point at the text you read it in, as file:line. It is not decoration: a
    predicate that cannot cite a line is one the loop refuses.
  - Use the tool names exactly as the policy writes them.
  - If no shape fits the rule, answer {"kind": null, "why": <one sentence>}. That is a real
    answer. Forcing a rule into the wrong shape produces a gate that fires on correct work.
"""


def json_object(text: str) -> dict[str, Any]:
    """The outermost JSON object in the answer. Public because the critic answers this way too.

    Sliced rather than parsed whole because a model told to emit bare JSON still sometimes
    wraps it in a sentence or a fence, and that is a formatting slip rather than a refusal to
    answer. Anything that is not an object at all is a refusal and raises.
    """
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError(f"no JSON object in the answer: {text[:200]!r}")
    loaded = json.loads(text[start : end + 1])
    if not isinstance(loaded, dict):
        raise TypeError(f"expected an object, got {type(loaded).__name__}")
    return loaded


def parse(text: str) -> Predicate | None:
    """One model answer to a predicate, or None where it declined to encode a rule.

    Pure and total: every way the answer can be wrong leaves here as `ValueError`, never as a
    half-built predicate. This is a trust boundary -- the input is model output, and the reason
    the shapes are a closed set is lost the moment an unrecognised one is waved through.
    """
    raw = json_object(text)
    kind = raw.get("kind")
    if kind is None:
        return None
    shape = _SHAPES.get(kind)
    if shape is None:
        raise ValueError(f"unknown shape {kind!r} -- the set is closed: {sorted(_SHAPES)}")

    missing = sorted({f.name for f in fields(shape)} - raw.keys())
    if missing:
        raise ValueError(f"{kind} needs {missing}")
    args = {f.name: _frozen(raw[f.name]) for f in fields(shape)}

    for field_name in ("rule", "source"):
        if not str(raw.get(field_name, "")).strip():
            raise ValueError(f"{field_name!r} is empty -- D-106 makes the citation a field")
    return Predicate(rule=raw["rule"], source=raw["source"], check=shape(**args))


def _frozen(value: Any) -> Any:
    """Lists become tuples. The shapes are frozen dataclasses and a list defeats that."""
    return tuple(value) if isinstance(value, list) else value


async def ask(
    role: str,
    system: str,
    prompt: str,
    *,
    max_turns: int,
    allowed_tools: Sequence[str] = (),
    servers: Mapping[str, Any] | None = None,
) -> str:
    """One question to one role, and the text it answered with.

    Every loop agent comes through here, which is what makes the isolation flags one decision
    instead of three. `tools=[]` is the switch that turns the SDK's own Read/Bash/Glob off and
    `allowed_tools` is not, measured as DEF-064 -- so both are set, and `allowed_tools` grants
    only what a caller asks for. It defaults to nothing: a role gains a tool by naming it here
    (D-085 SS D), never by inheriting one.

    A partial answer is kept. Running out of turns is reported as a `ResultMessage` and then
    raised, and text already streamed is still an answer -- throwing it away would spend the
    five-hour window twice for one result.
    """
    if budget.quota_exhausted():
        raise budget.QuotaExhaustedError(f"quota reading: {budget.reading()}")

    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        RateLimitEvent,
        ResultMessage,
        TextBlock,
        query,
    )

    opts = ClaudeAgentOptions(
        model=config.LOOP_MODEL,
        system_prompt=system,
        tools=[],
        allowed_tools=list(allowed_tools),
        mcp_servers=dict(servers or {}),
        # [] is isolation; None loads this machine's CLAUDE.md and its model pin -- D-034.
        setting_sources=config.SETTING_SOURCES,
        max_turns=max_turns,
    )

    text: list[str] = []
    result = None
    try:
        async for msg in query(prompt=prompt, options=opts):
            if isinstance(msg, RateLimitEvent):
                budget.observe(msg.rate_limit_info)
            elif isinstance(msg, AssistantMessage):
                text.extend(b.text for b in msg.content if isinstance(b, TextBlock))
            elif isinstance(msg, ResultMessage):
                result = msg
    except Exception:
        if not text:
            raise
    if result is not None and result.is_error and not text:
        raise RuntimeError(f"the {role} failed: {result.subtype} {result.api_error_status}")
    return "\n".join(t for t in text if t)


async def extract(
    statement: str, source: str, counterexample: str | None = None
) -> Predicate | None:
    """Ask the curator to encode one policy statement. Returns None if no shape fits.

    `counterexample` is the session that motivated the rule, handed back on a later attempt so
    the model can see what its last answer failed to catch. That is the loop's iteration and it
    is P3.4's; the parameter is here because the prompt is the only place it can go.
    """
    prompt = f"Policy statement, from {source}:\n\n{statement}\n"
    if counterexample:
        prompt += f"\nA session your last answer did not catch:\n\n{counterexample}\n"
    return parse(await ask("curator", SYSTEM, prompt, max_turns=config.AGENT_TURNS))
