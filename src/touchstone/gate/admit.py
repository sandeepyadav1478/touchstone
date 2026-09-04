"""P2 -- admission: the three mechanical gates between a handed-over candidate and the suite.

D-084 cut five gates to three. `not_a_void` was dropped rather than stubbed, because a gate
that cannot fail reads exactly like a gate that passes; it returns with P2.4, when a run of
ours can produce a void at all. `not_flaky` merged into `reproducible`, which is one predicate
rather than two names for one.

Nothing here holds a model, and nothing here runs inside the loop (D-086 SS D): the input is a
FINISHED candidate, so admission cannot spend an attempt or change a verdict. All it can do is
refuse, and each refusal is aimed at a specific way a bad case poisons a suite that has to be
trusted for months. docs/02 SS5 states the three failures; this file states the checks.

    reproducible   fires on every trial of its group, not only the one it was mined from
    distinct       no admitted case already covers this task
    justified      the citation resolves to a line the policy actually has

`cleared_by` returns the gate SET rather than a bool (D-084 SS A.4). The list has changed once
already, five to three, and is specified to change again when `not_a_void` returns -- so a
case recording only that it was admitted could not be told from one admitted under a different
set, and reading the set is what makes that a read instead of a migration.
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import TYPE_CHECKING

from touchstone.gate.predicate import evaluate
from touchstone.loop import corpus

if TYPE_CHECKING:
    from collections.abc import Container, Sequence

    from touchstone.gate.predicate import Predicate

__all__ = ["GATES", "admitted", "cleared_by", "distinct", "justified", "reproducible"]

GATES = ("reproducible", "distinct", "justified")

# Filename loose, line number strict -- see `justified`.
_CITATION = re.compile(r"(?:^|/)policy\.md:(\d+)$")


@lru_cache(maxsize=1)
def _groups() -> dict[tuple[str, str], tuple[corpus.Session, ...]]:
    """The corpus indexed by (task_id, agent): one baseline's repeated trials of one task.

    Grouped on the pair and not on `task_id` alone. The corpus is four baselines, and a
    predicate that fires on all four trials of one is a different claim from one that fires on
    all sixteen. `reproducible` asks the first, because the session being admitted came from
    one baseline and that run is what it has evidence about.
    """
    out: dict[tuple[str, str], list[corpus.Session]] = {}
    for session in corpus.load():
        out.setdefault((session.task_id, session.agent), []).append(session)
    return {key: tuple(group) for key, group in out.items()}


def reproducible(predicate: Predicate, session: corpus.Session) -> bool:
    """Does the candidate fire on every trial of its group, or only on the one it was mined on?

    D-084 SS A.2 states the merged gate as: fails on all k trials, k distinct seeds. The
    specimen supplies k directly: retail is 107 tasks x 4 baselines x 4 trials, which
    is 428 groups of exactly 4. A predicate that fires on one trial and not its siblings is
    keying on a sampling accident, and clearing it puts a case in the suite that fails an agent
    at random -- somebody then debugs a regression that never happened.

    Measured 2026-09-04 with one RequiresPriorTool candidate: it fires on 342 of the 428 groups
    and on all four trials in 328 of them, so this refuses 14, 4.1%. Nothing here rests on the
    seeds being replayable; D-084 SS C leaves replay identity unverified and the check is over
    trials that were already run.

    A group of one cannot support the claim and is refused. That branch cannot fire on retail,
    where every group is 4 -- it is here for the specimen swap D-062 leaves open, and it is
    stated rather than dropped for the reason D-084 SS A.1 gives about gates that cannot fail.
    """
    group = _groups().get((session.task_id, session.agent), ())
    return len(group) > 1 and all(evaluate(predicate, s.messages) for s in group)


def distinct(session: corpus.Session, covered: Container[str]) -> bool:
    """Is this task already covered by an admitted case?

    D-083's task_id half, and only that half. The signature half stays deferred behind D-078
    SS11.2 (D-084 SS A.3): a bucketing heuristic carrying one to two orders of magnitude of
    error must not hold an UNDOABLE rejection, and a recorded `duplicate_of` is reversible
    where a refusal is not.

    Takes the covered set rather than reading the suite. The suite's on-disk shape is the next
    commit, and a gate that owned a file format would have to change whenever the format did.
    """
    return session.task_id not in covered


def justified(predicate: Predicate) -> bool:
    """Does the citation resolve to a line the policy actually has?

    docs/02 SS5 refuses a case nobody can ever delete: six months on, a failure with no rule
    behind it cannot be told from something mined in a hurry, so it stays forever and the suite
    ratchets on cases no one can defend. The rule text and the arrival date are the case's own
    fields; the one field a model wrote is the citation, and it is the one worth checking.

    NOT a non-empty check. `extract._predicate` already raises on an empty `rule` or `source`,
    so repeating that here would be a clause that cannot fail. What extract does not check is
    whether the citation RESOLVES: it accepts "the policy" and "policy.md:9999" alike, and each
    is a rule nobody can go and read.

    Filename loose, line number strict. The curator's prompt inserts the policy under "The
    policy, line-numbered" and never names the file, so the model picks the name -- `tier1.py`
    writes `retail/policy.md:132` and the loop's fixtures write `policy.md:20`. The line number
    is the part the prompt does specify, so it is the part that can be held to.
    """
    match = _CITATION.search(predicate.source.strip())
    if not match:
        return False
    return 1 <= int(match.group(1)) <= len(corpus.policy_text().splitlines())


def cleared_by(
    predicate: Predicate, session: corpus.Session, covered: Container[str]
) -> tuple[str, ...]:
    """The gates this candidate passed, in `GATES` order.

    Every gate is run even once one has failed. A refusal that stopped at the first failure
    would record which gate happened to be checked first rather than which the case failed,
    and the difference is the whole reason the field is a set.
    """
    passed = {
        "reproducible": reproducible(predicate, session),
        "distinct": distinct(session, covered),
        "justified": justified(predicate),
    }
    return tuple(gate for gate in GATES if passed[gate])


def admitted(cleared: Sequence[str]) -> bool:
    """All three. Derived from `GATES` so the count is not written down a second place."""
    return len(cleared) == len(GATES)
