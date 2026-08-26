"""Translation across the seam: τ²'s data model ↔ the SDK's, in both directions.

Separate from `adapter` because none of it needs the SDK, τ² or a network — it is values in,
values out, so the shapes that break a run are pinned by a unit test that runs in milliseconds.
Three conversions, one per thing τ² and the SDK disagree about:

    render      τ² message history → an SDK `system_prompt` plus one rendered transcript
    tool_name   the SDK's namespaced tool name → the bare name τ² registered
    usage_of    the SDK's usage dict → the two counts τ²'s `get_response_usage()` reads
"""

from __future__ import annotations

import json
from typing import Any

# The SDK namespaces in-process MCP tools as ``mcp__<server>__<name>``. τ²'s tool names have to
# round-trip through that, so the prefix is stripped on the way back rather than guessed at.
_SERVER = "tau2"
_PREFIX = f"mcp__{_SERVER}__"


def render(messages: list[Any]) -> tuple[str, str]:
    """Split τ²'s history into an SDK ``system_prompt`` and one rendered transcript.

    Tool calls and their results are rendered as tags rather than dropped: τ²'s agent loop is
    about tool use, and a transcript that loses the results asks the model to answer from a
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

    `prompt_tokens` folds the cache reads back in. The SDK reports `input_tokens` net of
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
