# 00 — The stack: every package, every version, and the model path

> ⚠️ **Specification, phase 0.** This describes the design; it is not a description of shipped code. `touchstone doctor` is the only implemented command today — see the [README](../README.md) for what runs and what does not. ⛔ **And the specimen changed under it.** D-062 replaced the self-authored infra-RCA corpus with **τ²-bench retail** — 114 tasks, MIT, deterministic DB-state-diff reward. Where this file still says *incident*, *root cause*, *affected service* or *escalate*, it is describing the **archived** specimen (branch `incident-specimen`), not what touchstone measures. **The loop is unchanged; that is the claim the swap was for.**

**Read this before `uv add` anything.** Every package below was resolved against PyPI on
**2026-08-14** and every SDK field quoted was read out of the installed wheel, not from
memory. Nothing here is aspirational.

---

## 0. How these were chosen

**Two filters, applied in order.** First: does the ecosystem actually converge on a tool for
this job, or is it a capability everyone describes and nobody has standardised? Where a
standard exists — MCP for tool exposure — take it. ⚠️ **This clause named OTLP first until
D-074**, and dropping it is the honest edit: the filter is still right, but *this* stack no longer
spends it on transport. Where one does not,
**the gap is the interesting part**, and the right response is to build the thing and measure
it rather than adopt whichever vendor is loudest. Agent memory is the clearest case, and D-022
makes it an experiment instead of a dependency.

Second: **is it mature enough to depend on**, checked against PyPI and the upstream repo on the
same day rather than from memory. That filter removed more candidates than the first one did.

### Maturity, checked 2026-08-14

| Question | Answer | Source |
|---|---|---|
| Are OTel's **GenAI semantic conventions** stable? | ⛔ No. Development status, no 1.0. On 2026-06-12 (semconv v1.42.0) they were deprecated out of the main repo into `semantic-conventions-genai`, which has no tagged release | OTel semconv repo |
| Is OTel itself mature? | ✅ Yes — `opentelemetry-sdk` 1.44.0, stable protocol. The protocol and the conventions are two different questions, and only one of them is unstable | PyPI |
| Is MCP ready to depend on? | ✅ Yes. Spec 2026-07-28: stateless core, formal extensions, a 12-month deprecation policy. `mcp` 2.0.0 shipped the same day — ⚠️ **but this project pins 1.x**, because the LangChain bridge does not support 2.0 at any published version (D-031) | modelcontextprotocol.io |
| ~~Is Phoenix real or a demo?~~ | 🔴 **Question retired by D-074, 2026-08-21 — it was the wrong question.** Phoenix is real; it was dropped because **nothing needed collecting**. ⚠️ And the answer above was wrong on a fact it did not need: `arize-phoenix` is **Elastic-2.0, not Apache-2.0** (its `-client`/`-otel` siblings are Apache-2.0). *Maturity was never the deciding axis, which is why the error survived* | PyPI + Arize docs |
| Is MLflow real, and who ships it? | ✅ `mlflow-skinny` **3.15.1**, Apache-2.0, maintainer `Databricks <mlflow-oss-maintainers@googlegroups.com>`, org created 2018-06-05, `mlflow/mlflow` ★27598. ⚠️ Its PEP 740 attestation names `mlflow/releases` — **a repository that 404s to the public**, so the build is signed but not auditable. Signed-but-private beats unsigned; it is not the same as inspectable | PyPI + GitHub |
| Is DeepEval maintained? | ✅ Yes — 516 releases, the last 2 days before this was written. **It was cut on fit, not on health** (D-020) — and 🆕 **the fit changed**: D-076 admits it as a *diagnostic*, never a gate. ⚠️ It also **phones home by default** (PostHog + Confident AI); `DEEPEVAL_TELEMETRY_OPT_OUT` is set in `config.py` | PyPI |
| Anything dead in the candidate set? | ⛔ `agentops` — last release **350 days** ago. ⚠️ `ragas` — 213 days. ⛔ `promptfoo` on PyPI is a 5-release stub; the real one is JavaScript | PyPI |

---

## 1. The model path — Anthropic first

⛔ **Anthropic models only, in every role — D-067.** There is **one** path, not three. It is
`claude-agent-sdk` spawning the `claude` CLI, authenticated by the Claude Code login already on
this machine (`~/.claude/.credentials.json`) and billed to the **subscription**: no API key, no
separate invoice.

**Five roles, five pins, all of them Anthropic.** The constants are in
[`config.py`](../src/touchstone/config.py); this table restates them, and **`config.py` is the
authority if the two ever disagree.**

| Constant | Model | Role |
|---|---|---|
| `MODEL` | `claude-sonnet-5` | **The agent under test** — the thing being measured |
| `USER_MODEL` | `claude-haiku-4-5-20251001` | The τ² user simulator — **frozen apparatus**, changing it changes the instrument |
| `LOOP_MODEL` | `claude-opus-5` | **All three mining-loop agents** — router, curator, critic (`D-082`). ⛔ Not `MODEL`: sonnet-5 is under test and must not also be apparatus. *(Was `JUDGE_MODEL`, haiku, the rubric judge that reported and never gated.)* |
| `NL_ASSERTION_MODEL` | `claude-opus-5` | τ²'s NL-assertion evaluator |
| `REVIEW_MODEL` | `claude-opus-5` | The opt-in hallucination reviewer — validates the *simulator*, not the agent |

