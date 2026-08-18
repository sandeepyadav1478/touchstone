"""The corpus: one topology, ten renderers, and the deletion that makes the eleventh class.

Four rules govern everything here (docs/01 §4):

1. **Seeded and reproducible.** Same seed, byte-identical suite. ⛔ No clock, no `uuid`, no set
   iteration order, no unsorted dict — a benchmark whose bytes move cannot be hashed, and
   `benchmark_hash` is what makes two versions comparable at all.
2. **The truth is never rendered.** `GroundTruth` is built beside the `Incident`, never inside
   it. Invariant 1, and `tests/unit/test_invariants.py` checks the rendered JSON for it rather
   than trusting this sentence.
3. **Every case carries a plausible wrong answer.** The distractor is a *repeating* template,
   because that is what the Loghub read measured — a single odd line reads as a clue, the same
   line thirty times reads as background (docs/01 §4).
4. **`insufficient_evidence` is a deletion, not a renderer.** Take a rendered case, drop the
   distinguishing bucket, keep everything else. That is why the correct answer is *escalate*
   and not a guess: the signal that would settle it is genuinely not there.
"""

from __future__ import annotations

import hashlib
import json
import random
from datetime import timedelta
from operator import itemgetter
from typing import TYPE_CHECKING, NamedTuple

from touchstone.config import INTERVAL_SECONDS
from touchstone.domain import (
    Evidence,
    GroundTruth,
    Incident,
    RootCause,
    ServiceNode,
    TimeWindow,
)
from touchstone.incidents.renderers import EPOCH, POINTS, RENDERERS, Rendered, Scene

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# The topology. One graph, shared by every case (docs/01 §2).
# ---------------------------------------------------------------------------

# Named after the OpenTelemetry demo's service graph — names, shapes and edges only, read from
# opentelemetry.io and never vendored (D-029, docs/01 §4). One shared topology across all cases
# so that a version cannot get better by memorising a per-case graph: the only thing that varies
# between cases is the evidence.
#
# ⚠️ `accounting` is load-bearing. It reaches `postgres` and nothing reaches it, so it is
# unreachable by walking edges *from* an alert — which is exactly what makes `noisy_neighbor`
# satisfy docs/01 §3's "the cause is in a service with no dependency edge to the alerting one".
# Deleting that asymmetry would quietly make one of the ten classes unsolvable-by-design.
TOPOLOGY: list[ServiceNode] = [
    ServiceNode(name="accounting", kind="worker", depends_on=["postgres", "kafka"]),
    ServiceNode(name="cart", kind="api", depends_on=["valkey"]),
    ServiceNode(
        name="checkout",
        kind="api",
        depends_on=["cart", "payment", "shipping", "product-catalog", "kafka"],
    ),
    ServiceNode(name="flagd", kind="external", depends_on=[]),
    ServiceNode(name="fraud-detection", kind="worker", depends_on=["kafka"]),
    ServiceNode(
        name="frontend",
        kind="api",
        depends_on=["checkout", "cart", "product-catalog", "recommendation", "shipping"],
    ),
    ServiceNode(name="kafka", kind="queue", depends_on=[]),
    ServiceNode(name="payment", kind="api", depends_on=["flagd"]),
    ServiceNode(name="postgres", kind="datastore", depends_on=[]),
    ServiceNode(name="product-catalog", kind="api", depends_on=["postgres"]),
    ServiceNode(name="quote", kind="api", depends_on=["rate-provider"]),
    ServiceNode(name="rate-provider", kind="external", depends_on=[]),
    ServiceNode(name="recommendation", kind="worker", depends_on=["product-catalog"]),
    ServiceNode(name="shipping", kind="api", depends_on=["quote"]),
    ServiceNode(name="valkey", kind="cache", depends_on=[]),
]

WINDOW = TimeWindow(start=EPOCH, end=EPOCH + timedelta(seconds=INTERVAL_SECONDS * (POINTS - 1)))


class CaseSpec(NamedTuple):
    """One row of the suite: which mechanism to draw, with which seed, and whether to keep it.

    Attributes:
        id: The case id, and the stem of its file.
        cause: The key into `RENDERERS`. ⚠️ For a deleted case this is the mechanism that was
            *drawn*, not the answer — the answer is `insufficient_evidence`.
        seed: The only source of variation. Distinct per case so two cases cannot accidentally
            share a draw.
        resolvable: `False` runs the deletion path.
    """

    id: str
    cause: str
    seed: int
    resolvable: bool


