#!/usr/bin/env python3
"""Price the two surviving DEF-076 fixes -- and this is why neither one was written.

This ran BEFORE D-109, and D-109 is its verdict: the shape it prices was retired instead of
fixed. The script is kept, and kept runnable, because the retirement rests on these numbers and
a finding whose command no longer runs is prose (CLAUDE.md rule 11). It is also now the only
place `ASSENT` and the assent scan exist -- `measure-control-set.py` imports the scan from here
to keep DEF-076's 44 and its 41-of-44 corroboration reproducible after the shape went.

DEF-076 left three candidates and the hand-labelled subset is struck: a person as the source
of truth is the thing D-040 and docs/02 SS5's gauntlet removed. What is left is the window and
a fourth shape, and both have been argued and neither measured.

  the window   `RequiresUserAssent` reads only the LAST user message before the call. The
               docstring prices the wide window's failure -- "a yes given to an earlier,
               different action" -- and never prices the narrow one's. This sweeps k = 1, 2,
               3, all and prints what each k silences.
  the shape    a fourth shape would say "the user's own request authorises the call". That is
               a TEXT match, and `RequiresUserAssent` is already the only text-matching shape
               and the only broken one. So the question is whether a mechanical version is
               even possible: does the last user message carry the tool's own rarest name
               token? Printed with its base rate, because a test that fires everywhere has
               measured nothing (CLAUDE.md rule 1).

The rarest token is derived from tau2's own tool vocabulary rather than a stop list written
here -- a hand-typed list of "generic" words would be the same guess as lengthening ASSENT.

Reads nothing from `src/`. The window sweep reimplemented the assent scan locally so that
`gate/predicate.py` stayed untouched until a measurement said what to change. It said: remove it.
That local copy is the reason this file still runs.

    uv run python scripts/measure-assent-window.py
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

_tier1 = importlib.import_module("measure-tier1")
_pred = importlib.import_module("measure-predicate")

# policy.md:16 states the requirement and gives one word for it -- "explicit user confirmation
# (yes)". The rest are the ordinary ways a simulated user says yes. Lived in
# `measure-predicate.py` until D-109 retired the shape; it is kept here because this script is
# the record of WHY it was retired, and a finding whose command no longer runs is prose.
ASSENT = (
    "yes", "yeah", "yep", "correct", "confirm", "go ahead", "please do", "sounds good",
    "that's right", "thats right", "sure", "ok", "okay", "proceed", "do it", "let's do",
)

WINDOWS = (1, 2, 3, 0)  # 0 means every earlier user message


def rarest(tools: list[str]) -> dict[str, str]:
    """Each tool's least-shared name token, from the tool vocabulary itself.

    `return_delivered_order_items` and `cancel_pending_order` share `order`; what tells them
    apart is `delivered` and `cancel`. Taking the rarest token is how that is found without a
    stop list, which would be a hand-authored guess of exactly the kind ASSENT already is.
    """
    freq: Counter[str] = Counter(t for name in tools for t in set(name.split("_")))
    return {name: min(set(name.split("_")), key=lambda t: (freq[t], t)) for name in tools}


def unconfirmed(messages: list[dict], writes: set[str], k: int = 1) -> bool:
    """True if some write call has no ASSENT phrase in the k user messages before it.

    k = 1 is what the retired `RequiresUserAssent` did, and it reproduces DEF-076's 44 firings
    on the clean set exactly -- which is what licenses reading the other windows off the same
    scan. Kept as one function so this file and `measure-control-set.py` cannot drift.
    """
    for i, m in enumerate(messages):
        for call in m.get("tool_calls") or []:
            if call.get("requestor", "assistant") != "assistant":
                continue
            if call.get("name") not in writes:
                continue
            said = user_before(messages, i, k)
            if not any(p in one for one in said for p in ASSENT):
                return True
    return False


def user_before(messages: list[dict], i: int, k: int) -> list[str]:
    """The k most recent user messages before message i, most recent first. k = 0 means all."""
    said = [
        str(m.get("content") or "").lower()
        for m in reversed(messages[:i])
        if m.get("role") == "user"
    ]
    return said if k == 0 else said[:k]


def main() -> None:
    """Sweep the window and test the fourth shape's premise. No model, no quota."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    files = _tier1.corpus_files()
    from tau2.utils.utils import DATA_DIR

    moved = _tier1.moved_tasks(files, Path(DATA_DIR) / "tau2" / "domains" / "retail" / "tasks.json")
    writes = _pred.write_tools()
    token = rarest(writes)
    logging.info(
        "── milestone 1/3 · %d write tool(s), rarest token each: %s",
        len(writes),
        ", ".join(f"{k}→{v}" for k, v in sorted(token.items())),
    )

    n: Counter[str] = Counter()
    for f in files:
        for s in json.loads(f.read_text())["simulations"]:
            if str(s["task_id"]) in moved:
                continue
            info = s.get("reward_info") or {}
            clean = bool((info.get("db_check") or {}).get("db_match")) and all(
                a.get("action_match") for a in (info.get("action_checks") or [])
            )
            side = "clean" if clean else "dirty"
            n[side] += 1
            messages = s["messages"]
            named = False
            for i, m in enumerate(messages):
                for call in m.get("tool_calls") or []:
                    if call.get("requestor", "assistant") != "assistant":
                        continue
                    name = call.get("name")
                    if name in token:
                        last = user_before(messages, i, 1)
                        named = named or any(token[name] in one for one in last)
            for k in WINDOWS:
                n[f"w{k}|{side}"] += unconfirmed(messages, set(token), k)
            # Base rate: the fourth shape's test over every session carrying a write call,
            # firing or not. Without it, "26 of 44 name the action" is a numerator alone.
            if any(m.get("tool_calls") for m in messages):
                n[f"named|{side}"] += named
                n[f"haswrite|{side}"] += 1

    logging.info(
        "── milestone 2/3 · %d clean, %d dirty in the adopted corpus", n["clean"], n["dirty"]
    )
    logging.info("")
    logging.info("%-22s %10s %10s %10s", "assent window", "on CLEAN", "on DIRTY", "clean share")
    for k in WINDOWS:
        c, d = n[f"w{k}|clean"], n[f"w{k}|dirty"]
        label = "last message only (now)" if k == 1 else (f"last {k}" if k else "every earlier")
        logging.info("%-22s %10d %10d %9.1f%%", label, c, d, 100 * c / max(c + d, 1))

    logging.info("")
    logging.info("── milestone 3/3 · the fourth shape's premise, with its base rate")
    for side in ("clean", "dirty"):
        hit, tot = n[f"named|{side}"], n[f"haswrite|{side}"]
        logging.info(
            "  rarest token in the last user message, %-5s %4d of %4d  %5.1f%%",
            side,
            hit,
            tot,
            100 * hit / max(tot, 1),
        )


if __name__ == "__main__":
    main()
