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

__all__ = ["failed", "harvest", "mined_path"]


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
        "waved_through": record.waved_through,
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


def failed(session: corpus.Session, error: Exception) -> dict[str, Any]:
    """A session that raised, written down instead of taking the harvest with it.

    There is no `exit_reason` for this and there deliberately is not one: D-093 SS C gives
    that field to the graph's edge, and a session that fell over never reached an edge to be
    decided by. So the row carries `error` and a null exit, and `harvest` counts it under
    `failed` rather than inventing a fifth door into D-094's table.

    Ceiling: this catches a bug as readily as a bad model answer, so a systematic fault becomes
    N identical rows rather than one traceback. The error string is kept verbatim for that --
    N rows that all say the same thing are the traceback, spread out.
    """
    return {
        "session_id": session.id,
        "exit_reason": None,
        "error": f"{type(error).__name__}: {error}",
        "attempts": [],
    }


def _work(session: corpus.Session) -> mine.Record:
    """One session, inside one span. The span is the only place the loop is observable live.

    Every flag is set here by hand, and D-090 SS D is the reason there is no shorter way. It
    sends the flags to the trace so a human can read why one lap ended without the loop being
    allowed to branch on them -- so a flag that is only in the JSON has been written to the
    half of that decision the loop does not use.

    Ceiling: this span has no children. `mlflow.langgraph` is not in `mlflow-skinny` 3.15.1
    (measured 2026-09-01, `ModuleNotFoundError`), so there is no autolog to attach, and the
    critic's tool calls happen inside the Agent SDK's own subprocess where an in-process
    autolog would not see them anyway. Per-attempt evidence lives in `row`, not in the trace.
    """
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
        span.set_attribute("touchstone.told_to_exit", record.told_to_exit)
        span.set_attribute("touchstone.gave_up", record.gave_up)
        span.set_attribute("touchstone.waved_through", record.waved_through)
        span.set_attribute("touchstone.rule_searched_for", record.rule_searched_for or "")
        return record


def harvest(label: str, limit: int, session_ids: tuple[str, ...] = ()) -> Path:
    """Mine a set of sessions and write the records. Returns the file it wrote.

    A quota exhaustion stops the harvest and is not an error: the window rejects rather than
    bills (D-001), so the sessions already worked are paid for and throwing them away would
    mean paying twice. The file says how far it got, which is what a resume needs to know.

    The two failures are not the same failure and are handled differently. The window is
    shut for every session after it, so the harvest STOPS. Anything else is one session's
    problem, so that session gets a `failed` row and the next one is worked -- and the money
    behind the rows already collected is the whole reason. A malformed model answer is the
    ordinary case here, not the exotic one: `extract.parse` and `extract.json_object` are trust
    boundaries and RAISE by design, so before this a curator emitting one bad object on session
    4 discarded the three sessions in front of it.

    The file is rewritten after every session, for the third door out of the same argument:
    a Ctrl-C, an OOM or a closed laptop lid does not reach either `except`, and writing once at
    the end would lose every paid session to it. This is τ²'s `auto_resume` rule from D-015 --
    write each unit as it completes -- applied to the loop that runs beside it.

    ponytail: rewrites the whole file each time, so it is O(n^2) bytes in the session count.
    `--limit` defaults to 5. Append a line per record if a harvest ever runs to hundreds. No
    resume either: the file records how far it got, and nothing reads it back yet.
    """
    telemetry.install()
    rows: list[dict[str, Any]] = []
    stopped = None
    for session in pick(limit, session_ids):
        try:
            rows.append(row(_work(session)))
        except budget.QuotaExhaustedError as exhausted:
            stopped = str(exhausted)
            break
        except Exception as error:  # broad on purpose -- see `failed`; the money is spent
            rows.append(failed(session, error))
        _write(label, rows, stopped)
    telemetry.flush()
    return _write(label, rows, stopped)


def _write(label: str, rows: list[dict[str, Any]], stopped: str | None) -> Path:
    """The harvest file as it stands. Called after every session, and once at the end.

    The last call is not redundant: a harvest the quota stopped `break`s before the in-loop
    write, and one that picked no sessions never enters the loop. Both still owe a file -- an
    absent file and an empty harvest are different findings and would otherwise look the same.
    """
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
                "exits": dict(Counter(
                    "failed" if r.get("error") else r["exit_reason"] for r in rows
                )),
                "records": rows,
            },
            indent=2,
        )
        + "\n"
    )
    return out
