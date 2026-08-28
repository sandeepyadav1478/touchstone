"""Tier 1's checks, and the invariant that its path can never consult a model."""

from __future__ import annotations

import ast
from pathlib import Path

from touchstone.gate.tier1 import EXCHANGE, check

ROOT = Path(__file__).resolve().parents[2]

# The markers a model call leaves in this codebase. `litellm` is here because the whole
# adapter exists to keep it out of the loop, so its name reaching the gating path is the
# same defect as an SDK import.
MODEL_CALLS = ("claude_agent_sdk", "litellm", "anthropic", "ClaudeSDKClient", "acompletion")


def test_an_item_exchanged_for_itself_is_a_violation() -> None:
    found = check(EXCHANGE, {"item_ids": ["111"], "new_item_ids": ["111"]})
    assert [v.constraint for v in found] == ["self_swap"]
    assert found[0].rule == "retail/policy.md:132"


def test_a_different_product_option_is_not() -> None:
    assert check(EXCHANGE, {"item_ids": ["111"], "new_item_ids": ["222"]}) == []


def test_each_bad_pair_is_reported_separately() -> None:
    """A caller that only reports the first violation understates a degenerate call."""
    found = check(EXCHANGE, {"item_ids": ["1", "2", "3"], "new_item_ids": ["1", "9", "3"]})
    assert len(found) == 2
    assert "1" in found[0].detail
    assert "3" in found[1].detail


def test_another_tool_is_not_tier_1s_business() -> None:
    assert check("return_delivered_order_items", {"item_ids": ["1"], "new_item_ids": ["1"]}) == []


def test_a_malformed_call_returns_no_opinion_rather_than_raising() -> None:
    """The gate sees calls the environment is about to reject, so raising here crashes a run.

    A length mismatch is the environment's error to report — tier 1 truncates and stays quiet
    rather than duplicating a message the tool already produces.
    """
    assert check(EXCHANGE, {}) == []
    assert check(EXCHANGE, {"item_ids": "111", "new_item_ids": "111"}) == []
    assert check(EXCHANGE, {"item_ids": [None], "new_item_ids": [None]}) == []
    assert check(EXCHANGE, {"item_ids": ["1", "2"], "new_item_ids": ["1"]}) != []


def test_no_model_in_gating_path() -> None:
    """Every touchstone module reachable from `gate/tier1.py` is free of a model call.

    The phase-2 exit gate asks for this by name. It is the negative control's twin and it is
    cheaper: P2.5 proves a gate CAN block, this proves the blocking path cannot consult a
    model to decide whether to. Walked through imports rather than asserted about one file,
    because the way this breaks is a helper three modules down.

    Two roots, not one. `predicate.py` is the tier-2 evaluator and nothing reached it from
    here — it imports `tier1`, so the walk ran the wrong way down the only edge between them
    and the file that decides tier 2 was never covered. Found while widening
    `test_only_the_seam_and_the_doctor_may_reach_a_model` for `gate.extract` (D-107): the
    argument for letting a model propose is that nothing lets one decide, and that half was
    unasserted.
    """
    seen: set[Path] = set()
    gate = ROOT / "src" / "touchstone" / "gate"
    queue = [gate / "tier1.py", gate / "predicate.py"]
    while queue:
        path = queue.pop()
        if path in seen or not path.exists():
            continue
        seen.add(path)
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                assert not name.startswith(MODEL_CALLS), f"{path.name} imports {name}"
                if name.startswith("touchstone"):
                    rel = name.replace(".", "/")
                    queue += [ROOT / "src" / f"{rel}.py", ROOT / "src" / rel / "__init__.py"]
        for marker in MODEL_CALLS:
            assert marker not in path.read_text(), f"{path.name} mentions {marker}"

    assert len(seen) >= 2
