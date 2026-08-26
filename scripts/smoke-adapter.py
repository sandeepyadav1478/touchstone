#!/usr/bin/env python
"""One live pass through the seam — P1.1's runnable check, extended by P1.2.

This makes real model calls and the unit suite must not. Phase 1's exit gate is
"`pytest tests/unit` green, no network, under 2 seconds", so the SDK half of `adapter.py`
is checked here instead: `uv run python scripts/smoke-adapter.py`.

It asserts the four things that would each fail silently:

1. `install()` reached more than the home module — the ten-module trap.
2. The role modules' own `generate` is ours, not upstream's.
3. A retail tool schema survives the round trip and comes back as a τ² `ToolCall` under its
   unprefixed name, so `Environment.make_tool_call()` can find it.
4. The cost is the SDK's measured `total_cost_usd`, not litellm's price table (7e-05 against a
   measured 0.0040 on the probe that settled this — docs/00 §3).
5. The `touchstone.llm` span reached the store with the model call's numbers on it —
   D-073. `doctor`'s round trip proves the store works; this proves the adapter's own span
   goes into it, which is a different claim and the one v1–v5 all rest on. Until P1.2 the span
   was written against a no-op tracer, and no assertion here would have noticed.
"""

import sys

from touchstone import adapter, config, telemetry


def main() -> int:
    print(f"telemetry.install() -> {telemetry.install()}")
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

    import mlflow

    telemetry.flush()
    spans = [
        s
        for t in mlflow.search_traces(return_type="list", max_results=5)
        for s in t.data.spans
        if s.name == "touchstone.llm"
    ]
    assert spans, "the model call left no touchstone.llm span — D-073's whole point"
    attrs = spans[0].attributes
    print(f"span        {attrs.get('llm.model_name')} "
          f"{attrs.get('llm.token_count.prompt')}/{attrs.get('llm.token_count.completion')} tok "
          f"${attrs.get('touchstone.cost_usd')} {attrs.get('touchstone.tool_call')}")
    assert attrs.get("llm.model_name") == config.MODEL
    assert attrs.get("llm.token_count.prompt") == reply.usage["prompt_tokens"]
    assert attrs.get("touchstone.cost_usd") == reply.cost
    assert attrs.get("touchstone.tool_call") == call.name

    print("\n✓ the seam holds, and it is instrumented")
    return 0


if __name__ == "__main__":
    sys.exit(main())
