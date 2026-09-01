"""P3.4 -- running the loop over more than one session, and what it leaves behind.

`mine.mine()` works one session and returns a record. This is the part that picks which ones,
binds the three agents from `agents.py` to it, and writes the records where something can read
them. It is the only file in the loop that does I/O.

The record is the product, not the predicate. D-089 SS D says the give-up rate is the number
that tells a correct refusal from a lazy one, and D-094 that the exit reasons only mean
anything if they can be told apart -- so every session that entered leaves a row, including
the ones the router skipped and the ones nobody could write a rule for.

The header records the model and the rubric hash and NOT the attempt cap, which
`test_the_attempt_cap_has_exactly_one_reader` caught this file reaching for. D-091 SS C keeps
`attempts_exhausted()` as the only thing that reads it, and a provenance field is still a
second place that knows the number. What a reader needs is in the rows: `dispatches` tops out
at the cap and `budget_exhausted` says it was reached.

Sessions are taken in corpus order and NOT filtered by `Session.anomalous`. Handing the router
only the failures would answer rubric criterion 1 before it is asked, and that criterion is
where the router's own error rate comes from (D-082 SS B). It costs a model call on sessions
that will be skipped, and that cost is the measurement.
"""

from __future__ import annotations

import asyncio
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import mlflow

from touchstone import config, telemetry
from touchstone.loop import agents, budget, corpus, mine

__all__ = ["harvest", "mined_path"]


def mined_path(label: str) -> Path:
    """Where a harvest lands. Beside the run and score results, and named the same way."""
    return config.RESULTS / f"mined-{label}.json"


def pick(limit: int, session_ids: tuple[str, ...] = ()) -> list[corpus.Session]:
    """The sessions to work, in corpus order.

    First-N, not a sample, and the difference matters for anything reported off it: the corpus
    is sorted by file and then by index, so the first N are four agents' early tasks rather
    than a draw from the population. A figure over the corpus is a script's job, and it says
    so in its own header.
    """
    if session_ids:
        wanted = set(session_ids)
        return [s for s in corpus.load() if s.id in wanted]
    return list(corpus.load()[:limit])


def row(record: mine.Record) -> dict[str, Any]:
    """One record as JSON, with every attempt and what the check returned for it.

    D-082 requires an unmineable to carry all of them. Kept for the other exits too: a
    hand-over that took four attempts and one that took one are different evidence about the
    curator, and a row that only recorded the winner cannot tell them apart.
    """
    return {
        "session_id": record.session_id,
        "exit_reason": record.exit_reason,
        "dispatches": record.dispatches,
        "gave_up": record.gave_up,
        "told_to_exit": record.told_to_exit,
        "rule_searched_for": record.rule_searched_for,
        "attempts": [
            {
                "predicate": agents.shape(a.predicate),
                "fired_on_target": a.fired_on_target,
                "counterexample": a.counterexample,
                "holds": a.holds,
            }
            for a in record.attempts
        ],
    }


def _work(session: corpus.Session) -> mine.Record:
    """One session, inside one span. The span is the only place the loop is observable live."""
    with mlflow.start_span("touchstone.mine") as span:
        span.set_attribute("touchstone.session_id", session.id)
        record = asyncio.run(
            mine.mine(
                session,
                router=agents.router,
                curator=agents.curator,
                critic=agents.critic,
            )
        )
        span.set_attribute("touchstone.exit_reason", record.exit_reason or "")
        span.set_attribute("touchstone.attempts", record.dispatches)
        return record


def harvest(label: str, limit: int, session_ids: tuple[str, ...] = ()) -> Path:
    """Mine a set of sessions and write the records. Returns the file it wrote.

    A quota exhaustion stops the harvest and is not an error: the window rejects rather than
    bills (D-001), so the sessions already worked are paid for and throwing them away would
    mean paying twice. The file says how far it got, which is what a resume needs to know.
    """
    telemetry.install()
    rows, stopped = [], None
    for session in pick(limit, session_ids):
        try:
            rows.append(row(_work(session)))
        except budget.QuotaExhaustedError as exhausted:
            stopped = str(exhausted)
            break
    telemetry.flush()

    out = mined_path(label)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "label": label,
                "written": datetime.now(UTC).isoformat(),
                "model": config.LOOP_MODEL,
                "rubric_hash": agents.RUBRIC_HASH,
                "stopped_early": stopped,
                "exits": dict(Counter(r["exit_reason"] for r in rows)),
                "records": rows,
            },
            indent=2,
        )
        + "\n"
    )
    return out
