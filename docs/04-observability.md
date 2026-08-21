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

⚠️ **v1–v4 and v5 do not produce the same tree, and the difference is the measurement.**
v1–v4 run τ²'s own `LLMAgent` — one model call per turn, no nodes at all. v5 is our LangGraph
graph (D-071), and the node spans exist **only** there. ⛔ **A scorer that requires a node span
cannot score the baseline**, which is four of the five rows in the version table.

**v1–v4 — the τ² agent, at the seam:**

```
touchstone.run                        run_id, version, tier, benchmark_hash
└── touchstone.simulation             task_id, attempt      ← one τ² simulation
    ├── touchstone.llm                🔴 HAND-WRITTEN by adapter.py — see below
    ├── touchstone.tool.<name>        tool.name, tool.result_size, tool.truncated
    │                                 ⛔ emitted at make_tool_call(), not by the agent
    └── touchstone.verdict            ← exactly one, per invariant 3
                                        reward_breakdown[DB]  ← THE GATE, no model
                                        reward (composite), termination_reason, cost
```

**v5 adds one layer, and nothing else changes:**

```
    ├── touchstone.node.supervisor    hop, next
    ├── touchstone.node.identity      hop   ← and these never overlap: invariant 14
    ├── touchstone.node.catalogue     hop
    ├── touchstone.node.policy        hop   ← holds no τ² tool: a reasoning node by construction
    └── touchstone.node.synthesizer   hop   ← ⛔ the only node that may call a WRITE tool
```

🔴 **`touchstone.llm` is hand-written, and that is a finding rather than a preference.**
This tree said `LLM ← OpenInference, emitted by the instrumentor` until 2026-08-20. **Nothing
emits it.** Three separate paths were assumed and all three are dead:

| Assumed emitter | Why it never fires |
|---|---|
| `openinference-instrumentation-anthropic` | There is no in-process `anthropic` client to patch — `claude-agent-sdk` ships one transport and it **shells out to the Claude Code CLI**. `instrument()` returns normally and patches nothing (D-072, [docs/00](00-stack.md) §4) |
| `openinference-instrumentation-langchain` | Real, but it sees **LangGraph nodes** — and τ²'s agent never touches LangChain. It covers **v5 only**. 🔴 **Gone with D-074** — `mlflow.langchain.autolog()` (verified present, `mlflow` 3.15.1) is the v5 path now, and it has the same v1–v4 blind spot |
| litellm's own OTel callback | D-063 assumed it. `P1.1` displaces litellm at `llm_utils.py:15`, and the callback leaves with it |

🎯 **So the `cost` column would have been empty for v1, v2, v3 and v4 — and the failure is
silent.** Spans still arrive, the tree still looks right, and the scorer reads a missing
attribute as a run that simply cost nothing. **`adapter.py` writes the span or the version table
has no cost in it.**

✅ **The attributes are all obtainable at the seam.** The SDK's `ResultMessage` carries
`total_cost_usd` and per-call usage, which [docs/05](05-scoring.md) §4 already scores from; the
`model` argument to `generate()` names the role. **One `with tracer.start_as_current_span()` in
the adapter covers every τ² role at once**, for the same reason the adapter itself is one
function and not four.

