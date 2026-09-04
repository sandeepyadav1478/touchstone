"""The gauntlet: what it admits, what it refuses, and what it calls this file's own fault.

Three outcomes, and the third is the one worth a suite. A refusal is the gates working; an
`inconsistent` is the harvest disagreeing with itself, and D-086 SS D names that as the failure
its ceiling predicts. Folded together they would let a loop defect hide inside a refusal rate.

Every test drives the real `gauntlet()` end to end over a written file rather than calling
`verdict()` alone. What is being asserted is that admission WRITES -- the defect this closes is
three gates nothing called, so a suite that only exercised the pure function would reproduce it.

No corpus load and no policy read: four stub sessions and a six-line policy stand in, and the
two caches over `corpus.load` are cleared on the way in and out.
"""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from touchstone import config, suite
from touchstone.gate import admit, extract
from touchstone.gate.gauntlet import gauntlet, report_path
from touchstone.gate.predicate import Predicate, RequiresPriorTool
from touchstone.loop import corpus, harvest

AUTH = Predicate(
    rule="a lookup must follow authentication",
    source="policy.md:3",
    check=RequiresPriorTool(tool="get_order_details", prior=("get_user_details",)),
)

POLICY = "one\ntwo\nthree\nfour\nfive\nsix\n"


def session(sid: str, *, authenticated: bool, task: str = "7") -> corpus.Session:
    """One trial of one task. Fires the predicate unless it authenticates first."""
    names = ["get_user_details"] if authenticated else []
    names.append("get_order_details")
    return corpus.Session(
        id=sid,
        task_id=task,
        trial=int(sid[-1]),
        agent="a",
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


@pytest.fixture(autouse=True)
def _corpus(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """A group of four that all fire, a six-line policy, and a suite nobody else can see."""
    admit._groups.cache_clear()
    corpus._by_id.cache_clear()
    sessions = tuple(session(f"s{i}", authenticated=False) for i in range(4))
    monkeypatch.setattr(corpus, "load", lambda: sessions)
    monkeypatch.setattr(corpus, "policy_text", lambda: POLICY)
    monkeypatch.setattr(config, "REGRESSION", tmp_path / "regression")
    monkeypatch.setattr(config, "RESULTS", tmp_path / "results")
    yield
    admit._groups.cache_clear()
    corpus._by_id.cache_clear()


def row(
    sid: str = "s0", *, holds: bool = True, shape: dict[str, Any] | None = None
) -> dict[str, Any]:
    """One harvest row for a handed-over candidate, with the run that backs it."""
    handed = shape if shape is not None else extract.shape(AUTH)
    return {
        "session_id": sid,
        "exit_reason": "handed_over",
        "handed_over": handed,
        "attempts": [{"predicate": handed, "holds": holds}],
    }


def wrote(*records: dict[str, Any], label: str = "h1") -> Any:
    """Write a harvest file the way `harvest` writes one, then run the gauntlet over it."""
    out = harvest.mined_path(label)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"label": label, "written": "t", "records": list(records)}))
    return json.loads(gauntlet(label).read_text())


def test_a_candidate_that_clears_three_gates_is_written_into_the_suite() -> None:
    """The defect this closes: `admit.cleared_by` existed, was tested, and nothing called it.

    Asserted on the FILE on disk and not only on the report, because a pass that reported an
    admission it never wrote would look identical from the report alone.
    """
    report = wrote(row())
    assert report["admitted"] == 1
    assert report["verdicts"][0]["cleared_by"] == list(admit.GATES)
    assert report["verdicts"][0]["case"] == "7.json"
    assert suite.covered() == {"7"}
    assert suite.predicates() == (AUTH,)


def test_running_it_twice_admits_nothing_the_second_time() -> None:
    """`distinct` refuses on `task_id`, so a re-run is safe rather than a duplicate or a crash.

    The second pass must report a REFUSAL and not raise. `suite.write` also refuses an existing
    file, but reaching that would be the right answer by the wrong mechanism -- a crash where
    the report should carry a row saying which gate said no.
    """
    wrote(row())
    again = wrote(row())
    assert again["admitted"] == 0
    assert again["refused"] == 1
    assert again["verdicts"][0]["refused_by"] == ["distinct"]
    assert len(suite.load()) == 1


