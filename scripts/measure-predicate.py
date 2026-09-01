#!/usr/bin/env python3
"""Shadow-run hand-written policy predicates over the shipped retail simulations.

This runs BEFORE `gate/extract.py` exists, and that order is deliberate. D-105 found tier 1
silent on the adopted corpus because four of its five constraints were already the
environment's job -- discovered by measuring, after the code was written. The same question is
cheaper to ask one phase earlier here: a predicate shape that fires on nothing across 1,824
real sessions is a shape the curator never needs to be able to emit, and the extractor's schema
is smaller for knowing that first.

The three rules below are written by hand, from `data/tau2/domains/retail/policy.md`, so this
measures the SHAPES rather than any model's ability to find them. What a model then does with
the same policy is a separate measurement and it needs quota; this one needs none.

  authentication   policy.md:10 -- a user id must be located before acting for that user
  cancel reason    policy.md:90 -- only two reasons are acceptable

policy.md:16's confirmation rule was here too, as the third row, until D-109 retired the shape
that encoded it. `scripts/measure-assent-window.py` still measures it and is why it went.

Both populations are printed, always -- 1,824 over 114 tasks and D-080's 1,712 over 107 --
because D-105 is the worked example of the two disagreeing.

The control set here is `db_match` plus every `action_check`, which is the pair
`measure-tier1.py` uses. It deliberately does NOT include the unconfirmed-write signal docs/02
counts as its third: filtering the control set by a predicate is how you test a predicate
against a set defined by that same predicate. D-109 is the harder version of that problem --
the key cannot see confirmation at all, so no control set here can rule on it.

    uv run python scripts/measure-predicate.py
"""

from __future__ import annotations

import importlib
import json
import logging
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from touchstone.gate.predicate import (  # noqa: E402
    ArgumentIn,
    Predicate,
    RequiresPriorTool,
    evaluate,
)

# The corpus plumbing is imported rather than copied: `moved_tasks` normalises gold actions in
# a way that reports 112 of 114 as moved when it is got wrong, and a second copy of that is a
# second thing to get wrong.
_tier1 = importlib.import_module("measure-tier1")

AUTH = ("find_user_id_by_email", "find_user_id_by_name_zip")


def write_tools() -> list[str]:
    """The mutating retail tools, from τ² rather than from a list written here."""
    from tau2.domains.retail.environment import get_environment

    tk = get_environment().tools
    return sorted(n for n in tk.tools if tk.tool_mutates_state(n))


def rules(writes: list[str]) -> dict[str, list[Predicate]]:
    """The three policy rules, expanded to one predicate per tool they govern."""
    return {
        "authentication": [
            Predicate("a user id must be located before acting for that user",
                      "retail/policy.md:10", RequiresPriorTool(w, AUTH))
            for w in writes
        ],
        "cancel reason": [
            Predicate("either 'no longer needed' or 'ordered by mistake'",
                      "retail/policy.md:90",
                      ArgumentIn("cancel_pending_order", "reason",
                                 ("no longer needed", "ordered by mistake")))
        ],
    }


def main() -> None:
    """Measure every shape over both populations and print what would have fired."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    files = _tier1.corpus_files()
    from tau2.utils.utils import DATA_DIR

    moved = _tier1.moved_tasks(files, Path(DATA_DIR) / "tau2" / "domains" / "retail" / "tasks.json")
    writes = write_tools()
    logging.info("── milestone 1/3 · %d write tool(s) from τ², %d task(s) excluded by D-080",
                 len(writes), len(moved))

    by_rule = rules(writes)
    n: Counter[str] = Counter()
    for f in files:
        for s in json.loads(f.read_text())["simulations"]:
            adopted = str(s["task_id"]) not in moved
            n["sims_all"] += 1
            n["sims_corpus"] += adopted
            info = s.get("reward_info") or {}
            clean = bool((info.get("db_check") or {}).get("db_match")) and all(
                a.get("action_match") for a in (info.get("action_checks") or [])
            )
            for name, preds in by_rule.items():
                hits = sum(len(evaluate(p, s["messages"])) for p in preds)
                if not hits:
                    continue
                n[f"{name}|all"] += 1
                if adopted:
                    n[f"{name}|corpus"] += 1
                    n[f"{name}|clean"] += clean

    logging.info("── milestone 2/3 · %d simulation(s) read, %d in the adopted corpus",
                 n["sims_all"], n["sims_corpus"])
    logging.info("")
    logging.info("%-16s %13s %13s %13s", "rule", "sims/1824", "sims/1712", "of those CLEAN")
    for name in by_rule:
        logging.info("%-16s %13d %13d %13d",
                     name, n[f"{name}|all"], n[f"{name}|corpus"], n[f"{name}|clean"])
    logging.info("")
    logging.info("── milestone 3/3 · a shape that fires on nothing is one the curator never needs")
    for name in by_rule:
        verdict = "LIVE" if n[f"{name}|corpus"] else "DEAD on this specimen"
        logging.info("  %-16s %s", name, verdict)


if __name__ == "__main__":
    main()