⚠️ **Two names in this tree changed with the specimen and the old ones are recorded, not
deleted.** `touchstone.triage` was the per-attempt span and *triage* was the **incident
specimen's verb** — D-062 replaced the specimen and the noun is now τ²'s, `simulation`.
`case_id` is `task_id` for the same reason. `touchstone.node.resource` and
`touchstone.tool.get_metrics` named tools that no longer exist in any version.

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
| `touchstone.run` | `version`, `tier`, `benchmark_hash` | ours | scorer | Grouping, and the comparability guard |
| `touchstone.simulation` | `task_id`, `attempt` | ours | scorer | Per-case grouping. ⚠️ **`task_id` is τ²'s word**; `case_id` was the archived specimen's |
| `touchstone.tool.*` | `tool.name`, `tool.result_size`, `tool.truncated` | ours | scorer | Tool-call count, truncation rate |
| `touchstone.llm` | `llm.model_name`, `llm.token_count.prompt`, `llm.token_count.completion` | **OpenInference names, written by us** | scorer | Cost, and the model on record. ⚠️ **We keep OpenInference's attribute names while emitting the span ourselves** — 🔴 **the reason changed with D-074.** It was *"Phoenix reads them"*; Phoenix is gone and nothing reads them natively any more. They stay because they are a **stable, versioned vocabulary** for `llm.*` that we would otherwise have to invent, and because v5's autologged span lands in the same shape |
| `touchstone.llm` | `llm.prompt_template.template` — **the rendered prompt** | **OpenInference names, written by us** | 🆕 **human** | ⚠️ **Declared, not inherited** — and as of 2026-08-20 there is no instrumentor left to inherit it *from*. This row already said *"a default is not a contract"*. **The default was not weak; it was absent.** |
| `touchstone.reward` | `reward_breakdown` (per `RewardType`), `reward` (composite), `reward_basis`, `termination_reason` | ours, read off τ²'s `RewardInfo` | scorer | **`reward_breakdown["DB"]` is the gate and the only gating number** (D-069). ⚠️ The composite is on the span **beside** it, unmodified, because it is what the public leaderboard compares — a span that carried only our number would make the two indistinguishable later |
| `touchstone.turn.*` | turn index on every model call, plus the span's own start and end times | ours + OTel intrinsics | scorer | ⚠️ **This row replaced the node/specialist row with D-062, and D-071 put the nodes back** — invariants 13 and 14 are un-retired ([docs/01](01-spec.md) §6) and the overlap assertion is live again, **for v5**. The turn index still earns its place: it is the only ordering v1–v4 have, having no node spans to order |
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
committed file**, not just in the tracking store.

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
| Span writer | **`mlflow.start_span()`**, `mlflow-skinny` 3.15.1 | ✅ stable. 🔴 **Was OTLP + `opentelemetry-sdk` 1.44.0 until D-074** — the SDK left with the seven packages, and `mlflow.tracing.get_bridged_tracer_provider()` is the seam back to OTel if a second backend ever needs one |
| LLM/tool attributes | **OpenInference** (Apache-2.0, since 2023) | ✅ versioned. ⚠️ **A vocabulary we write, not a protocol anything speaks here** — see the `touchstone.llm` row in §1 |
| Scoring fields | **`touchstone.*`**, defined in the table above | ours, namespaced so it cannot collide |

⚠️ **"OpenTelemetry is mature" and "OpenTelemetry's AI conventions are mature" are two
different claims.** The first is true, the second is not, and this project only makes the first.

⚠️ **And after D-074 it makes neither out loud.** Dropping the OTel SDK removed the *transport*
claim from the surface; what remains is the naming argument above, which was always the load-bearing
half. **Do not restate the maturity line as a reason for the current stack** — it is a reason for a
stack this project no longer has.

---

## 3. Wiring order

Order matters and getting it wrong produces traces that look right and are missing the LLM
spans.

1. `mlflow.set_tracking_uri()` + `mlflow.set_experiment()` — **before importing anything
   that autologs.** 🔴 **Was `phoenix.otel.register()` until D-074.** The order requirement did
   not go away with the backend: an autologger that binds at import time binds to whatever is
   configured then
2. `mlflow.langchain.autolog()` — LangGraph nodes become spans. ⚠️ **v5 only**;
   there is nothing for it to see in v1–v4
3. Application code — and `adapter.py` opens `touchstone.llm` itself

~~`AnthropicInstrumentor().instrument()` — model calls become `LLM` spans~~ 🔴 **Struck
2026-08-20. It cannot fire** (§2), and it stays visible because deleting it loses the reason.
🎯 **Note what this list did:** its own header warns that getting the order wrong
*"produces traces that look right and are missing the LLM spans"* — and then prescribed a step
that produces exactly that, in a repo where a silent no-op has now been found four times.
**A numbered procedure is a claim about the code, and nobody had run this one.**

`telemetry.py` does all three in `init_telemetry()`, called once from `cli.py`. ⚠️ **A test
asserts the span tree shape on a canned run** — the wiring is the part that breaks silently
on a dependency upgrade.

---

## 4. Exporters, and the swap that proves the point

- **MLflow local tracking store** by default — a directory, no service, no container. 🔴 **Was
  `OTLP → Phoenix` on `6006`/`4317` behind `docker compose up` until D-074.** ⚠️ **The
  persistence warning outlived the backend and is the reason the row is worth reading:** the
  Phoenix version needed `PHOENIX_SQL_DATABASE_URL` or `PHOENIX_WORKING_DIR` + a volume or
  **the traces died with the container**, taking the evidence for every past row of the version
  table. A directory on disk cannot fail that way, which is most of why it won.
- **Console exporter** under `TOUCHSTONE_TRACE=console` for debugging.
- **File exporter** in CI — spans land as JSONL artifacts so `score` runs on committed traces
  and **a scoring bug can be re-run against the original evidence** without re-running the
  agent.

