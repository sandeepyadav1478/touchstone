# 09 — Schemas, file map and the contracts implementation runs against

> ⚠️ **Specification, phase 0.** This describes the design; it is not a description of shipped code. `touchstone doctor` is the only implemented command today — see the [README](../README.md) for what runs and what does not.

**Everything the other docs name but do not define.** [docs/01](01-spec.md) §2 gives the models
that carry meaning; this file gives the ones that carry data, plus the four contracts a phase
would otherwise have to invent: the hash, the attempt record, the retrieval corpus and the
prompt interface.

⛔ **Nothing here is a new decision.** Every shape below is the mechanical consequence of a
decision already recorded. Where a shape had a real alternative, the alternative is named in the
row — but a choice with an argument behind it belongs in `DECISIONS.md`, and none of these
needed one.

---

## 1. The evidence surface — the gap `Incident` left open

[docs/01](01-spec.md) §2 defines `Incident` as the alert, the window, the topology and the seed.
**The tools read the generated incident** ([docs/03](03-agent-and-tools.md) §2) and there is no
live system, so the rendered evidence has to be *in the incident file* — and the model as
written has nowhere to put it.

```python
class Point(BaseModel):
    at: datetime
    value: float

class Series(BaseModel):
    service: str
    metric: str                    # "db_pool_wait_ms", "cache_hit_rate", "rss_bytes"
    unit: str                      # "ms", "ratio", "bytes", "count"
    points: list[Point]            # one per interval across the window, no gaps
    truncated: bool = False
    total: int | None = None       # points before truncation, when truncated

class LogLine(BaseModel):
    at: datetime
    service: str
    level: Literal["DEBUG", "INFO", "WARN", "ERROR"]
    message: str

class Deploy(BaseModel):
    at: datetime
    service: str
    sha: str                       # 7 hex chars, from the seed
    summary: str                   # "add index on returns.merchant_id"
    rolled_back: bool = False

class TimeWindow(BaseModel):
    start: datetime
    end: datetime

class Evidence(BaseModel):         # ⛔ the whole agent-visible world
    series: list[Series]
    logs: list[LogLine]
    deploys: list[Deploy]
```

`Incident` gains one field and one correction:

```python
class Incident(BaseModel):
    id: str
    alert: Alert
    window: TimeWindow             # was tuple[datetime, datetime] — see the note below
    topology: list[ServiceNode]
    evidence: Evidence             # ← the addition
    seed: int
```

⚠️ **`window` was a bare tuple in [docs/01](01-spec.md) §2 and every tool signature takes a
`TimeWindow`.** Two representations of one concept is how a filter silently compares the wrong
end of a range, so the tuple loses. **The tuple form does not survive anywhere** — grep for it
before phase 1 ends.

**Fixed interval, stated once: 30 seconds.** Every series covers the same window at the same
resolution, so `len(points)` is identical across services and a missing series means *absent*
rather than *sparse*. That distinction is what makes `insufficient_evidence` generatable by
deletion ([docs/01](01-spec.md) §4 rule 4) rather than by noise.

---

## 2. The closed sets