⚠️ **`doctor` resolves exactly one of these five against a live call — `MODEL`.** The other four
have no caller yet, and a probe with nothing behind it would report green on a pin that was never
resolved: it would be checking this table against itself. ⛔ **A green `doctor` is evidence about
one pin, not five**, and the gap closes as each role gains a real caller, not by adding four more
assertions here.

⛔ **ollama and Cerebras are `doctor` diagnostics and never model sources.** Both are reachable
from this machine, which is exactly why the rule has to be written down rather than enforced by
absence. A run that quietly falls back to a local model is not a cheaper run — it is a
different experiment wearing the same version number.

⚠️ **This section said the opposite until 2026-08-20**, and the way it was wrong is the useful
part. It carried a three-path table — path B **Cerebras** as *"the judge, high-k runs, and the
fallback when A is rate-limited"*, path C **ollama** as *"last resort"* — which is a coherent,
sensible design. It was simply not this project's design any more. D-067 settled Anthropic-only,
the README and both diagrams were corrected, **and nothing walked backwards to the stack doc**:
the correction reached every artifact that cited the rule and missed the one that *stated* it.
A reader following the docs in order would have hit the retired answer first.

### ⚠️ The distinction that matters, stated precisely

**Claude Pro is not API credits.** A program calling `api.anthropic.com` with an
`ANTHROPIC_API_KEY` is billed per token on the API console, entirely separately from the
subscription.

**But the Agent SDK does not do that.** `claude-agent-sdk` spawns the `claude` CLI as a
subprocess and inherits the CLI's own credentials — the same login that runs Claude Code
interactively. So a programmatic run over path A is **subscription-backed**, and this is what
makes running the suite k times per case affordable.

**Verified on this machine, 2026-08-14:** `claude` 2.1.231 at `~/.local/bin/claude`,
`~/.claude/.credentials.json` present, and **no `ANTHROPIC_API_KEY` set in the environment.**

⛔ **Never set `ANTHROPIC_API_KEY` for this project.** If it is set, the CLI may use it and
the runs start billing the API account. `touchstone doctor` asserts it is absent — see §6.

### What you pay instead: quota, not dollars

The subscription has usage windows, and the suite is not small:

```
one candidate scored = tasks × k attempts × model calls per task
                     = 114   × 3          × (agent + simulator turns, UNMEASURED)
```

⚠️ **Only two of those three factors are known.** 114 is τ² retail's task count and `K = 3` is
the constant in `config.py`; **calls per task has never been measured here**, because no run has
happened. Multiplying by a guess would produce a total that reads like a measurement. The
honest statement is the shape: **a candidate costs hundreds of model calls, and the two knobs
are the task subset and `k`.**

*(This block read `10 × 5` until 2026-08-20 — the archived specimen's ten cases at the `k` that
D-030 lowered to 3. Both factors were stale and the product was quoted as ≈250.)*

**That is a real constraint and it shapes two design decisions** — the resumable runner
(D-015) and CI scoring committed spans instead of calling a model (D-014). Both are in
`DECISIONS.md`. **They are not workarounds; they are the honest consequences of a quota.**
⛔ **A third once sat here — D-016, "the judge lives on Cerebras" — and it is retired.** The
judge is now the **router's rubric** under `LOOP_MODEL`, Anthropic (`D-082`);
what makes it affordable is that it runs on a completed session, and what makes it safe is that
it selects and never gates.

**The SDK hands you the quota state, so use it.** `RateLimitInfo` carries
`status` (`"allowed" | "allowed_warning" | "rejected"`), `utilization` (0.0–1.0),
`rate_limit_type` and `resets_at`. **The runner pauses on `allowed_warning`, stops on
`rejected`, and resumes at `resets_at`** — a runner that manages its own quota finishes the
suite; one that does not dies at 3am halfway through and leaves a partial table.

---

## 2. The seam: one wrapper, ~60 lines

**One small adapter is the entire integration**, and the reason it can be one is structural:
`tau2.utils.llm_utils.generate()` at `llm_utils.py:355` is the **single chokepoint** for every
model role in τ² — the agent, the user simulator and the hallucination reviewer all import that
one function. So the adapter dispatches on the `model` argument rather than existing four times.

⚠️ **This paragraph used to justify the same smallness differently** — *"keeping it small is
what lets path B and C drop in unchanged"* — which was true of the pre-D-067 design and is now
an argument for a property nothing needs. **There are no paths B and C.** Smallness still earns
its keep; it just earns it for a different reason, and a stale justification for a surviving
decision is harder to spot than a stale decision.

```python
# src/touchstone/models.py  — the only place the SDK is imported
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage

async def complete(prompt: str, *, system: str, schema: dict, model: str,
                   max_usd: float) -> tuple[dict, Usage]:   # Usage — docs/09 §4
    opts = ClaudeAgentOptions(
        model=model,
        system_prompt=system,
        tools=[],                  # 🔴 THIS is what turns the SDK's own tools off — DEF-064
        allowed_tools=tools,       # the whitelist — D-085/D-089: [] for router/curator,
                                   #    ["run_predicate", "attempt_budget"] for the critic
        max_turns=2,               # ⚠️ NOT 1 — output_format spends a turn of its own (D-032)
        setting_sources=[],        # ⛔ [] is isolation; None loads everything (D-034)
        output_format=schema,      # structured output; the Verdict comes back typed
        max_budget_usd=max_usd,    # a hard per-call ceiling, enforced by the CLI
    )
    async for msg in query(prompt=prompt, options=opts):
        if isinstance(msg, ResultMessage):
            return msg.structured_output, Usage.from_result(msg)
```

