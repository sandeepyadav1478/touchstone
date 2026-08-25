"""The parts of the seam that are logic rather than an SDK call.

Everything here runs without importing τ² (1.71 s) or reaching the network, because phase 1's
exit gate is *"`pytest tests/unit` green, no network, under 2 seconds"*. The SDK call itself is
covered by the live smoke check, not from here.
"""

import sys
import types

from touchstone.adapter import _PREFIX, rebind, render, tool_name, usage_of


class Msg:
    """A stand-in for a τ² message — only the fields `render` reads."""

    def __init__(self, role, content=None, tool_calls=None, id=None):
        self.role, self.content, self.tool_calls, self.id = role, content, tool_calls, id


class Call:
    def __init__(self, id, name, arguments):
        self.id, self.name, self.arguments = id, name, arguments


def test_system_messages_leave_the_transcript() -> None:
    system, transcript = render([Msg("system", "the policy"), Msg("user", "hello")])
    assert system == "the policy"
    assert "the policy" not in transcript
    assert transcript == "user: hello"


def test_several_system_messages_are_joined() -> None:
    system, _ = render([Msg("system", "one"), Msg("system", "two")])
    assert system == "one\n\ntwo"


def test_a_tool_call_and_its_result_both_survive() -> None:
    """The agent loop is about tool use — a transcript that drops the result asks the model to
    answer from a conversation it cannot see."""
    _, transcript = render([
        Msg("user", "where is order W123?"),
        Msg("assistant", None, [Call("toolu_1", "get_order", {"order_id": "W123"})]),
        Msg("tool", '{"status": "delivered"}', id="toolu_1"),
    ])
    assert '<tool_call id=toolu_1 name=get_order>{"order_id": "W123"}</tool_call>' in transcript
    assert '<tool_result id=toolu_1>\n{"status": "delivered"}\n</tool_result>' in transcript


def test_text_and_a_tool_call_in_one_message_both_survive() -> None:
    _, transcript = render([Msg("assistant", "let me look", [Call("t", "get_order", {})])])
    assert "let me look" in transcript and "<tool_call id=t" in transcript


def test_the_mcp_prefix_round_trips() -> None:
    assert tool_name(_PREFIX + "get_order") == "get_order"
    assert tool_name("get_order") == "get_order", "an unprefixed name is passed through"


def test_prompt_tokens_include_the_cached_prefix() -> None:
    """⚠️ The SDK reports `input_tokens` net of cache reads. Passing that through would make a
    re-run of the same task look cheaper than its first run for no reason but caching."""
    usage = usage_of({
        "input_tokens": 2,
        "cache_read_input_tokens": 7790,
        "cache_creation_input_tokens": 3099,
        "output_tokens": 124,
    })
    assert usage == {"prompt_tokens": 10891, "completion_tokens": 124}


def test_no_usage_is_none_not_zero() -> None:
    assert usage_of(None) is None


def test_rebind_reaches_the_modules_that_imported_the_function() -> None:
    """⛔ The ten-module trap: patching the home module alone leaves every role on upstream."""

    def upstream() -> str:
        return "upstream"

    def ours() -> str:
        return "ours"

    home = types.ModuleType("tau2.utils.llm_utils")
    home.generate = upstream
    role = types.ModuleType("tau2.agent.llm_agent")
    role.generate = upstream
    bystander = types.ModuleType("tau2.runner.batch")
    bystander.generate = lambda: "someone else's generate"
    outsider = types.ModuleType("elsewhere.thing")
    outsider.generate = upstream

    added = {m.__name__: m for m in (home, role, bystander, outsider)}
    sys.modules.update(added)
    try:
        assert rebind(home, ours) == 2, "the home module and the one role holding a reference"
        assert home.generate is ours and role.generate is ours
        assert bystander.generate() == "someone else's generate", "a different function is left alone"
        assert outsider.generate is upstream, "only tau2.* is patched"
    finally:
        for name in added:
            sys.modules.pop(name, None)
