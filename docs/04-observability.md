# 04 — Observability: the spans *are* the score

> ⚠️ **Specification, phase 0.** This describes the design; it is not a description of shipped code. `touchstone doctor` is the only implemented command today — see the [README](../README.md) for what runs and what does not. ⛔ **And the specimen changed under it.** D-062 replaced the self-authored infra-RCA corpus with **τ²-bench retail** — 114 tasks, MIT, deterministic DB-state-diff reward. Where this file still says *incident*, *root cause*, *affected service* or *escalate*, it is describing the **archived** specimen (branch `incident-specimen`), not what touchstone measures. **The loop is unchanged; that is the claim the swap was for.**

**The reframe that makes this project different from every "we added tracing" repo:**
instrumentation here is not a dashboard someone looks at. It is the **input to the scorer**.
`touchstone score` reads spans and never reads the agent's prose.

That inverts the usual incentive. Tracing is normally the thing you add last and never look
at again. Here, if a span is missing, **a metric cannot be computed** — so the instrumentation
is load-bearing and stays correct.

---

## 1. Why score from spans rather than from return values

| | Return values | Spans |
|---|---|---|
| Tool calls made | invisible | counted, with arguments |
| Tokens spent | needs threading through every call | on the LLM span, free |
| Where the time went | one total | per node, per tool |
| Why a run scored zero | one number, no context | the whole path that led to it |
| Retries, parse failures | swallowed | visible |

**And the practical reason:** the agent's structure changes between versions — v1 has one
node, v2 has five. A scorer that reads spans does not change when the graph does. **A scorer
coupled to the agent's return shape would need rewriting for every candidate**, which is the
thing that would kill the loop by attrition.

