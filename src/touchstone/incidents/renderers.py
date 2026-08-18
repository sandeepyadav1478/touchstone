"""Ten cause renderers and the deletion path that makes the eleventh class.

Each renderer builds one failure **from its mechanism** and returns its evidence in two buckets:

* `ambient` — the baseline traffic, the neighbours, and at least one plausible-but-wrong signal.
  Present in every case (docs/01 §4 rule 3).
* `distinguishing` — the evidence that names the cause. ⛔ This is the bucket the deletion path
  removes to produce `insufficient_evidence` (docs/01 §4 rule 4), which is why it is a separate
  field rather than a comment: the eleventh class is *these ten minus one bucket*, and a renderer
  that cannot say which of its signals is decisive cannot be used that way.

The split also derives `required_specialist` (D-042) rather than restating it: whichever
specialist's tools reach the distinguishing bucket is the one that could have answered.

⚠️ **The log shapes here were measured, not remembered** — docs/01 §4, "What the read actually
produced". Two of three Loghub corpora contain no `ERROR` line at all in 2,000 lines, so the
signal usually rides *inside* a routine `INFO` line, and a distractor is a template repeated
dozens of times rather than one odd line.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from touchstone.config import INTERVAL_SECONDS
from touchstone.domain import Alert, Deploy, Evidence, LogLevel, LogLine, Point, Series

if TYPE_CHECKING:
    import random
    from collections.abc import Callable

    from touchstone.domain import Specialist

# The window every case covers: 30 minutes at the one interval, so `len(points)` is 60 for every
# series in every case and a missing series reads as absent rather than sparse (docs/09 §1).
WINDOW_MINUTES = 30
POINTS = WINDOW_MINUTES * 60 // INTERVAL_SECONDS

# ⛔ A fixed origin, never `datetime.now()`. Rule 1 of the generator is byte-identical output for
# the same seed, and a clock is the one input that cannot be seeded.
EPOCH = datetime(2026, 3, 14, 9, 0, tzinfo=UTC)

# Where the failure starts and where the alarm notices, in point indices. The 8-point gap is the
# lag RCAEval's cases show between first signal and detection, and it is what gives `timeline`
# something to find: the deploy or the ramp precedes the page.
ONSET = 24
FIRED = 32


@dataclass(frozen=True)
class Scene:
    """The fixed frame every renderer draws into: one seeded rng and one window.

    Attributes:
        rng: The case's seeded generator. ⛔ The only source of variation anywhere in a case.
    """

    rng: random.Random

    def at(self, index: int) -> datetime:
        """The timestamp of point `index`."""
        return EPOCH + timedelta(seconds=INTERVAL_SECONDS * index)


@dataclass(frozen=True)
class Rendered:
    """One case's evidence, split by whether it names the cause.

    Attributes:
        alert: What paged. ⚠️ Its `service` is where the alarm fired and is deliberately not the
            answer in roughly half the suite.
        ambient: Baseline and distractors. Survives the deletion path.
        distinguishing: The decisive evidence. ⛔ Removed to make `insufficient_evidence`.
        specialist: Whose tools reach `distinguishing`.
        rival: The cause a reader would land on once `distinguishing` is gone, named so the
            deletion path can say in `rationale` which two hypotheses were left standing.
    """

    alert: Alert
    ambient: Evidence
    distinguishing: Evidence
    specialist: Specialist
    rival: str


# ---------------------------------------------------------------------------
# Shapes. Five, because five cover every mechanism in docs/01 §3.
# ---------------------------------------------------------------------------


def _jit(scene: Scene, value: float, spread: float = 0.05) -> float:
    """`value` with proportional noise, rounded so the JSON is byte-stable across platforms."""
    return round(value * (1 + scene.rng.uniform(-spread, spread)), 3)


def _flat(scene: Scene, base: float, spread: float = 0.08) -> list[float]:
    """A healthy series: noise around a level, no trend."""
    return [_jit(scene, base, spread) for _ in range(POINTS)]


def _ramp(scene: Scene, base: float, peak: float, onset: int = ONSET) -> list[float]:
    """Flat, then a linear climb to `peak` at the end of the window. Saturation's shape."""
    span = max(POINTS - 1 - onset, 1)
    return [
        _jit(scene, base if i < onset else base + (peak - base) * (i - onset) / span)
        for i in range(POINTS)
    ]


