#!/usr/bin/env python
"""One live pass through the seam — P1.1's runnable check.

⚠️ **This makes real model calls and the unit suite must not.** Phase 1's exit gate is
*"`pytest tests/unit` green, no network, under 2 seconds"*, so the SDK half of `adapter.py`
is checked here instead: `uv run python scripts/smoke-adapter.py`.

It asserts the four things that would each fail silently:

1. `install()` reached more than the home module — the ten-module trap.
2. The role modules' own `generate` is ours, not upstream's.
3. A retail tool schema survives the round trip and comes back as a τ² `ToolCall` under its
   *unprefixed* name, so `Environment.make_tool_call()` can find it.
4. The cost is the SDK's measured `total_cost_usd`, not litellm's price table (7e-05 against a
   measured 0.0040 on the probe that settled this — docs/00 §3).
"""

import sys

from touchstone import adapter, config


def main() -> int:
    patched = adapter.install()
    print(f"install() rebound {patched} references")
    assert patched > 1, "patched only the home module — every role still holds upstream's generate"

    import tau2.agent.llm_agent as llm_agent
    import tau2.user.user_simulator as user_simulator

    for mod in (llm_agent, user_simulator):
        assert mod.generate is adapter.generate, f"{mod.__name__} still holds upstream's generate"
    print(f"the roles resolve to the adapter: {llm_agent.__name__}, {user_simulator.__name__}")

    from tau2.data_model.message import SystemMessage, UserMessage
    from tau2.domains.retail.environment import get_environment

    tools = get_environment().get_tools()
    by_name = {t.name: t for t in tools}
    picked = [by_name[n] for n in ("get_order_details", "get_user_details") if n in by_name]
    assert picked, f"expected retail tools, got {sorted(by_name)[:5]}"
    print(f"retail exposes {len(tools)} tools; passing {[t.name for t in picked]}")

    reply = llm_agent.generate(
        model=config.MODEL,
        messages=[
            SystemMessage(role="system", content="You are a retail agent. Use the tools. Be brief."),
            UserMessage(role="user", content="Look up the details of order #W0000000."),
        ],
        tools=picked,
        call_name="smoke",
    )

    print(f"content     {reply.content!r}")
    print(f"tool_calls  {reply.tool_calls}")
    print(f"cost        {reply.cost}")
    print(f"usage       {reply.usage}")
    print(f"terminal    {reply.raw_data['terminal_reason']}")

    assert reply.tool_calls, "the model answered without calling a tool — the schemas did not land"
    call = reply.tool_calls[0]
    assert not call.name.startswith("mcp__"), f"the SDK prefix leaked into τ²: {call.name}"
    assert call.name in by_name, f"{call.name} is not a retail tool"
    assert reply.cost and reply.cost > 0, "cost is not the SDK's measured total_cost_usd"
    assert reply.usage and reply.usage["prompt_tokens"] > 0

    print("\n✓ the seam holds")
    return 0


if __name__ == "__main__":
    sys.exit(main())
