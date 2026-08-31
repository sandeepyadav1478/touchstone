#!/usr/bin/env python3
"""Rebuild docs/02's control set from a command, and say which part of it will not rebuild.

docs/02 SS5 names the set a predicate must be silent on as 878, being 1,712 minus 834, and the
834 is three signals: 407 sessions failing the DB check, 371 passing it with a failed
`action_check`, and 56 with an unconfirmed write. The first two are recomputed here and land on
407 and 371 exactly. The third came from a regex over the most recent user message before each
write, that regex was never committed, and nothing in this repo reproduces it -- D-106 SS C, and
the reason P2.3 cannot report a false-positive rate against 878.

The obvious replacement is circular and is not taken. Recomputing "unconfirmed write" with
`RequiresUserAssent` would define the control set with the predicate the control set exists to
judge. So the third signal here is a DIFFERENT stated rule, picked because it reads only the
assistant's own message and so needs no assent list and no model: `policy.md:20` forbids a tool
call in the same message as text, and forbids more than one call at a time.

It does not reproduce 56 and was never going to -- it fires on 627 of the 934, so subtracting it
would delete two thirds of the corpus over a rule the harness never enforced. What it is for is
DEF-076's other half. docs/02 says 23 of the 44 confirmation firings are corroborated by it, and
a reader takes that as support. This prints the base rate beside it, which is the number that
decides whether it is support at all.

    uv run python scripts/measure-control-set.py
"""

from __future__ import annotations

import importlib
import json
import logging
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from touchstone.gate.predicate import evaluate  # noqa: E402

# What docs/02 SS5 states, kept here so the run reports which figures it reproduced instead of
# leaving a reader to diff two documents by eye.
RECORDED = {"fail_db": 407, "fail_action": 371, "unconfirmed": 56, "control": 878}


def breaks_one_call_at_a_time(
    messages: Sequence[Mapping[str, Any]],
) -> tuple[bool, bool]:
    """policy.md:20 as two mechanical checks: text beside a call, and more than one call.

    The line states both, and they are counted apart because they turn out to be different
    sets of the same size -- see the overlap printed with them, which is the only thing that
    tells a reader the two equal numbers are not one number printed twice.
    """
    text_beside_call = multi_call = False
    for m in messages:
        if m.get("role") != "assistant":
            continue
        calls = m.get("tool_calls") or []
        text_beside_call |= bool(calls) and bool(str(m.get("content") or "").strip())
        multi_call |= len(calls) > 1
    return text_beside_call, multi_call


def census() -> Counter[str]:
    """One pass over the adopted corpus, counting every signal the control set is built from."""
    from tau2.utils.utils import DATA_DIR

    # Imported here rather than at module scope, and not copied. `moved_tasks` normalises gold
    # actions in a way that reports 112 of 114 as moved when it is got wrong, and `rules` is
    # where the confirmation predicate is already spelled out -- a second copy of either is a
    # second thing to get wrong. Deferring them keeps importing this file free, which is what
    # lets `test_control_set.py` check the policy rule inside the suite's 2 s budget.
    _tier1 = importlib.import_module("measure-tier1")
    _pred = importlib.import_module("measure-predicate")

    files = _tier1.corpus_files()
    tasks = Path(DATA_DIR) / "tau2" / "domains" / "retail" / "tasks.json"
    moved = _tier1.moved_tasks(files, tasks)
    confirmation = _pred.rules(_pred.write_tools())["confirmation"]
    logging.info("-- milestone 1/3 - %d task(s) excluded by D-080, %d result file(s)",
                 len(moved), len(files))

    n: Counter[str] = Counter()
    for f in files:
        for s in json.loads(f.read_text())["simulations"]:
            if str(s["task_id"]) in moved:
                continue
            n["adopted"] += 1
            info = s.get("reward_info") or {}
            if not (info.get("db_check") or {}).get("db_match"):
                n["fail_db"] += 1
                continue
            if not all(a.get("action_match") for a in (info.get("action_checks") or [])):
                n["fail_action"] += 1
                continue
            n["clean"] += 1
            text, multi = breaks_one_call_at_a_time(s["messages"])
            fires = any(evaluate(p, s["messages"]) for p in confirmation)
            n["fires"] += fires
            for tag, hit in (("text", text), ("multi", multi), ("either", text or multi),
                             ("both", text and multi)):
                n[f"clean|{tag}"] += hit
                n[f"fires|{tag}"] += hit and fires
    logging.info("-- milestone 2/3 - %d adopted simulation(s) read", n["adopted"])
    return n


def main() -> None:
    """Print the control set, its policy.md:20 composition, and what did not reproduce."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    n = census()
    clean, fires = n["clean"], n["fires"]

    logging.info("")
    logging.info("%-26s %18s %18s", "policy.md:20", "of the clean set", "of the firings")
    for tag, label in (("text", "text beside a call"), ("multi", "more than one call"),
                       ("either", "either -- the rule")):
        c, g = n[f"clean|{tag}"], n[f"fires|{tag}"]
        logging.info("%-26s %9d %7.1f%% %9d %7.1f%%",
                     label, c, 100 * c / clean, g, 100 * g / fires)
    logging.info("%-26s %9d %25d", "sessions", clean, fires)
    logging.info("  the two equal counts are different sets: %d break both",
                 n["clean|both"])
    logging.info("")
    logging.info("  A firing is %.2fx as likely to break policy.md:20 as a clean session is.",
                 (n["fires|either"] / fires) / (n["clean|either"] / clean))
    logging.info("  docs/02 says at least 23 of them are corroborated by it; this counts %d.",
                 n["fires|either"])
    logging.info("  Neither figure carries the base rate, and the base rate is what decides")
    logging.info("  whether corroboration by this rule means anything at all -- DEF-076.")

    logging.info("")
    logging.info("-- milestone 3/3 - what reproduces, and what does not")
    for key, label in (("fail_db", "fails the DB check"),
                       ("fail_action", "DB ok, action_check fails")):
        got, want = n[key], RECORDED[key]
        logging.info("  %-26s %5d  recorded %3d  %s",
                     label, got, want, "REPRODUCED" if got == want else "CONFLICT")
    logging.info("  %-26s %5s  recorded %3d  LOST - the regex was never committed",
                 "unconfirmed write", "--", RECORDED["unconfirmed"])
    logging.info("  %-26s %5d  recorded %3d  CONFLICT - %d = %d + %d, so they agree on the",
                 "control set", clean, RECORDED["control"], clean, RECORDED["control"],
                 RECORDED["unconfirmed"])
    logging.info("  %-26s %5s  arithmetic and disagree on which is reproducible.", "", "")


if __name__ == "__main__":
    main()