**Four of those arguments each kill a whole class of bug, and all four were read from the
installed `types.py`:**

- ⛔ **`setting_sources=[]`** — 🔴 **this said `None` until 2026-08-14, and `None` is the value
  that leaks.** From `types.py:1807`: *"When `None`, all sources are loaded (matches CLI
  defaults). Pass `[]` to disable filesystem settings (SDK isolation mode)."* Under `None` the
  agent pulls in this machine's global `CLAUDE.md`, skills and MCP servers — **measured at 38,056
  cache-read tokens against 11,382 isolated** — and it also picks up `"model": "sonnet"` out of
  `~/.claude/settings.json`, so *isolating the agent changed which model answered*. Every score
  would depend on files outside the repo. ⚠️ **Assert it by measurement, not by reading the
  constant**: `get_context_usage()` reports `memoryFiles`, `agents` and `mcpTools`, and
  `touchstone doctor` requires all three empty (D-034).
- ⛔ **`tools=[]`** — the SDK ships Read/Bash/Glob. If the model can reach the
  filesystem it can read `suite/benchmark/truth.json` — and `suite/regression/`, which holds
  the cases that gate. **This is the leakage path that would produce a perfect score.**
  🔴 **This bullet said `allowed_tools=[]` until 2026-08-25 and that is the wrong lever.**
  `allowed_tools` means *auto-approve nothing*, not *offer nothing*: measured under
  `allowed_tools=[]`, the model ran `Read` → `Bash pwd` → `Read` and answered out of a file on
  disk — **there is no permission prompt in a non-interactive session to fail closed on.**
  `tools=[]` is the field that removes them, and the same probe under it got *"NO ACCESS."*
  DEF-064. ⚠️ **It leaks a second way**: with the built-ins live the model reached for
  `ToolSearch` before an in-process MCP tool, so the agent under measurement is not the one
  τ² defined.
  ⚠️ **The critic is the one exception and it is a whitelist, not a relaxation** —
  `["run_predicate", "attempt_budget"]`, both written here, neither able to reach a file
  (D-085, D-089). ⛔ **A whitelist in `allowed_tools` still needs `tools=[]` beside it.**
- **`max_turns=2`** — ⚠️ **the intent is one completion per node; the value is 2 because
  `output_format` spends a turn of its own** (D-032). LangGraph does the looping, so the graph
  stays the thing being measured. ⛔ **`max_turns` is not a count of model calls** — a budget
  derived from it under-counts by one and reports a breach that did not happen.
- **`max_budget_usd`** — the CLI enforces a per-call ceiling, so half of `budget.py` is free.

### What comes back, and why it is better than what was planned

`ResultMessage` carries more than a string. **Read from `claude_agent_sdk/types.py` at
0.2.137:**

| Field | What it gives the scorer |
|---|---|
| `structured_output` | The typed `Verdict` — no prose parsing, no regex, no retry-until-JSON |
| `total_cost_usd` | 🔴 **Cost is measured, not arithmetic.** See §3 |
| `model_usage` — a plain `dict[str, Any]` | **The model id is the key**, not a field: `{"claude-sonnet-4-6": {"inputTokens", "outputTokens", "cacheReadInputTokens", "cacheCreationInputTokens", "costUSD", "contextWindow", "maxOutputTokens"}}`. So the id on record still comes from the run rather than from config. ⚠️ **Restated 2026-08-26 against SDK 0.2.142** — the type is now `dict[str, ModelUsage] | None` (`types.py:1333`), and `ModelUsage` *is* a Python `TypedDict` (`:1293`, exported from the package root) carrying `canonicalModel` (`:1308`) and `provider` (`:1312`). ⛔ **Both are `NotRequired`, so a declared field is not an arriving one** — D-033's finding that `provider` does not come back was a claim about the *payload*, and only a run re-opens it. The match stays on the **key**, which is the half that is always present (D-035) |
| `duration_ms` / `duration_api_ms` | Latency, split between wall clock and API |
| `num_turns`, `terminal_reason` | `"max_turns"` is a scored outcome, not a crash |
| `is_error` + `api_error_status` | A 429 is distinguishable from a wrong answer. ⛔ **A rate-limited attempt is a *void* attempt, never a failed one** |

⚠️ **`cacheReadInputTokens` is why cost per correct triage must be read from the SDK rather
than computed.** Prompt caching means tokens × list price is simply wrong, and it is wrong in
the flattering direction.

---

## 3. What this changes about the cost metric

On a free local model, cost is *arithmetic, not spend* — a token count multiplied by a price
nobody paid. On path A the opposite is true and the naive label is wrong in the other
direction, because the calls are real and the quota they consume is finite. Say the exact
thing:

> **`total_cost_usd` is what the run would have cost at API list prices. It was not billed —
> it came out of a subscription quota.**

