"""Every type the rest of the system speaks in. Written first; everything imports it.

The split this file closes: [docs/01](../../docs/01-spec.md) §2 defines the models that carry
*meaning* — the incident, the answer key, the verdict — and [docs/09](../../docs/09-schemas.md)
§1-§3 defines the ones that carry *data*: the rendered evidence, the closed sets, the tool
return types. Two files, one module, because a tool signature that names `TimeWindow` and a
generator that emits a tuple are the same concept represented twice, and that is how a filter
silently compares the wrong end of a range.

⛔ **The graph state is NOT here** — `Finding`, `FindingHeader` and `AgentState` live in
`agent/state.py` (docs/09 §9's file map, D-055). This module has no dependency on LangGraph,
on the SDK, or on `config`, so the scorer can import it without importing the agent.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import IntEnum, StrEnum
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel

if TYPE_CHECKING:  # the SDK is a runtime dependency; `from_result` only reads attributes
    from claude_agent_sdk import ResultMessage

# ---------------------------------------------------------------------------
# The closed sets — docs/09 §2
# ---------------------------------------------------------------------------


class RootCause(StrEnum):
    """The answer key space: eleven classes, docs/01 §3.

    Ten are causes with a renderer; `INSUFFICIENT_EVIDENCE` is made by *deleting* a signal
    from a rendered incident (docs/01 §4 rule 4), which is why the generator has ten
    renderers and a deletion path rather than eleven renderers.
    """

    DB_POOL_EXHAUSTED = "db_pool_exhausted"
    SLOW_QUERY_AFTER_MIGRATION = "slow_query_after_migration"
    CACHE_STAMPEDE = "cache_stampede"
    QUEUE_BACKLOG_HOL = "queue_backlog_hol"
    BAD_DEPLOY_REGRESSION = "bad_deploy_regression"
    UPSTREAM_TIMEOUT = "upstream_timeout"
    DISK_PRESSURE = "disk_pressure"
    MEMORY_LEAK_OOM = "memory_leak_oom"
    CONFIG_DRIFT = "config_drift"
    NOISY_NEIGHBOR = "noisy_neighbor"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class BlastRadius(IntEnum):
    """How far an action reaches. Ordered, so escalation is one comparison.

    An `IntEnum` and not a `StrEnum` on purpose: it makes `escalate` literally
    `action.blast_radius >= ESCALATION_THRESHOLD`, and invariant 4 a test over six enum
    members rather than over prose.
    """

    NONE = 0
    ONE_HUMAN = 1
    ONE_SERVICE = 2
    SERVICE_LIVE = 3
    SERVICE_ALL = 4
    DOWNSTREAM = 5


class Action(StrEnum):
    """What the agent may recommend. The verdict names one of these or none."""

    ANNOTATE_INCIDENT = "annotate_incident"
    PAGE_SECONDARY = "page_secondary"
    SCALE_WORKERS = "scale_workers"
    RESTART_SERVICE = "restart_service"
    ROLLBACK_DEPLOY = "rollback_deploy"
    FAILOVER_DATASTORE = "failover_datastore"

    @property
    def blast_radius(self) -> BlastRadius:
        """The action's reach, from the hand-written table in docs/01 §5."""
        return _BLAST[self]


# The table from docs/01 §5, transcribed once. ⛔ Nothing else may restate it.
_BLAST: dict[Action, BlastRadius] = {
    Action.ANNOTATE_INCIDENT: BlastRadius.NONE,
    Action.PAGE_SECONDARY: BlastRadius.ONE_HUMAN,
    Action.SCALE_WORKERS: BlastRadius.ONE_SERVICE,
    Action.RESTART_SERVICE: BlastRadius.SERVICE_LIVE,
    Action.ROLLBACK_DEPLOY: BlastRadius.SERVICE_ALL,
    Action.FAILOVER_DATASTORE: BlastRadius.DOWNSTREAM,
}

# ⛔ At or above this, the verdict escalates. A named constant, never the literal 3, and
# deliberately NOT a config value — a tunable threshold is a policy the system could learn,
# and docs/01 §5 says this one is hand-written on purpose (D-056).
#
# ⚠️ Called APPROVAL_THRESHOLD until D-040. The rename is not cosmetic: nothing approves
# anything now, and a constant whose name promises a gate that does not exist is how a reader
# concludes the system has one.
ESCALATION_THRESHOLD = BlastRadius.SERVICE_LIVE


# ---------------------------------------------------------------------------
# The evidence surface — docs/09 §1. ⛔ The whole agent-visible world.
# ---------------------------------------------------------------------------


class Point(BaseModel):
    """One sample of one series."""

    at: datetime
    value: float


class Series(BaseModel):
    """A metric over the incident window, at the fixed interval (`config.INTERVAL_SECONDS`).

    Every series covers the same window at the same resolution, so `len(points)` is identical
    across services and a **missing series means absent, not sparse** — the distinction that
    makes `insufficient_evidence` generatable by deletion.
    """

    service: str
    metric: str
    unit: str
    points: list[Point]
    truncated: bool = False
    total: int | None = None


class LogLine(BaseModel):
    """One rendered log line. The level set is closed so a tool can filter on it."""

    at: datetime
    service: str
    level: Literal["DEBUG", "INFO", "WARN", "ERROR"]
    message: str


class Deploy(BaseModel):
    """A deploy inside or just before the window. `sha` is 7 hex chars, from the seed."""

    at: datetime
    service: str
    sha: str
    summary: str
    rolled_back: bool = False


class TimeWindow(BaseModel):
    """A half-open interval. ⛔ The tuple form from docs/01 §2 does not survive anywhere."""

    start: datetime
    end: datetime