```python
class RootCause(StrEnum):
    DB_POOL_EXHAUSTED         = "db_pool_exhausted"
    SLOW_QUERY_AFTER_MIGRATION = "slow_query_after_migration"
    CACHE_STAMPEDE            = "cache_stampede"
    QUEUE_BACKLOG_HOL         = "queue_backlog_hol"
    BAD_DEPLOY_REGRESSION     = "bad_deploy_regression"
    UPSTREAM_TIMEOUT          = "upstream_timeout"
    DISK_PRESSURE             = "disk_pressure"
    MEMORY_LEAK_OOM           = "memory_leak_oom"
    CONFIG_DRIFT              = "config_drift"
    NOISY_NEIGHBOR            = "noisy_neighbor"
    INSUFFICIENT_EVIDENCE     = "insufficient_evidence"

class BlastRadius(IntEnum):        # ordered, so the gate is a comparison
    NONE         = 0
    ONE_HUMAN    = 1
    ONE_SERVICE  = 2
    SERVICE_LIVE = 3               # ← the approval threshold
    SERVICE_ALL  = 4
    DOWNSTREAM   = 5

class Action(StrEnum):
    ANNOTATE_INCIDENT  = "annotate_incident"
    PAGE_SECONDARY     = "page_secondary"
    SCALE_WORKERS      = "scale_workers"
    RESTART_SERVICE    = "restart_service"
    ROLLBACK_DEPLOY    = "rollback_deploy"
    FAILOVER_DATASTORE = "failover_datastore"

    @property
    def blast_radius(self) -> BlastRadius:
        return _BLAST[self]

APPROVAL_THRESHOLD = BlastRadius.SERVICE_LIVE
```

**`BlastRadius` is an `IntEnum` so that the gate in [docs/03](03-agent-and-tools.md) §3 is
literally `action.blast_radius >= APPROVAL_THRESHOLD`** — one comparison, no table lookup at the
decision point, and invariant 5 is a test over six enum members rather than over prose. The
mapping in `_BLAST` is the table from [docs/01](01-spec.md) §5, transcribed once.

⛔ **The threshold is a named constant, not the literal `3` and not a config value.** A tunable
approval threshold is a policy the system could learn, and [docs/01](01-spec.md) §5 says this one
is hand-written on purpose.

---

## 3. Tool return types — and the one signature that was wrong

```python
class LogPage(BaseModel):
    lines: list[LogLine]
    truncated: bool
    total: int                     # lines matched before the cap

class RunbookChunk(BaseModel):
    runbook_id: str                # "rb-db-pool"
    title: str
    text: str
    score: float                   # retrieval score — reported, never gated

class Signature(BaseModel):        # v5 — what "have we seen this before" matches on
    alert_signal: str
    alert_service: str
    service_kind: str
    top_metric: str | None         # the metric with the largest deviation in the window

class PastIncident(BaseModel):     # v5 — history/ entries, truth deliberately intact
    id: str                        # "hist-014"
    occurred: date
    signature: Signature
    root_cause_id: RootCause
    affected_service: str
    fix: str
```

⚠️ **[docs/03](03-agent-and-tools.md) §2 types `get_logs` as `-> list[LogLine]`, and rule 2 on
the same page requires it to return `truncated: true, total: N`.** A bare list cannot carry
that, so the signature is `-> LogPage`. **The rule is right and the signature was wrong** — a
tool that truncates without saying so teaches the agent to trust a partial view, which is the
one thing rule 2 exists to prevent.

⛔ **`Signature` must not contain the root cause, and that is the entire design of the false
friend.** A past incident and a live one that share a signature and differ in cause is what
[docs/08](08-memory.md) §4 plants to catch anchoring. A signature that leaked the cause would
make every retrieval correct by construction and the experiment would measure nothing.

---

## 4. Graph state

```python
class Finding(BaseModel):
    specialist: Literal["timeline", "resource", "dependency"]
    hop: int
    claims_cause: bool
    root_cause_id: RootCause | None
    summary: str
    evidence: list[str]            # which tool calls it read, by span id

    def header(self) -> FindingHeader:
        """⛔ The ONLY projection the supervisor is allowed to see — D-025."""
        return FindingHeader(specialist=self.specialist,
                             hop=self.hop,
                             claims_cause=self.claims_cause)

class FindingHeader(BaseModel):
    specialist: str
    hop: int
    claims_cause: bool

class AgentState(TypedDict):
    incident: Incident
    findings: Annotated[list[Finding], add]   # D-012 — the only reduced key
    hops: int
    verdict: Verdict | None
```

