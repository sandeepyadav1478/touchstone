#!/usr/bin/env python3
"""Every gate's shadow score: what it would have blocked, and how often it would be wrong.

D-065 says a gate runs in shadow before it enforces, and the ROADMAP's phase-2 exit turns that
into a checkable line -- no gate reaches phase 3 without precision, recall, and a count of the
sessions it would have blocked. `measure-tier1.py` and `measure-predicate.py` already print
FIRINGS; a firing is not a score. This divides them by the answer key.

The answer key is the one D-108 left standing: 778 anomalous against 934 clean, over the 1,712
adopted simulations. Not 834/878 -- that pair needs the 56 unconfirmed writes, whose regex was
never committed, so a recall quoted against 834 divides by a figure no command produces.

    true positive    the gate fired and the session was anomalous
    false positive   the gate fired and the session was clean -- docs/02 SS5 rejects the gate
    recall           TP / 778
    precision        TP / (TP + FP)

Two ceilings, and neither is small.

  1. A true positive here means the gate fired on a session that failed for SOME reason, not
     that it fired for THAT reason. This scores agreement with the answer key, never causal
     correctness, and no arrangement of these files can tell the two apart.
  2. The confirmation row used to be here and used to be REJECTED, on 44 false positives, and
     D-109 retired the shape rather than fixing it. Read what that did to this table with
     care: no gate is rejected now, and NOT ONE was cleared by the change. Deleting the gate
     that was failing is not the gate passing. What is left is one gate cleared on a single
     firing and two that fire on nothing, which is the same negative result in a quieter form.

    uv run python scripts/measure-shadow.py
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
from touchstone.gate.tier1 import check  # noqa: E402


def tier1_fires(messages: Sequence[Mapping[str, Any]]) -> bool:
    """Whether tier 1 has an opinion on a call the environment ACCEPTED.

    The accepted filter is `measure-tier1.py`'s and it is load-bearing rather than tidy: a gate
    firing on a call the tool already refused has changed nothing, because no write happened
    either way, so counting it would inflate both halves of the score at once.
    """
    results = {m["id"]: m for m in messages if m.get("role") == "tool"}
    return any(
        check(c["name"], c["arguments"] or {})
        and not results.get(c["id"], {}).get("error", True)
        for m in messages
        for c in (m.get("tool_calls") or [])
    )


def score(n: Counter[str], gate: str, anomalous: int) -> str:
    """One row: what it blocked, and the two ratios with the populations they came from."""
    tp, fp = n[f"{gate}|tp"], n[f"{gate}|fp"]
    fired = tp + fp
    if not fired:
        return f"{gate:<16} SILENT on all 1,712 - no score, and a shape the curator never needs"
    precision = f"{100 * tp / fired:5.1f}%"
    recall = f"{100 * tp / anomalous:5.1f}%"
    return (f"{gate:<16} {fired:5d} blocked  {tp:5d}/{anomalous} recall {recall}"
            f"  {tp:5d}/{fired} precision {precision}")


def main() -> None:
    """Score tier 1 and each hand-written tier-2 rule against D-108's 778/934 answer key."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    # Deferred, and not copied. `moved_tasks` normalises gold actions in a way that reports 112
    # of 114 as moved when it is got wrong, and `rules` is where the three policy predicates are
    # already spelled out -- a second copy of either is a second thing to get wrong.
    _tier1 = importlib.import_module("measure-tier1")
    _pred = importlib.import_module("measure-predicate")
    from tau2.utils.utils import DATA_DIR

    files = _tier1.corpus_files()
    moved = _tier1.moved_tasks(files, Path(DATA_DIR) / "tau2" / "domains" / "retail" / "tasks.json")
    by_rule = _pred.rules(_pred.write_tools())
    gates = ["tier 1", *by_rule]
    logging.info("-- milestone 1/3 - %d gate(s), %d task(s) excluded by D-080",
                 len(gates), len(moved))

    n: Counter[str] = Counter()
    for f in files:
        for s in json.loads(f.read_text())["simulations"]:
            if str(s["task_id"]) in moved:
                continue
            msgs = s["messages"]
            info = s.get("reward_info") or {}
            anomalous = not (info.get("db_check") or {}).get("db_match") or not all(
                a.get("action_match") for a in (info.get("action_checks") or [])
            )
            n["anomalous" if anomalous else "clean"] += 1
            fired = {"tier 1": tier1_fires(msgs)}
            for name, preds in by_rule.items():
                fired[name] = any(evaluate(p, msgs) for p in preds)
            for gate, hit in fired.items():
                n[f"{gate}|{'tp' if anomalous else 'fp'}"] += hit
    logging.info("-- milestone 2/3 - %d anomalous, %d clean, %d adopted",
                 n["anomalous"], n["clean"], n["anomalous"] + n["clean"])

    logging.info("")
    for gate in gates:
        logging.info("  %s", score(n, gate, n["anomalous"]))
    logging.info("")
    logging.info("-- milestone 3/3 - a false positive disqualifies a gate; a low recall does not")
    for gate in gates:
        fp, tp, clean = n[f"{gate}|fp"], n[f"{gate}|tp"], n["clean"]
        # A silent gate is not a cleared gate, and printing it as one would be a check that
        # cannot fail. docs/02 SS5 rejects a gate that fires on a clean session, so a gate that
        # fires on nothing passes it without ever taking it.
        if fp:
            verdict = f"REJECTED by docs/02 SS5 - {fp} of {clean} clean sessions"
        elif not tp:
            verdict = "UNSCORED - it fired on nothing, which SS5 cannot reject or clear"
        else:
            verdict = f"CLEARED by docs/02 SS5 - {tp} firing(s), none on a clean session"
        logging.info("  %-16s %s", gate, verdict)
    logging.info("  D-109 removed the one REJECTED row; the exit is no closer for it.")


if __name__ == "__main__":
    main()
