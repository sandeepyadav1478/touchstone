#!/usr/bin/env python3
"""Score a stored τ² simulation twice and prove the two runs are byte-identical.

[D-014](DECISIONS.md) requires the scorer be decoupled from whatever produced the trace, and
D-080 re-aimed that requirement at the shipped corpus: the proof no longer needs a run of ours
to exist. This is phase 1's exit-gate box for it.

A script rather than a CLI flag, and the reason is a ceiling rather than taste. `touchstone
score` deliberately takes a version and never a path, because an arbitrary `--results` opens a
route to publish τ²'s four third-party baselines under one of our version labels — D-080 ceiling
1 forbids quoting their numbers. So this reads the corpus, calls `score()` directly, and never
touches `results/` or `write()`. Nothing it computes is published; the only output is whether two
dictionaries match.

Three milestones, each a different way the property can be false:

  1. Two calls on the same input agree, byte for byte through `json.dumps`.
  2. Input order does not change the answer — the corpus is re-read reversed. A scorer that
     accumulates into a dict keyed by insertion order passes milestone 1 and fails here.
  3. No model was called. Asserted by the absence of a network stack, not by reading the code:
     `score` is imported and run with `socket.socket` replaced by something that raises.

Milestone 3 proves the scorer made no call, never that the numbers are right. A pure function
that computes the wrong thing is perfectly deterministic; `tests/unit/test_score.py` is where
correctness lives.

    uv run python scripts/check-determinism.py
    uv run python scripts/check-determinism.py --file <a τ² results json>
"""

from __future__ import annotations

import argparse
import json
import logging
import socket
import sys
from pathlib import Path
from typing import Any

from touchstone.config import K
from touchstone.loop.score import score


def corpus_files() -> list[Path]:
    """The shipped retail baselines, read from τ²'s own data directory.

    Read through τ²'s path constant rather than a path of ours: a re-derived path gives a check
    that can pass while the run fails, which is the reason `freeze-benchmark` does the same.
    """
    from tau2.utils.utils import DATA_DIR

    return sorted((Path(DATA_DIR) / "tau2" / "results" / "final").glob("*_retail_*.json"))


def no_network() -> None:
    """Replace `socket.socket` with something that raises, so a model call cannot be silent.

    Checking that no call happened by reading the source is checking the code someone already
    wrote; this checks the code that actually runs, including anything a dependency imported.
    """

    def refuse(*_: object, **__: object) -> None:
        raise AssertionError("the scorer opened a socket — D-007 says it makes no model call")

    socket.socket = refuse  # type: ignore[assignment,misc]


def main() -> int:
    """Score twice, score reversed, and compare. Returns an exit code."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", type=Path, help="A τ² results json. Default: every retail baseline.")
    ap.add_argument("--k", type=int, default=K)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)

    files = [args.file] if args.file else corpus_files()
    if not files:
        logging.error("FAIL — no corpus file found. Is TAU2_DATA_DIR set? `touchstone doctor`")
        return 1

    no_network()
    logging.info("── milestone 3/3 · sockets refused before the first score() call")

    failures: list[str] = []
    total = 0
    for f in files:
        sims: list[dict[str, Any]] = json.loads(f.read_text())["simulations"]
        total += len(sims)
        first = json.dumps(score(sims, args.k), sort_keys=True)
        again = json.dumps(score(sims, args.k), sort_keys=True)
        # `list(reversed(...))`: a new list, so the second call cannot see a mutation the
        # first one made to the input — which would pass milestone 1 by agreeing with itself.
        flipped = json.dumps(score(list(reversed(sims)), args.k), sort_keys=True)

        name = f.name
        if first != again:
            failures.append(f"{name}: two calls on the same input disagree")
        elif first != flipped:
            failures.append(f"{name}: the answer depends on input ORDER")
        else:
            logging.info("  ✓ stable   %-58s %d simulations", name, len(sims))

    logging.info("── milestone 1/3 · %d file(s) scored twice, k=%d", len(files), args.k)
    logging.info("── milestone 2/3 · %d file(s) re-scored in reverse order", len(files))

    for f in failures:
        logging.error("  ✗ %s", f)
    if failures:
        logging.error("\nFAIL — %d file(s) not deterministic", len(failures))
        return 1

    logging.info("\nPASS — %d simulations, identical twice and order-independent", total)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