**`header()` is where invariant 13 is enforced, and it is a method rather than a convention on
purpose.** The supervisor's prompt is built from `[f.header() for f in state["findings"]]` and
there is no code path that hands it a `Finding`. **A test that renders the supervisor prompt
against a state holding two findings and asserts neither `summary` appears** is then checking one
function instead of trusting every future edit to the routing prompt.

⛔ **Specialists receive no `findings` at all** — not headers, not summaries. Their prompt is the
incident plus their own prior tool results, per D-025.

### `Usage` — what one model call reports back

The adapter in [docs/00](00-stack.md) §2 returns `tuple[dict, Usage]`. **It is a projection of
what `ResultMessage` actually carries, which is less than the docs for the TypeScript SDK
suggest** (D-033): `model_usage` is a bare `dict[str, Any]`, the model id is its **key**, and
`provider` is on no field at all. `canonical_model` is therefore still per-call and still from the
run — **and a mid-suite provider switch is visible in *it*, not in `provider`**, because path B
answers as `llama-3.3-70b` and path C as an ollama tag.

```python
class Usage(BaseModel):
    canonical_model: str           # the model_usage KEY matching the configured model —
                                   # ⛔ never next(iter(...)): D-035 / DEF-001
    provider: Literal["subscription", "cerebras", "ollama"]   # ⚠️ from config; the SDK
                                   #    reports no provider. The id above is the evidence.
    prompt_tokens: int
    completion_tokens: int
    cache_read_tokens: int         # why tokens × list price would be wrong — docs/05 §4
    cache_creation_tokens: int
    cost_usd: float                # measured: ResultMessage.total_cost_usd
    duration_ms: int
    duration_api_ms: int

    @classmethod
    def from_result(cls, msg: "ResultMessage") -> "Usage": ...
```

⛔ **`from_result` matches the key by name and raises when it is absent — it never falls back to
whatever key is there.** `model_usage` routinely holds a second entry: the CLI's own housekeeping
call, on haiku, sorting *first*. Two rules, both load-bearing:

1. **Absent configured model → raise.** Recording a model that was never asked for is worse than
   crashing, because it makes the version table's rows unattributable and nothing downstream can
   detect it (D-013).
2. **The extra keys are recorded, not discarded** — `results/*.json` keeps them under
   `other_models`, so *"this run also spent $0.0006 on haiku"* stays visible. ⚠️ **A run's
   `total_cost_usd` includes them** (measured: ~16% of a trivial call), which is why
   cost-per-correct is a figure about the *attempt*, never about the model named in the row.

**This is DEF-001, and it is in this document because the first version of this section told the
implementer to write the bug** — `next(iter(...))` on a dict whose first key is the wrong model.
It went red in `doctor` at the exact moment the underlying model pin was fixed, which is the
shape of the whole class: a check that passes for the wrong reason until something else improves.

**One `Usage` per model call; an attempt sums them** — `cost_usd` in §6 is that sum across a run's
five or six nodes, not one node's figure. ⚠️ **`provider` is asserted constant within an attempt**:
if it changes mid-run the attempt is `void`, per D-015, and that check needs the field to have been
recorded per call.

---

## 5. `benchmark_hash` — exactly what is hashed

Referenced by seven places and gating every comparison, so it needs one definition rather than
seven compatible guesses.

```python
HASHED_FIELDS = ("id", "seed", "root_cause_id", "precedent")

def benchmark_hash(suite_dir: Path) -> str:
    """sha256 over what changes the measurement. Nothing else."""
    h = hashlib.sha256()
    manifest = json.loads((suite_dir / "manifest.json").read_text())
    for entry in sorted(manifest["cases"], key=itemgetter("id")):
        h.update(json.dumps({k: entry.get(k) for k in HASHED_FIELDS},
                            sort_keys=True, separators=(",", ":")).encode())
        h.update((suite_dir / f"{entry['id']}.json").read_bytes())   # the evidence
    h.update((suite_dir / "truth.json").read_bytes())                # the answer key
    return h.hexdigest()
```

