"""P3.5 -- the gauntlet: a finished candidate meets D-084's three gates, and a case is written.

D-086 SS D said this could not be built early because its input did not exist: it runs on a
FINISHED candidate and the loop is what produces one. `Record.handed_over` is that input, so
the dependency is discharged and the gates stop being code nothing calls.

It reads a harvest FILE rather than taking records in memory, and that is the decision worth
stating. Mining costs quota and admission costs nothing, so the two are separated at the point
where the money was spent: a gate with a bug is re-run over a saved harvest for free, where the
same bug found inside `harvest` would mean re-mining at full price. It is D-001's rule -- the
window rejects rather than bills, so paid work is never thrown away -- applied one stage later.

Two more consequences follow from reading a file, and both are in the loop's favour:

  - `harvest`'s broad `except Exception` cannot swallow a gate failure. Inline, a bug in
    `reproducible` would be caught there and written as a `failed` row, mislabelling a session
    that mined correctly as one that fell over.
  - the suite genuinely cannot change during a harvest, which is what `harvest._work` already
    assumes when it snapshots `suite.predicates()` once. Inline admission would have made that
    snapshot wrong, and D-087 SS E point 2 states it as an invariant of this split.

Running it twice is safe and that is not an accident: `distinct` refuses on `task_id`, so the
second pass finds every case it wrote already covered and admits nothing.

NO MODEL, at any point. D-086 SS A's ceiling is that the loop has no mechanical gate left in
it, and that the boundary which survives is this one -- so a model here would leave the suite
with no mechanical boundary at all.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from touchstone import config, suite
from touchstone.gate import admit, extract
from touchstone.loop import corpus
from touchstone.loop.harvest import mined_path

if TYPE_CHECKING:
    from pathlib import Path

    from touchstone.gate.predicate import Predicate

__all__ = ["gauntlet", "held_in_file", "report_path", "verdict"]


def report_path(label: str) -> Path:
    """Where a gauntlet pass lands. Beside the harvest it read, and named the same way."""
    return config.RESULTS / f"gauntlet-{label}.json"


def held_in_file(record: Mapping[str, Any], shape: Mapping[str, Any]) -> bool:
    """Does a recorded run of THIS predicate say it came back clean? D-086 SS D's `wrong if`.

    Not a fourth gate -- D-084 settled the count at three and this refuses nothing on its own.
    It is a consistency check across the serialisation boundary, and it re-asks in the file the
    question `mine.held` asked in memory: a `handed_over` row whose own attempts do not include
    a holding run of the predicate it handed over means the edge and the writer disagree.

    Matched on the predicate rather than on the last attempt, for D-110's reason: a critic is
    free to call no tool on its last lap, so `attempts[-1]` can belong to a candidate two laps
    old and would clear a hand-over on evidence about a different predicate.
    """
    return any(a["predicate"] == shape and a["holds"] for a in record.get("attempts", []))


def _candidate(record: Mapping[str, Any]) -> tuple[Predicate | None, str | None]:
    """The handed-over predicate, or None and the reason it cannot be used.

    Three ways a `handed_over` row can fail to yield one, and each is a statement about the
    file rather than about the candidate. A shape `parse` refuses came from a version with a
    shape this one does not have; a null came from an edge that recorded a hand-over with
    nothing behind it; and the third is `held_in_file`.
    """
    try:
        predicate = extract.parse(json.dumps(record["handed_over"]))
    except ValueError as bad_shape:
        return None, str(bad_shape)
    if predicate is None:
        return None, "handed over a null predicate"
    if not held_in_file(record, record["handed_over"]):
        return None, "no holding run of the handed-over predicate"
    return predicate, None


def verdict(
    record: Mapping[str, Any], covered: set[str]
) -> tuple[dict[str, Any], Predicate | None]:
    """One harvest row's outcome and the candidate that earned it. Pure, so it can be tested.

    Returns the predicate alongside the row rather than making the caller parse a second time.
    Two parses of one field is two chances to disagree about it, and the second would sit in
    the branch that WRITES -- which is the branch where disagreeing is expensive.

    Three outcomes and not two. `inconsistent` is kept apart from `refused` because they are
    findings about different things: a refusal is the gates working on a real candidate, and
    an inconsistency is this file disagreeing with itself. Counting them together would let a
    loop defect hide inside a gate's refusal rate, which is the number D-087 SS D says to watch.
    """
    session = corpus.by_id(record["session_id"])
    predicate, why = _candidate(record)
    if predicate is None:
        return _outcome(session, "inconsistent", (), why), None
    cleared = admit.cleared_by(predicate, session, covered)
    outcome = "admitted" if admit.admitted(cleared) else "refused"
    return _outcome(session, outcome, cleared, None), predicate


def _outcome(
    session: corpus.Session, outcome: str, cleared: tuple[str, ...], why: str | None
) -> dict[str, Any]:
    """A verdict row. `refused_by` is derived so the two lists cannot disagree about a gate."""
    return {
        "session_id": session.id,
        "task_id": session.task_id,
        "outcome": outcome,
        "cleared_by": list(cleared),
        "refused_by": [g for g in admit.GATES if g not in cleared],
        "why": why,
    }


def gauntlet(label: str) -> Path:
    """Run every handed-over candidate in one harvest past the gates. Returns the report.

    `suite.covered()` is re-read for every row, and this is the one place in the project that
    deliberately does NOT snapshot. The suite is changing under this loop, which is the point:
    two sessions of the same task in one harvest must not both be admitted, and a snapshot
    taken at the top would admit the second and then hit `suite.write`'s existing-file refusal
    -- the right answer reached by the wrong mechanism, and reported as a crash rather than as
    `distinct` doing its job.

    Rows that are not `handed_over` are not in the report at all. They are already counted by
    `exits` in the harvest file, and repeating them here would be a second denominator for a
    population this pass never looked at.
    """
    harvest = json.loads(mined_path(label).read_text())
    rows = []
    for record in harvest["records"]:
        if record.get("exit_reason") != "handed_over":
            continue
        row, predicate = verdict(record, suite.covered())
        if predicate is not None and row["outcome"] == "admitted":
            case = suite.case(
                predicate, record["session_id"], row["task_id"], tuple(row["cleared_by"]), label
            )
            row["case"] = suite.write(case).name
        rows.append(row)
    return _write(label, harvest, rows)


def _write(label: str, harvest: Mapping[str, Any], rows: list[dict[str, Any]]) -> Path:
    """The report. Carries the harvest's own header so a case can be traced back to its run.

    `handed_over` is stated beside the three outcomes because they sum to it, and a reader who
    cannot cross-foot a table against the total near it has to trust it (rule 4).
    """
    out = report_path(label)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "label": label,
                "written": datetime.now(UTC).isoformat(),
                "harvest_written": harvest.get("written"),
                "model": harvest.get("model"),
                "rubric_hash": harvest.get("rubric_hash"),
                "gates": list(admit.GATES),
                "handed_over": len(rows),
                "admitted": sum(r["outcome"] == "admitted" for r in rows),
                "refused": sum(r["outcome"] == "refused" for r in rows),
                "inconsistent": sum(r["outcome"] == "inconsistent" for r in rows),
                "verdicts": rows,
            },
            indent=2,
        )
        + "\n"
    )
    return out