# The ten. Eight diagnosable and two deleted — 20%, inside docs/01 §3's "2 to 3 of 10" target.
#
# ⚠️ **`config_drift` and `noisy_neighbor` are drawn but never scored as themselves**, because
# they are the two the deletion path consumes. That is a real limit of v1 of this benchmark and
# it is stated in `suite/benchmark/README.md` rather than left for someone to discover: a
# version could answer those two classes wrongly in every case and the score would not move.
# The alternative — a twelfth and thirteenth case — is a benchmark version bump, so it waits.
SUITE: list[CaseSpec] = [
    CaseSpec("inc-001", "db_pool_exhausted", 101, resolvable=True),
    CaseSpec("inc-002", "slow_query_after_migration", 202, resolvable=True),
    CaseSpec("inc-003", "cache_stampede", 303, resolvable=True),
    CaseSpec("inc-004", "queue_backlog_hol", 404, resolvable=True),
    CaseSpec("inc-005", "bad_deploy_regression", 505, resolvable=True),
    CaseSpec("inc-006", "upstream_timeout", 606, resolvable=True),
    CaseSpec("inc-007", "disk_pressure", 707, resolvable=True),
    CaseSpec("inc-008", "memory_leak_oom", 808, resolvable=True),
    CaseSpec("inc-009", "config_drift", 909, resolvable=False),
    CaseSpec("inc-010", "noisy_neighbor", 1010, resolvable=False),
]

# The service the deleted evidence would have implicated, per drawn mechanism. ⛔ Only read for
# a non-resolvable case, where docs/05 §1 never compares `affected_service` at all — it is
# recorded so the rationale can say what was removed, not so anything can score against it.
_DELETED_TARGET = {"config_drift": "payment", "noisy_neighbor": "accounting"}


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------


def _merge(*buckets: Evidence) -> Evidence:
    """Combine evidence buckets and put every list in a total order.

    Sorting matters for rule 1, not for looks. The renderers place log lines at random points,
    so the emission order encodes the rng call sequence; sorting on the record itself means a
    later change to *how many* rng draws a renderer makes cannot reorder unrelated lines.
    """
    return Evidence(
        series=sorted(
            (s for b in buckets for s in b.series), key=lambda s: (s.service, s.metric)
        ),
        logs=sorted(
            (line for b in buckets for line in b.logs),
            key=lambda line: (line.at, line.service, line.level, line.message),
        ),
        deploys=sorted(
            (d for b in buckets for d in b.deploys), key=lambda d: (d.at, d.service, d.sha)
        ),
    )


def _rationale(spec: CaseSpec, drawn: Rendered) -> str:
    """The answer key's prose: why this is the cause, or why nothing can settle it.

    ⛔ Never rendered into the incident. It is read by a human auditing the suite and by the
    judge at scoring time, and by nothing that runs before a verdict exists.
    """
    if spec.resolvable:
        return (
            f"{spec.cause} in {drawn.specialist} territory. The distinguishing evidence is "
            f"{_names(drawn.distinguishing)}, which the alert on {drawn.alert.service} does not "
            f"show. The plausible wrong answer is {drawn.rival}, supported by the ambient "
            f"signals and by the distractor template."
        )
    return (
        f"Drawn as {spec.cause} and then stripped: {_names(drawn.distinguishing)} was removed, "
        f"and nothing that remains separates {spec.cause} from {drawn.rival}. Both stay "
        f"standing on the ambient evidence alone, so the correct action is to escalate rather "
        f"than to pick one."
    )


def _names(bucket: Evidence) -> str:
    """`service.metric` for each series in a bucket, plus a count of its log lines."""
    series = ", ".join(f"{s.service}.{s.metric}" for s in bucket.series)
    logs = f"{len(bucket.logs)} log lines" if bucket.logs else ""
    return " and ".join(part for part in (series, logs) if part) or "nothing"


def generate_case(spec: CaseSpec) -> tuple[Incident, GroundTruth]:
    """Draw one case and its answer key.

    Args:
        spec: The row from `SUITE`.

    Returns:
        The incident the agent sees, and the truth it never sees.

    Raises:
        KeyError: If `spec.cause` names no renderer.
    """
    drawn = RENDERERS[spec.cause](Scene(rng=random.Random(spec.seed)))

    # Rule 4, in one line: the deletion path is the resolvable case minus one bucket.
    kept = (drawn.ambient, drawn.distinguishing) if spec.resolvable else (drawn.ambient,)

    incident = Incident(
        id=spec.id,
        alert=drawn.alert,
        window=WINDOW,
        topology=TOPOLOGY,
        evidence=_merge(*kept),
        seed=spec.seed,
    )
    truth = GroundTruth(
        incident_id=spec.id,
        root_cause_id=(
            RootCause(spec.cause) if spec.resolvable else RootCause.INSUFFICIENT_EVIDENCE
        ),
        affected_service=(
            _service_of(drawn) if spec.resolvable else _DELETED_TARGET[spec.cause]
        ),
        resolvable=spec.resolvable,
        rationale=_rationale(spec, drawn),
        # D-042: derived from the split rather than restated. Whichever specialist's tools reach
        # the distinguishing bucket is the one that could have answered — and when that bucket
        # is gone, no specialist could, which is what `None` means here.
        required_specialist=drawn.specialist if spec.resolvable else None,
    )
    return incident, truth