| In the hash | Why |
|---|---|
| Every case file, byte for byte | **The evidence the agent sees *is* the measurement** |
| `truth.json`, byte for byte | Change the answer key and every past score becomes a different claim |
| `id`, `seed`, `root_cause_id`, `precedent` from each manifest entry | The case's identity and its stratum label |

| Out of the hash | Why |
|---|---|
| `why`, `added`, `reviewed_by`, `origin`, `history[]` | ⛔ **Provenance prose must never invalidate the version table.** Fixing a typo in a justification would otherwise orphan every past result |
| `status` | Benchmark cases have no status machine — that is the regression tier (D-024) |
| The manifest's own `benchmark_hash` field | Self-reference |
| File mtimes, key order, whitespace | Canonical JSON, sorted keys, sorted by id — **a re-serialise must not change the digest**, or `git checkout` alone could block a comparison |

⚠️ **`precedent` is in the hash even though it only matters at v5.** It is a label on the
benchmark that changes what a stratified score means ([docs/05](05-scoring.md) §1), so it is part
of the measurement from the day it exists. **Adding it later is a benchmark version bump**,
budgeted in `ROADMAP.md`'s Deferred list, not a free edit.

⛔ **`regression/` gets no hash and must not grow one.** It is a gate, not a comparison — that
asymmetry is D-024, and a hash over a set designed to grow would refuse every run after the
first.

---

## 6. The attempt record

`results/<version>.json` elides `"attempts": [...]`. One entry per attempt, written by
`touchstone score` from spans and by nothing else:

```json
{
  "attempt": 1,
  "run_id": "01J8…", "trace_id": "4bf92f35…",
  "status": "scored",
  "root_cause_id": "db_pool_exhausted", "affected_service": "postgres-primary",
  "confidence": 0.82,
  "correct": true,
  "escalated": false, "expected_escalate": false,
  "interrupted": false,
  "recommended_action": "scale_workers",
  "tool_calls": 6, "budget_exceeded": false, "truncated_reads": 1,
  "hops_exhausted": false,
  "tokens": {"prompt": 8412, "completion": 391},
  "cost_usd": 0.0231, "latency_s": 24.7,
  "other_models": {"claude-haiku-4-5-20251001": 0.000578},
  "hops": 3
}
```

| `status` | Means | Counts toward |
|---|---|---|
| `scored` | The run finished and produced a parseable verdict | Everything |
| `parse_failure` | Structured output violated the schema | ⛔ **Scored as wrong** — D-013's "a parse failure is a scored failure, not a retry" |
| `void` | 429, or a provider switch mid-run | ⛔ **Nothing.** `void_attempts` only — a quota limit must never look like a regression |
| `incomplete` | The process died; the checkpoint exists | Nothing. `touchstone run --resume` picks it up (D-015) |

**`other_models` is every `model_usage` key that is not the candidate's model, with its cost** —
usually the CLI's housekeeping haiku call, and usually absent. It exists so that `cost_usd`, which
*includes* those calls, can be read honestly: the row names one model and the figure covers all of
them (§4, DEF-001). ⛔ **An entry here is not a provider switch** — that is D-015, it is detected on
`canonical_model` changing *within* the attempt, and it voids the run rather than annotating it.

**`hops_exhausted` is the pair of `hops`, and the reason both are here is that one is useless
alone**: `hops == 6` does not say whether the supervisor finished at six or was cut off at six.
The scorer reads it off the last `touchstone.node.supervisor` span — `next` naming a specialist
while the synthesizer runs next means the ceiling fired (D-039). ⛔ **Not a new state key**; the
attribute is already on every supervisor span ([docs/04](04-observability.md) §2).

⛔ **`correct` is computed by the scorer, never emitted by the agent**, and it reads
`root_cause_id` and `affected_service` only — invariant 8. `reasoning` is not in this record at
all; it reaches the judge through the span and nowhere else.

