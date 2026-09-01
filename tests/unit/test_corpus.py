"""The answer key's own logic, checked where a corpus run cannot check it.

`corpus.load()` has 1,712 sessions to disagree with -- 778 and 934 have to sum to it, and
`measure-tier1.py` prints the same seven excluded tasks from its own derivation. `is_anomalous`
has no such anchor: it is one boolean per session, and a rule that answered True everywhere
would still produce two sets that sum correctly.

No tau2 import, so the suite's 2 s budget is untouched: every function under test here takes
the simulation dict rather than fetching it.
"""

from touchstone.loop.corpus import _gold, is_anomalous


def sim(db: bool, actions: list[bool]) -> dict:
    """One simulation's `reward_info`, reduced to the two signals D-108 kept."""
    return {
        "reward_info": {
            "db_check": {"db_match": db},
            "action_checks": [{"action_match": a} for a in actions],
        }
    }


def test_a_failed_db_check_is_anomalous() -> None:
    """The 407. The signal that was the whole selector until docs/02 measured its blind spot."""
    assert is_anomalous(sim(db=False, actions=[True])) is True


def test_a_clean_session_is_not() -> None:
    """The control. Without it a rule that returned True always would pass every other case."""
    assert is_anomalous(sim(db=True, actions=[True, True])) is False


def test_a_passed_db_with_a_failed_action_is_anomalous() -> None:
    """The 371, and the reason the second half of the rule exists.

    These sat in the silence set while the selector was `DB` alone, so a correct predicate
    catching a process failure met them and was rejected as a false positive.
    """
    assert is_anomalous(sim(db=True, actions=[True, False])) is True


def test_a_session_with_no_action_checks_is_judged_on_db_alone() -> None:
    """`all([])` is True, so an empty list must not quietly make every session anomalous."""
    assert is_anomalous(sim(db=True, actions=[])) is False


def test_a_session_with_no_reward_info_is_anomalous() -> None:
    """The safe direction, and it is a choice rather than an accident.

    An unscored session lands in the 778, never the 934. A wrong answer there costs recall on
    one session; the same wrong answer in the clean set disqualifies a correct gate.
    """
    assert is_anomalous({}) is True


def test_gold_actions_compare_across_key_order() -> None:
    """Why `moved_tasks` normalises: a plain `==` reports 112 of 114 as moved.

    That is the comparison failing, not the corpus changing, and it would exclude the corpus
    down to nothing while looking like a legitimate freshness check.
    """
    a = [{"name": "x", "requestor": "assistant", "arguments": {"b": 1, "a": 2}}]
    b = [{"name": "x", "arguments": {"a": 2, "b": 1}}]
    assert _gold(a) == _gold(b)


def test_gold_actions_still_notice_a_real_change() -> None:
    """The normalisation is not allowed to be so loose that nothing is ever moved."""
    a = [{"name": "x", "arguments": {"a": 1}}]
    b = [{"name": "x", "arguments": {"a": 2}}]
    assert _gold(a) != _gold(b)
