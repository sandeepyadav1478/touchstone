"""P2 -- the regression tier: what an admitted case is on disk, and what it has to carry.

D-024 splits the suite in two. The benchmark freezes and produces the version table; this tier
grows forever and answers one question, `did something that worked stop working?` A binary over
`has this ever passed` is well defined however many cases exist, so adding here resets no
denominator -- which is the whole reason a mined case is affordable at all.

One JSON file per case, named by `task_id`. Two harvests admitting different tasks then cannot
conflict, where a single index file is a thing every writer has to serialise on; and `history`
can be appended to without rewriting anybody else's row.

Note that `reviewed_by` is NOT a field, and D-024 argued for it explicitly rather than by default.
Its argument was that a wrong label entering silently gates CORRECT behaviour forever and gets
debugged as an agent regression. That argument is answered, not dismissed: D-086 SS A put three
mechanical gates in front of this directory, and `cleared_by` records WHICH of them passed
(D-084 SS A.4). A gate set is strictly more provenance than a name -- it says what was checked,
it is reproducible, and it survives the gate list changing. The candidate's standing
instruction is that this project is automatic end to end, so the human step is deprecated and
the mechanism that replaced it is named in the file it writes.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from touchstone import __version__, config
from touchstone.gate import extract

if TYPE_CHECKING:
    from pathlib import Path

    from touchstone.gate.predicate import Predicate

__all__ = ["FIELDS", "blank", "case", "covered", "index", "load", "path", "predicates", "write"]

# Invariant 11's subject: a case with any of these empty does not get to gate anything.
FIELDS = ("task_id", "origin", "why", "added", "cleared_by", "predicate", "history")


def path(task_id: str) -> Path:
    """Where one case lives. Named by task, because `distinct` admits at most one per task."""
    return config.REGRESSION / f"{task_id}.json"


def load() -> list[dict[str, Any]]:
    """Every admitted case, in task order. An absent directory is an empty suite, not an error.

    Sorted by filename rather than by `added`. Two cases written in the same second have no
    order by date, and a listing that changed between runs would make every diff of a suite
    report unreadable for a reason that has nothing to do with the suite.
    """
    if not config.REGRESSION.is_dir():
        return []
    return [json.loads(f.read_text()) for f in sorted(config.REGRESSION.glob("*.json"))]


def covered() -> set[str]:
    """The task ids already admitted. This is what `admit.distinct` is asking about."""
    return {c["task_id"] for c in load()}


def index() -> str:
    """The suite as the curator is shown it: what already gates, one line each.

    D-087 SS B's judged half, and it changes no control flow. The exact half already refuses a
    session an admitted predicate fires on; this is for the case that half cannot see -- a
    session with a genuinely different failure whose NEAREST rule is one already in the suite.
    Nothing mechanical can tell that apart from a real second rule, so the curator is told what
    is here and writes around it.

    `task_id` and `why` and nothing else. The predicate's encoded shape is the answer to the
    question being asked, and D-092's guard would refuse this prompt if it carried one --
    a curator shown three worked examples writes a fourth in their shape rather than the
    session's. What it needs is the rules that are taken, not how they were written.

    Empty until P2.4 admits the first case. An empty suite renders as nothing rather than as an
    empty heading, because a heading with nothing under it reads as a suite that was searched
    and found wanting.
    """
    cases = load()
    if not cases:
        return ""
    rules = "\n".join(f"  {c['task_id']}  {c['why']}" for c in cases)
    return f"Rules already in the suite, which a new one may not restate:\n\n{rules}\n"


def predicates() -> tuple[Predicate, ...]:
    """Every admitted case as a live predicate, for the exact half of D-087 SS B.

    Read back through `extract.parse` rather than a second builder. `parse` is already the
    trust boundary that refuses a `kind` outside the closed set, so a case written by a version
    that had a fourth shape is refused here by the rule that refuses a model inventing one --
    and a second constructor would be the place those two answers drift apart.

    It refuses by RAISING, which is right where it was written and wrong here. At the model
    boundary the raise costs one session a `failed` row; on this path the same raise would take
    down every session in the harvest, including every one that has nothing to do with the bad
    file. So it is caught and the case is dropped, and the cost of dropping is bounded: the
    loop may spend a lap re-mining that task and `admit.distinct` refuses the result on the
    task id, which is exactly the backstop D-087 SS D keeps it for.
    """
    out = []
    for case_ in load():
        try:
            out.append(extract.parse(json.dumps(case_["predicate"])))
        except ValueError:
            continue
    return tuple(p for p in out if p)


def case(
    predicate: Predicate,
    session_id: str,
    task_id: str,
    cleared: tuple[str, ...],
    harvest: str,
) -> dict[str, Any]:
    """One case, with the provenance D-024 requires and nothing a reader has to take on trust.

    `why` is the predicate's own rule and citation rather than free text. D-024 wanted a
    sentence answering `why is this here?`, and the rule IS that sentence -- with the advantage
    that `admit.justified` has already checked the citation resolves to a line of the policy,
    which no hand-written sentence would have been.

    `origin` carries the version because a case mined by one version and a case mined by
    another are different evidence, and the harvest label because the trace that produced it is
    in that file and nowhere else.
    """
    return {
        "task_id": task_id,
        "origin": {
            "kind": "mined",
            "version": __version__,
            "harvest": harvest,
            "session_id": session_id,
        },
        "why": f"{predicate.rule} -- {predicate.source}",
        "added": datetime.now(UTC).isoformat(),
        "cleared_by": list(cleared),
        "predicate": extract.shape(predicate),
        "history": [{"at": datetime.now(UTC).isoformat(), "was": "admitted", "by": list(cleared)}],
    }


def blank(record: dict[str, Any]) -> list[str]:
    """The required fields this case leaves empty. Invariant 11 fails CI on a non-empty answer.

    Falsy and not missing. A case that carries `"why": ""` and one that carries no `why` are
    the same defect to a reader six months out, and a check that only caught the second would
    pass the one a writer is more likely to produce.
    """
    return [f for f in FIELDS if not record.get(f)]


def write(record: dict[str, Any]) -> Path:
    """Persist one case, refusing an incomplete one and refusing to overwrite an existing task.

    Both refusals are the same rule from opposite sides. `history` is append-only because
    D-024 requires `why is this here?` to be answerable from the file, and an overwrite answers
    it with whatever the last writer believed; a blank field answers it with nothing at all.
    """
    if missing := blank(record):
        raise ValueError(f"case {record.get('task_id')!r} leaves {missing} empty -- D-024")
    out = path(record["task_id"])
    if out.exists():
        raise ValueError(f"{out.name} already exists -- `distinct` should have refused this")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2) + "\n")
    return out
