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
from dataclasses import fields
from typing import TYPE_CHECKING, Any

from touchstone import config
from touchstone.gate.predicate import ArgumentIn, Predicate, RequiresPriorTool, RequiresUserAssent
from touchstone.loop import budget

if TYPE_CHECKING:
    from touchstone.gate.predicate import Check

__all__ = ["SYSTEM", "extract", "parse"]

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


def _object(text: str) -> dict[str, Any]:
    """The outermost JSON object in the answer.

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
    raw = _object(text)
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


async def extract(
    statement: str, source: str, counterexample: str | None = None
) -> Predicate | None:
    """Ask the curator to encode one policy statement. Returns None if no shape fits.

    `counterexample` is the session that motivated the rule, handed back on a later attempt so
    the model can see what its last answer failed to catch. That is the loop's iteration and it
    is P3.4's; the parameter is here because the prompt is the only place it can go.
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
        system_prompt=SYSTEM,
        # `tools=[]` is the switch that turns the SDK's own Read/Bash/Glob off; `allowed_tools`
        # is not, measured as DEF-064. Both, because the curator gets no tools at all (D-085).
        tools=[],
        allowed_tools=[],
        # [] is isolation; None loads this machine's CLAUDE.md and its model pin -- D-034.
        setting_sources=[],
        # ponytail: 2 is a guess, not a measurement -- one answer needs one turn and the spare
        # is for a model that narrates first. The partial-answer path below is what makes it
        # non-fatal; the first live run should read `num_turns` and pin this to it.
        max_turns=2,
    )

    prompt = f"Policy statement, from {source}:\n\n{statement}\n"
    if counterexample:
        prompt += f"\nA session your last answer did not catch:\n\n{counterexample}\n"

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
        # Same shape as the seam's: running out of turns is reported as a ResultMessage and
        # then raised. An answer already streamed is still an answer, and throwing it away
        # would spend the window twice for one result.
        if not text:
            raise
    if result is not None and result.is_error and not text:
        raise RuntimeError(f"the curator failed: {result.subtype} {result.api_error_status}")
    return parse("\n".join(t for t in text if t))