**That last one is worth doing early.** It means a fix to the scorer does not invalidate
the history: re-score every past version from its committed spans and the whole table
regenerates.

### The one-env-var backend swap — a check, not a feature

```bash
MLFLOW_TRACKING_URI=<a second store> touchstone run v1 --k 1
```

**A phase-2 acceptance check runs one case against a second tracking store and asserts the same
span count.** It costs a few minutes and it is the only thing that turns *"traces are
portable"* from a slogan into a demonstrated property.

⚠️ **The claim got narrower with D-074, and the honest version says so.** It was
`OTEL_EXPORTER_OTLP_ENDPOINT` pointed at *any* OTLP receiver — a genuine vendor-neutrality
demonstration. `MLFLOW_TRACKING_URI` swaps the **store**, not the **vendor**. The wider claim is
still reachable through `mlflow.tracing.get_bridged_tracer_provider()` (verified present), and
🔴 **until that has actually been run, do not say "vendor-neutral" out loud** — say "the
store is swappable, and there is a documented seam to OTel."

⛔ **And it is a check, not a dependency.** No hosted account is required to run this repo. The
claim being made is *"the backend is replaceable"* — which is exactly the claim that goes stale
the moment it stops being tested.

---

## 4a. How the scorer reads spans back

The scorer does not tail a log or scrape a UI:

```python
import mlflow
df = mlflow.search_traces(locations=["touchstone"], return_type="pandas")
```

🔴 **Was `phoenix.client.Client().spans.get_spans_dataframe()` until D-074.** Signature verified
against the installed `mlflow` 3.15.1: `search_traces(experiment_ids, filter_string, max_results,
order_by, extract_fields, run_id, return_type, model_id, sql_warehouse_id, include_spans,
locations, …)`. ⚠️ **`experiment_ids` is deprecated in favour of `locations`** — the same trap the
struck `query_spans()` note recorded for the old client, one library later.

**This is the reason a queryable store and not a write-only backend.** A trace store the scorer
cannot query programmatically would force the spans to be written twice — once for humans, once
for scoring — and two copies of the truth is how the version table starts lying.

🎯 **And the CI path got shorter, which is the part worth noticing.** `mlflow.entities.Trace`
has `to_json()` and `from_json()` (both verified present), so the committed-JSONL artefact D-014
depends on is **a native round-trip rather than a custom file exporter**. The Phoenix design
needed one written by hand.

### run → span → score — the phase 1 gate diagram (D-021)

**The sequence docs/07 §7 calls the important one**, because it is where the design either does or
does not survive: the scorer and the agent never speak.

✅ **Everything in this picture is phase 1 except `Cmp` (`compare.py`, `P2.4`)**, which needs a
second version before it means anything. **The telemetry lifeline was `[phase 2]` until 2026-08-15**
and D-037 moved `telemetry.py` into phase 1 (it is `P1.2`; `P1.5` is `score.py`) — so phase 1 now ends with the
emitter, the scorer, and a `results/v1.json` built from spans the agent actually produced.

⛔ **The phase-2 half is the *backend*, not the emission.** `P1.5` ships the console and file
exporters; the tracking **server** (as opposed to the local directory) arrives at `P2.6`
(🔴 **this said `P2.8` and was simply wrong** — ROADMAP:284 is the backend row, ROADMAP:286 is
`record.py`. Caught 2026-08-21 while sweeping for a different error, which is the usual way). 🔴 **That
slot said "the Phoenix container" until D-074.** The scorer reads committed JSONL either way,
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

⚠️ **And one thing it deliberately narrows.** The Mermaid drew the scorer calling the store's
query API; the replacement draws it reading **committed JSONL**. Both are real — the code block at
the top of this section is the local path, D-014 is the CI path — but **only the file path is
load-bearing**, because it is the one that has to work with no credential. Drawing the live query
as *the* way the scorer gets spans is what makes D-014 look optional.

🎯 **D-074 vindicated that narrowing rather than invalidating it.** The API named in this
paragraph was `get_spans_dataframe()` against Phoenix and is now `mlflow.search_traces()`; the
**diagram did not have to change**, because it never drew the vendor. That is the whole argument
for drawing the file path, arrived at a year early by accident.

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

🎯 **The honest artifact is the substrate, not a dashboard:** the trace export *is* what such a
monitor would run on, and the one-environment-variable store swap (§4) is the demonstration that
it would. **That survives *"show me it running."*** A dashboard built for this corpus does not.
⚠️ **Read §4's narrowing before repeating this** — after D-074 the demonstrated claim is
*swappable store*, not *vendor-neutral transport*.
D-043.
