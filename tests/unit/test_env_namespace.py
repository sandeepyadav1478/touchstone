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
WRITTEN_NOT_READ = {"DEEPEVAL_TELEMETRY_OPT_OUT"}


def _env_names_read() -> set[tuple[str, str]]:
    """(file, var) for every literal name passed to os.environ.get / os.getenv."""
    found = set()
    for path in SRC.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            fn = node.func
            name = (
                fn.attr if isinstance(fn, ast.Attribute)
                else fn.id if isinstance(fn, ast.Name) else ""
            )
            if name in {"get", "getenv", "setdefault"} and isinstance(node.args[0], ast.Constant):
                arg = node.args[0].value
                if isinstance(arg, str) and arg.isupper():
                    found.add((path.name, arg))
    return found


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
