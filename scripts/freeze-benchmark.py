#!/usr/bin/env python3
"""Freeze the benchmark tier — the task IDs and the hash they were read at (P1.3).

⛔ **IDs and a hash, never task bytes.** Vendoring the corpus would make this repo its
owner again, which is what [D-062] exists to stop. The tasks stay upstream at the pinned
commit; `suite/benchmark/manifest.json` records *which* ones and *what the file said* when
they were chosen.

Two modes and they share one function, so the check cannot drift from the generator:

    uv run python scripts/freeze-benchmark.py            # write the manifest
    uv run python scripts/freeze-benchmark.py --check    # invariant 7, for CI

⚠️ **`--check` is invariant 7** ([docs/01] §6): *the task file is never modified*. It
guards a file we do not own, so a silent upstream update fails here rather than quietly
moving what the version table measures.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "suite" / "benchmark" / "manifest.json"

# D-098. Both halves are load-bearing and neither is a preference:
#
#   SPLIT — τ²'s own held-out set, read by `retail/environment.py:49 get_tasks_split()`,
#   which `get_tasks()` filters on. It is live upstream code, not stranded data, so the
#   subset is traceable to a function a run actually calls. ⛔ The DEFAULT split is
#   `base`, which is `train + test` CONCATENATED — all 114 in a different order from
#   tasks.json. A reader who takes "base" for "the whole file" gets the right ids in the
#   wrong order, and a hash over a list is a hash over its order.
#
#   N — D-024's benchmark tier is n=10, frozen; adding to it resets the baseline. The
#   binding constraint is the five-hour quota (config.py), since 10 x k=3 is already 30
#   simulations.
SPLIT = "test"
N = 10


def select(split_ids: list[str], n: int = N) -> list[str]:
    """Pick the frozen subset: the first `n` of the split, numerically ordered.

    ⛔ **A prefix, not a sample.** No seed to remember, no judgement to defend, and one
    line re-derives it from the pin. A difficulty-weighted or hand-picked subset would be
    the cherry-pick the freeze exists to prevent — and it could not be checked by a
    stranger, which is the only property that makes "frozen" mean anything.

    ⚠️ **Sorted here rather than trusted.** The split file happens to be in numeric order
    today; `sorted(key=int)` says what the order IS instead of inheriting whatever the
    next upstream edit leaves behind. String sort would give 0, 1, 10, 100 — the ids are
    decimal strings, so the collation has to be pinned with the hash.

    Args:
        split_ids: The task ids of one upstream split.
        n: How many to freeze.

    Returns:
        `n` task ids, ascending numerically.
    """
    return sorted(split_ids, key=int)[:n]


def build() -> dict:
    """Read the live specimen and produce the manifest that would freeze it.

    ⚠️ **It reads τ²'s own path constants**, the same reason `doctor._tau2_data` does: a
    re-derived path gives a check that can pass while the run fails. The import is local
    because it costs ~1.7 s and runs τ²'s data resolution as a side effect.

    Returns:
        The manifest dict — ids, counts, and the sha256 of the file they were read from.
    """
    from tau2.domains.retail.environment import get_tasks_split
    from tau2.domains.retail.utils import RETAIL_TASK_SET_PATH

    tasks_path = Path(RETAIL_TASK_SET_PATH)
    raw = tasks_path.read_bytes()
    tasks = json.loads(raw)
    ids = select(get_tasks_split()[SPLIT])

    by_id = {t["id"]: t for t in tasks}
    missing = [i for i in ids if i not in by_id]
    if missing:
        raise SystemExit(f"selected ids absent from tasks.json: {missing}")

    return {
        "tier": "benchmark",
        "domain": "retail",
        "tau2_commit": "a2c024725189",
        "source": "data/tau2/domains/retail/tasks.json",
        "selection": f"sorted(split_tasks.json['{SPLIT}'], key=int)[:{N}]",
        "tasks_sha256": hashlib.sha256(raw).hexdigest(),
        "tasks_total": len(tasks),
        "split_total": len(get_tasks_split()[SPLIT]),
        "task_ids": ids,
        "reward_basis": {i: by_id[i]["evaluation_criteria"]["reward_basis"] for i in ids},
    }


def main(argv: list[str]) -> int:
    """Write the manifest, or compare the live specimen against the frozen one.

    Args:
        argv: Command-line arguments; `--check` verifies instead of writing.

    Returns:
        0 on success, 1 when the live specimen no longer matches the manifest.
    """
    live = build()
    if "--check" not in argv:
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST.write_text(json.dumps(live, indent=2) + "\n")
        print(f"wrote {MANIFEST.relative_to(ROOT)} — {len(live['task_ids'])} ids, "
              f"sha256 {live['tasks_sha256'][:12]}…")
        return 0

    if not MANIFEST.exists():
        print(f"FAIL — {MANIFEST.relative_to(ROOT)} does not exist", file=sys.stderr)
        return 1

    frozen = json.loads(MANIFEST.read_text())
    drift = [k for k in live if frozen.get(k) != live[k]]
    if drift:
        for k in drift:
            print(f"FAIL — {k}: frozen {frozen.get(k)!r} != live {live[k]!r}", file=sys.stderr)
        print("\ninvariant 7: the task file is never modified. An upstream change here is a "
              "CI failure, not a goalpost to move.", file=sys.stderr)
        return 1

    print(f"PASS — {len(frozen['task_ids'])} frozen ids, tasks.json unchanged "
          f"({frozen['tasks_sha256'][:12]}…)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
