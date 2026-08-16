"""The one piece of `doctor` that is logic rather than I/O — and the one that had the bug.

`model_usage` can carry more than one model, and in isolation mode the CLI's housekeeping
call on haiku sorts *first*. Reading position instead of name reported a correctly pinned
model as a failed pin (D-035). These two cases are that bug, frozen.
"""

from touchstone import config
from touchstone.doctor import model_check

HOUSEKEEPING = "claude-haiku-4-5-20251001"


def test_pinned_model_is_found_even_when_it_is_not_first():
    usage = {HOUSEKEEPING: {"outputTokens": 11}, config.MODEL: {"outputTokens": 4}}
    check = model_check(usage, 0.0036)
    assert check.status == "pass"
    assert HOUSEKEEPING in check.note  # reported, not hidden — it is real spend


def test_only_the_pinned_model_needs_no_note():
    check = model_check({config.MODEL: {"outputTokens": 4}}, 0.0030)
    assert check.status == "pass"
    assert check.note == ""


def test_a_pin_that_did_not_take_fails():
    check = model_check({HOUSEKEEPING: {"outputTokens": 11}}, 0.0006)
    assert check.status == "fail"


def test_no_model_at_all_fails():
    assert model_check({}, 0.0).status == "fail"
