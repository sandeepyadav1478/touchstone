"""The adopted corpus and the answer key D-108 settled, in the form `mine` needs them.

The four `measure-*.py` scripts each rebuild this from the same files. They are NOT refactored
onto this module and that is deliberate: each one is the recorded query behind a published
figure, and a number whose derivation has been edited is a different number. Two independent
derivations agreeing is evidence; one shared function would only be consistency.

So this is checked against them rather than substituted for them. It reads 1,712 adopted,
778 anomalous, 934 clean and the same seven excluded tasks that `measure-tier1.py` prints.

Two populations, and mixing them is the whole risk:

    1,824   every shipped retail simulation, all 114 tasks
    1,712   the 107 tasks whose gold actions did not move between the shipped runs and today's
            `tasks.json` -- the corpus D-080 adopted, and the only one `mine` sees

Inside the 1,712 the answer key is D-108's: 778 anomalous, 934 clean, on the two signals a
committed command can rebuild. Not 834/878 -- that pair needs a third signal, 56 unconfirmed
writes, whose regex lived in a scratch script and was never committed, so a recall quoted
against 834 divides by a figure nothing in this repo produces.

The corpus is four third-party agents behind a `gpt-4.1` simulator (D-080 ceiling 1). It is a
corpus and never a baseline; no number taken from it is ours.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

__all__ = [
    "Session",
    "anomalous",
    "clean",
    "data_dir",
    "files",
    "is_anomalous",
    "load",
    "moved_tasks",
]


@dataclass(frozen=True)
class Session:
    """One adopted simulation, with the label the answer key gives it.

    `agent` is the baseline that produced it, kept because the corpus is four of them and a
    finding that holds on one is a different claim from one that holds on all four.
    """

    id: str
    task_id: str
    trial: int
    agent: str
    anomalous: bool
    termination_reason: str
    messages: list[dict[str, Any]]


def data_dir() -> Path:
    """Where the specimen keeps its data, resolved through its own constant.

    Imported inside the function: `TAU2_DATA_DIR` is read at tau2's import, which costs 1.71 s,
    and a module constant would put that in front of every caller that only wanted a type.
    """
    from tau2.utils.utils import DATA_DIR

    return Path(DATA_DIR)


def files() -> list[Path]:
    """The four shipped retail baselines."""
    return sorted((data_dir() / "tau2" / "results" / "final").glob("*_retail_*.json"))


def _gold(actions: list[dict[str, Any]]) -> list[tuple[str, str, str]]:
    """A gold action list flattened to something comparable across two files."""
    return [
        (
            a["name"],
            a.get("requestor") or "assistant",
            json.dumps(a.get("arguments") or {}, sort_keys=True),
        )
        for a in actions
    ]


@lru_cache(maxsize=1)
def moved_tasks() -> frozenset[str]:
    """Tasks whose gold actions differ between a shipped run and today's `tasks.json`.

    Compared on name, requestor and arguments rather than the raw dict: the shipped copies
    carry serialisation differences that make a plain `==` report 112 of 114 as moved, which
    is a comparison failing rather than a corpus that changed.
    """
    tasks_json = data_dir() / "tau2" / "domains" / "retail" / "tasks.json"
    today = {
        str(t["id"]): _gold((t.get("evaluation_criteria") or {}).get("actions") or [])
        for t in json.loads(tasks_json.read_text())
    }
    moved = set()
    for f in files():
        for t in json.loads(f.read_text())["tasks"]:
            shipped = _gold((t.get("evaluation_criteria") or {}).get("actions") or [])
            if shipped != today.get(str(t["id"])):
                moved.add(str(t["id"]))
    return frozenset(moved)


def is_anomalous(sim: Mapping[str, Any]) -> bool:
    """D-108's answer key for one simulation, and the only place it is spelled out.

    Fails the DB check, or passes it with any failed `action_check`. The 371 that pass DB with
    a failed action check are why the second half exists: they were sitting in the silence set,
    where a correct predicate catching a process failure was rejected as a false positive.

    The third signal docs/02 names is deliberately absent, not forgotten. It is unbuildable,
    and the confirmation predicate was not allowed to stand in for it -- that would define the
    control set with the predicate it exists to judge. D-109 then retired that predicate for a
    related reason: the key cannot see confirmation, so this function is silent on it either
    way, and a gate whose subject the key does not score cannot be cleared against it.
    """
    info = sim.get("reward_info") or {}
    return not (info.get("db_check") or {}).get("db_match") or not all(
        a.get("action_match") for a in (info.get("action_checks") or [])
    )


@lru_cache(maxsize=1)
def load() -> tuple[Session, ...]:
    """Every adopted simulation, labelled. Cached because it is 91 MB of JSON across 4 files.

    Never called at import. `mine` pays it once per process and the unit suite never pays it
    at all, which is what keeps the whole suite under the 2 s budget.
    """
    moved = moved_tasks()
    out: list[Session] = []
    for f in files():
        agent = f.name.split("_retail_")[0]
        for s in json.loads(f.read_text())["simulations"]:
            if str(s["task_id"]) in moved:
                continue
            out.append(
                Session(
                    id=str(s["id"]),
                    task_id=str(s["task_id"]),
                    trial=int(s["trial"]),
                    agent=agent,
                    anomalous=is_anomalous(s),
                    termination_reason=str(s.get("termination_reason") or ""),
                    messages=s["messages"],
                )
            )
    return tuple(out)


def anomalous() -> tuple[Session, ...]:
    """The 778 the router reads one at a time (D-082 A) and the recall denominator."""
    return tuple(s for s in load() if s.anomalous)


def clean() -> tuple[Session, ...]:
    """The 934 a candidate must be silent on. Seven are DEF-075 and 44 are DEF-076.

    Both are sessions that are clean on the two mechanical signals and break a stated rule
    anyway, so a correct predicate firing on one is rejected. The rates are recorded rather
    than corrected, because the cost of meeting them later without a name is an afternoon
    spent doubting a rule that was right.
    """
    return tuple(s for s in load() if not s.anomalous)
