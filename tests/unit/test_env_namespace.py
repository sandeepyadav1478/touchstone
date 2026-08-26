"""Every environment variable this project READS must be `TOUCHSTONE_*`.

The two bare names are asserted ABSENT rather than consumed, and that assertion only
means something under the exact spelling the vendor's SDK reads — namespacing
`ANTHROPIC_API_KEY` would turn `doctor`'s one reason for existing into a tautology.

This exists because there is a system-wide litellm under systemd on this machine and a
config value silently supplied by a neighbouring tool is the failure with no symptom.
`OLLAMA_URL` was that shape: not ollama's convention (`OLLAMA_HOST`) and not ours either.
"""

import ast
import pathlib

SRC = pathlib.Path(__file__).resolve().parents[2] / "src" / "touchstone"

# Bare by design. A name here is one we check for the ABSENCE of, never one we consume.
ASSERTED_ABSENT = {"ANTHROPIC_API_KEY", "CEREBRAS_API_KEY"}

# Written, not read — a third party's own opt-out, whose name is not ours to choose.
# ⚠️ `MLFLOW_ALLOW_FILE_STORE` is not an opt-out of telemetry but an opt-IN to a backend
# MLflow deprecates: `mlflow-skinny` 3.15.1 refuses the file store without it, and its
# suggested alternative (`sqlite:///`) is not registered in skinny at all. Same category
# for this guard's purpose — a vendor's spelling, set by us, read by them.
WRITTEN_NOT_READ = {"DEEPEVAL_TELEMETRY_OPT_OUT", "MLFLOW_ALLOW_FILE_STORE"}


def _is_environ(node: ast.AST) -> bool:
    """`os.environ` or a bare `environ` — the RECEIVER, not just the method name.

    🔴 **This check was missing until 2026-08-26 and the detector matched any `.get("UPPER")`**
    (DEF-070). `loop/score.py`'s `reward_breakdown.get("DB")` is a dict read, and the guard
    reported it as an un-namespaced environment variable. ⚠️ **A method name is not a call to
    a particular object** — same shape as *a substring is not a symbol*, one level up the tree.
    """
    return (isinstance(node, ast.Attribute) and node.attr == "environ") or (
        isinstance(node, ast.Name) and node.id == "environ"
    )


def _reads_env(fn: ast.AST) -> bool:
    """True when this call target actually reads the environment."""
    if isinstance(fn, ast.Attribute) and fn.attr in {"get", "setdefault"}:
        return _is_environ(fn.value)
    if isinstance(fn, ast.Attribute) and fn.attr == "getenv":
        return isinstance(fn.value, ast.Name) and fn.value.id == "os"
    return isinstance(fn, ast.Name) and fn.id == "getenv"


def _env_names_read() -> set[tuple[str, str]]:
    """(file, var) for every literal name read from the environment, by any of its spellings.

    ⚠️ **`os.environ["X"]` is covered too** — it was not before, and it is the commonest form.
    The old `arg.isupper()` filter is gone with it: it was standing in for the receiver check,
    and it would have let a lowercase read through in the one direction a guard must not fail.
    """
    found = set()
    for path in SRC.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            literal = None
            if isinstance(node, ast.Subscript) and _is_environ(node.value):
                literal = node.slice
            elif isinstance(node, ast.Call) and node.args and _reads_env(node.func):
                literal = node.args[0]
            if isinstance(literal, ast.Constant) and isinstance(literal.value, str):
                found.add((path.name, literal.value))
    return found


def test_the_detector_reads_the_receiver_not_the_method_name() -> None:
    """⛔ Written after the guard flagged a dict. A check nobody has watched fail is not a check."""
    import textwrap

    def names(src: str) -> set[str]:
        # Same narrowing as `_env_names_read`: a looser probe agrees for the wrong reason.
        found = set()
        for node in ast.walk(ast.parse(textwrap.dedent(src))):
            literal: ast.expr | None = None
            if isinstance(node, ast.Subscript) and _is_environ(node.value):
                literal = node.slice
            elif isinstance(node, ast.Call) and node.args and _reads_env(node.func):
                literal = node.args[0]
            if isinstance(literal, ast.Constant) and isinstance(literal.value, str):
                found.add(literal.value)
        return found

    assert names('breakdown.get("DB")') == set(), "a dict is not the environment"
    assert names('cfg.getenv("X")') == set(), "nor is anything else that owns a method by that name"
    assert names('os.environ.get("A"); os.getenv("B"); os.environ["C"]') == {"A", "B", "C"}
    assert names('environ.get("D")') == {"D"}, "the bare-import spelling still counts"


def test_every_consumed_variable_is_namespaced() -> None:
    stray = {
        (f, v)
        for f, v in _env_names_read()
        if not v.startswith("TOUCHSTONE_") and v not in ASSERTED_ABSENT | WRITTEN_NOT_READ
    }
    assert not stray, (
        f"un-namespaced environment reads: {sorted(stray)}. "
        "Prefix with TOUCHSTONE_, or add it to ASSERTED_ABSENT with the reason it must stay bare."
    )


def test_the_guard_can_actually_see_a_variable() -> None:
    """An empty scan passes the test above vacuously — rule 2, absence needs evidence."""
    assert ("config.py", "TOUCHSTONE_OLLAMA_URL") in _env_names_read()