Both halves are load-bearing. The number is real, measured, per-run and cache-aware — **not
tokens × a price you looked up.** And it was not an invoice, so quoting it as spend would be
the mislabelled-unit failure this repo's whole discipline exists to prevent.

**Record the path alongside it — and record it honestly.** 🔴 **The SDK does not tell you which
provider served the call** (D-033); the model id does, since Cerebras and ollama answer under
different names. What fixes the *meaning* of a cost figure here is the auth mode, and that is
asserted rather than inferred: `touchstone doctor` requires `ANTHROPIC_API_KEY` absent, so
`"auth": "subscription"` in every results file is a checked precondition rather than a label.

---

## 4. The dependency manifest

**Resolved against PyPI 2026-08-14. All of them exist; nothing below is a guess.** Pin the minor,
let the patch float. 🆕 **There is no container any more** — D-074 deleted
the only one, so every package on this page is a declared dependency.

*(Cross-foot, **recounted 2026-08-21 from `pyproject.toml` itself, not stepped by hand**:
**15** declared — **9** runtime, **1** in the `diagnostics` extra, **5** dev — and **no container**.
Was 29 including the container on 2026-08-20; D-074 removed 7 packages
and the container, D-076 added 1. ⚠️ **A manifest that states its own
size has to recount when it changes**, and nothing here does that automatically — this is the
third recount, and 🔴 **the previous two were BOTH off by one, both in the direction that hides a
package.** It read 14/9/1/4 against a measured 15/9/1/5 on 2026-08-26; the dev group had gained
`mypy` and `pillow` and the prose had been stepped by hand. ⛔ **Stop stepping it** —
`doctor`'s `uv.lock` row derives the same total from `pyproject.toml` on every run and printed
**15** while this line said 14.)*

🔴 **Existence is not the property that matters, and checking it was the wrong check.** Every
package below resolved on PyPI and two of them still cannot do the job the table gives them —
`openinference-instrumentation-anthropic` has nothing to patch, and `arize-phoenix-evals`
duplicates a judge τ² already ships. **Ask what fires, not what installs.**

### Core — phase 0, install all of these

