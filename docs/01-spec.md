# 01 — Spec: the incident, the verdict, the generator

> ⚠️ **Specification, phase 0.** This describes the design; it is not a description of shipped code. `touchstone doctor` is the only implemented command today — see the [README](../README.md) for what runs and what does not.

**Write this file's code first, before any agent exists.** The corpus is what makes every
later number falsifiable; an agent built before the answer key is an agent you cannot score.

---

## 1. The shape of the problem

An **incident** is a paging event plus a body of evidence. A verdict is what the agent
concludes. The suite pairs each incident with a ground truth the agent never sees.

```
  Alert ──▶ [ agent investigates via read-only tools ] ──▶ Verdict
                                                             │
  GroundTruth (hidden) ─────────────────────────────────────▶ scored
```

The domain is a generic Python web stack: a Django-style API, Postgres, Redis, a queue
consumer fleet, and a deploy pipeline. **Nothing about it is specific to any employer** —
these are the failure modes documented in the Postgres manual and every SRE book written.

---

## 2. Domain model

Pydantic models, in `src/touchstone/domain.py`. Write this file first. **The models that carry
meaning are here; the ones that carry data — `Evidence`, `Series`, `LogLine`, `Deploy`, the two
enums and the graph state — are in [docs/09](09-schemas.md), and `domain.py` holds both.**

```python
class ServiceNode(BaseModel):
    name: str                      # "billing-api", "worker-pool", "postgres-primary"
    kind: Literal["api", "worker", "datastore", "cache", "queue", "external"]
    depends_on: list[str]

class Alert(BaseModel):
    id: str
    fired_at: datetime
    service: str                   # where the alarm fired — NOT necessarily the cause
    signal: str                    # "http_5xx_rate", "p99_latency", "queue_depth", "oom_kill"
    value: float
    threshold: float

class Incident(BaseModel):
    id: str                        # "inc-007"
    alert: Alert
    window: TimeWindow
    topology: list[ServiceNode]
    evidence: Evidence             # the rendered series, logs and deploys — docs/09 §1
    seed: int                      # regenerates this incident byte-identically

class GroundTruth(BaseModel):      # ⛔ never rendered into agent context
    incident_id: str
    root_cause_id: RootCause
    affected_service: str
    resolvable: bool               # False → the correct verdict is escalation
    rationale: str                 # for the report, never for scoring
```

⚠️ **`alert.service` is deliberately not the answer.** In roughly half the suite the alarm
fires downstream of the cause — the API pages because the database is saturated. An agent
that answers with the alerting service scores near zero, which is the intended behaviour: it
is the single most common naive triage failure.

### The verdict

```python
class Verdict(BaseModel):
    incident_id: str
    root_cause_id: RootCause | None
    affected_service: str | None
    confidence: float              # 0..1
    escalate: bool
    recommended_action: Action | None
    reasoning: str                 # judged dimension only, never the primary metric
```

---

## 3. The root-cause classes — the answer key space

Eleven classes. **A closed set is what makes exact match possible**; an open-ended "describe
the cause" field would put you back to judging prose.

| id | The failure | The evidence that distinguishes it |
|---|---|---|
| `db_pool_exhausted` | Connection pool saturated; requests queue at checkout | Pool wait time climbs, DB CPU flat, no slow queries |
| `slow_query_after_migration` | A migration changed a plan; one query got expensive | Deploy immediately precedes; one query's p99 dominates |
| `cache_stampede` | Mass TTL expiry; every miss hits the datastore | Cache hit rate cliff, DB read spike, periodic shape |
| `queue_backlog_hol` | One slow message type blocks a shared consumer | Queue depth climbs on one partition only |
| `bad_deploy_regression` | New code throws on a live path | 5xx starts within minutes of a deploy, one endpoint |
| `upstream_timeout` | A third party got slow; the retry budget amplified it | External span latency up, own CPU idle, retries climbing |
| `disk_pressure` | Log or temp volume filled | Disk % ramps linearly, writes fail late |
| `memory_leak_oom` | Worker RSS climbs until the kernel intervenes | Sawtooth RSS, restart events, no traffic change |
| `config_drift` | An env var differs between environments | Failures confined to a subset of instances |
| `noisy_neighbor` | An unrelated batch job saturates a shared resource | Cause is in a service with no dependency edge to the alert |
| `insufficient_evidence` | **The evidence genuinely does not determine a cause** | Two hypotheses fit equally; the distinguishing signal is missing |