def _service_of(drawn: Rendered) -> str:
    """The service the distinguishing evidence points at.

    ⚠️ Read off the evidence, not declared beside it. A renderer that names one service in its
    answer key and emits its decisive signal on another is the bug this closes by construction,
    and it is the bug the `alert.service` trap makes easy to write.
    """
    if drawn.distinguishing.series:
        return drawn.distinguishing.series[0].service
    return drawn.distinguishing.logs[0].service


def generate_suite() -> list[tuple[Incident, GroundTruth]]:
    """Every case in `SUITE`, in id order."""
    return [generate_case(spec) for spec in SUITE]


# ---------------------------------------------------------------------------
# Writing and hashing
# ---------------------------------------------------------------------------

# docs/09 §5, verbatim. The manifest fields that are part of the measurement; everything else in
# an entry is provenance prose and must never be able to invalidate a past score.
HASHED_FIELDS = ("id", "seed", "root_cause_id", "precedent")

def _canon(payload: object) -> str:
    """Canonical JSON: sorted keys, no spaces.

    ⛔ One spelling, used for both the files on disk and the bytes fed to the digest. Rule 1
    needs `git checkout` alone to be unable to change a hash, so key order and whitespace are
    fixed here rather than left to whichever call site writes next.
    """
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _dump(path: Path, payload: object) -> None:
    """Write canonical JSON with a trailing newline."""
    path.write_text(_canon(payload) + "\n")


def benchmark_hash(suite_dir: Path) -> str:
    """sha256 over what changes the measurement. Nothing else.

    Args:
        suite_dir: The tier directory — `suite/benchmark`. ⛔ The tier, not `suite/`, because
            `truth.json` lives inside each tier (docs/01 §2, DEF-005).

    Returns:
        The hex digest quoted in every results file and every row of the version table.
    """
    h = hashlib.sha256()
    manifest = json.loads((suite_dir / "manifest.json").read_text())
    for entry in sorted(manifest["cases"], key=itemgetter("id")):
        h.update(_canon({k: entry.get(k) for k in HASHED_FIELDS}).encode())
        h.update((suite_dir / f"{entry['id']}.json").read_bytes())
    h.update((suite_dir / "truth.json").read_bytes())
    return h.hexdigest()


def write_suite(suite_dir: Path, *, added: str) -> str:
    """Generate the suite, write the tier, and stamp it with its hash.

    Args:
        suite_dir: The tier directory to fill.
        added: The ISO date recorded as each case's arrival. ⛔ Passed in rather than read from
            the clock — `datetime.now()` here would make the manifest differ on every run, and
            the manifest is inside the hash.

    Returns:
        The `benchmark_hash` of what was written.
    """
    suite_dir.mkdir(parents=True, exist_ok=True)
    cases = generate_suite()

    for incident, _ in cases:
        _dump(suite_dir / f"{incident.id}.json", incident.model_dump(mode="json"))
    _dump(
        suite_dir / "truth.json",
        {truth.incident_id: truth.model_dump(mode="json") for _, truth in cases},
    )

    # ⚠️ `precedent` is deliberately absent at v1. It stratifies a memory experiment that has no
    # history corpus yet, and its *values* change when one arrives — so writing "none" now would
    # not avoid the version bump, only disguise it. docs/09 §5 budgets that bump; `entry.get`
    # hashes the missing key as null, which is stable.
    _dump(
        suite_dir / "manifest.json",
        {
            "version": "benchmark v1",
            "cases": [
                {
                    "id": spec.id,
                    "tier": "benchmark",
                    "root_cause_id": str(truth.root_cause_id),
                    "seed": spec.seed,
                    "added": added,
                    "added_in": "benchmark v1",
                    "origin": "generated",
                    "why": (
                        f"Covers {spec.cause}"
                        + ("" if spec.resolvable else ", stripped to make it unanswerable")
                        + f"; the plausible wrong answer is planted on {truth.affected_service}'s"
                        " neighbours."
                    ),
                }
                for spec, (_, truth) in zip(SUITE, cases, strict=True)
            ],
        },
    )

    digest = benchmark_hash(suite_dir)
    manifest = json.loads((suite_dir / "manifest.json").read_text())
    manifest["benchmark_hash"] = digest
    _dump(suite_dir / "manifest.json", manifest)
    return digest
