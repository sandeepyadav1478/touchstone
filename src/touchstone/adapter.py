"""P1.1 — the single seam: the Claude Agent SDK behind τ²'s `generate()`.

`tau2.utils.llm_utils.generate()` (`llm_utils.py:355`) is the one chokepoint every live τ²
model role passes through — agent, user simulator, NL-assertion evaluator, hallucination
reviewer — so **one** adapter dispatching on the `model` argument covers all four. ⛔ **No fork
of τ².** The pin is commit `a2c024725189` and it stays readable as upstream, which is what makes
*"we did not write the benchmark"* checkable by a stranger.

🔴 **The seam is `generate()`, not the litellm import at `llm_utils.py:15`, and that is a
correction to what the roadmap row implied.** Replacing `completion` would keep more of τ²
running, which is the attractive property — but `generate()` then overwrites the cost by calling
`get_response_cost()`, which recomputes from litellm's own price table. Measured here on the
probe call: litellm's table says **7e-05** for a response the SDK measured at **0.0040**, a
factor of 58, and wrong in the flattering direction because prompt caching is invisible to
arithmetic. [docs/00](../../docs/00-stack.md) §3 says cost is measured, not arithmetic, so the
seam has to sit *above* the line that recomputes it.

⚠️ **The adapter is stateless, and that is a deliberate ceiling rather than an oversight.**
τ² hands `generate()` the whole history on every call, so each call here is one fresh SDK
session with the history rendered into the prompt. The SDK's own defer→resume path was probed
and does not take a caller-supplied `tool_result` back (the model reads the resume as a
cancellation and says so), so making sessions work would mean fighting the CLI for a property
τ² does not ask for. What it costs: the model sees a rendered transcript rather than native
assistant/tool turns. What it buys: nothing to key sessions on, and no way for the adapter's
state to drift from τ²'s.

**It also opens `touchstone.llm`** — D-073. ⛔ **P1.1 is not done without the span**: it is the
only point every version shares, and no instrumentor can emit it (the SDK shells out to the CLI,
so there is no in-process client to wrap).

🔴 **The span is `mlflow.start_span()`, not the OTel SDK, and P1.1 shipped with that wrong.**
D-074 deleted `opentelemetry-sdk` and the OTLP exporter; `opentelemetry-api` survives only as one
of MLflow's own transitives, so `trace.get_tracer()` resolved, returned a **no-op**, and every
attribute set below went nowhere. It looked exactly like *"correct code waiting for its provider"*
— which is what the paragraph here used to claim — and both readings predict an empty store, so
nothing distinguished them until the store was measured. ⚠️ **A dependency you did not declare
answering your import is not the same as your dependency being present** (DEF-052 again, third
time). `telemetry.install()` is what makes this land, and `doctor` round-trips it.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from typing import Any

import mlflow
from mlflow.entities import SpanType

from touchstone import config

# The SDK namespaces in-process MCP tools as ``mcp__<server>__<name>``. τ²'s tool names have to
# round-trip through that, so the prefix is stripped on the way back rather than guessed at.
_SERVER = "tau2"
_PREFIX = f"mcp__{_SERVER}__"

_DEFER = {
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "defer",
        "permissionDecisionReason": "τ² owns tool execution — Environment.make_tool_call()",
    }
}


# ── pure: everything testable without the SDK, the CLI or a network ───────────────────────────


def render(messages: list[Any]) -> tuple[str, str]:
    """Split τ²'s history into an SDK ``system_prompt`` and one rendered transcript.

    Tool calls and their results are rendered as tags rather than dropped: τ²'s agent loop is
    *about* tool use, and a transcript that loses the results asks the model to answer from a
    conversation it cannot see.
    """
    system: list[str] = []
    turns: list[str] = []
    for m in messages:
        role = getattr(m, "role", None)
        if role == "system":
            if m.content:
                system.append(m.content)
            continue
        if role == "tool":
            turns.append(f"<tool_result id={m.id}>\n{m.content or ''}\n</tool_result>")
            continue
        parts: list[str] = []
        if content := (getattr(m, "content", None) or "").strip():
            parts.append(content)
        for call in getattr(m, "tool_calls", None) or []:
            parts.append(
                f"<tool_call id={call.id} name={call.name}>"
                f"{json.dumps(call.arguments)}</tool_call>"
            )
        turns.append(f"{role}: " + "\n".join(parts) if parts else f"{role}:")
    return "\n\n".join(system), "\n\n".join(turns)


def tool_name(sdk_name: str) -> str:
    """``mcp__tau2__get_order`` → ``get_order``. Anything unprefixed is passed through."""
    return sdk_name[len(_PREFIX) :] if sdk_name.startswith(_PREFIX) else sdk_name


def usage_of(raw: dict[str, Any] | None) -> dict[str, int] | None:
    """The two counts τ²'s `get_response_usage()` returns, from the SDK's usage dict.

    ⚠️ **`prompt_tokens` folds the cache reads back in.** The SDK reports `input_tokens` net of
    them, and a prompt-token count that silently excludes a cached prefix is not comparable
    between a first run and a re-run of the same task.
    """
    if not raw:
        return None
    return {
        "completion_tokens": raw.get("output_tokens", 0),
        "prompt_tokens": (
            raw.get("input_tokens", 0)
            + raw.get("cache_read_input_tokens", 0)
            + raw.get("cache_creation_input_tokens", 0)
        ),
    }


# ── the SDK call ──────────────────────────────────────────────────────────────────────────────


def _sdk_tools(tools: list[Any] | None) -> list[Any]:
    """τ² `Tool` objects → in-process SDK tools carrying the same JSON Schema.

    The handlers raise. A handler that ran would mean the SDK executed a τ² tool behind τ²'s
    back, bypassing `Environment.make_tool_call()` — the enforcement point — so it fails loudly
    rather than returning something plausible.
    """
    from claude_agent_sdk import tool as sdk_tool

    async def _never(args: dict[str, Any]) -> dict[str, Any]:
        raise AssertionError(f"the SDK executed a τ² tool: {args!r} — the defer hook did not fire")

    out = []
    for t in tools or []:
        fn = t.openai_schema["function"]
        schema = fn.get("parameters") or {"type": "object", "properties": {}}
        out.append(sdk_tool(fn["name"], fn.get("description") or fn["name"], schema)(_never))
    return out


async def _defer(_input: dict[str, Any], _tool_use_id: str | None, _ctx: Any) -> dict[str, Any]:
    return _DEFER


async def _ask(model: str, system: str, prompt: str, tools: list[Any] | None) -> Any:
    """One SDK session. Returns the `ResultMessage` plus the text blocks seen along the way."""
    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        HookMatcher,
        ResultMessage,
        TextBlock,
        create_sdk_mcp_server,
        query,
    )

    decls = _sdk_tools(tools)
    opts = ClaudeAgentOptions(
        model=model,
        system_prompt=system or None,
        # ⛔ Built-ins off. Measured: with the default set the model reaches for `ToolSearch`
        # first and the τ² tools sit behind an indirection, so the run is about a different
        # agent. `allowed_tools=[]` does NOT do this — `tools` is what restricts availability.
        tools=[],
        allowed_tools=[_PREFIX + d.name for d in decls],
        mcp_servers={_SERVER: create_sdk_mcp_server(_SERVER, tools=decls)} if decls else {},
        # ⛔ [] is isolation; None loads this machine's CLAUDE.md, skills, MCP servers and the
        # model out of ~/.claude/settings.json — D-034.
        setting_sources=[],
        max_turns=config.MAX_SDK_TURNS,
        # ⚠️ A PreToolUse hook, not `can_use_tool`: an `allowed_tools` entry auto-approves the
        # call before that callback is consulted, and the SDK says so itself
        # (`CanUseToolShadowedWarning`). The hook runs either way.
        hooks={"PreToolUse": [HookMatcher(matcher=None, hooks=[_defer])]},
    )

    text: list[str] = []
    result = None
    try:
        async for msg in query(prompt=prompt, options=opts):
            if isinstance(msg, AssistantMessage):
                text.extend(b.text for b in msg.content if isinstance(b, TextBlock))
            elif isinstance(msg, ResultMessage):
                result = msg
    except Exception:
        # ⚠️ Running out of turns is a *result*, and the SDK reports it twice: it yields a
        # ResultMessage with `subtype=error_max_turns` and then raises. Keeping the message
        # turns "the agent did not finish" into a scored row rather than a dead suite; a
        # failure with no ResultMessage is a real one and still propagates.
        if result is None:
            raise
    if result is None:
        raise RuntimeError("the SDK stream ended without a ResultMessage")
    return result, "\n".join(t for t in text if t)


# ── the seam ──────────────────────────────────────────────────────────────────────────────────


def generate(
    model: str,
    messages: list[Any],
    tools: list[Any] | None = None,
    tool_choice: str | None = None,
    call_name: str | None = None,
    **kwargs: Any,
) -> Any:
    """Drop-in for `tau2.utils.llm_utils.generate()`, backed by the Claude Agent SDK.

    ⚠️ `tool_choice` and `**kwargs` are accepted and ignored. τ² passes litellm knobs
    (`num_retries`, `temperature`) that the CLI does not take, and dropping them silently is
    wrong in the other direction — so the ones that would change a measured number are asserted
    against here rather than swallowed.
    """
    from tau2.data_model.message import AssistantMessage, ToolCall
    from tau2.utils.llm_utils import validate_message_history

    validate_message_history(messages)
    if (temp := kwargs.get("temperature")) not in (None, 0.0):
        raise ValueError(f"temperature={temp} — the CLI does not take it; the run would not be "
                         "the one the version table claims")

    system, prompt = render(messages)
    with mlflow.start_span("touchstone.llm", span_type=SpanType.LLM) as span:
        # ⚠️ OpenInference names, not `gen_ai.*` — docs/04 §2. v5's instrumentor-emitted spans
        # land in the same shape, so the scorer has one vocabulary rather than two.
        span.set_attribute("llm.model_name", model)
        span.set_attribute("touchstone.call_name", call_name or "")
        started = time.perf_counter()
        result, text = asyncio.run(_ask(model, system, prompt, tools))
        seconds = time.perf_counter() - started

        usage = usage_of(result.usage)
        deferred = result.deferred_tool_use
        if usage:
            span.set_attribute("llm.token_count.prompt", usage["prompt_tokens"])
            span.set_attribute("llm.token_count.completion", usage["completion_tokens"])
        # 🔴 Measured, never arithmetic — the SDK bills the call, we do not price it.
        span.set_attribute("touchstone.cost_usd", result.total_cost_usd or 0.0)
        span.set_attribute("touchstone.terminal_reason", result.terminal_reason or "")
        span.set_attribute("touchstone.tool_call", tool_name(deferred.name) if deferred else "")

    calls = None
    if deferred is not None:
        calls = [ToolCall(id=deferred.id, name=tool_name(deferred.name), arguments=deferred.input)]

    return AssistantMessage(
        role="assistant",
        content=text or None,
        tool_calls=calls,
        cost=result.total_cost_usd,
        usage=usage,
        raw_data={
            "session_id": result.session_id,
            "model_usage": result.model_usage,
            "terminal_reason": result.terminal_reason,
            "num_turns": result.num_turns,
            "is_error": result.is_error,
            "api_error_status": result.api_error_status,
        },
        generation_time_seconds=seconds,
    )


def rebind(home: Any, replacement: Any) -> int:
    """Bind `replacement` over `home.generate` and every `tau2.*` module already holding it.

    ⛔ **Patching `tau2.utils.llm_utils.generate` alone is a silent no-op for ten modules.** They
    do `from tau2.utils.llm_utils import generate` at import, so each holds its own reference —
    including `agent/llm_agent.py`, `user/user_simulator.py`, `evaluator/evaluator_nl_assertions.py`
    and `evaluator/hallucination_reviewer.py`, which are the four roles this exists for.

    ⚠️ **Both halves are needed and they cover different modules.** Setting `home.generate`
    covers every module imported *after* this runs, because their `from … import generate` reads
    the patched attribute; the sweep covers the ones already imported, which the assignment
    cannot reach. Measured on the smoke check: 8 references, because only 7 τ² modules were
    loaded at that point — the count is a floor on what is bound, not a census of the ten.

    ⚠️ **Split from `install()` so it can be tested without importing τ².** Same reason as
    `doctor.specimen_check` — that import costs 1.71 s against phase 1's two-second gate — and the
    same shape: the logic takes values, the wrapper does the I/O.
    """
    upstream = home.generate
    home.generate = replacement
    patched = 1
    for name, mod in list(sys.modules.items()):
        if name.startswith("tau2.") and getattr(mod, "generate", None) is upstream:
            mod.generate = replacement
            patched += 1
    return patched


def install() -> int:
    """Put this adapter behind every τ² model role. Returns how many references it replaced.

    The count comes back so a caller can assert a *value* rather than the absence of an
    exception (DEF-052) — an installer that patches nothing raises nothing.
    """
    import tau2.utils.llm_utils as llm_utils

    return rebind(llm_utils, generate)
