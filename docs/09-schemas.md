# 09 — Schemas: the file map, the hash, and what the archived specimen defined

> ⚠️ **Specification, phase 0.** This describes the design; it is not a description of shipped code. `touchstone doctor` is the only implemented command today — see the [README](../README.md) for what runs and what does not. ⛔ **And the specimen changed under it.** D-062 replaced the self-authored infra-RCA corpus with **τ²-bench retail** — 114 tasks, MIT, deterministic DB-state-diff reward. Where this file still says *incident*, *root cause*, *affected service* or *escalate*, it is describing the **archived** specimen (branch `incident-specimen`), not what touchstone measures. **The loop is unchanged; that is the claim the swap was for.**

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
> ⛔ **Archived specimen (D-062).** `Evidence`, `Series`, `LogLine` and `Deploy` were the rendered incident the agent read; retail's agent reads a database through 16 tools instead. The section is kept because §9's archived map points at it, and the *shape* of the problem it solved — how much evidence to render, and what to leave out — is the same question the τ² user simulator's `known_info`/`unknown_info` split answers upstream.


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
> ⛔ **Archived specimen (D-062).** `RootCause`, `Specialist` and `Action` were ours. The closed sets that matter now are upstream: `RewardType` (5 members) and `TerminationReason` (10) — docs/01 §2. The section is kept because `ESCALATION_THRESHOLD`'s argument — that a value compared against an enum belongs beside the enum, not in `config.py` (D-056) — outlived the enum, and `config.py` still follows it for the model pins.


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

class BlastRadius(IntEnum):        # ordered, so escalation is a comparison
    NONE         = 0
    ONE_HUMAN    = 1
    ONE_SERVICE  = 2
    SERVICE_LIVE = 3               # ← at or above this, the verdict escalates
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

ESCALATION_THRESHOLD = BlastRadius.SERVICE_LIVE

# Two closed sets that are `Literal`s rather than enums, and the reason differs for each.
Specialist = Literal["timeline", "resource", "dependency"]
LogLevel   = Literal["DEBUG", "INFO", "WARN", "ERROR"]
```

**`Specialist` is a `Literal` because it is the *edge* vocabulary of the graph.** The
supervisor's `next` also takes `"done"` (§8), which is not a specialist — so an enum here would
either be missing a member or carrying one that no specialist answers to. It is the type of
`GroundTruth.required_specialist` ([docs/01](01-spec.md) §2) and of the router's own output, and
naming it once is what keeps those two from drifting apart.

**`LogLevel` is a `Literal` because two modules need the same closed set**: `LogLine` validates
against it and the generator's log helpers take it as a parameter. Spelling a four-member set
twice is how sets drift — and the generator is the one place that could widen it silently.

**`BlastRadius` is an `IntEnum` so that escalation ([docs/03](03-agent-and-tools.md) §3) is
literally `verdict.escalate = action.blast_radius >= ESCALATION_THRESHOLD`** — one comparison, no
table lookup at the decision point, and invariant 4 is a test over six enum members rather than
over prose. The mapping in `_BLAST` is the table from [docs/01](01-spec.md) §5, transcribed once.

⛔ **The threshold is a named constant, not the literal `3` and not a config value.** A tunable
threshold is a policy the system could learn, and [docs/01](01-spec.md) §5 says this one is
hand-written on purpose.

⚠️ **It was called `APPROVAL_THRESHOLD` until D-040.** The rename is not cosmetic: nothing
approves anything now, and a constant whose name promises a gate that does not exist is how a
reader concludes the system has one.

---

## 3. Tool return types — and the one signature that was wrong
> ⛔ **Archived specimen (D-062).** Those five tools are on the branch. Retail's 16 are upstream, typed by `ToolType`, and we do not define their returns — docs/01 §5. The section is kept because the *finding* is not specimen-bound: a signature in a spec disagreed with the signature in the prose beside it, and only writing both out caught it.


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
> ⛔ **Archived specimen (D-062).** There is no graph. τ² runs one agent through its own orchestrator (`orchestrator.py:260`); `AgentState`, `Finding` and `FindingHeader` are archived with `agent/`. The section is kept because D-025 and D-026 — no specialist reads another's finding, no two spans overlap — are the reason invariants 13 and 14 exist, and docs/01 §6 keeps them retired-in-place rather than deleted.


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
run — **and a mid-run MODEL switch is visible in *it*, not in `provider`**: the id that answered
is the only thing the call reports.

⚠️ **This sentence used to say *provider* switch**, and illustrated it with *"path B answers as
`llama-3.3-70b` and path C as an ollama tag"*. D-067 makes every role Anthropic, so there is no
second provider to switch to. **What the field is for did not change** — five Anthropic pins can
still drift, and `canonical_model` is still what catches it. Only the example was impossible.

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

    other_models: dict[str, float] = {}   # every OTHER model_usage key → its cost (§6)

    @classmethod
    def from_result(cls, msg: "ResultMessage", *, model: str,
                    provider: Provider) -> "Usage": ...
```