def _step(scene: Scene, before: float, after: float, onset: int = ONSET) -> list[float]:
    """One level to another in a single interval. A deploy, a config change, a TTL cliff."""
    return [_jit(scene, before if i < onset else after) for i in range(POINTS)]


def _sawtooth(scene: Scene, low: float, high: float, period: int) -> list[float]:
    """Climb, drop, repeat. A leak with a restart at the top of each tooth."""
    return [_jit(scene, low + (high - low) * ((i % period) / period), 0.02) for i in range(POINTS)]


def _periodic(
    scene: Scene, base: float, peak: float, period: int, onset: int = ONSET
) -> list[float]:
    """Flat, then a repeating surge. Mass TTL expiry re-synchronises and comes back."""
    return [
        _jit(
            scene, base if i < onset else base + (peak - base) * abs(math.sin(math.pi * i / period))
        )
        for i in range(POINTS)
    ]


def _series(service: str, metric: str, unit: str, values: list[float], scene: Scene) -> Series:
    """Wrap a list of values as a `Series` over the whole window."""
    return Series(
        service=service,
        metric=metric,
        unit=unit,
        points=[Point(at=scene.at(i), value=v) for i, v in enumerate(values)],
    )


# ---------------------------------------------------------------------------
# Logs. The measured register: a wall of INFO, a repeating WARN, a handful of signal.
# ---------------------------------------------------------------------------

# One routine template per service kind, each carrying a *number* the way OpenStack's `nova-api`
# lines carry `status: 200 len: 1893 time: 0.2477829`. The degradation is visible inside these
# lines before any WARN appears, which is the whole point of the measurement in docs/01 §4.
_ROUTINE: dict[str, str] = {
    "api": "handled {method} {path} status={status} len={size} time={value:.3f}",
    "worker": "task {task} completed in {value:.3f}s attempt=1",
    "datastore": "statement {task} rows={size} time={value:.3f}",
    "cache": "GET {path} hit={status} time={value:.3f}",
    "queue": "partition {task} committed offset={size} lag={value:.0f}",
    "external": "outbound {method} {path} status={status} time={value:.3f}",
}
# ⚠️ Measured, not chosen. Each renderer states its routine line count as a *weight* — how much
# traffic this service carries relative to its neighbours — and this multiplies all of them to
# the level mix the public corpora actually show: OpenStack 98.5% INFO, HDFS 96.0% (docs/01 §4).
# Without it the suite runs at ~75% INFO and every WARN reads as a signal, which is the exact
# failure the read was done to avoid. `tests/unit/test_invariants.py` asserts the resulting band.
#
# It also makes `get_logs` truncate for real, which docs/03 rule 2 needs: a tool that never hits
# its cap never teaches the agent that it is looking at a partial view.
ROUTINE_SCALE = 7

_PATHS = ("/api/v1/returns", "/api/v1/labels", "/api/v1/rates", "/api/v1/orders")
_METHODS = ("GET", "POST", "PUT")
_TASKS = ("reconcile", "settle", "reindex", "expire")


def _routine(
    scene: Scene, service: str, kind: str, count: int, latency: list[float] | None = None
) -> list[LogLine]:
    """The `INFO` wall: `count` lines of ordinary traffic, spread across the window.

    Args:
        scene: The case's frame.
        service: Which service emits them.
        kind: Its `ServiceNode.kind`, which picks the template.
        count: The service's share of the traffic, multiplied by `ROUTINE_SCALE` to reach the
            measured level mix. ⚠️ This dominates the log stream on purpose.
        latency: If given, the per-point series the embedded number is read from, so the routine
            lines degrade with the incident instead of staying flat through it.

    Returns:
        Lines in ascending time order.
    """
    template = _ROUTINE[kind]
    lines = []
    for _ in range(count * ROUTINE_SCALE):
        i = scene.rng.randrange(POINTS)
        value = latency[i] if latency else scene.rng.uniform(0.02, 0.09)
        lines.append(
            LogLine(
                at=scene.at(i),
                service=service,
                level="INFO",
                message=template.format(
                    method=scene.rng.choice(_METHODS),
                    path=scene.rng.choice(_PATHS),
                    status=scene.rng.choice((200, 200, 200, 204)),
                    size=scene.rng.randrange(180, 4096),
                    task=scene.rng.choice(_TASKS),
                    value=value,
                ),
            )
        )
    return lines