class Evidence(BaseModel):
    """Everything the agent can see. There is no live system behind the tools."""

    series: list[Series]
    logs: list[LogLine]
    deploys: list[Deploy]


# ---------------------------------------------------------------------------
# The incident, the answer key, the verdict — docs/01 §2
# ---------------------------------------------------------------------------


class ServiceNode(BaseModel):
    """One node of the topology the agent is given up front."""

    name: str
    kind: Literal["api", "worker", "datastore", "cache", "queue", "external"]
    depends_on: list[str]


class Alert(BaseModel):
    """What paged.

    ⚠️ `service` is where the alarm fired and is **deliberately not the answer**: in roughly
    half the suite the API pages because the datastore is saturated. An agent that answers
    with the alerting service scores near zero, which is the intended behaviour.
    """

    id: str
    fired_at: datetime
    service: str
    signal: str
    value: float
    threshold: float


class Incident(BaseModel):
    """One case. `seed` regenerates it byte-identically."""

    id: str
    alert: Alert
    window: TimeWindow
    topology: list[ServiceNode]
    evidence: Evidence
    seed: int


class GroundTruth(BaseModel):
    """The answer key. ⛔ Never rendered into agent context — invariant 1.

    `resolvable=False` means the correct verdict is escalation, and `rationale` is for the
    report only: the scorer never reads prose.
    """

    incident_id: str
    root_cause_id: RootCause
    affected_service: str
    resolvable: bool
    rationale: str


class Verdict(BaseModel):
    """What the agent returns. Scored on the structured fields; `reasoning` is judged only."""

    incident_id: str
    root_cause_id: RootCause | None
    affected_service: str | None
    confidence: float
    escalate: bool
    recommended_action: Action | None
    reasoning: str


# ---------------------------------------------------------------------------
# Tool return types — docs/09 §3
# ---------------------------------------------------------------------------


class LogPage(BaseModel):
    """`get_logs` returns this, not a bare list.

    A tool that truncates without saying so teaches the agent to trust a partial view, which
    is the one thing the truncation rule exists to prevent (docs/03 §2 rule 2).
    """

    lines: list[LogLine]
    truncated: bool
    total: int


class RunbookChunk(BaseModel):
    """One BM25 hit over `runbooks/`. `score` is reported, never gated on."""

    runbook_id: str
    title: str
    text: str
    score: float


class Signature(BaseModel):
    """What "have we seen this before" matches on.

    ⛔ Contains no root cause, and that is the entire design of the false friend: a signature
    that leaked the cause would make every retrieval correct by construction.
    """

    alert_signal: str
    alert_service: str
    service_kind: str
    top_metric: str | None


class PastIncident(BaseModel):
    """A `history/` entry, truth deliberately intact — it is the past, not the case."""

    id: str
    occurred: date
    signature: Signature
    root_cause_id: RootCause
    affected_service: str
    fix: str


# ---------------------------------------------------------------------------
# What one model call reports back — docs/09 §4
# ---------------------------------------------------------------------------

Provider = Literal["subscription", "cerebras", "ollama"]


class Usage(BaseModel):
    """One model call's cost and tokens. An attempt sums these across its five or six nodes.

    ⚠️ `provider` comes from configuration — the SDK reports none. `canonical_model` is the
    evidence: path B answers as `llama-3.3-70b`, path C as an ollama tag, so a mid-suite
    provider switch is visible there and voids the attempt (D-015).
    """

    canonical_model: str
    provider: Provider
    prompt_tokens: int
    completion_tokens: int
    cache_read_tokens: int
    cache_creation_tokens: int
    cost_usd: float
    duration_ms: int
    duration_api_ms: int
    other_models: dict[str, float] = {}

    @classmethod
    def from_result(cls, msg: ResultMessage, *, model: str, provider: Provider) -> Usage:
        """Project a `ResultMessage` onto this model, matching `model` by name.

        ⛔ Never `next(iter(msg.model_usage))` — DEF-001. `model_usage` routinely holds a
        second entry, the CLI's own housekeeping call on haiku, and it sorts *first*.
        Recording a model that was never asked for is worse than crashing, because it makes
        the version table's rows unattributable and nothing downstream can detect it (D-013).

        Args:
            msg: The SDK's terminal message for one call.
            model: The configured model id — `config.MODEL`. Required, never defaulted: a
                default is a second place this can be silently wrong.
            provider: Which path served the call. Asserted constant within an attempt.

        Returns:
            The projection, with every non-matching `model_usage` key kept under
            `other_models` as `{model_id: cost_usd}`.

        Raises:
            ValueError: `model` is absent from `model_usage`.
        """
        by_model: dict[str, dict[str, float]] = msg.model_usage or {}
        if model not in by_model:
            raise ValueError(
                f"configured model {model!r} absent from model_usage; "
                f"got {sorted(by_model)} — the run did not use the pinned model (D-013)"
            )
        entry = by_model[model]
        return cls(
            canonical_model=model,
            provider=provider,
            prompt_tokens=int(entry.get("inputTokens", 0)),
            completion_tokens=int(entry.get("outputTokens", 0)),
            cache_read_tokens=int(entry.get("cacheReadInputTokens", 0)),
            cache_creation_tokens=int(entry.get("cacheCreationInputTokens", 0)),
            # ⚠️ The RUN's total, which includes `other_models` — measured at ~16% of a
            # trivial call. Cost-per-correct is therefore a figure about the attempt, never
            # about the model the row names.
            cost_usd=float(msg.total_cost_usd or 0.0),
            duration_ms=msg.duration_ms,
            duration_api_ms=msg.duration_api_ms,
            other_models={
                key: float(val.get("costUSD", 0.0))
                for key, val in by_model.items()
                if key != model
            },
        )