def test_a_hand_over_with_no_holding_run_behind_it_is_the_files_fault_not_a_refusal() -> None:
    """D-086 SS D's `wrong if`, checked across the serialisation boundary.

    `mine.held` asks this in memory and the edge will not emit `handed_over` without it, so a
    row that carries one anyway means the edge and the writer disagree. Counted apart from
    `refused` and it writes nothing -- the gates were never reached.
    """
    report = wrote(row(holds=False))
    assert report["inconsistent"] == 1
    assert report["refused"] == 0
    assert report["verdicts"][0]["why"] == "no holding run of the handed-over predicate"
    assert suite.load() == []


def test_a_shape_this_version_cannot_parse_costs_its_row_and_not_the_pass() -> None:
    """One bad row must not take down the rows beside it -- the harvest was paid for.

    Asserted beside a good one, because a pass that dropped everything would also report no
    admission for the bad row.
    """
    bad = extract.shape(AUTH) | {"kind": "RequiresIncantation"}
    report = wrote(row("s0"), row("s1", shape=bad))
    assert report["admitted"] == 1
    assert report["inconsistent"] == 1
    assert "RequiresIncantation" in report["verdicts"][1]["why"]


def test_only_handed_over_rows_are_in_the_report() -> None:
    """Only the rows this pass ruled on.

    The other exits are already counted by `exits` in the harvest, and a second denominator
    over a population this pass never looked at is the fused-denominator failure.
    """
    report = wrote(
        {"session_id": "s1", "exit_reason": "budget_exhausted", "attempts": []},
        {"session_id": "s2", "exit_reason": "skipped", "attempts": []},
        row("s0"),
    )
    assert report["handed_over"] == 1
    assert [v["session_id"] for v in report["verdicts"]] == ["s0"]


def test_the_three_outcomes_sum_to_the_handed_over_count() -> None:
    """Rule 4: cross-foot a table against the total stated near it, or a reader has to trust it."""
    report = wrote(row("s0"), row("s1", holds=False), row("s2"))
    assert report["handed_over"] == 3
    assert report["admitted"] + report["refused"] + report["inconsistent"] == 3


def test_a_predicate_one_trial_of_the_group_does_not_fire_on_is_refused_as_unreproducible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-084 SS D: all four trials of the (task, agent) group, not just the one it was mined on.

    The one that authenticates is the trial where the agent got it right, and a rule that fires
    on three runs of four is a rule about a run rather than about the policy.
    """
    admit._groups.cache_clear()
    corpus._by_id.cache_clear()
    mixed = (
        *(session(f"s{i}", authenticated=False) for i in range(3)),
        session("s3", authenticated=True),
    )
    monkeypatch.setattr(corpus, "load", lambda: mixed)
    report = wrote(row())
    assert report["refused"] == 1
    assert report["verdicts"][0]["refused_by"] == ["reproducible"]
    assert suite.load() == []


def test_the_case_is_keyed_on_the_session_the_row_names_and_not_on_another(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Two groups, and the row names the second. Everything downstream hangs off this lookup.

    `verdict` resolves a session id into a `Session`, and every gate then reads that object --
    `reproducible` takes its group from it and `distinct` takes the task id. A lookup that
    returned any session at all would check the wrong four trials and file the case under
    someone else's task, and with one task in the corpus that is indistinguishable from
    correct. It is the gap a single-group fixture cannot see.
    """
    admit._groups.cache_clear()
    corpus._by_id.cache_clear()
    two = (
        *(session(f"s{i}", authenticated=False) for i in range(4)),
        *(session(f"t{i}", authenticated=False, task="9") for i in range(4)),
    )
    monkeypatch.setattr(corpus, "load", lambda: two)
    report = wrote(row("t2"))
    assert report["verdicts"][0]["task_id"] == "9"
    assert report["verdicts"][0]["case"] == "9.json"
    assert suite.covered() == {"9"}


def test_the_report_names_the_gates_it_ran() -> None:
    """A pass run before a gate was added and one run after are different evidence (D-084 A.4)."""
    assert wrote(row())["gates"] == list(admit.GATES)


def test_a_report_is_written_even_when_the_harvest_handed_nothing_over() -> None:
    """An absent file and an empty pass are different findings.

    `_write` is the only place that difference is recorded, which is the same argument
    `harvest._write` makes about a harvest that picked no sessions.
    """
    report = wrote({"session_id": "s0", "exit_reason": "gave_up", "attempts": []})
    assert report_path("h1").exists()
    assert report["handed_over"] == 0
    assert report["verdicts"] == []