def _chronic(scene: Scene, service: str, message: str, count: int = 14) -> list[LogLine]:
    """The distractor: one `WARN` template repeated across the whole window, incident or not.

    ⛔ This is what makes a distractor plausible rather than decorative. Loghub's OpenStack
    sample carries 31 warnings that are all one message, and Zookeeper sits at 66% `WARN` at
    rest — so a warning is only evidence if it *started*.
    """
    return [
        LogLine(
            at=scene.at(scene.rng.randrange(POINTS)), service=service, level="WARN", message=message
        )
        for _ in range(count)
    ]


def _burst(
    scene: Scene,
    service: str,
    message: str,
    level: LogLevel = "ERROR",
    count: int = 6,
    onset: int = ONSET,
) -> list[LogLine]:
    """The signal: a template that appears only after `onset`. Rare, because real ERRORs are."""
    return [
        LogLine(
            at=scene.at(scene.rng.randrange(onset, POINTS)),
            service=service,
            level=level,
            message=message.format(n=scene.rng.randrange(2, 40)),
        )
        for _ in range(count)
    ]


def _deploy(
    scene: Scene, service: str, summary: str, index: int, rolled_back: bool = False
) -> Deploy:
    """A deploy at point `index`, with a sha derived from the seeded rng."""
    return Deploy(
        at=scene.at(index),
        service=service,
        sha=f"{scene.rng.randrange(16**7):07x}",
        summary=summary,
        rolled_back=rolled_back,
    )


def _alert(scene: Scene, service: str, signal: str, value: float, threshold: float) -> Alert:
    """The page. ⚠️ `service` is where the alarm fired, which is often not the cause."""
    return Alert(
        id=f"alt-{scene.rng.randrange(16**6):06x}",
        fired_at=scene.at(FIRED),
        service=service,
        signal=signal,
        value=round(value, 3),
        threshold=threshold,
    )


def _ev(
    series: list[Series] | None = None,
    logs: list[LogLine] | None = None,
    deploys: list[Deploy] | None = None,
) -> Evidence:
    """An `Evidence` bucket with the empty lists filled in."""
    return Evidence(series=series or [], logs=logs or [], deploys=deploys or [])


# ---------------------------------------------------------------------------
# The ten. Each one is its mechanism, and each names the signal that settles it.
# ---------------------------------------------------------------------------


def db_pool_exhausted(scene: Scene) -> Rendered:
    """Checkout's connection pool saturates; the datastore itself is idle.

    The trap: the API is slow and the database is *fine*, so a reader who stops at
    `db_cpu_utilization` concludes the datastore is healthy and moves on. Pool wait time is the
    only series that separates this from a genuinely overloaded datastore.
    """
    lat = _ramp(scene, 90, 2400)
    return Rendered(
        alert=_alert(scene, "checkout", "request_latency_p99_ms", lat[FIRED], 500),
        ambient=_ev(
            series=[
                _series("checkout", "request_latency_p99_ms", "ms", lat, scene),
                _series("checkout", "request_rate", "count", _flat(scene, 240), scene),
                _series("postgres", "db_cpu_utilization", "ratio", _flat(scene, 0.31), scene),
                _series("postgres", "query_p99_ms", "ms", _flat(scene, 14), scene),
            ],
            logs=[
                *_routine(scene, "checkout", "api", 46, [v / 1000 for v in lat]),
                *_routine(scene, "postgres", "datastore", 22),
                *_chronic(scene, "checkout", "retrying idempotent charge, attempt 2 of 3"),
            ],
        ),
        distinguishing=_ev(
            series=[
                _series("checkout", "db_pool_wait_ms", "ms", _ramp(scene, 2, 1900), scene),
                _series("checkout", "db_pool_in_use", "count", _ramp(scene, 6, 20), scene),
            ],
            logs=_burst(scene, "checkout", "timed out waiting {n}s for a connection from the pool"),
        ),
        specialist="resource",
        rival="upstream_timeout",
    )


