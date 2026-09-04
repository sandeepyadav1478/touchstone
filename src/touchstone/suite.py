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
from touchstone.loop.agents import shape

if TYPE_CHECKING:
    from pathlib import Path

    from touchstone.gate.predicate import Predicate

__all__ = ["FIELDS", "blank", "case", "covered", "load", "path", "write"]

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
        "predicate": shape(predicate),
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
