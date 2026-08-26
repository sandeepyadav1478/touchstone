"""The invariants of [docs/01] §6 that can be asserted without running anything — P1.4.

⛔ **Static, and deliberately so.** The invariants that need a run (3, 8, 15, 16) need machinery
that does not exist yet, and a test that imports τ² costs 1.71 s against a 2-second gate for the
whole suite. What is here instead is the half that a *source* can answer: **which module is
allowed to reach a model, and which fields our code may never read.** Both fail on the edit that
would break them rather than on the run that would reveal it.

⚠️ **`ast`, never `grep`.** A substring is not a symbol — `evaluation_criteria` appears in this
docstring, and a text scan would flag the file that enforces the rule. The parser sees names.

Coverage of §6 from here, stated so the gaps are visible rather than implied:

| invariant | here? |
|---|---|
| 1 — the agent never sees the answer key | ✅ at *our* boundary — `test_no_module_reads_the_answer_key` |
| 7 — the task file is never modified | ⛔ elsewhere: `scripts/freeze-benchmark.py --check`, plus `test_benchmark_freeze.py` |
| 3, 8, 15, 16 | ⛔ need a run; they land with `loop/score.py` (P1.5) and the gates (phase 2) |
| 11, 12 | ⛔ vacuous — the regression manifest is empty until the gauntlet (D-030) |
| 13, 14 | ⛔ need specialist spans; un-retired by D-071, not yet buildable |
| **new** — no model appears in any gating path | ✅ `test_only_the_seam_and_the_doctor_may_reach_a_model` |
"""

import ast
from collections.abc import Iterator
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src" / "touchstone"

# ⛔ rglob, not `SRC.glob("*.py")` — a glob is not a tree, and `loop/` arrived in P1.5.
#
# 🔴 **Keyed on the dotted path, not `p.stem` — the stem collided the day `loop/` landed**
# (DEF-069). Two `__init__.py` files have the same stem, so a dict keyed on it silently kept one
# and dropped the other: 8 files on disk, 7 keys, and every assertion below simply stopped seeing
# a module. **A dict comprehension over a tree is a silent deduplicator**, and the count check on
# the next line is the cheap thing that would have caught it on day one.
MODULES = {
    str(p.relative_to(SRC).with_suffix("")).replace("/", "."): ast.parse(p.read_text(), p.name)
    for p in sorted(SRC.rglob("*.py"))
}
assert len(MODULES) == len(list(SRC.rglob("*.py"))), "a module was swallowed by a key collision"


def _runtime_nodes(node: ast.AST) -> Iterator[ast.AST]:
    """Walk `node`, skipping the body of any `if TYPE_CHECKING:` block.

    ⛔ **A `TYPE_CHECKING` import is not a reach.** `config.py` names `SettingSource` under one,
    and that block never executes — the annotation is a string at runtime. Adding `config` to the
    allowed set below would have made this test pass and would have been a **false statement about
    the design**: config would then be permitted a real SDK import forever, silently. ⚠️ The
    cheapest way to fix a failing invariant is to widen it, which is the one repair that cannot be
    detected later.
    """
    yield node
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.If) and "TYPE_CHECKING" in ast.dump(child.test):
            for orelse in child.orelse:
                yield from _runtime_nodes(orelse)
            continue
        yield from _runtime_nodes(child)


def imported(tree: ast.AST) -> set[str]:
    """Every top-level package name this module imports **at runtime**.

    ⚠️ **The walk matters.** Both places that reach the SDK do it *inside a function* — deferred
    so `doctor` can report that the import itself failed, and so the 1.7 s is not paid at
    startup. A check that read only module-scope imports would pass on every one of them.

    Args:
        tree: A parsed module.

    Returns:
        Root package names, e.g. `claude_agent_sdk` for `from claude_agent_sdk import tool`.
    """
    names: set[str] = set()
    for node in _runtime_nodes(tree):
        if isinstance(node, ast.Import):
            names |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            names.add(node.module.split(".")[0])
    return names


def attributes(tree: ast.AST) -> set[str]:
    """Every attribute name read anywhere in the module — `x.foo` yields `foo`."""
    return {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}


def strings(tree: ast.AST) -> set[str]:
    """Every string literal in the module."""
    return {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)}


def test_only_the_seam_and_the_doctor_may_reach_a_model() -> None:
    """The invariant the specimen swap created — ⛔ no model appears in any gating path.

    Set equality, not a subset check: a third module reaching the SDK fails here and has to be
    argued for out loud. `adapter` is the single seam (D-095); `doctor` asserts the pin took,
    which is diagnostics and gates nothing.
    """
    reach = {name for name, tree in MODULES.items() if "claude_agent_sdk" in imported(tree)}
    assert reach == {"adapter", "doctor"}, (
        f"{reach - {'adapter', 'doctor'}} reaches a model. The gate is mechanical — "
        "reward_breakdown['DB'] — and a model anywhere near it makes the number unfalsifiable"
    )


def test_the_model_pins_live_in_config_and_nowhere_else() -> None:
    """One place to change a pin, and one place to read one off.

    ⚠️ A hardcoded model *string* is the version of the failure above that no import check sees:
    it needs no new import, because the module that calls the SDK is already allowed to.
    """
    for name, tree in MODULES.items():
        if name in {"config", "__init__"}:
            continue
        hardcoded = {s for s in strings(tree) if s.startswith(("claude-", "anthropic/", "openai/"))}
        assert not hardcoded, f"{name}.py hardcodes {hardcoded} — the pins live in config.py"


def test_no_module_reads_the_answer_key() -> None:
    """Invariant 1, asserted where we can actually break it.

    ⛔ Upstream already keeps the key out of the agent's context; what this repo can do wrong is
    *merge* them — read a task's grading fields and let them reach a prompt. τ² hands our seam
    `messages`, so any code here touching these names has gone and fetched the key.
    """
    banned = {"evaluation_criteria", "user_scenario", "reward_basis"}
    for name, tree in MODULES.items():
        assert not (found := attributes(tree) & banned), (
            f"{name}.py reads {found} — that is the answer key, and the seam is handed messages"
        )


def test_the_answer_key_check_can_fail() -> None:
    """⛔ A check nobody has watched fail is a check nobody has watched.

    Two of the four tests above are absence assertions, and an absence assertion passes just as
    happily when the thing that would detect the presence is broken. This runs the detector
    against a positive case.
    """
    assert attributes(ast.parse("task.evaluation_criteria")) == {"evaluation_criteria"}
    assert imported(ast.parse("def f():\n    from claude_agent_sdk import tool")) == {"claude_agent_sdk"}
    type_only = "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    from claude_agent_sdk import X"
    assert imported(ast.parse(type_only)) == {"typing"}, "a TYPE_CHECKING import is not a reach"
    assert strings(ast.parse('M = "claude-opus-5"')) == {"claude-opus-5"}