def slow_query_after_migration(scene: Scene) -> Rendered:
    """A migration dropped an index; one statement's p99 now dominates the datastore.

    The trap: the deploy is on `product-catalog` and the pain is on `postgres`, so the two halves
    live in different services and only the deploy history joins them.
    """
    q99 = _step(scene, 12, 780)
    return Rendered(
        alert=_alert(scene, "product-catalog", "request_latency_p99_ms", 1650, 500),
        ambient=_ev(
            series=[
                _series(
                    "product-catalog", "request_latency_p99_ms", "ms", _step(scene, 70, 1650), scene
                ),
                _series("product-catalog", "error_rate", "ratio", _flat(scene, 0.002), scene),
                _series("postgres", "db_cpu_utilization", "ratio", _step(scene, 0.28, 0.83), scene),
            ],
            logs=[
                *_routine(scene, "product-catalog", "api", 44),
                *_routine(scene, "postgres", "datastore", 26, [v / 1000 for v in q99]),
                *_chronic(scene, "postgres", "checkpoint starting: time"),
            ],
        ),
        distinguishing=_ev(
            series=[_series("postgres", "query_p99_ms", "ms", q99, scene)],
            logs=_burst(
                scene,
                "postgres",
                "duration: {n}214.7 ms  statement: "
                "SELECT * FROM catalog_item WHERE merchant_id = $1",
                level="WARN",
                count=9,
            ),
            deploys=[
                _deploy(
                    scene,
                    "product-catalog",
                    "drop unused index on catalog_item.merchant_id",
                    ONSET - 2,
                )
            ],
        ),
        specialist="timeline",
        rival="db_pool_exhausted",
    )


def cache_stampede(scene: Scene) -> Rendered:
    """A synchronised TTL expiry; every miss falls through to the datastore, repeatedly.

    The trap: the periodic shape. A single spike reads as a traffic burst; the *recurrence* at
    the TTL period is what says the cache is re-synchronising rather than the load changing.
    """
    hits = _step(scene, 0.94, 0.21)
    return Rendered(
        alert=_alert(scene, "product-catalog", "request_latency_p99_ms", 1180, 500),
        ambient=_ev(
            series=[
                _series(
                    "product-catalog",
                    "request_latency_p99_ms",
                    "ms",
                    _periodic(scene, 80, 1180, 9),
                    scene,
                ),
                _series("product-catalog", "request_rate", "count", _flat(scene, 310), scene),
                _series(
                    "postgres", "db_cpu_utilization", "ratio", _periodic(scene, 0.3, 0.88, 9), scene
                ),
            ],
            logs=[
                *_routine(scene, "product-catalog", "api", 42),
                *_routine(scene, "valkey", "cache", 30),
                *_chronic(scene, "valkey", "maxmemory policy is noeviction, 2 keys over budget"),
            ],
        ),
        distinguishing=_ev(
            series=[
                _series("valkey", "cache_hit_rate", "ratio", hits, scene),
                _series("valkey", "evictions", "count", _step(scene, 0, 1240), scene),
            ],
            logs=_burst(
                scene, "valkey", "{n} keys expired in one pass, ttl bucket 900s", level="WARN"
            ),
        ),
        specialist="resource",
        rival="db_pool_exhausted",
    )