> This is [`tracebench`](https://github.com/sandeepyadav1478/tracebench)'s design, brought
> forward — it scores CrewAI runs on OTel spans for the same reason.

---

## 2. The span tree

```
touchstone.run                      run_id, version, case_id, attempt, tier, benchmark_hash
└── touchstone.triage
    ├── touchstone.node.supervisor  hop, next
    │   └── LLM                     ← OpenInference, emitted by the instrumentor
    ├── touchstone.node.resource    hop        ← and these never overlap: invariant 14
    │   ├── touchstone.tool.get_metrics  service, metric, points, truncated
    │   └── LLM
    ├── touchstone.node.synthesizer
    │   └── LLM
    └── touchstone.verdict          ← exactly one, per invariant 3
                                      reward_breakdown[DB]  ← THE GATE, no model
                                      reward (composite), termination_reason, cost
```

⛔ **There is no `touchstone.gate` span, because there is no gate node** (D-040). `blast_radius`
moved onto `touchstone.verdict`, where it belongs: it is a property of the action the agent
chose, not of a separate step that inspected it. **The run has no terminal span other than the
verdict** — every path ends there.

### Required attributes

**Two contracts, not one — the scorer's and the diagnostician's** (D-043). **A missing attribute
is a failed run, not a zero** — silently scoring a broken trace as a wrong answer would corrupt the
version table.

⛔ **The second contract exists because D-040 removed every human from the running system.** With
nobody standing inside a run, the trace is the *only* surface a person can act on, and an attribute
that only the scorer needs is not enough to improve anything. **Both columns are asserted by the
same test.** A contract enforced for one reader and hoped for by the other is one contract.

| Span | Attribute | Convention | Read by | Used for |
|---|---|---|---|---|
| `touchstone.run` | `version`, `case_id`, `attempt`, `tier`, `benchmark_hash` | ours | scorer | Grouping, and the comparability guard |
| `touchstone.tool.*` | `tool.name`, `tool.result_size`, `tool.truncated` | ours | scorer | Tool-call count, truncation rate |
| `LLM` | `llm.model_name`, `llm.token_count.prompt`, `llm.token_count.completion` | **OpenInference** | scorer | Cost, and the model on record |
| `LLM` | `llm.prompt_template.template` — **the rendered prompt** | **OpenInference** | 🆕 **human** | ⚠️ **Declared, not inherited.** OpenInference may capture input messages by default; *Why not `gen_ai.*`* below argues that a default is not a contract, and the rest of this table relied on one |
| `touchstone.reward` | `reward_breakdown` (per `RewardType`), `reward` (composite), `reward_basis`, `termination_reason` | ours, read off τ²'s `RewardInfo` | scorer | **`reward_breakdown["DB"]` is the gate and the only gating number** (D-069). ⚠️ The composite is on the span **beside** it, unmodified, because it is what the public leaderboard compares — a span that carried only our number would make the two indistinguishable later |
| `touchstone.turn.*` | turn index on every model call, plus the span's own start and end times | ours + OTel intrinsics | scorer | ⚠️ **This row replaced the node/specialist row with D-062** — there are no nodes, and invariant 14's overlap assertion is retired in place ([docs/01](01-spec.md) §6). The times stay recorded anyway: they are what would make a fan-out visible on the day one is added, and adding the attribute afterwards means the earlier versions cannot be checked |
| `touchstone.node.supervisor` | 🆕 `findings_seen` — the finding **headers** it routed on (D-025) | ours | 🆕 **human** | *Why did it route wrong?* Without this the question is unanswerable from the trace, which guts the router metric ([docs/05](05-scoring.md) §5a) at the moment it is most useful |
| `touchstone.run` | 🆕 `attempt_status`, and `parse_error` when there is one | ours | 🆕 **human** | §1 claims spans make parse failures visible and no attribute named them. `parse_failure` is one of four attempt states ([docs/09](09-schemas.md) §6), scored **wrong** and never retried (D-013) — **a state the trace cannot express is a state nobody can diagnose** |

⚠️ **Stated cost: prompt text is bytes, and these prompts are not small.** No sampling is the rule
(§6). If the volume becomes a problem the answer is a `prompt_hash` plus the text committed in
`prompts/` — where it already lives ([docs/09](09-schemas.md) §8) — **never sampling, and never
dropping the attribute.**

**Invariant 14 needs no new attribute and it does constrain the export.** Start and end are
OTel intrinsics, so the assertion was *"no specialist span starts before another ends"* over what
is already recorded — **but only if the JSONL committed for CI keeps the timestamps.** A trace
export that drops them scores identically and silently makes the invariant unrunnable, which is
the shape of every quiet failure in this project. ⛔ **Assert the timestamps are present in the
committed file**, not just in Phoenix.

**`tier` is `benchmark` or `regression`** (D-024), and it is on the span rather than looked up
at score time on purpose: **the scorer applies a different rule to each** — a per-case average
against the incumbent for the benchmark, a binary "has this ever passed" for regression — and a
trace that cannot say which tier it came from cannot be scored twice. **`benchmark_hash` is on
every run span regardless of tier**, because it identifies *the run*, and a regression result
recorded under an unknown benchmark is not attributable to a version.

### ⛔ Why not `gen_ai.*`

The obvious choice is OpenTelemetry's own GenAI semantic conventions, and **they are not ready**:
Development status, no 1.0, and on 2026-06-12 (semconv v1.42.0) they were deprecated out
of the main `semantic-conventions` repo into `semantic-conventions-genai`, **which has no tagged
release**. `OTEL_SEMCONV_STABILITY_OPT_IN` exists because the names are still moving.

**Instrumenting to a moving vocabulary would break the scorer against its own history** — a
renamed attribute in six months invalidates every committed trace, and the version table is the
whole product.

So the split is deliberate, and it is worth being able to say out loud:

| Layer | Choice | Stability |
|---|---|---|
| Transport | **OTLP**, `opentelemetry-sdk` 1.44.0 | ✅ stable — this is the part that is mature |
| LLM/tool attributes | **OpenInference** (Apache-2.0, since 2023) | ✅ versioned, and what Phoenix speaks natively |
| Scoring fields | **`touchstone.*`**, defined in the table above | ours, namespaced so it cannot collide |

⚠️ **"OpenTelemetry is mature" and "OpenTelemetry's AI conventions are mature" are two
different claims.** The first is true, the second is not, and this project only makes the first.

---

## 3. Wiring order

Order matters and getting it wrong produces traces that look right and are missing the LLM
spans.

1. `phoenix.otel.register()` — `TracerProvider` + OTLP exporter, **before importing anything
   that instruments**
2. `LangChainInstrumentor().instrument()` — LangGraph nodes become spans
3. `AnthropicInstrumentor().instrument()` — model calls become `LLM` spans
4. Application code

`telemetry.py` does all four in `init_telemetry()`, called once from `cli.py`. ⚠️ **A test
asserts the span tree shape on a canned run** — the wiring is the part that breaks silently
on a dependency upgrade.

---

## 4. Exporters, and the swap that proves the point

- **OTLP → Phoenix** by default. `docker compose up` brings it; UI and OTLP/HTTP on `6006`,
  gRPC on `4317`. ⚠️ Set `PHOENIX_SQL_DATABASE_URL` or `PHOENIX_WORKING_DIR` + a volume, or
  **the traces die with the container** and every past row of the version table loses its
  evidence.
- **Console exporter** under `TOUCHSTONE_TRACE=console` for debugging.
- **File exporter** in CI — spans land as JSONL artifacts so `score` runs on committed traces
  and **a scoring bug can be re-run against the original evidence** without re-running the
  agent.

**That last one is worth doing early.** It means a fix to the scorer does not invalidate
the history: re-score every past version from its committed spans and the whole table
regenerates.

### The one-env-var backend swap — a check, not a feature

```bash
OTEL_EXPORTER_OTLP_ENDPOINT=https://api.smith.langchain.com/otel touchstone run v1 --k 1
```

**A phase-2 acceptance check runs one case against a second OTLP backend and asserts the same
span count.** It costs a few minutes and it is the only thing that turns *"traces are
vendor-neutral"* from a slogan into a demonstrated property.

⛔ **And it is a check, not a dependency.** No hosted account is required to run this repo. The
claim being made is *"the backend is replaceable"* — which is exactly the claim that goes stale
the moment it stops being tested.

---

## 4a. How the scorer reads spans back

The scorer does not tail a log or scrape a UI:

```python
from phoenix.client import Client
df = Client().spans.get_spans_dataframe(project_identifier="touchstone")
```

⚠️ **`query_spans()` is deprecated** — the current call is `get_spans_dataframe()`, from
`arize-phoenix-client`. ⛔ Do not reach for the deprecated one because an older tutorial uses it.

**This is the reason Phoenix and not a write-only backend.** A trace store the scorer cannot
query programmatically would force the spans to be written twice — once for humans, once for
scoring — and two copies of the truth is how the version table starts lying.

### run → span → score — the phase 1 gate diagram (D-021)

**The sequence docs/07 §7 calls the important one**, because it is where the design either does or
does not survive: the scorer and the agent never speak.

✅ **Everything in this picture is phase 1 except `Cmp` (`compare.py`, `P2.4`)**, which needs a
second version before it means anything. **The telemetry lifeline was `[phase 2]` until 2026-08-15**
and D-037 moved `telemetry.py` to `P1.5` — so phase 1 now ends with the
emitter, the scorer, and a `results/v1.json` built from spans the agent actually produced.

⛔ **The phase-2 half is the *backend*, not the emission.** `P1.5` ships the console and file
exporters; the Phoenix container arrives at `P2.8`. The scorer reads committed JSONL either way,
which is the whole of D-014.

*This paragraph recorded an open question until 2026-08-15 — ROADMAP's `P2.2` described re-pointing
the scorer at spans, which only makes sense if phase 1 had read return values, the option D-007
rejected by name. `P2.2` is struck. **DEF-004, closed.***

📐 **The picture is [`diagrams/sequence.eraser`](../diagrams/sequence.eraser), rendered to
[`diagrams/sequence.png`](../diagrams/sequence.png).** A Mermaid `sequenceDiagram` stood here until
2026-08-17 and was **replaced, not supplemented** — two sequence diagrams of one run is exactly the
drift D-036 exists to stop, and a `.eraser` source is the one that gets rendered, guarded by
`scripts/check-diagram.py`, and kept in sync with the hosted workspace. **Every line of the argument
above and below this paragraph is the original's; only the drawing moved.**

**Three things the replacement says that the Mermaid could not:**

- **`agent/models.py` → the `claude` subprocess → the network** is drawn as two separate boundaries.
  The Mermaid had a `tools` participant and no model layer at all, so the *one* crossing that makes
  this a sequence diagram rather than a flowchart was missing from it.
- **The checkpoint lands after every node**, on its own lifeline to `.touchstone/checkpoints.db` —
  and the label says that nothing reads it back yet, which is a fact about *today* that a spec
  diagram usually hides.
- **The telemetry wiring is three numbered self-messages on `telemetry.py`.** §3 above is the
  authority for the order; the drawing now asserts it in the same shape the code will have.

⚠️ **And one thing it deliberately narrows.** The Mermaid drew the scorer calling
`get_spans_dataframe()` against Phoenix; the replacement draws it reading **committed JSONL**. Both
are real — the code block at the top of this section is the local path, D-014 is the CI path — but
**only the file path is load-bearing**, because it is the one that has to work with no credential.
Drawing the Phoenix read as *the* way the scorer gets spans is what makes D-014 look optional.

⛔ **`note over` is not available.** Eraser accepts it, round-trips it verbatim in the API response,
and renders nothing at all — measured 2026-08-17. The Mermaid's four `Note over` lines therefore
became message labels and block labels, which is why the replacement's labels are longer than a
sequence diagram's usually are. **Three of those four notes carried the load-bearing claims**
(invariant 1, invariant 14, and the missing arrow below), so a port that kept the arrows and let the
notes fall would have looked complete and asserted nothing.

⛔ **The missing arrow is the design.** The scorer reads spans, never a return value — which is
what lets CI score a committed JSONL with no model call (D-014), and what stops `score.py` from
inheriting the agent's shape. **If a return value ever reaches the scorer, both properties are
gone and nothing fails visibly.**

⚠️ **`truth.json` is loaded by the scorer and by nothing else in this picture.** It has no edge to
the graph, to `tools/` or to the exporter — the same reason there is no arrow from a container to
`suite/` in [docs/06](06-api.md) §3. In the replacement it is a **self-message on `Score`**, which
is the strongest form the claim can take in a sequence diagram: a self-message has no other end.

---

## 5. The budget

`budget.py`, checked **before** each model call.

| Budget | Default | On breach | Enforced by |
|---|---|---|---|
| USD per triage | ⟨set from v1⟩ | Abort the attempt, record `budget_exceeded` | **`max_budget_usd`, in the CLI** — a hard ceiling below the wrapper, so a runaway attempt cannot outspend it even if `budget.py` has a bug |
| Tool calls per triage | ⟨set from v1⟩ | Abort the attempt | `budget.py`, in the supervisor |
| Wall clock per triage | 120 s | Abort the attempt | `budget.py` |

⚠️ **The cost budget is in dollars, not tokens, and that is deliberate.** `ModelUsage` carries
`cacheReadInputTokens`, so a token budget prices cached reads as if they were fresh — it would
tighten as prompt caching *improved*. `total_cost_usd` already accounts for it.

**A breach is a scored outcome, not a crash.** It appears in the results file as its own
category, because "got the right answer after 40 tool calls" and "gave up" are different
failures and the table should show which.

⛔ **A `max_budget_usd` abort is a breach, not a void.** It is the agent's own behaviour. A 429
is a void attempt (D-015) — the run did not happen, and the two must never land in the same
bucket.

⛔ **Set the budgets from the v1 baseline's measured numbers**, not from a guess. A budget
invented before the first run is a number with no provenance — the exact shape this repo's
failure table is full of.

---

## 6. What is deliberately absent

- ⛔ **No Grafana, no dashboards, and no realtime production monitoring.** Nobody is watching this
  in real time. The consumer of the spans is a scorer, and now also a human reading them after the
  fact (§2's second contract).
- ⛔ **No sampling.** Every run is traced; the volume is ten cases × k.
- ⛔ **No distributed tracing claim.** One service, one machine. Stated in the README's Limits.

⚠️ **The monitoring row is the one under pressure, so the reason is written out.** A gate list for
an enterprise agentic system reasonably includes *realtime monitoring in production*. **This
project has no production and no users** — a dashboard over 114 benchmark tasks is a directory
that looks like a capability, which is the failure [docs/03](03-agent-and-tools.md) names by name.

🎯 **The honest artifact is the substrate, not a dashboard:** the OTLP export *is* what such a
monitor would run on, and the one-environment-variable backend swap (§4) is the demonstration that
it would. **That survives *"show me it running."*** A dashboard built for this corpus does not.
D-043.