| Package | Version | Job | ⛔ Not for |
|---|---|---|---|
| `langgraph` | `1.2.9` | The graph, state, `max_hops`. ⛔ **Not `interrupt()`** — no node waits (D-040) | — |
| ~~`langgraph-checkpoint-sqlite`~~ | 🔴 **NEVER INSTALLED** | ⛔ **Struck 2026-08-26 — the phase-1 answer, and it is not the one the question expected.** The row asked *"does anything read the checkpointer back?"* for eleven days. Measured: it is **not in `[project.dependencies]`**, **not in `uv.lock`** (only `langgraph-checkpoint`, langgraph's own transitive, is there) and **not importable** — `PackageNotFoundError`. Nothing could have read it back, and a version cell that resolves on PyPI reads exactly like one that is installed. 🎯 **The question was answerable by one command for the whole time it was open, and asking about the design instead is what kept it open.** ⚠️ **This is not a `uv remove`** — there is nothing to remove; the phase-0 `uv add` line names it and the package did not land. Re-add it at **P3.4**, where `loop/mine.py` is the first LangGraph graph, and only if something resumes one |
| `langchain-core` | `1.6.0` | Messages, `@tool` schemas, the `BaseChatModel` interface the wrapper implements | ⛔ not the orchestrator |
| `claude-agent-sdk` | `0.2.142` | **Path A — the subscription-backed model** | — |
| `pydantic` | `2.13.4` | ⚠️ **Ours no longer define the domain** (D-062) — τ²'s `Task`, `RewardInfo` and `TerminationReason` are pydantic and come with the package. We use it for the results file and the gate predicates | — |
| `typer` | `0.27.1` | The CLI — the primary surface | — |
| `rich` | `14.3.4` | The compare table. `touchstone compare` output is read by a human | ⛔ never in the results JSON |

### Observability — phase 2

🔴 **Rewritten 2026-08-21 by D-074. Eight packages became one.**

| Package | Version | Job |
|---|---|---|
| `mlflow-skinny` | `~=3.15` | **Traces, runs, metrics, Prompt Registry, and the `@scorer` gate predicates.** Autologs LangGraph **in-process**, writing to `mlruns/` on disk |
| `langgraph` | `==1.2.9` | ⚠️ Pinned to MLflow's *tested autolog ceiling*, not to latest — D-075. `ml_package_versions.py` declares `0.6.2`–`1.2.9` |

**Deleted (7):** `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp`,
`openinference-instrumentation-langchain`, `openinference-semantic-conventions`,
`arize-phoenix-otel`, `arize-phoenix-client`. `arize-phoenix` itself was a container, never a
dependency, and it is gone too. `PHOENIX_URL` is out of `config.py`; `doctor` no longer probes a
trace server (D-077).

🎯 **The reason is one measured fact, and it invalidated an assumption nobody had checked:** the
chain *"OpenInference instrumentation → therefore an OTLP collector → therefore Phoenix"* was
assumed from the first draft onward. MLflow autologs LangGraph natively, so **there was nothing
for a collector to collect.** The container, its port, its `docker compose` row and its `doctor`
check all existed to serve a need that was never established.

⚠️ **What this changes about D-073, which is otherwise intact.** D-073's
decision stands — **the model span at the seam is written by hand, because no instrumentor can
see a subprocess transport.** What changes is the API it is written *with*: `mlflow.start_span()`,
not the OTel SDK, which is no longer installed. **The span still exists, is still explicit, and is
still the same span in v1 and in v5.**

⚠️ **The OpenInference attribute *names* still stay** (`llm.model_name`,
`llm.token_count.prompt`, `llm.token_count.completion`, `llm.prompt_template.template`) — now as
MLflow span attributes. ⛔ **But the justification changed and the old one must not be quoted.**
D-073 defended them partly as *"Phoenix reads them"*; Phoenix does not read anything any more.
They stay because one stable, versioned, published vocabulary beats a bespoke one — and the
argument against `gen_ai.*` below is untouched and is the real reason.

⛔ **Do not claim `gen_ai.*` compliance.** OpenTelemetry's GenAI semantic conventions are
**Development status with no 1.0**, and on **2026-06-12** they were deprecated out of the main
`semantic-conventions` repo into `semantic-conventions-genai`, **which has no tagged release at
all**. `OTEL_SEMCONV_STABILITY_OPT_IN` exists precisely because the names are still moving.

**So split the claim in two, because only one half is shaky:**

| Layer | Status | What we say |
|---|---|---|
| ~~OTLP + the OTel SDK~~ | ~~**Stable**, 1.44.0~~ | 🔴 **Not ours to say any more — D-074.** The SDK is gone; the portable-backend claim now runs through `mlflow.tracing.get_bridged_tracer_provider()` and is **unrun**, so [docs/04](04-observability.md) §4 narrows it to *"the store is swappable"* |
| `gen_ai.*` attribute names | **Development, no release** | *nothing* ⛔ |
| **OpenInference** attributes | Apache-2.0, shipping since 2023, versioned | "Instrumented with OpenInference conventions" ✅ |
| `touchstone.*` attributes | Ours, defined in `docs/04` | "Our scoring fields, namespaced so they can't collide" ✅ |

**So the answer to *"is OpenTelemetry mature enough for AI work?"* is neither yes nor no:** the
protocol is, the AI-specific vocabulary is not, and OpenInference is what fills the gap today.

⚠️ **Kept because the question keeps getting asked, not because this project answers it.** After
D-074 the only row above that is still a claim we make is the OpenInference one — and even that is
now *"a vocabulary we write"* rather than *"a protocol something reads"*. **A survey that outlives
the decision it justified reads as the current design to anyone who skims it.**

### Evals — phase 2

| Package | Version | Job | ⛔ Not for |
|---|---|---|---|
| ~~`arize-phoenix-evals`~~ | `3.4.0` | 🔴 **No job left — delete it.** The judged dimension is **τ²'s** `NL_ASSERTION`, computed by `evaluator_nl_assertions.py:121` through `generate()` — **our seam**, so it is already scored from the same substrate. ⚠️ **The row was written when the judged dimension was ours to build**; D-062 handed it to the benchmark and this outlived the reason | ⛔ **never a gating metric** — unchanged, and now enforced by there being no second judge to turn on |
| 🆕 `deepeval` | `~=4.1` | **Optional `diagnostics` extra** (D-076), reached through `mlflow/genai/scorers/deepeval`. 45 agent-trajectory metric modules — the widest of any candidate | ⛔ **Never a gate.** MLflow's registry marks **28 of 30** `is_deterministic=False`, including `ToolCorrectness` and `PlanAdherence`. ⛔ Nothing that gates may import this extra |
| `pytest` / `pytest-asyncio` | `9.1.1` / `1.4.0` | Invariants and the eval suite | — |

### MCP — phase 2, **not** deferred

| Package | Version | Job |
|---|---|---|
| `mcp` | `1.29.0` (`~=1.24`) | The official SDK. 🆕 **Serves *our* tools** — the five read-only ones named here were the archived specimen's and no longer exist. Under retail it is the `policy` node's path to the domain policy document. ⛔ **Never τ²'s sixteen**: a protocol hop inserted into the agent under test makes v1–v4 incomparable to τ²'s published baseline. ⚠️ **Not 2.0** — see below |
| `langchain-mcp-adapters` | `0.3.2` | Bridges those same tools back into LangGraph, so **one definition serves both paths**. ✅ **The reason survived D-062 and D-071 unchanged** — it is a property of having one tool definition, not of any particular domain |

⛔ **`mcp~=2.0` and this bridge do not resolve together, and the failure is disguised as a
success.** 0.3.2 declares `mcp<2.0.0`, so asking for 2.0 silently resolves the *adapters* down to
0.3.1; 0.3.1 then installs against mcp 2.0 and dies at import on a module 2.0 renamed away.
**Pin `mcp~=1.24`.** Nothing here uses a 2.0 feature and `claude-agent-sdk` needs only
`mcp>=1.23.0`. Measured at P0, recorded as **D-031**.

✅ **So the server class is `FastMCP`, from `mcp.server.fastmcp`** — the name every tutorial uses
is the right one on 1.x. *(An earlier revision of this table warned the opposite. It was written
from 2.0's release notes rather than from an installed package, which is the mistake, not the
rename.)*

⛔ **This is a server, not an integration.** The tools already exist and already have schemas —
exposing them over MCP is a thin adapter and a compose service, not a subsystem. If it grows
past that, it has stopped being worth the phase-2 slot.

### Service — phase 2

| Package | Version | Job |
|---|---|---|
| `fastapi` | `0.141.1` | Five endpoints (`docs/06`) |
| `uvicorn` | `0.52.3` | Serving |
| `httpx` | `0.28.1` | The Cerebras path and the API tests |

### Fallback providers — 🔴 **RETIRED by D-067, removal tracked as DEF-039**

⛔ **There are no fallback providers.** Anthropic in every role; ollama and Cerebras are `doctor`
diagnostics and never model sources. The three packages below are still declared in
`pyproject.toml` and are **the clearest deletion in that file** — held back only so the whole
dependency question lands as one reviewed change at P1.1 rather than in pieces. The *Job* column
names paths that no longer exist; it is left as written so the removal has something to check
itself against.

| Package | Version | Job |
|---|---|---|
| `cerebras-cloud-sdk` | `1.91.0` | Path B transport |
| `langchain-cerebras` | `0.8.2` | Path B as a chat model. ⚠️ Older than the rest (2025-11-24) — check it against `langchain-core` 1.5 at phase 0 and fall back to the raw SDK over `httpx` if it fights |
| `langchain-ollama` | `1.1.0` | Path C |

### Dev

`ruff` `0.16.3` · `uv` (the installer, not a dependency)

### 🔴 The backend, as a container — DELETED 2026-08-21

**D-074 removed the `docker-compose.yml` Phoenix service, its ports
(6006 UI/OTLP-HTTP, 4317 OTLP-gRPC) and its persistence settings.** MLflow writes to `mlruns/` on
disk in-process, so this project has **no service to start** and `docker compose` is not part of
running it.

⚠️ **The warning this section carried was correct and is worth keeping as a lesson:** without a
persistence setting, traces would have lived in the container and died with it — *silently
destroying the evidence behind every past row of the version table*. **A local directory has that
property by default, which is a reason to prefer it and not merely a convenience.**

---

## 5. `pyproject.toml`

⛔ **The file is in the repo — [`pyproject.toml`](../pyproject.toml) — and this section no
longer copies it.** A verbatim copy here was a **second source of truth with nothing keeping it
in sync**, and it drifted twice: it still listed `fastapi`, `uvicorn`,
`openinference-instrumentation-anthropic` and a `[project.optional-dependencies] fallback` of
`cerebras-cloud-sdk` / `langchain-ollama` **after D-067 banned every non-Anthropic model source
and D-072 deleted the packages**. 🎯 **A published doc quoting a file that lives four
directories away is a stale claim waiting to happen** — §4 above carries the *reasons*, which is
the part a file cannot carry.

**What the file says that is not obvious from reading it:**

- ⛔ **`langchain-mcp-adapters~=0.3.2`, not `~=2.0` and not `~=0.3`** — D-031.
- ⛔ **`tau2` is pinned to commit `a2c024725189`, and the commit is the identity** — the
  `[tool.uv.sources]` entry is not decoration: `tau2` on PyPI is a different project (DEF-050),
  and `1.0.1` is a stale version string on `main`, **not** the tag `v1.0.1`, which is a different
  tree (DEF-055). **The code ships; the data does not** — set `TAU2_DATA_DIR` (DEF-051).
- **`dev` holds `mypy~=1.19`.** Typing is total and there is no tests exemption — D-054.

⛔ **Commit `uv.lock`.** The version table is a comparison across time; an unpinned tree makes
every past row a claim about a dependency set nobody can reconstruct.

---

## 6. `touchstone doctor` — phase 0, and it is the first thing to write

One command, run before anything else, that fails loudly rather than producing a quietly wrong
number. **This is real output, 2026-08-14** — the same block is pasted in D-001:

⚠️ **It is a dated record and four of its lines have since been overtaken. Kept verbatim
anyway**, because rewriting a pasted measurement to match today is how a record stops being
one. What changed: the `model` line reads `claude-sonnet-4-6`, and the pin is now
`claude-sonnet-5` (D-067). The two ⚠ lines about `CEREBRAS_API_KEY` and `ollama` describe them
as *unavailable paths* — under D-067 both are diagnostics and **absent is the correct state**,
so `doctor` now reports the Cerebras key as a **pass** when it is missing. And the `uv.lock`
line says **27 direct deps** where `doctor` now prints **14** — recounted from `pyproject.toml`
2026-08-21, after D-074 removed seven packages and the container and D-076 added one. **Re-run
the command to refresh this block; do not hand-edit it.**

🔴 **That instruction was disregarded on 2026-08-21 and the block was hand-edited to today's
values, then reverted.** The tell was this annotation: a record that carries its own list of
overtaken lines makes the edit look like maintenance. ⚠️ **It also could not have been done
honestly** — the run available was `--no-probe`, so `model` and `setting_sources` had no live
values and would have been carried over from 2026-08-14 into a block relabelled as a fresh run.
**A composite of two runs presented as one is a fabricated measurement**, and that is the reason
for the rule, not tidiness.

⚠️ **That fourth line was found by recomputing it, not by reading it** — the annotation above
said *three* for a day while sitting directly on top of a fourth. A count pasted inside a record
is invisible to every sweep that greps for vocabulary, because nothing about `27` looks stale.

```
touchstone doctor
  ✓ claude CLI         2.1.232  (~/.local/bin/claude)
  ✓ subscription auth  ~/.claude/.credentials.json present (mode 600)
  ✓ ANTHROPIC_API_KEY  absent
  ✓ model              claude-sonnet-4-6  (pinned, answered by a live call, $0.0035 total)
  ✓ setting_sources    [] — 0 memory files, 0 agents, 0 MCP tools (11382 ctx tokens)
  ⚠ CEREBRAS_API_KEY   absent   — path B unavailable, the judge has no fallback
  ⚠ ollama             http://localhost:11434/api/tags unreachable   — path C unavailable
  ✓ uv.lock            present, 27 direct deps
```

🎯 **Two of those lines are measurements, not assertions, and that is the whole design of this
command.** The `model` line is the id that *answered a live call*, matched by name against the pin
(⛔ never by position — D-035). The `setting_sources` line is what the session **reported
loading**, via `get_context_usage()`: zero memory files, zero agents, zero MCP tools. A constant
that says isolation and a session that is isolated are different claims (D-034), and this command
exists to keep them apart.

**The `ANTHROPIC_API_KEY absent` check is the important line.** It is the difference
between a suite that consumes quota and one that quietly runs up an API bill, and it is a
one-line assertion.

**`touchstone doctor` output goes in `DECISIONS.md` D-001 verbatim** — that is how the blank gets
filled, from the machine rather than from memory.

---

## 7. What was considered and rejected

| Rejected | Why not |
|---|---|
| **Raw `anthropic` SDK + `ANTHROPIC_API_KEY`** | Bills separately from Pro. The suite is ~250 calls per candidate, so this turns the loop into something run monthly by hand — which is the failure this project is about. ⚠️ It is also the *easy* thing to reach for; that is why §6 asserts against it |
| **`langchain-anthropic`** | Clean and idiomatic, and it is an **API-key** path. Same problem. ✅ Keep it in mind as the swap if API credits ever exist — the wrapper is the only file that changes |
| **A local model as the default** | An earlier draft chose it, and it answers the wrong question. The comparison this project exists to make is between *versions of the agent*; a weak default model compresses every version difference toward noise, so the instrument stops resolving what it was built to resolve. ⚠️ **The original line ended *"kept as path C, where a local model is a fallback rather than the baseline"* — and path C is gone (D-067).** The rejection stands and its reasoning is untouched; only the consolation prize was withdrawn |
| **LiteLLM as a universal router** | One config for three providers, and ⚠️ **it drops `think: False` on ollama and returns empty content** — measured here before. Three thin adapters beat one leaky abstraction |
| **The SDK's own subagents instead of LangGraph** | The SDK can orchestrate. Then the graph is Claude Code's, not yours, and there is nothing versionable to put in the table. **LangGraph owns orchestration; the SDK is transport** |
| 🔴 ~~**MLflow**~~ **— REVERSED ON SCOPE by D-074, 2026-08-21** | ⚠️ **The reason below is untouched and still binding.** MLflow is admitted for a *different job*: **in-process trace autologging**, which is what let Phoenix and its container be deleted. ⛔ **It is NOT admitted as the version-comparison store** — `results/*.json` and the README table remain that, for exactly the reason given here. A reversal that quietly widened to the original job would re-create the two-stores problem. *Original reason:* its job here was *comparing versions*, which is **exactly what `results/*.json` and the README table already do** — from committed artifacts, in git, readable in a diff. **Two stores answering one question, and the one being cut is the one nobody can read in a diff.** ⚠️ Not a judgement on MLflow; a judgement on a second store for already-versioned data |
| 🔴 ~~**DeepEval**~~ **— REVERSED ON SCOPE by D-076, 2026-08-21** | ⚠️ **The reason below is untouched and still binding**, and is now enforced mechanically: MLflow's own registry marks **28 of 30** DeepEval metrics `is_deterministic=False`, `ToolCorrectness` and `PlanAdherence` among them. Admitted as an optional `diagnostics` extra reached through `mlflow/genai/scorers/deepeval` — **a diagnostic that explains a failure after the gate has ruled**. ⛔ Nothing that gates may import it. *Original reason:* chosen for pytest-native gating — and the judge here never gates (`docs/05`), so the one thing it is best at is the one thing this project forbids. ✅ Actively maintained; health was never the problem |
| **Raw `gen_ai.*` semantic conventions** | Development status, no 1.0, and moved out of the main semconv repo on 2026-06-12 into a repo with no tags. Instrumenting to a moving vocabulary means re-labelling spans mid-project, which would break the scorer against its own history. OpenInference instead, plus `touchstone.*` for our fields |
| **LangSmith as the backend** | Genuinely good, and hosted, account-required, and LangChain-shaped. ✅ Kept as a proof instead of a dependency: the exporter is one env var, so `docs/04` ships a swap-the-backend check. Demonstrating vendor-neutrality is worth more than picking a vendor |
| **Langfuse** | Same reasoning. ⚠️ **The second half of this row said *"also OTLP-compatible — the same one-line swap"* and D-074 removed the swap it referred to.** The rejection stands on the hosted-account argument alone, which is the half that was ever load-bearing. **The point is that the choice is reversible, not that it was hard** — and reversibility is now a documented seam rather than an exercised one |
| ⛔ **mem0 / Zep / Letta as agent memory** | Rejected as infrastructure, admitted as a candidate. Persistent memory across attempts makes `all_k` measure recall; across cases it leaks the frozen benchmark; across versions it makes v4's score depend on v1–v3 — and the version comparison is the product. What v5 became instead (D-023) is a frozen corpus of past resolved incidents carried by the *environment*, plus planted false precedents. ⛔ That needs no memory library: a read-only corpus needs retrieval, which `search_runbooks` already does at the same scale, while extraction and consolidation only exist on a write path. And the write path does not want one either (D-027) — mem0's ADD/UPDATE/DELETE is *an LLM deciding whether a new fact contradicts an old one*, a second inference step that fails silently and in the direction of confidence. The promotion rule already refuses a memory that breaks a passing case, which is a gate rather than a guess, and the store is `langgraph.store.BaseStore` — already pinned, zero new dependencies. [docs/08](08-memory.md) §9 |
| **Eraser MCP as a runtime dependency** | ⛔ Never in `pyproject.toml`. An authoring tool used before code, not a package the agent imports. Its free-tier limits are unpublished, so a build that needed it could stall on somebody else's quota. The gate in [`docs/07`](07-diagrams.md) requires an approved diagram, not an Eraser one — Mermaid in the repo is the always-available fallback |
| 🆕 **Phoenix as the trace backend** | ⛔ **Rejected 2026-08-21 (D-074) after being the chosen backend**, and not on install difficulty. MLflow **autologs LangGraph in-process to `mlruns/` on disk**, so there was never anything for a collector to collect — the container was answering a need that did not exist. It also fails this project's standing rule that **a gate must read a file, not query a service**; a verdict that can fail because a container is down is a flaky test. ⚠️ Separately and *not* the reason: `arize-phoenix` 20.3.0 is **Elastic-2.0, not OSI**. Langfuse and Opik fall to the identical collector argument |
| **A dashboard on top of all this** | Nobody watches it. See `docs/04` §6 |

---

## 8. The two things to check at phase 0 before writing code

**Both are five-minute checks that each cost an evening if skipped.**

⚠️ **1. `langchain-cerebras` 0.8.2 is dated 2025-11-24** — roughly nine months older than
`langchain-core` 1.5.4. It is the only version skew in the manifest.

**Resolve it in five minutes, not in an evening of import errors:** `uv add` it, import it,
make one call. If it fights `langchain-core` 1.x, drop it and drive Cerebras through
`cerebras-cloud-sdk` over `httpx` directly — path B is one function, not a framework, so the
loss is nil. **Record which one you used in `DECISIONS.md` D-016.**

✅ **2. The MCP pin — checked, and it moved the manifest.** `mcp` 2.0.0 did rename the server
class (`FastMCP` → `MCPServer`, `mcp.server.fastmcp.*` → `mcp.server.mcpserver.*`), **but
`langchain-mcp-adapters` does not support 2.0 at any published version**, so this project is on
`mcp~=1.24` and the class is **`FastMCP`** (D-031). The five-minute check was the right one; the
answer inverted the warning. **Import it once and confirm before writing the server** — that
instruction stands, and it is the instruction that caught this.

✅ **3. `max_turns=1` fails when `output_format` is set.** The structured-output step spends a
turn, so a single answer needs 2. It surfaces as `Reached maximum number of turns (1)` on the
first live call. ⛔ **`budget.py` must not equate `max_turns` with model calls** — derive the
tool-call budget from the spans (D-032).

---

## 9. Where these choices came from — the trail

| Decision | Evidence | Recorded as |
|---|---|---|
| Claude via `claude-agent-sdk` | The installed SDK + this machine's credential state | D-013 |
| OpenInference, not `gen_ai.*` | OTel semconv v1.42.0 deprecation, 2026-06-12 | D-017 |
| ~~Phoenix, not MLflow~~ **→ reversed** | 🔴 **D-074, 2026-08-21.** The duplication argument was right and still binds — `results/*.json` remains the version record. What was wrong was the premise that a collector was needed at all | D-018 → **D-074** |
| MCP into phase 2 | The tools already carry schemas — a thin adapter, not a rewrite | D-019 |
| ~~`arize-phoenix-evals`, not DeepEval~~ **→ reversed** | 🔴 **D-076, 2026-08-21.** *"The judge never gates"* still binds and is now mechanical: 28 of 30 DeepEval metrics are non-deterministic. DeepEval is admitted as a diagnostic; `arize-phoenix-evals` had no job left either way | D-020 → **D-076** |
| Diagram approved before any code | A process gate, not a tool choice | D-021 |
| Memory as candidate v5, not as infrastructure | Measurement independence | D-022 |
| History as a second frozen corpus + planted false friends | The cost side of memory is the unmeasured half, and the per-case gate already catches it | D-023 |

⚠️ **The subset denominator moved from 851 to 883 on 2026-08-14** and 851 was discarded as
unreproducible. **No decision changed** — the numerators were re-derived and matched. If a
figure anywhere in this repo is still divided by 851, it is stale.