---

## 7. The runbook corpus

`runbooks/` — **13 markdown files, committed, frozen with the benchmark.**

| | |
|---|---|
| One per *diagnosable* class | 10 files. ⛔ **No runbook for `insufficient_evidence`** — a runbook saying "sometimes there is not enough evidence" is a retrieval shortcut to the single hardest class, and it would make the escalation metric a lookup |
| Decoys | 3 files. Plausible, well-written, and wrong for every case in the suite — a stale runbook for a service that no longer exists, one for a cause the generator never produces, one whose symptoms match two classes |
| Size | 150–400 words each. **The whole file is the chunk** — at 13 documents, chunking is a parameter with nothing to tune and a second thing to version |
| Retrieval | BM25 over the 13, top 3 returned with scores. ⛔ **No vector store, no embedding model** — same reasoning as the history corpus in D-023, and an embedding model inside the loop is an unversioned dependency the version table cannot see |
| Frozen | Hashed into `benchmark_hash`? **No** — it is not a case. It gets its own `runbook_hash` in `results/*.json`, because **editing a runbook changes v3's score and nothing else would record that** |

⚠️ **The decoys are the reason this corpus is worth building.** Retrieval that can only return
correct answers is not retrieval, and v3-minus-v2 would then measure "we gave it the answer key
in prose."

---

## 8. The prompt contract

`prompts/` — one file per node, versioned with the candidate (D-013). **The wording is written
during phase 1; the interface is fixed here**, because a node that receives something not on this
list breaks invariant 13 without failing any test that exists yet.

| Node | Receives | Returns | ⛔ Must never receive |
|---|---|---|---|
| `supervisor` | Alert, topology, `hops`/`max_hops`, `list[FindingHeader]` | `next: "timeline" \| "resource" \| "dependency" \| "done"` | Any `Finding` body — headers only, D-025 |
| `timeline` | Incident, its own prior tool results | `Finding` | Another specialist's finding; `GroundTruth` |
| `resource` | Incident, its own prior tool results | `Finding` | Same |
| `dependency` | Incident, its own prior tool results | `Finding` | Same |
| `synthesizer` | Incident, **the full `findings` list in arrival order** | `Verdict` | Tools — it decides, it does not investigate |

**Every node returns a pydantic model through the SDK's `output_format`** ([docs/00](00-stack.md)
§2), so there is no prose parsing anywhere in the graph and a schema violation is a scored
`parse_failure`.

⛔ **No few-shot examples from either tier**, per [docs/03](03-agent-and-tools.md) §4. Examples,
if any, come from cases generated with a different seed and are recorded in `DECISIONS.md`.

---

## 9. The file map

`mkdir -p` in `ROADMAP.md` phase 0 creates the directories; this places the files the phases name.

