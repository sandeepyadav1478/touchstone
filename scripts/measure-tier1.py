#!/usr/bin/env python3
"""Shadow-run tier 1 over τ²'s shipped retail simulations and report what it would have done.

This is the evidence P2.1 rests on, not a guard: it has no pass condition, because a gate's
firing rate is a measurement and a threshold on it would be a number invented here. What it
does enforce is that any figure quoted about tier 1 came from a command in the repo rather
than from a scratch script that no longer exists (rule 11).

Two populations, and mixing them is the whole risk:

  1,824 simulations  every retail baseline, all 114 tasks
  1,712 simulations  the 107 tasks whose gold actions did not move between the shipped runs
                     and today's tasks.json — the corpus D-080 adopted and P3.4 mines

Both are printed, always, because tier 1's answer differs between them and a reader given one
number would draw the wrong conclusion from it.

A firing is only interesting if the environment ACCEPTED the call. A gate that fires on a call
the tool already refused has changed nothing — no write happened either way — so accepted and
errored are counted apart rather than summed.

    uv run python scripts/measure-tier1.py
"""

from __future__ import annotations

import json
import logging
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from touchstone.gate.tier1 import check


def corpus_files() -> list[Path]:
    """The shipped retail baselines, through τ²'s own path constant."""
    from tau2.utils.utils import DATA_DIR

    return sorted((Path(DATA_DIR) / "tau2" / "results" / "final").glob("*_retail_*.json"))


def _gold(actions: list[dict[str, Any]]) -> list[tuple[str, str, str]]:
    """A gold action list flattened to something comparable across two files."""
    return [
        (a["name"], a.get("requestor") or "assistant",
         json.dumps(a.get("arguments") or {}, sort_keys=True))
        for a in actions
    ]


def moved_tasks(files: list[Path], tasks_json: Path) -> set[str]:
    """Tasks whose gold actions differ between a shipped run and today's tasks.json.

    Compared on name, requestor and arguments rather than the raw dict: the shipped copies
    carry serialisation differences that make a plain `==` report 112 of 114 as moved, which
    is a comparison failing, not a corpus that changed.
    """
    today = {
        str(t["id"]): _gold((t.get("evaluation_criteria") or {}).get("actions") or [])
        for t in json.loads(tasks_json.read_text())
    }
    moved = set()
    for f in files:
        for t in json.loads(f.read_text())["tasks"]:
            shipped = _gold((t.get("evaluation_criteria") or {}).get("actions") or [])
            if shipped != today.get(str(t["id"])):
                moved.add(str(t["id"]))
    return moved


def main() -> int:
    """Print both populations and the false-positive count. Always returns 0."""
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    files = corpus_files()
    if not files:
        logging.error("FAIL — no corpus file found. Is TAU2_DATA_DIR set? `touchstone doctor`")
        return 1

    from tau2.utils.utils import DATA_DIR

    moved = moved_tasks(files, Path(DATA_DIR) / "tau2" / "domains" / "retail" / "tasks.json")
    logging.info("── milestone 1/3 · %d task(s) excluded, gold actions moved: %s",
                 len(moved), ", ".join(sorted(moved, key=int)))

    n: Counter[str] = Counter()
    per_task: Counter[str] = Counter()
    for f in files:
        for s in json.loads(f.read_text())["simulations"]:
            adopted = str(s["task_id"]) not in moved
            n["sims_all"] += 1
            n["sims_corpus"] += adopted
            results = {m["id"]: m for m in s["messages"] if m.get("role") == "tool"}
            hits = [
                c
                for m in s["messages"]
                for c in (m.get("tool_calls") or [])
                if check(c["name"], c["arguments"] or {})
            ]
            accepted = [c for c in hits if not results.get(c["id"], {}).get("error", True)]
            n["fired_all"] += len(hits)
            n["accepted_all"] += len(accepted)
            n["fired_corpus"] += len(hits) * adopted
            n["accepted_corpus"] += len(accepted) * adopted
            per_task[str(s["task_id"])] += len(accepted)
            if not (accepted and adopted):
                continue
            info = s.get("reward_info") or {}
            db = bool((info.get("db_check") or {}).get("db_match"))
            n["sims_with_a_firing"] += 1
            n["db_passed"] += db
            n["in_the_clean_set"] += db and all(
                a.get("action_match") for a in (info.get("action_checks") or [])
            )

    logging.info("── milestone 2/3 · %d simulation(s) read, %d in the adopted corpus",
                 n["sims_all"], n["sims_corpus"])
    logging.info("")
    logging.info("%-34s %14s %14s", "", "all 114 tasks", "the 107")
    logging.info("%-34s %14d %14d", "simulations", n["sims_all"], n["sims_corpus"])
    logging.info("%-34s %14d %14d", "tier-1 firings", n["fired_all"], n["fired_corpus"])
    logging.info("%-34s %14d %14d", "  on a call the env ACCEPTED",
                 n["accepted_all"], n["accepted_corpus"])
    logging.info("")
    logging.info("accepted firings by task: %s",
                 {k: v for k, v in sorted(per_task.items(), key=lambda x: int(x[0])) if v})
    logging.info("")
    logging.info("── milestone 3/3 · false positives, the only figure that can disqualify a gate")
    logging.info("  corpus simulations with an accepted firing : %d", n["sims_with_a_firing"])
    logging.info("    of those, db_check PASSED                : %d", n["db_passed"])
    logging.info("    of those, in the CLEAN control set       : %d  <- false positives",
                 n["in_the_clean_set"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
