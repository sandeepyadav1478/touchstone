"""The three admission gates, and for each one the case it is there to refuse.

A gate is only worth its line if it can say no, so every check here is asserted in both
directions. D-084 SS A.1 dropped `not_a_void` rather than stub it precisely because a gate
that cannot fail reads exactly like a gate that passes, and a suite that only ever tested the
clearing half would have shipped that same shape one level up.

No corpus load and no policy read. `_groups()` and `justified()` are the two functions that
touch either, and both are substituted with a fixture of four sessions and a six-line policy --
91 MB of JSON would put the suite over its 2 s budget for facts about four sessions.
"""

from collections.abc import Callable, Iterator

import pytest

from touchstone.gate import admit
from touchstone.gate.predicate import Predicate, RequiresPriorTool
from touchstone.loop import corpus

Group = Callable[..., None]

AUTH = Predicate(
    rule="a lookup must follow authentication",
    source="policy.md:3",
    check=RequiresPriorTool(tool="get_order_details", prior=("get_user_details",)),
)


def session(sid: str, *, authenticated: bool, task: str = "1", agent: str = "a") -> corpus.Session:
    """One session that either authenticates before the lookup or does not."""
    names = ["get_user_details"] if authenticated else []
    names.append("get_order_details")
    return corpus.Session(
        id=sid,
        task_id=task,
        trial=0,
        agent=agent,
        anomalous=not authenticated,
        termination_reason="user_stop",
        messages=[
            m
            for n, name in enumerate(names)
            for m in (
                {"role": "assistant", "content": "", "tool_calls": [{"id": str(n), "name": name}]},
                {"role": "tool", "id": str(n)},
            )
        ],
    )


@pytest.fixture
def group(monkeypatch: pytest.MonkeyPatch) -> Iterator[Group]:
    """Substitute the corpus with a group of four, and hand back a way to set its trials.

    `_groups` is cached for one dictionary over 1,712 sessions, so the cache is cleared on the
    way in AND on the way out -- a fixture that only cleared on entry would leave the next test
    reading four stub sessions out of a cache it never populated.
    """

    def build(*authenticated: bool) -> None:
        admit._groups.cache_clear()
        sessions = tuple(
            session(f"s{i}", authenticated=a) for i, a in enumerate(authenticated)
        )
        monkeypatch.setattr(corpus, "load", lambda: sessions)

    yield build
    admit._groups.cache_clear()


def test_a_predicate_that_fires_on_three_of_four_trials_is_refused(group: Group) -> None:
    """The flaky case D-084 SS A.2 merged `not_flaky` into `reproducible` to catch.

    One trial of the four authenticated, so the predicate is silent there and fires on the
    other three. Clearing it would put a case in the suite that fails an agent at random, and
    somebody would spend an afternoon debugging a regression that never happened.
    """
    group(False, False, False, True)
    assert admit.reproducible(AUTH, session("t", authenticated=False)) is False


def test_a_predicate_that_fires_on_every_trial_clears(group: Group) -> None:
    """The other direction, on the same fixture, so the refusal above is about the trial."""
    group(False, False, False, False)
    assert admit.reproducible(AUTH, session("t", authenticated=False)) is True


def test_a_group_of_one_cannot_support_the_claim(group: Group) -> None:
    """k=1 is no evidence of reproducibility, so it is refused rather than trivially cleared.

    Unreachable on retail, where all 428 groups are exactly 4. It is here for the specimen
    swap D-062 leaves open, and asserted so the branch is not deleted as dead code by someone
    who checked only the current specimen.
    """
    group(False)
    assert admit.reproducible(AUTH, session("t", authenticated=False)) is False


def test_the_group_is_keyed_on_the_baseline_as_well_as_the_task() -> None:
    """Four trials of one agent, not sixteen across four.

    The corpus is four baselines and the session being admitted came from one of them. A
    predicate cleared against all sixteen would be making a claim about agents whose run had
    nothing to do with the case, and it would be refused by whichever baseline behaved
    differently -- which is a fact about that baseline, not about the rule.
    """
    admit._groups.cache_clear()
    sessions = (
        session("s0", authenticated=False, agent="a"),
        session("s1", authenticated=False, agent="a"),
        session("s2", authenticated=True, agent="b"),
        session("s3", authenticated=True, agent="b"),
    )
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(corpus, "load", lambda: sessions)
        assert admit.reproducible(AUTH, session("t", authenticated=False, agent="a")) is True
    admit._groups.cache_clear()


def test_an_already_covered_task_is_not_distinct() -> None:
    """D-083's task_id half, and the two failures it refuses.

    A suite that grows without covering more, and a pass rate that counts one failure mode
    twice.
    """
    assert admit.distinct(session("t", authenticated=False, task="7"), {"7"}) is False
    assert admit.distinct(session("t", authenticated=False, task="7"), {"8"}) is True


@pytest.mark.parametrize("source", ["policy.md:3", "retail/policy.md:3", "policy.md:6"])
def test_a_citation_that_resolves_clears(monkeypatch: pytest.MonkeyPatch, source: str) -> None:
    """Filename loose, line strict. The prompt never names the file, so the model picks it."""
    monkeypatch.setattr(corpus, "policy_text", lambda: "a\nb\nc\nd\ne\nf\n")
    assert admit.justified(Predicate(rule="r", source=source, check=AUTH.check)) is True


@pytest.mark.parametrize("source", ["the policy", "policy.md:7", "policy.md:0", "notpolicy.md:3"])
def test_a_citation_that_does_not_resolve_is_refused(
    monkeypatch: pytest.MonkeyPatch, source: str
) -> None:
    """The four `extract._predicate` lets through: it checks non-empty and nothing else.

    A six-line policy, so `policy.md:7` is a line that does not exist -- which is the case a
    reader would assume was covered by "the citation is required" and is not.
    """
    monkeypatch.setattr(corpus, "policy_text", lambda: "a\nb\nc\nd\ne\nf\n")
    assert admit.justified(Predicate(rule="r", source=source, check=AUTH.check)) is False


def test_every_gate_runs_even_once_one_has_failed(
    group: Group, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A refusal records which gates the case failed, not which was checked first.

    The candidate here is reproducible and justified and duplicates a covered task, so a
    `cleared_by` that short-circuited would return an empty tuple or a truncated one. Both
    would say the same thing about a case that failed all three, which is the ambiguity the
    set exists to remove (D-084 SS A.4).
    """
    group(False, False, False, False)
    monkeypatch.setattr(corpus, "policy_text", lambda: "a\nb\nc\nd\ne\nf\n")
    target = session("t", authenticated=False, task="1")
    assert admit.cleared_by(AUTH, target, {"1"}) == ("reproducible", "justified")
    assert admit.cleared_by(AUTH, target, set()) == admit.GATES


def test_admission_is_all_three() -> None:
    """Derived from GATES, so `not_a_void` returning at P2.4 does not need this line edited."""
    assert admit.admitted(admit.GATES) is True
    assert admit.admitted(("reproducible", "justified")) is False