### Why `insufficient_evidence` is the most important class

It is the only class whose correct verdict is `escalate=True` with `root_cause_id=None`.

**Without it the escalation metric is trivially gameable in both directions.** An agent that
never escalates scores perfectly on a suite where escalation is never right; an agent that
always escalates scores perfectly on a suite where it always is. Mixing them means **both
over-confidence and over-caution are punished**, and the escalation F1 becomes a real number.

⚠️ Target **2–3 of 10** cases in this class. Below that it is noise; above that the suite
stops measuring triage.

---

## 4. The generator

`src/touchstone/incidents/generate.py`. **Truth first, then render the evidence it implies.**

```
pick root_cause_id + affected_service + seed
        ↓
render metrics series  (the shape that cause produces)
render log lines       (the lines that cause produces)
render deploy history  (present iff the cause is deploy-linked)
render the alert       (fires downstream, per the topology)
        ↓
Incident (agent-visible)  +  GroundTruth (hidden)
```

**Rules the generator must obey:**

1. **Seeded and deterministic.** Same seed → byte-identical incident. Without this the suite
   drifts and every version comparison is meaningless.
2. **The truth is never rendered.** No log line names the root cause. The word
   `"pool exhausted"` may appear as a *symptom* the code would really log — never as a
   conclusion.
3. **Distractors are mandatory.** Every incident carries at least one plausible-but-wrong
   signal. An incident with one clean signal tests nothing.
4. **`insufficient_evidence` cases are made by removing a signal**, not by adding noise —
   generate a normal incident, then delete the series that distinguishes its two candidates.

### Where the renderers get their shapes — read once, at P1.2 (D-029)

