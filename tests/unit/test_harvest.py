"""What a harvest keeps, and what it keeps when the window shuts on it.

`harvest()` itself is three model roles behind a span, so what is checkable without quota is
the bookkeeping either side: which sessions get picked, what a record looks like written down,
and that a run cut short by the quota still writes the sessions it already paid for.

That last one is the reason this file exists. The five-hour window REJECTS rather than bills
(D-001), so a harvest that raised its way out would discard work that cost a window and cannot
be re-run for free.
"""

import json
from pathlib import Path

import pytest

from touchstone import telemetry
from touchstone.gate.extract import parse
from touchstone.gate.predicate import Predicate, RequiresPriorTool
from touchstone.loop import budget, corpus, harvest, mine

AUTH = Predicate(
    rule="a lookup must follow authentication",
    source="policy.md:10",
    check=RequiresPriorTool(tool="get_order_details", prior=("get_user_details",)),
)


def session(sid: str) -> corpus.Session:
    """A session with nothing in it. `pick` reads ids and never messages."""
    return corpus.Session(
        id=sid,
        task_id="1",
        trial=0,
        agent="stub",
        anomalous=False,
        termination_reason="user_stop",
        messages=[],
    )


@pytest.fixture
def three(monkeypatch: pytest.MonkeyPatch) -> None:
    """A corpus of three, so nothing here loads the 91 MB the real one is."""
    loaded = tuple(session(sid) for sid in ("a", "b", "c"))
    monkeypatch.setattr(corpus, "load", lambda: loaded)


@pytest.mark.usefixtures("three")
def test_the_limit_takes_the_first_n_in_corpus_order() -> None:
    """Order, not just the count.

    First-N over a corpus sorted by file means one agent's early tasks, and a `pick` that
    reordered would make two harvests incomparable while looking identical in the file.
    """
    assert [s.id for s in harvest.pick(2)] == ["a", "b"]


@pytest.mark.usefixtures("three")
def test_named_sessions_ignore_the_limit() -> None:
    """Naming sessions is how failed ones get re-worked.

    A limit that still applied would silently drop every name past it, which reads as the loop
    skipping them rather than as never having been asked.
    """
    assert [s.id for s in harvest.pick(1, ("a", "c"))] == ["a", "c"]


def test_a_record_is_written_with_every_attempt_behind_it() -> None:
    """D-082 requires every attempt under an unmineable, and the shape has to survive the trip.

    A row that recorded a rule but not its check could not be re-run against anything, so the
    predicate is round-tripped through `parse` rather than compared as a dictionary.
    """
    record = mine.Record(session_id="a", dispatches=2, gave_up=True, rule_searched_for="none")
    record.attempts.append(mine.Attempt(AUTH, fired_on_target=True, counterexample="c9"))
    written = json.loads(json.dumps(harvest.row(record)))

    assert written["gave_up"] is True
    assert written["rule_searched_for"] == "none"
    assert len(written["attempts"]) == 1
    assert written["attempts"][0]["counterexample"] == "c9"
    assert parse(json.dumps(written["attempts"][0]["predicate"])) == AUTH


@pytest.mark.usefixtures("three")
def test_the_quota_shutting_keeps_what_it_already_paid_for(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The window rejects rather than bills, so worked sessions cannot be bought back.

    Two things are asserted, and the second is the one that matters: the finished row is in
    the file, and `stopped_early` says the harvest was cut short. A truncated harvest that
    looked complete is worse than one that raised, because the count it reports is wrong.
    """
    worked = []

    def one(s: corpus.Session) -> mine.Record:
        if s.id == "b":
            raise budget.QuotaExhaustedError("the window is shut")
        worked.append(s.id)
        return mine.Record(session_id=s.id, exit_reason="skipped")

    monkeypatch.setattr(harvest, "_work", one)
    monkeypatch.setattr(telemetry, "install", lambda: "")
    monkeypatch.setattr(telemetry, "flush", lambda: None)
    monkeypatch.setattr(harvest, "mined_path", lambda label: tmp_path / f"{label}.json")

    written = json.loads(harvest.harvest("t", 3).read_text())
    assert worked == ["a"]
    assert [r["session_id"] for r in written["records"]] == ["a"]
    assert written["stopped_early"] == "the window is shut"
    assert written["exits"] == {"skipped": 1}


@pytest.mark.usefixtures("three")
def test_one_bad_model_answer_costs_its_session_and_not_the_harvest(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The quota stops the harvest; nothing else does, and the difference is where the money is.

    The error raised here is the real one: `parse` is a trust boundary and RAISES on an answer
    it cannot read, so a curator emitting one bad object is the ordinary case rather than the
    exotic one. Before this, that on session `b` discarded `a` — which cost a five-hour window
    that rejects rather than bills, so it could not be bought back.

    `exit_reason` is null on the failed row and stays null: D-093 §C gives that field to the
    graph's edge, and a session that fell over never reached one. It is counted under `failed`.
    """
    def one(s: corpus.Session) -> mine.Record:
        if s.id == "b":
            parse("the curator narrated instead of answering")
        return mine.Record(session_id=s.id, exit_reason="skipped")

    monkeypatch.setattr(harvest, "_work", one)
    monkeypatch.setattr(telemetry, "install", lambda: "")
    monkeypatch.setattr(telemetry, "flush", lambda: None)
    monkeypatch.setattr(harvest, "mined_path", lambda label: tmp_path / f"{label}.json")

    written = json.loads(harvest.harvest("t", 3).read_text())
    assert [r["session_id"] for r in written["records"]] == ["a", "b", "c"]
    assert written["stopped_early"] is None, "one bad answer is not the window shutting"
    assert written["exits"] == {"skipped": 2, "failed": 1}

    bad = written["records"][1]
    assert bad["exit_reason"] is None
    assert bad["error"].startswith("ValueError: no JSON object")


@pytest.mark.usefixtures("three")
def test_the_file_is_on_disk_before_the_harvest_ends(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A Ctrl-C reaches neither `except`, so writing once at the end would lose the lot.

    Asserted by reading the file from inside the third session rather than by simulating a
    kill: if `a` and `b` are already on disk while `c` is still being worked, then whatever
    ends the process next cannot take them. Same argument as the quota test above — the
    window rejects rather than bills, so a paid session is not re-buyable.
    """
    seen: list[list[str]] = []
    out = tmp_path / "t.json"

    def one(s: corpus.Session) -> mine.Record:
        got = json.loads(out.read_text()) if out.exists() else {"records": []}
        seen.append([r["session_id"] for r in got["records"]])
        return mine.Record(session_id=s.id, exit_reason="skipped")

    monkeypatch.setattr(harvest, "_work", one)
    monkeypatch.setattr(telemetry, "install", lambda: "")
    monkeypatch.setattr(telemetry, "flush", lambda: None)
    monkeypatch.setattr(harvest, "mined_path", lambda _: out)

    harvest.harvest("t", 3)
    assert seen == [[], ["a"], ["a", "b"]]