def queue_backlog_hol(scene: Scene) -> Rendered:
    """One slow message type blocks a shared consumer; a single partition backs up.

    The trap: aggregate queue depth looks merely elevated. Only the per-partition lag shows that
    nine partitions are healthy and one is not, which is what makes it head-of-line and not load.
    """
    return Rendered(
        alert=_alert(scene, "fraud-detection", "consumer_lag", 41200, 5000),
        ambient=_ev(
            series=[
                _series("kafka", "queue_depth", "count", _ramp(scene, 900, 44000), scene),
                _series("fraud-detection", "cpu_utilization", "ratio", _flat(scene, 0.34), scene),
                _series(
                    "fraud-detection", "tasks_completed", "count", _step(scene, 210, 34), scene
                ),
                _series("checkout", "request_latency_p99_ms", "ms", _flat(scene, 95), scene),
            ],
            logs=[
                *_routine(scene, "kafka", "queue", 34),
                *_routine(scene, "fraud-detection", "worker", 30),
                *_chronic(scene, "kafka", "group rebalance in progress for consumer-group fraud-1"),
            ],
        ),
        distinguishing=_ev(
            series=[
                _series("kafka", "partition_7_lag", "count", _ramp(scene, 40, 41200), scene),
                _series("kafka", "partition_3_lag", "count", _flat(scene, 55), scene),
            ],
            logs=_burst(
                scene,
                "fraud-detection",
                "message type BULK_SETTLEMENT took {n}9.4s, blocking partition 7",
                level="WARN",
                count=8,
            ),
        ),
        specialist="resource",
        rival="noisy_neighbor",
    )


def bad_deploy_regression(scene: Scene) -> Rendered:
    """New code throws on one live path, minutes after it shipped.

    The trap: a second, innocent deploy landed on a neighbouring service inside the same window.
    Picking the deploy that is merely *near* the alert is the failure this case plants.
    """
    errs = _step(scene, 0.003, 0.21)
    return Rendered(
        alert=_alert(scene, "shipping", "error_rate", errs[FIRED], 0.02),
        ambient=_ev(
            series=[
                _series("shipping", "error_rate", "ratio", errs, scene),
                _series("shipping", "request_rate", "count", _flat(scene, 180), scene),
                _series("shipping", "cpu_utilization", "ratio", _flat(scene, 0.29), scene),
            ],
            logs=[
                *_routine(scene, "shipping", "api", 40),
                *_routine(scene, "quote", "api", 22),
                *_chronic(scene, "shipping", "deprecated field `zone_id` read by 2 callers"),
            ],
            # The innocent one. Same window, wrong service, no error follows it.
            deploys=[_deploy(scene, "cart", "bump valkey client to 7.2.1", ONSET - 6)],
        ),
        distinguishing=_ev(
            logs=_burst(
                scene,
                "shipping",
                "unhandled TypeError in rate_for_zone: NoneType has no attribute 'code' (req {n})",
            ),
            deploys=[
                _deploy(scene, "shipping", "rewrite zone lookup for multi-carrier rates", ONSET - 1)
            ],
        ),
        specialist="timeline",
        rival="upstream_timeout",
    )


def upstream_timeout(scene: Scene) -> Rendered:
    """A third party slowed down and the retry budget amplified it into an outage.

    The trap: retries make our own request rate climb, so the service looks overloaded by its own
    traffic. Own CPU sitting idle through it is what separates amplification from saturation.
    """
    up = _ramp(scene, 120, 9800)
    return Rendered(
        alert=_alert(scene, "shipping", "request_latency_p99_ms", 6100, 500),
        ambient=_ev(
            series=[
                _series("shipping", "request_latency_p99_ms", "ms", _ramp(scene, 140, 6100), scene),
                _series("shipping", "cpu_utilization", "ratio", _flat(scene, 0.22), scene),
                _series("quote", "request_rate", "count", _ramp(scene, 90, 410), scene),
            ],
            logs=[
                *_routine(scene, "shipping", "api", 38),
                *_routine(scene, "quote", "api", 26),
                *_chronic(scene, "quote", "connection pool recycled after 300s idle"),
            ],
        ),
        distinguishing=_ev(
            series=[
                _series("rate-provider", "upstream_latency_p99_ms", "ms", up, scene),
                _series("quote", "retry_rate", "count", _ramp(scene, 1, 260), scene),
            ],
            logs=_burst(
                scene,
                "quote",
                "outbound POST rates.carrier-api.example status=504 after {n}000ms, retry 3 of 3",
                level="WARN",
                count=10,
            ),
        ),
        specialist="dependency",
        rival="bad_deploy_regression",
    )