```
src/touchstone/
  domain.py            §1–4 here + docs/01 §2 — write first, everything imports it
  config.py            env vars (§10 below), paths, APPROVAL_THRESHOLD, the interval constant
  models.py            the SDK wrapper, ~60 lines — docs/00 §2
  telemetry.py         span tree, required attributes, exporter setup — docs/04     [phase 1, P1.5]
                       ⛔ console + file exporters only; the Phoenix container is P2.8.
                       Moved out of phase 2 by D-037 — a phase that emits no span
                       ends with a scorer that has never read one.
  cli.py               typer app; every command in docs/06 §1
  api.py               fastapi; the five endpoints in docs/06 §2                    [phase 2]
  incidents/
    generate.py        truth first, then render — docs/01 §4
    renderers.py       ten cause renderers + the deletion path for insufficient_evidence
    signature.py       Signature extraction                                         [deferred]
  agent/
    graph.py           StateGraph, edges, checkpointer, interrupt
    nodes.py           supervisor, three specialists, synthesizer, gate
    state.py           AgentState, Finding, FindingHeader (§4)
  tools/
    read.py            four of the five read-only tools — the incident's own state
    runbooks.py        the fifth: BM25 over runbooks/ (§7) — v3's whole delta
    history.py         search_incident_history over history/                        [deferred]
    mcp_server.py      the same five over MCP — FastMCP, mcp 1.x (D-019, D-031)     [phase 2]
  loop/
    run.py             suite runner, k attempts, --resume, attempt cache (D-015)
    score.py           spans → results/*.json (§6)
    compare.py         the five promotion conditions — docs/02 §1                   [phase 2]
    promote.py         results/index.json, open → locked
    mine.py            failures → suite/proposed/                                   [phase 3]
    suite.py           show / diff / log / review / quarantine                      [phase 3]
    budget.py          thresholds from v1's measured numbers                        [phase 2]
    record.py          → the README table                                           [phase 2]
  doctor.py            phase 0, first file written — docs/00 §6

prompts/               one per node (§8)
runbooks/              13 markdown files (§7)
suite/                 benchmark/ · regression/ · proposed/ · CHANGELOG.md
                       ⛔ truth.json lives INSIDE each tier — §5's hash reads
                       suite_dir/truth.json, and suite_dir is the tier (DEF-005)
history/               v5 only — docs/01 §4                                         [deferred]
results/               one json per version + index.json + negative-control.md
diagrams/              the D-021 artifacts, committed before their implementation
tests/unit/            the 14 invariants, zero model calls, under 2 seconds
tests/evals/           judged dimension only — never gates
```

⚠️ **`domain.py` and `doctor.py` are the only two files with a fixed order.** Everything else
follows the build order in `ROADMAP.md`, which is the ordering that keeps the scorer independent
of the agent's shape.

---

## 10. Environment

| Variable | Set where | Purpose | ⛔ |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | **nowhere** | — | ⛔ **Asserted absent by `touchstone doctor`.** If set, runs bill an API account instead of the subscription and nothing else notices (D-001) |
| `CEREBRAS_API_KEY` | `.env`, local only | Fallback path B, and the judge (D-016) | Never in CI — CI calls no model (D-014) |
| `TOUCHSTONE_TRACE` | shell | `console` prints the span tree; unset exports OTLP | — |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | compose | Phoenix, `http://phoenix:6006` | The one variable the backend swap changes — docs/04 §4 |
| `PHOENIX_SQL_DATABASE_URL` *or* `PHOENIX_WORKING_DIR` | compose | ⚠️ **Without one, traces die with the container** and every past row loses its evidence | — |
| `TOUCHSTONE_SUITE_DIR` | tests | Points the runner at a fixture suite | Never set in a scored run |
| `ERASER_API_KEY` | shell, optional | Diagram authoring only | ⛔ Never in `pyproject.toml` — not a dependency (D-021) |

**`.env` is gitignored; `.env.example` is committed with every key present and every value
blank.** A variable that only exists in one person's shell is the failure the fresh-clone check
in [docs/06](06-api.md) §3 exists to catch.

---

## 11. What this file deliberately does not fix

- ⛔ **Budget thresholds stay unset.** `ROADMAP.md` P2.3 sets them from v1's *measured*
  numbers. A guessed threshold in a spec becomes a real one nobody re-derives.
- ⛔ **Prompt wording is not here.** The interface is a contract; the wording is a candidate, and
  a candidate belongs in git under a version number, not in a doc.
- ⛔ **`n` and `k` stay at 10 and 3.** Changing either is a decision with a cost (D-024, D-030),
  not a schema detail.
- ⚠️ **No `Verdict` validator is specified beyond the type.** Whether `escalate=True` with a
  non-null `root_cause_id` is a schema error or a scored wrong answer is decided by invariant 4's
  test in phase 1 — and it should be decided *there*, against a real agent's failure mode, rather
  than guessed here.
