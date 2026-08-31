"""The two pieces of `measure-shadow.py` a corpus run cannot check for itself.

The script's counts have the corpus to disagree with: 778 and 934 have to sum to 1,712, and the
confirmation row's 44 has to match what `measure-predicate.py` prints independently. Its two
helpers have no such anchor. `tier1_fires` returned False on every one of the 1,712, which is
the right answer -- tier 1's 37 accepted firings all sit in the tasks D-080 excluded -- but a
broken filter returns False on everything too, and the run cannot tell those apart.

No tau2 import. The script defers `measure-tier1` and `measure-predicate` into `main()`, so
importing the file is free and the specimen's 1.71 s is never paid.
"""

import importlib.util
from collections import Counter

from touchstone.config import ROOT
from touchstone.gate.tier1 import EXCHANGE

_spec = importlib.util.spec_from_file_location(
    "measure_shadow", ROOT / "scripts" / "measure-shadow.py"
)
# Two asserts, not one composite, so a renamed script says which half is missing (D-100).
assert _spec is not None, "scripts/measure-shadow.py is not where this test expects it"
assert _spec.loader is not None, "scripts/measure-shadow.py resolved without a loader"
shadow = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(shadow)


def session(error: bool) -> list[dict]:
    """One self-swap exchange -- a tier-1 violation -- and the environment's answer to it."""
    call = {"id": "c1", "name": EXCHANGE, "arguments": {"item_ids": ["1"], "new_item_ids": ["1"]}}
    return [
        {"role": "assistant", "content": "", "tool_calls": [call]},
        {"role": "tool", "id": "c1", "error": error},
    ]


def test_an_accepted_violation_fires() -> None:
    """The positive control. Without it a filter that returns False always would look correct."""
    assert shadow.tier1_fires(session(error=False)) is True


def test_a_refused_violation_does_not() -> None:
    """The accepted filter, and it is load-bearing: no write happened, so nothing was prevented.

    Counting it would inflate recall and precision at once, since the same firing lands in
    whichever half of the score the session's own outcome puts it.
    """
    assert shadow.tier1_fires(session(error=True)) is False


def test_a_call_with_no_result_at_all_does_not() -> None:
    """A truncated session. `error=True` is the default, so an unanswered call is not a firing."""
    assert shadow.tier1_fires(session(error=False)[:1]) is False


def test_a_legal_exchange_does_not() -> None:
    """Tier 1 has no opinion here, so the accepted filter never gets asked."""
    msgs = session(error=False)
    msgs[0]["tool_calls"][0]["arguments"] = {"item_ids": ["1"], "new_item_ids": ["2"]}
    assert shadow.tier1_fires(msgs) is False


def test_the_score_row_carries_both_populations() -> None:
    """Rule 1 asserted rather than trusted: neither ratio may print without its denominator."""
    row = shadow.score(Counter({"g|tp": 36, "g|fp": 44}), "g", 778)
    assert "36/778" in row
    assert "36/80" in row
    assert "4.6%" in row
    assert "45.0%" in row


def test_a_gate_that_fires_on_nothing_gets_no_ratio() -> None:
    """0/0 is not 0% precision. Printing one would be a number about no sessions at all."""
    row = shadow.score(Counter(), "g", 778)
    assert "SILENT" in row
    assert "%" not in row