⚠️ **`model` and `provider` are REQUIRED keyword arguments, not defaults read from `config`.**
A default is a second place the pinned model can be wrong, and it is the silent one; it also
keeps `domain.py` importable with no project dependency at all, so the scorer never drags in
the agent's configuration to read a results file.

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

⛔ **D-062 inverted what it hashes, and that is a strengthening.** It used to hash *our* suite —
fields we chose, over cases we generated, checked against tampering by us. It now hashes
`data/tau2/domains/retail/tasks.json`, **a file we do not own**, so a silent upstream edit is a
CI failure rather than a moved goalpost (docs/01 §6, invariant 7). The `HASHED_FIELDS` selection
below is archived with the generator: there is nothing to select, because the whole file is the
input. ⚠️ **Pin the collation if the input ever becomes a *list* of files again** — a hash over
a list is a hash over its order, and a shell `sort` and Python's `sorted()` disagree on
punctuation (D-068).

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
| `why`, `added`, `admitted_by`, `origin`, `history[]` | ⛔ **Provenance prose must never invalidate the version table.** Fixing a typo in a justification would otherwise orphan every past result. ⚠️ **This row is why the `reviewed_by` → `admitted_by` rename (D-040) cost nothing** — a provenance field can be renamed without orphaning a single past score |
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

⚠️ **The keys below are the archived specimen's** — `root_cause_id`, `affected_service`,
`escalate`. The live shape is docs/05 §6, and the fields that replace them are
`reward_breakdown`, `termination_reason` and `tau2_commit`. **The structure is unchanged**:
one record per attempt, written from spans, never edited by hand — which is the part D-062 was
supposed to leave standing.