**The renderers are where realism is decided**, and the stated risk for this whole design is that
generated incidents come out *stylised* — solvable by pattern-matching the renderer rather than by
diagnosis (D-002's "Wrong if"). The mitigation is to build each failure **from its mechanism**, and
these are where the mechanism is observable rather than remembered.

⛔ **Read, never loaded.** Nothing below enters the repo, `pyproject.toml` or any import path —
a dataset dependency would be D-029 reversed by accident. What comes out is a shape and a note.

| Source | What it is | What it is read for | Licence |
|---|---|---|---|
| [RCAEval](https://github.com/phamquiluan/RCAEval) RE2 | 270 fault cases over Online Boutique, Sock Shop and Train Ticket, with metrics **plus logs and traces**, each labelled with root-cause service, fault type and injection time | **The best single source.** What a saturation ramp looks like against its own baseline, and how far ahead of the alert the first signal moves | MIT |
| [Loghub](https://github.com/logpai/loghub) | 19 real log corpora (HDFS, BGL, Thunderbird, OpenStack), 6 of them labelled | ⚠️ **Log register only** — what a real error line says at the moment of failure, and how much unrelated traffic surrounds it. The distractor rule lives or dies on this | per-dataset, check each |
| [OpenTelemetry demo](https://github.com/open-telemetry/opentelemetry-demo) | The reference OTel app, with `flagd` failure flags (`cartServiceFailure`, `paymentServiceFailure`, `kafkaQueueProblems`) | **Span and attribute naming**, so `touchstone`'s topology and metric names read like a real OTel deployment rather than an invention | Apache-2.0 |
| [danluu/post-mortems](https://github.com/danluu/post-mortems) · [postmortems.app](https://postmortems.app/) | ~242 indexed public incident write-ups, tagged by category | ⚠️ **Prose only, and it is the weakest of the four** — a postmortem is written *after* the cause was found, so it shows which failures recur and never what the evidence looked like beforehand | unstated — cite, do not vendor |

⚠️ **Coverage is partial and the gap runs one way.** These corpora inject at the infrastructure
layer — CPU, memory, disk, network delay, packet loss, socket. That covers `disk_pressure`,
`memory_leak_oom` and `noisy_neighbor` well, `upstream_timeout` and `queue_backlog_hol`
approximately, and **six of the eleven classes not at all**: `db_pool_exhausted`,
`slow_query_after_migration`, `cache_stampede`, `bad_deploy_regression`, `config_drift` and
`insufficient_evidence`. **Those six are built from the mechanism and from the vendor
documentation that describes it** — which is the honest position, and it belongs in the README's
Limits rather than being papered over.

### The two tiers (D-024)

```
suite/
├── benchmark/
│   ├── manifest.json    # case ids, seeds, expected causes, provenance, benchmark hash
│   └── inc-001.json … inc-010.json
├── regression/
│   ├── manifest.json    # same shape + status (open|locked|quarantined|superseded)
│   └── r-001.json …     # grows forever, never shrinks
├── proposed/            # mine writes here; nothing here gates anything
├── CHANGELOG.md         # one entry per suite version — what, why, which failures drove it
└── truth.json           # ⛔ loaded only by the scorer, never by the agent
```

⛔ **A case is immutable once written, in either tier.** Fixing a case means adding a new one
and setting `superseded_by`, never editing it. Only `status` and the append-only `history[]`
may change, and each change carries its reason.

**The `benchmark/` manifest carries a hash over all its cases, and the scorer refuses to
compare two runs whose benchmark hashes differ** — that guard is what makes the version table
honest, and it is one of the first things to write. ⚠️ **`regression/` has no such
requirement**: it is a gate, not a comparison, so adding to it resets nothing.
[docs/02](02-promotion.md) §1.

**Every case in either tier carries its own provenance** — `origin`, a required non-empty
`why`, `added`, `reviewed_by`, the mining trace if it has one, and an append-only `history[]`.
Full schema and the `touchstone suite show` / `diff` / `log` commands:
[docs/02](02-promotion.md) §5.

### The second frozen corpus — `history/`, for v5 (D-023)

The same generator, different seeds, **and the truth left in**: N past incidents carrying a
signature, the cause, the affected service, the fix and a date. Frozen and hashed exactly like
the suite, and **disjoint from it** — asserted, not assumed.

```
history/
├── manifest.json        # entry ids, seeds, history hash
└── hist-001.json …      # signature · root cause · service · fix · date
```

It is **environment, not agent state**: identical for every attempt, every case and every
candidate, so it contaminates nothing. And every suite case gains one label in its manifest
entry — `precedent: true | false_friend | none` — by what this corpus holds for it.

🔴 **`false_friend` is the one that matters**: a past incident with the *same signature and a
different cause*, with the distinguishing signal present in the live incident. It plants the
anchoring failure the same way `alert.service` (§2) plants the naive one. **Generator rules 1–4
are unchanged** — a false friend is built by placing a near-twin in `history/`, never by
altering the case. Full design: [docs/08](08-memory.md).

---

## 5. The blast-radius threshold

An action is *safe* or it *requires approval*. This is a hand-written rule, not a policy the
system learns.

| Action | Blast radius | Requires approval |
|---|---|---|
| `annotate_incident` | none | no |
| `page_secondary` | one human | no |
| `scale_workers` | one service | no |
| `restart_service` | one service, live traffic | **yes** |
| `rollback_deploy` | one service, all traffic | **yes** |
| `failover_datastore` | everything downstream | **yes** |

Anything at or above `restart_service` sets `verdict.escalate`. **It does not stop the graph,
and nothing waits for a human** — the run completes, the verdict records that a human would
have had to authorise the action, and the scorer treats that flag as one of its axes (D-040).
**Escalation is not failure** — it is a scored outcome, and on `insufficient_evidence` cases it
is the *correct* one.

⚠️ **"Requires approval" is a property of the action, not a step in the pipeline.** The
column above is what the agent must *recognise*; §7 is why there is nothing to authorise.

---

## 6. Invariants

Each one gets a test in `tests/unit/`. **These are the assertions that keep the numbers
meaning what they say.**

| # | Invariant | How it is enforced |
|---|---|---|
| 1 | The agent never sees `GroundTruth` | A test renders the full agent context for all cases and asserts no truth field appears in it |
| 2 | Every tool is read-only | No tool function may write; asserted by signature review and a no-mutation test double |
| 3 | Exactly one `verdict` span per run | Span assertion in the run test |
| 4 | **Any `recommended_action` at or above `restart_service` ⟹ `escalate=True`** | A unit test walks the §5 table, renders a verdict for each action and asserts the flag. No model call. ⚠️ **Rewritten by D-040** — it used to read *"`escalate=True` ⟹ no action executed"* and name a dispatcher, which does not exist and never will (§7). An invariant over an absent component is vacuous: it passes because nothing can violate it. This version asserts the thing §5 actually claims |
| 5 | ~~Any action ≥ `restart_service` hits an interrupt before executing~~ | ⛔ **Retired by D-040, and kept in place rather than renumbered** — the other thirteen are cited by number across `docs/`, so closing the gap would silently redirect every one of those citations. It was vacuous on two counts: nothing executes, so *"before executing"* names an event that cannot occur, and the interrupt it guarded is deleted. Its surviving content is invariant 4 |
| 6 | Same seed ⟹ byte-identical incident | Regenerate twice, compare bytes |
| 7 | A frozen case is never modified | `manifest.json` hash check in CI |
| 8 | Correctness never reads `verdict.reasoning` | The scorer takes structured fields only; asserted by passing garbage prose and an intact `root_cause_id` |
| 9 | *(v5)* `history/` is disjoint from **both tiers** | No history entry shares a `(root_cause_id, affected_service, seed)` with a benchmark or regression case. A set intersection over all three manifests — ⚠️ the regression side has to be re-checked as the tier grows, and it is the half a one-time check would miss |
| 10 | *(v5)* **Nothing is ever written to `history/`** | The corpus is opened read-only and its hash is re-checked after every suite run. ⛔ **This is the invariant the whole memory design rests on** — [docs/08](08-memory.md) §5 |
| 11 | **Every case has a non-empty `why`, an `added` date and an `origin`** | CI walks both manifests and fails on a blank field. ⛔ **A case nobody can justify does not get to gate anything** — D-024 |
| 12 | **A `locked` regression case only ever became locked by passing** | `locked_at` names a version, and `results/<that version>.json` shows it `all_k`. A lock with no run behind it is a fabricated gate |
| 13 | **No specialist's prompt contains another specialist's finding** | Render every specialist's full prompt against a state already holding two findings and assert neither appears — same shape as invariant 1, zero model calls. ⛔ This is what makes a version diff attributable: once `resource`'s output depends on `timeline`'s, a correctness movement belongs to neither node. D-025 |
| 14 | **No two specialist spans overlap in time** | Over the span JSONL already committed for CI (D-014), assert no specialist span starts before another ends. A fan-out added later — `asyncio.gather`, a parallel edge — fails here and nowhere else, and it would otherwise surface as **flakiness that looks like the agent's**. D-026 |

⚠️ **13 and 14 are the two that fail *quietly*.** Every other invariant here breaks something
visible; these two just make the version table mean less than it says, and nothing in a run
reports it. **An orchestration bug wearing the costume of the thing being measured is the worst
defect this design can have** — which is why they are assertions rather than a convention.

**Invariant 8 is what the headline number means.** Not *"the agent scored 0.8"* but *"the
agent's structured output matched a planted key 0.8 of the time"* — prose quality is a separate,
separately reported dimension.

---

## 7. What is deliberately absent

- ⛔ **No real integrations.** No Datadog, no PagerDuty, no Prometheus. The tools read the
  generated incident. Adding a real source would make the suite unfreezable.
- ⛔ **No remediation that actually does anything.** Actions are recorded, not executed —
  there is nothing to restart.
- ⛔ **No time-series database.** Metric series are arrays in the incident JSON.
- ⛔ **No multi-tenancy, no auth, no UI.**