def disk_pressure(scene: Scene) -> Rendered:
    """A log volume fills; writes fail only once it is actually full.

    The trap: the linear ramp is visible for twenty minutes and nothing breaks until the end, so
    the first error arrives long after the cause started. The alert timestamp is not the onset.
    """
    used = _ramp(scene, 0.71, 0.998, onset=0)
    return Rendered(
        alert=_alert(scene, "accounting", "error_rate", 0.34, 0.02),
        ambient=_ev(
            series=[
                _series(
                    "accounting", "error_rate", "ratio", _step(scene, 0.001, 0.34, FIRED - 2), scene
                ),
                _series("accounting", "cpu_utilization", "ratio", _flat(scene, 0.4), scene),
                _series(
                    "accounting", "tasks_completed", "count", _step(scene, 96, 12, FIRED - 2), scene
                ),
            ],
            logs=[
                *_routine(scene, "accounting", "worker", 44),
                *_chronic(
                    scene, "accounting", "ledger export took longer than the 60s soft budget"
                ),
            ],
        ),
        distinguishing=_ev(
            series=[_series("accounting", "disk_used_ratio", "ratio", used, scene)],
            logs=_burst(
                scene,
                "accounting",
                "write failed: No space left on device (/var/log, {n}%)",
                onset=FIRED - 2,
            ),
        ),
        specialist="resource",
        rival="memory_leak_oom",
    )


def memory_leak_oom(scene: Scene) -> Rendered:
    """Worker RSS climbs until the kernel intervenes, then climbs again.

    The trap: traffic is flat throughout, so nothing external explains it. The sawtooth is the
    tell, and a single point of high memory would not be one.
    """
    return Rendered(
        alert=_alert(scene, "recommendation", "restart_count", 4, 1),
        ambient=_ev(
            series=[
                _series("recommendation", "request_rate", "count", _flat(scene, 150), scene),
                _series("recommendation", "cpu_utilization", "ratio", _flat(scene, 0.44), scene),
                _series(
                    "recommendation",
                    "request_latency_p99_ms",
                    "ms",
                    _sawtooth(scene, 90, 480, 15),
                    scene,
                ),
            ],
            logs=[
                *_routine(scene, "recommendation", "worker", 42),
                *_chronic(scene, "recommendation", "model cache warm-up skipped, using cold path"),
            ],
        ),
        distinguishing=_ev(
            series=[
                _series(
                    "recommendation",
                    "rss_bytes",
                    "bytes",
                    _sawtooth(scene, 4.1e8, 2.02e9, 15),
                    scene,
                ),
                _series(
                    "recommendation", "restart_count", "count", _ramp(scene, 0, 4, onset=0), scene
                ),
            ],
            logs=_burst(
                scene,
                "recommendation",
                "worker {n} killed by signal 9 (oom), rss 2013 MiB of 2048 MiB limit",
                onset=8,
                count=4,
            ),
        ),
        specialist="resource",
        rival="disk_pressure",
    )