```json
{
  "attempt": 1,
  "run_id": "01J8…", "trace_id": "4bf92f35…",
  "status": "scored",
  "root_cause_id": "db_pool_exhausted", "affected_service": "postgres-primary",
  "confidence": 0.82,
  "correct": true,
  "escalated": false, "expected_escalate": false,
  "recommended_action": "scale_workers", "blast_radius": 2,
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
> ⛔ **Archived specimen (D-062).** 13 markdown runbooks were v3's whole delta, and there is no v3 corpus to search. Retail's equivalent is the domain policy, which upstream hands the agent directly. The section is kept because **it is the closest thing here to what a retrieval version would look like**, and if one is ever built it starts from this shape rather than from nothing.


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
> ⛔ **Archived specimen (D-062).** One prompt per node, and there are no nodes. The section is kept because the contract idea survives the swap intact: a prompt is a *candidate under a version number*, not a doc, and that is why §11 still refuses to put wording here.


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

`mkdir -p` in `ROADMAP.md` phase 0 creates the directories; this places the files the phases
name. ⛔ **This section is an authority, not documentation** — `scripts/check-diagram.py`
milestone 4 rejects any path a diagram cites that does not appear here or in `ROADMAP.md`. A
file that is real but unlisted fails the guard, which is the intended direction: the map is
what makes a fabricated path detectable.

```
src/touchstone/
  config.py            env vars (§10 below), paths, the five model pins (D-067)   [phase 0 ✅]
  doctor.py            phase 0, first file written — docs/00 §6                   [phase 0 ✅]
  cli.py               typer app; every command in docs/06 §1                     [phase 0 ✅]
  adapter.py           ⛔ THE ONE THAT MATTERS. The Claude Agent SDK behind τ²'s
                       `generate()` seam, dispatching on `model`. ONE adapter, FOUR
                       roles, because there is one chokepoint — `llm_utils.py:355`
                                                                                  [P1.1]
  telemetry.py         span tree, required attributes, exporter setup — docs/04    [P1.5]
                       ⛔ console + file exporters only; the tracking server is P2.6.
                       🔴 D-074: MLflow, not Phoenix — and the slot was misquoted as P2.8.
                       Moved out of phase 2 by D-037 — a phase that emits no span
                       ends with a scorer that has never read one.
  api.py               fastapi; the four endpoints in docs/06 §2 — ⚠️ its reason is open (D-040)
  gate/
    tier1.py           the hand-written DB constraints — NO model                 [P2.1]
    extract.py         the model TRANSLATES a stated policy into a predicate. ⛔ The
                       VERDICT is mechanical; it never judges "did well" (D-064)   [P2.2]
    enforce.py         REFUSES the call before it executes — the hook at
                       `Environment.make_tool_call()` (D-065)                      [P3.1]
  loop/
    run.py             suite runner, k attempts, --resume, attempt cache (D-015)
    score.py           spans + τ² `RewardInfo` → results/*.json (§6)
    compare.py         the acceptance conditions — docs/02 §1                      [phase 2]
    promote.py         results/index.json, open → locked
    mine.py            THE INNER LOOP — one trace, n attempts, docs/02 §5          [phase 3]
    suite.py           show / diff / log / review / quarantine                     [phase 3]
    budget.py          thresholds from v1's measured numbers                       [phase 2]
    record.py          → the README table                                          [phase 2]

suite/                 benchmark/ · regression/ · proposed/ · CHANGELOG.md
                       ⛔ **The benchmark tier is now the 114 upstream retail tasks**, read
                       from `data/tau2/domains/retail/tasks.json` and never copied here.
                       `suite/benchmark/manifest.json` records the hash it was read at —
                       invariant 7 — rather than the cases themselves
results/               one json per version + index.json + negative-control.md
diagrams/              the D-021 artifacts, committed before their implementation.
                       `diagrams/README.md` is the index — docs/07 §5
tests/unit/            the invariants of docs/01 §6, zero model calls, under 2s
tests/evals/           judged dimension only — never gates
scripts/               🆕 tooling that checks the OTHER files — not imported by anything
  check-diagram.py     the D-021 guard: 9 milestones over diagrams/*.eraser — 4 reads THIS
                       section, 4a hashes the 8 upstream files we attach to, 7 reads the
                       RENDER, 8 greps the DSL for a `[` — which Eraser eats the message for
  check-links.py       every markdown link resolves — against git, not the working tree
  p0-deps.sh           the phase 0 install, one command
  p0-probe.py          the two phase 0 measurements docs/00 §8 requires before code
.github/workflows/
  touchstone.yml       CI — ⛔ calls no model (D-014). Named in ROADMAP P2.7
~~docker-compose.yml~~   🔴 gone — D-040 cut the API, D-074 cut the backend, nothing left
```

### ⛔ Archived by D-062 — kept here because the guard reads this section

**These files are on branch `incident-specimen` at `109c424` and are not on `main`.** They stay
listed because a reader meeting them in an old diagram, an old decision or a commit message
needs somewhere that says *where they went*, and because deleting a name from a map is how a
citation becomes unresolvable rather than merely stale.

```
src/touchstone/
  domain.py            the Incident/Alert/GroundTruth/Verdict models — docs/01 §2, archived.
                       ⛔ It will not be rewritten: the domain types are upstream now
  models.py            the SDK wrapper — superseded by adapter.py, which attaches at a
                       seam instead of wrapping a client
  incidents/
    generate.py        truth first, then render — the generator, cut whole
    renderers.py       ten cause renderers + the deletion path for insufficient_evidence
    signature.py       signature extraction                                        [never built]
  agent/
    graph.py           StateGraph, edges, checkpointer. ⛔ no interrupt (D-040)
    nodes.py           supervisor, three specialists, synthesizer
    state.py           AgentState, Finding, FindingHeader (§4)
    models.py          the per-node model binding
  tools/
    read.py            four of the five read-only tools — the incident's own state
    runbooks.py        the fifth: BM25 over runbooks/ (§7) — v3's whole delta
    history.py         search_incident_history over history/                       [never built]
    mcp_server.py      the same five over MCP — FastMCP, mcp 1.x (D-019, D-031)    [never built]
prompts/               one per node (§8)
runbooks/              13 markdown files (§7)
history/               v5 only — cut twice, by D-030 and D-062                     [never built]
suite/benchmark/truth.json   the planted answer key — §5's hash read this
```

⚠️ **`scripts/` was missing from this map until 2026-08-16, and the diagram guard is what
found it** — `check-diagram.py` rejected a node citing its own path, because milestone 4 checks
every path against this list. Four committed files, ~26 KB, referenced by **no** doc: a
`grep -rn 'scripts/' docs/ ROADMAP.md` returned nothing at all. The cause is structural rather
than clerical — this map places *"the files the phases name"*, and **nothing that only checks
the work is ever named by a phase**, so the map could not see it by construction. Any tooling
added later lands in the same blind spot; put it here when it lands.

⚠️ **`domain.py` was the only file with a mandatory first position, and D-062 deleted the
position along with the file.** `doctor.py` keeps its own: it is what tells you whether the
machine can run anything at all. Everything else follows the build order in `ROADMAP.md`, which
is the ordering that keeps the scorer independent of the agent's shape.

---

## 10. Environment

| Variable | Set where | Purpose | ⛔ |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | **nowhere** | — | ⛔ **Asserted absent by `touchstone doctor`.** If set, runs bill an API account instead of the subscription and nothing else notices (D-001) |
| `CEREBRAS_API_KEY` | `.env`, local only | ⛔ **`touchstone doctor` diagnostic only.** This row said *"the judge (D-016)"*; there is no non-Anthropic model anywhere in the loop, and that judge is now the router's rubric under `LOOP_MODEL` = `claude-opus-5` (D-067, `D-082` — ⚠️ it was `JUDGE_MODEL` = haiku until 2026-08-23). ⚠️ It said `claude-opus-5` until 2026-08-20 — the correction that moved the judge back on-quota did not reach this row, and *"the judged dimension"* was ambiguous between two different pins, so the constant is named here instead of the role | Never in CI — CI calls no model (D-014) |
| `TOUCHSTONE_OLLAMA_URL` | shell, optional | ⛔ Same — a `doctor` reachability check, **never a model source**. 🔴 **This row said `OLLAMA_HOST` and the code read `OLLAMA_URL`** — two names, neither of them the other, and *nothing* read the one documented here. Namespaced 2026-08-21; ollama's own variable really is `OLLAMA_HOST`, which is exactly why ours must not be | Never in a scored run |
| ⛔ **the namespacing rule** | — | **Every variable this project *reads* is `TOUCHSTONE_*`.** The two bare names above (`ANTHROPIC_API_KEY`, `CEREBRAS_API_KEY`) are ones it *asserts absent*, never consumes — and that assertion needs the vendor's exact spelling to mean anything | `tests/unit/test_env_namespace.py` fails on a new bare read |
| `TOUCHSTONE_TRACE` | shell | `console` prints the span tree; unset writes to the tracking store | — |
| `MLFLOW_TRACKING_URI` | shell, optional | Where traces land. Defaults to a local directory — **no service** | The one variable the store swap changes — docs/04 §4, **and read its narrowing before calling it vendor-neutral** |
| ~~`OTEL_EXPORTER_OTLP_ENDPOINT`~~ | ~~compose~~ | ~~Phoenix, `http://phoenix:6006`~~ | 🔴 **Gone with D-074** |
| ~~`PHOENIX_SQL_DATABASE_URL`~~ *or* ~~`PHOENIX_WORKING_DIR`~~ | ~~compose~~ | 🔴 **Gone with D-074.** ⚠️ **The lesson outlived the variable**: without one of them the traces died with the container and every past row silently lost its evidence. A local directory cannot fail that way, which is most of why it won | — |
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
- ⛔ **No repair of upstream's evaluator.** `COMMUNICATE`'s substring match carries upstream's
  own `# TODO: This could be improved!` (`evaluator_communicate.py:69`) and stays as it is —
  repairing it would break comparability with the published leaderboard, which is the only
  reason a third-party benchmark is worth more than one we wrote.
- ⚠️ **No schema for what a gate *refusal* returns to the agent.** Whether `enforce` raises,
  returns an error string the agent can read, or returns a silent no-op changes what the agent
  learns from being refused — and it should be decided in P3.1 against a real refusal, not
  guessed here. ⛔ **The three are not interchangeable**: one voids the run, one is a turn the
  agent can recover from, one is a measurement that lies.
