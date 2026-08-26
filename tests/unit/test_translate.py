"""The τ² ↔ SDK conversions, checked against the shapes that break a run.

Values in, values out — no τ² import (1.71 s), no SDK, no network, which is why phase 1's
"`pytest tests/unit` green, under 2 seconds" gate can afford to check every one of them.
"""

from touchstone.translate import _PREFIX, render, tool_name, usage_of


class Msg:
    """A stand-in for a τ² message — only the fields `render` reads."""

    def __init__(
        self,
        role: str,
        content: str | None = None,
        tool_calls: list["Call"] | None = None,
        id: str | None = None,  # noqa: A002
    ) -> None:
        self.role, self.content, self.tool_calls, self.id = role, content, tool_calls, id


class Call:
    # `id` shadows a builtin, and stays: `render` reads τ²'s field by that name.
    def __init__(self, id: str, name: str, arguments: dict[str, object]) -> None:  # noqa: A002
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
    answer from a conversation it cannot see.
    """
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
    """The SDK reports `input_tokens` net of cache reads. Passing that through would make a
    re-run of the same task look cheaper than its first run for no reason but caching.
    """
    usage = usage_of({
        "input_tokens": 2,
        "cache_read_input_tokens": 7790,
        "cache_creation_input_tokens": 3099,
        "output_tokens": 124,
    })
    assert usage == {"prompt_tokens": 10891, "completion_tokens": 124}


def test_no_usage_is_none_not_zero() -> None:
    assert usage_of(None) is None