def config_drift(scene: Scene) -> Rendered:
    """One env var differs on a subset of instances; failures track the instances, not the load.

    The trap: at the service level this is a partial outage that looks exactly like a bad deploy.
    Only the per-instance split shows two of six instances failing and four healthy.

    ⚠️ Kept among the eleven on evidence: **Config Errors is the largest named category** in
    danluu/post-mortems, ahead of Database and Hardware (docs/01 §4).
    """
    return Rendered(
        alert=_alert(scene, "payment", "error_rate", 0.33, 0.02),
        ambient=_ev(
            series=[
                _series("payment", "error_rate", "ratio", _step(scene, 0.002, 0.33), scene),
                _series("payment", "request_rate", "count", _flat(scene, 120), scene),
                _series("payment", "cpu_utilization", "ratio", _flat(scene, 0.27), scene),
                _series("flagd", "upstream_latency_p99_ms", "ms", _flat(scene, 8), scene),
            ],
            logs=[
                *_routine(scene, "payment", "api", 40),
                *_chronic(scene, "payment", "falling back to default currency table"),
                *_burst(
                    scene, "payment", "charge rejected upstream: invalid api credentials (req {n})"
                ),
            ],
            # ⚠️ Load-bearing for inc-009, not decoration. Strip the distinguishing bucket and
            # this deploy is the only remaining explanation for a step change at ONSET — which
            # is what leaves two hypotheses standing rather than none. Without it the deleted
            # case has an obvious answer and stops testing escalation.
            deploys=[_deploy(scene, "payment", "widen the retry budget for 5xx", ONSET - 1)],
        ),
        distinguishing=_ev(
            series=[
                _series(
                    "payment", "instance_4_error_rate", "ratio", _step(scene, 0.002, 0.99), scene
                ),
                _series("payment", "instance_1_error_rate", "ratio", _flat(scene, 0.002), scene),
            ],
            logs=_burst(
                scene,
                "payment",
                "startup: PAYMENT_GATEWAY_URL=https://sandbox.gateway.internal "
                "on instance-4 (pod {n})",
                level="WARN",
                onset=0,
                count=5,
            ),
        ),
        specialist="timeline",
        rival="bad_deploy_regression",
    )


def noisy_neighbor(scene: Scene) -> Rendered:
    """A batch job saturates the shared datastore. It has no dependency edge to the alert at all.

    The trap: every service the alerting one depends on looks innocent, because the culprit is
    not among them. Following the topology from the alert never reaches `accounting`.
    """
    # ⚠️ The alert sits on `product-catalog` and not on `cart`, and that is a topology fact
    # rather than a taste: `cart` reaches only `valkey`, so postgres saturation could not slow
    # it and the mechanism would not hold. `product-catalog` reaches postgres in one hop and
    # still never reaches `accounting`, which is the whole point of the class.
    return Rendered(
        alert=_alert(scene, "product-catalog", "request_latency_p99_ms", 2100, 500),
        ambient=_ev(
            series=[
                _series(
                    "product-catalog", "request_latency_p99_ms", "ms", _ramp(scene, 60, 2100), scene
                ),
                _series("product-catalog", "cpu_utilization", "ratio", _flat(scene, 0.25), scene),
                _series("postgres", "db_cpu_utilization", "ratio", _ramp(scene, 0.3, 0.97), scene),
                _series("postgres", "connections_active", "count", _ramp(scene, 40, 190), scene),
            ],
            logs=[
                *_routine(scene, "product-catalog", "api", 40),
                *_routine(scene, "postgres", "datastore", 28),
                *_chronic(scene, "product-catalog", "price list reload took 3.1s, serving stale"),
            ],
        ),
        distinguishing=_ev(
            series=[
                _series("accounting", "db_query_rate", "count", _step(scene, 12, 4100), scene),
                _series("accounting", "cpu_utilization", "ratio", _step(scene, 0.2, 0.95), scene),
            ],
            logs=_burst(
                scene,
                "accounting",
                "month-end reconciliation started: {n} merchants, full table scan enabled",
                level="INFO",
                onset=ONSET - 1,
                count=3,
            ),
        ),
        specialist="dependency",
        rival="slow_query_after_migration",
    )


# The registry, in the order docs/01 §3 lists the classes. ⛔ Ten, not eleven: the eleventh is
# made by deleting a bucket from one of these, which is why it has no entry here.
RENDERERS: dict[str, Callable[[Scene], Rendered]] = {
    "db_pool_exhausted": db_pool_exhausted,
    "slow_query_after_migration": slow_query_after_migration,
    "cache_stampede": cache_stampede,
    "queue_backlog_hol": queue_backlog_hol,
    "bad_deploy_regression": bad_deploy_regression,
    "upstream_timeout": upstream_timeout,
    "disk_pressure": disk_pressure,
    "memory_leak_oom": memory_leak_oom,
    "config_drift": config_drift,
    "noisy_neighbor": noisy_neighbor,
}
