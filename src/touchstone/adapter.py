"""P1.1 — the single seam: the Claude Agent SDK behind τ²'s `generate()`.

`tau2.utils.llm_utils.generate()` (`llm_utils.py:355`) is the one chokepoint every live τ² model
role passes through — agent, user simulator, NL-assertion evaluator, hallucination reviewer — so
one adapter dispatching on `model` covers all four. No fork of τ²: the pin stays readable as
upstream, which is what makes "we did not write the benchmark" checkable by a stranger.

Three things about this seam that are not obvious from the code at it:

    where   `generate()`, not the litellm import at `llm_utils.py:15`. Replacing `completion`
            leaves more of τ² running, but `generate()` then overwrites cost via
            `get_response_cost()` — measured 7e-05 against the SDK's 0.0040 for the same call,
            a factor of 58 and wrong in the flattering direction, because prompt caching is
            invisible to arithmetic. docs/00 §3 requires cost to be measured, so the seam sits
            above the line that recomputes it.
    state   stateless, as a stated ceiling. τ² passes the whole history every call, so each
            call is one fresh SDK session with the transcript rendered into the prompt; the
            SDK's defer→resume path does not take a caller-supplied `tool_result` back. Costs
            native assistant/tool turns, buys nothing to key sessions on and no way for
            adapter state to drift from τ²'s.
    span    P1.1 is not done without it (D-073) — the only point every version shares, and no
            instrumentor can emit it, since the SDK shells out to the CLI. `mlflow.start_span()`
            rather than the OTel SDK: D-074 deleted the OTel SDK, so `trace.get_tracer()` still
            resolves via MLflow's transitive `opentelemetry-api` and returns a silent no-op
            (DEF-052). `telemetry.install()` makes it land; `doctor` round-trips it.

What is here is the half that needs the SDK or a live process. The value conversions τ² and the
SDK disagree about live in `translate`, which imports neither.
"""

from __future__ import annotations

import asyncio
import sys
import time
from typing import TYPE_CHECKING, Any

import mlflow
from mlflow.entities import SpanType

from touchstone import config
from touchstone.translate import _PREFIX, _SERVER, render, tool_name, usage_of

if TYPE_CHECKING:
    # Type-only, and the invariant test knows the difference. `if TYPE_CHECKING:` never
    # executes, so this is not the runtime SDK reach that `test_invariants` polices — it is the
    # SDK's own hook contract, used so `_defer` is checked against the signature the SDK will
    # actually call it with rather than against `Any`. The union is ten input types wide; naming
    # it `Any` was hiding a real mismatch, not simplifying one.
    from claude_agent_sdk import HookContext, HookInput, HookJSONOutput

    # `SyncHookJSONOutput` is not re-exported from the package root — only from `.types`.
    # Three of the four names sit at the root and the fourth does not, which is the kind of
    # asymmetry a `TYPE_CHECKING` block hides until the checker runs.
    from claude_agent_sdk.types import SyncHookJSONOutput

# Annotated, so the SDK's own `Literal`s check it. As a bare dict literal this was
# `dict[str, dict[str, str]]` and nothing verified the two strings that matter: `hookEventName`
# must be exactly `"PreToolUse"` and `permissionDecision` must be one of four values — `"defer"`
# is one of them (`types.py:420`), which is the answer to the obvious question about this payload.
# A typo in either would have reached the SDK at runtime as a silently ignored hook.
_DEFER: SyncHookJSONOutput = {
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "defer",
        "permissionDecisionReason": "τ² owns tool execution — Environment.make_tool_call()",
    }
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


async def _defer(_input: HookInput, _tool_use_id: str | None, _ctx: HookContext) -> HookJSONOutput:
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
        # Built-ins off. Measured: with the default set the model reaches for `ToolSearch`
        # first and the τ² tools sit behind an indirection, so the run is about a different
        # agent. `allowed_tools=[]` does not do this — `tools` is what restricts availability.
        tools=[],
        allowed_tools=[_PREFIX + d.name for d in decls],
        mcp_servers={_SERVER: create_sdk_mcp_server(_SERVER, tools=decls)} if decls else {},
        # [] is isolation; None loads this machine's CLAUDE.md, skills, MCP servers and the
        # model out of ~/.claude/settings.json — D-034.
        setting_sources=[],
        max_turns=config.MAX_SDK_TURNS,
        # A PreToolUse hook, not `can_use_tool`: an `allowed_tools` entry auto-approves the
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
        # Running out of turns is a result, and the SDK reports it twice: it yields a
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

    `tool_choice` and `kwargs` are accepted and ignored. τ² passes litellm knobs
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
        # OpenInference names, not `gen_ai.*` — docs/04 §2. v5's instrumentor-emitted spans
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
        # Measured, never arithmetic — the SDK bills the call, we do not price it.
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

    Patching `home.generate` alone is a silent no-op for ten modules: they each did
    `from tau2.utils.llm_utils import generate` at import and hold their own reference. Both
    halves are needed — the assignment catches modules imported after this, the sweep catches
    the ones already loaded. The returned count is a floor on what is bound, not a census.

    Split from `install()` so it can be tested without importing τ². Same reason as
    `doctor.specimen_check` — that import costs 1.71 s against phase 1's two-second gate — and the
    same shape: the logic takes values, the wrapper does the I/O.
    """
    upstream = home.generate
    home.generate = replacement
    patched = 1
    for name, mod in list(sys.modules.items()):
        if name.startswith("tau2.") and getattr(mod, "generate", None) is upstream:
            # `setattr`, not `mod.generate = …`: `ModuleType` declares no such attribute, so
            # the assignment form is a type error rather than a style choice. Rebinding a name in
            # someone else's already-imported module is dynamic by nature; this is the spelling
            # that says so.
            setattr(mod, "generate", replacement)  # noqa: B010
            patched += 1
    return patched


def install() -> int:
    """Put this adapter behind every τ² model role. Returns how many references it replaced.

    The count comes back so a caller can assert a value rather than the absence of an
    exception (DEF-052) — an installer that patches nothing raises nothing.
    """
    import tau2.utils.llm_utils as llm_utils

    return rebind(llm_utils, generate)
