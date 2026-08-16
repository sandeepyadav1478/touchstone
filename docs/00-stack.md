# 00 — The stack: every package, every version, and the model path

> ⚠️ **Specification, phase 0.** This describes the design; it is not a description of shipped code. `touchstone doctor` is the only implemented command today — see the [README](../README.md) for what runs and what does not.

**Read this before `uv add` anything.** Every package below was resolved against PyPI on
**2026-08-14** and every SDK field quoted was read out of the installed wheel, not from
memory. Nothing here is aspirational.

---

## 0. How these were chosen

**Two filters, applied in order.** First: does the ecosystem actually converge on a tool for
this job, or is it a capability everyone describes and nobody has standardised? Where a
standard exists — OTLP for transport, MCP for tool exposure — take it. Where one does not,
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
| Is Phoenix real or a demo? | ✅ `arize-phoenix` **20.2.0**, 682 releases, self-hosts in one container, Apache-2.0, no account | PyPI + Arize docs |
| Is DeepEval maintained? | ✅ Yes — 516 releases, the last 2 days before this was written. **It was cut on fit, not on health** (D-020) | PyPI |
| Anything dead in the candidate set? | ⛔ `agentops` — last release **350 days** ago. ⚠️ `ragas` — 213 days. ⛔ `promptfoo` on PyPI is a 5-release stub; the real one is JavaScript | PyPI |

---

## 1. The model path — Anthropic first

**Claude drives the agent.** Three paths, in priority order, and the difference between them
is *how they authenticate*, which is the whole reason this section exists.

| # | Path | Auth | Bills | Use for |
|---|---|---|---|---|
| **A** | **`claude-agent-sdk` → the `claude` CLI** | The Claude Code login already on this machine (`~/.claude/.credentials.json`) | **The Pro subscription.** No API key, no separate invoice | **The agent under test. The default.** |
| **B** | **Cerebras** (`langchain-cerebras`) | `CEREBRAS_API_KEY` | Its own free/paid tier | **The judge**, high-k runs, and the fallback when A is rate-limited |
| **C** | **ollama** (`langchain-ollama`) | none | nothing | Last resort — offline, and when both A and B are unavailable |

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
one candidate scored = n cases × k attempts × model calls per run
                     = 10      × 5          × ~5 (v2+)          ≈ 250 Claude calls
```

**That is a real constraint and it shapes three design decisions** — the resumable runner
(D-015), the judge living on Cerebras (D-016), and CI scoring committed spans instead of
calling a model (D-014). Each is in `DECISIONS.md`. **They are not workarounds; they are the
honest consequences of a quota, and each one is a better answer than what it replaced.**

**The SDK hands you the quota state, so use it.** `RateLimitInfo` carries
`status` (`"allowed" | "allowed_warning" | "rejected"`), `utilization` (0.0–1.0),
`rate_limit_type` and `resets_at`. **The runner pauses on `allowed_warning`, stops on
`rejected`, and resumes at `resets_at`** — a runner that manages its own quota finishes the
suite; one that does not dies at 3am halfway through and leaves a partial table.

---

## 2. The seam: one wrapper, ~60 lines

LangGraph nodes want a chat-model interface. The Agent SDK returns an agent result. **One
small adapter is the entire integration**, and keeping it small is what lets path B and C drop
in unchanged.

```python
# src/touchstone/models.py  — the only place the SDK is imported
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage

async def complete(prompt: str, *, system: str, schema: dict, model: str,
                   max_usd: float) -> tuple[dict, Usage]:   # Usage — docs/09 §4
    opts = ClaudeAgentOptions(
        model=model,
        system_prompt=system,
        allowed_tools=[],          # ⛔ the SDK's own tools stay off — LangGraph owns tools
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
- ⛔ **`allowed_tools=[]`** — the SDK ships Read/Bash/Glob. If the model can reach the
  filesystem it can read `suite/benchmark/truth.json` — and `suite/regression/`, which holds
  the cases that gate. **This is the leakage path that would produce a perfect score.**
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
| `model_usage` — a plain `dict[str, Any]` | **The model id is the key**, not a field: `{"claude-sonnet-4-6": {"inputTokens", "outputTokens", "cacheReadInputTokens", "cacheCreationInputTokens", "costUSD", "contextWindow", "maxOutputTokens"}}`. So the id on record still comes from the run rather than from config. ⛔ **No `ModelUsage` class, no `canonicalModel`, no `provider`** — those are the TypeScript SDK's (D-033) |
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

**Resolved against PyPI 2026-08-14. All 28 exist; nothing below is a guess.** Pin the minor,
let the patch float. ⚠️ **27 of the 28 are declared in `pyproject.toml`; `arize-phoenix` itself
is the 28th and runs as a container** — the Python side only talks to it.

### Core — phase 0, install all of these

| Package | Version | Job | ⛔ Not for |
|---|---|---|---|
| `langgraph` | `1.2.11` | The graph, state, `max_hops`. ⛔ **Not `interrupt()`** — no node waits (D-040) | — |
| `langgraph-checkpoint-sqlite` | `3.1.1` | Run state for a process that dies mid-run. A separate package — forgetting it is the classic phase-1 stall. ⚠️ **It lost its original justification with D-040** and is kept pending a phase-1 answer on whether anything reads it back | — |
| `langchain-core` | `1.5.4` | Messages, `@tool` schemas, the `BaseChatModel` interface the wrapper implements | ⛔ not the orchestrator |
| `claude-agent-sdk` | `0.2.137` | **Path A — the subscription-backed model** | — |
| `pydantic` | `2.13.4` | `Incident`, `Verdict`, `GroundTruth`; the JSON schema fed to `output_format` | — |
| `typer` | `0.27.1` | The CLI — the primary surface | — |
| `rich` | `15.0.0` | The compare table. `touchstone compare` output is read by a human | ⛔ never in the results JSON |

### Observability — phase 2

| Package | Version | Job |
|---|---|---|
| `opentelemetry-api` / `-sdk` | `1.44.0` | The spans that are the score (`docs/04`). ✅ Transport and SDK, both stable |
| `opentelemetry-exporter-otlp` | `1.44.0` | → Phoenix's OTLP endpoint. ⚠️ **The only line that names a backend** |
| `openinference-instrumentation-langchain` | `0.1.70` | Auto-instruments LangGraph nodes into OTel spans. **Without it every span is hand-written** |
| `openinference-instrumentation-anthropic` | `1.1.2` | Model-call spans under **OpenInference** attributes — see the warning below |
| `openinference-semantic-conventions` | `0.1.32` | The attribute names, as a dependency rather than as strings in our code |
| `arize-phoenix` | `20.2.0` | The trace backend — ⚠️ a container, not an import. Self-hosted, Apache-2.0, no account and no API key, 682 releases |
| `arize-phoenix-otel` | `0.17.1` | Three lines of exporter setup instead of thirty |
| `arize-phoenix-client` | `3.1.0` | **`get_spans_dataframe()` — how the scorer reads spans back.** This is the load-bearing one |

⛔ **Do not claim `gen_ai.*` compliance.** OpenTelemetry's GenAI semantic conventions are
**Development status with no 1.0**, and on **2026-06-12** they were deprecated out of the main
`semantic-conventions` repo into `semantic-conventions-genai`, **which has no tagged release at
all**. `OTEL_SEMCONV_STABILITY_OPT_IN` exists precisely because the names are still moving.

**So split the claim in two, because only one half is shaky:**

| Layer | Status | What we say |
|---|---|---|
| OTLP + the OTel SDK | **Stable**, 1.44.0 | "Traces are OTLP — point them at any backend" ✅ |
| `gen_ai.*` attribute names | **Development, no release** | *nothing* ⛔ |
| **OpenInference** attributes | Apache-2.0, shipping since 2023, versioned | "Instrumented with OpenInference conventions" ✅ |
| `touchstone.*` attributes | Ours, defined in `docs/04` | "Our scoring fields, namespaced so they can't collide" ✅ |

**So the answer to *"is OpenTelemetry mature enough for AI work?"* is neither yes nor no:** the
protocol is, the AI-specific vocabulary is not, and OpenInference is what fills the gap today.

### Evals — phase 2

| Package | Version | Job | ⛔ Not for |
|---|---|---|---|
| `arize-phoenix-evals` | `3.4.0` | The judged dimension only. Results land as annotations on the span, so the judge's output is scored from the same substrate as everything else | ⛔ **never a gating metric** |
| `pytest` / `pytest-asyncio` | `9.1.1` / `1.4.0` | Invariants and the eval suite | — |

### MCP — phase 2, **not** deferred

| Package | Version | Job |
|---|---|---|
| `mcp` | `1.29.0` (`~=1.24`) | The official SDK. Serves the five read-only tools over MCP. ⚠️ **Not 2.0** — see below |
| `langchain-mcp-adapters` | `0.3.2` | Bridges those same tools back into LangGraph, so **one definition serves both paths** |

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

### Fallback providers — phase 0, install but do not use

| Package | Version | Job |
|---|---|---|
| `cerebras-cloud-sdk` | `1.91.0` | Path B transport |
| `langchain-cerebras` | `0.8.2` | Path B as a chat model. ⚠️ Older than the rest (2025-11-24) — check it against `langchain-core` 1.5 at phase 0 and fall back to the raw SDK over `httpx` if it fights |
| `langchain-ollama` | `1.1.0` | Path C |

### Dev

`ruff` `0.16.3` · `uv` (the installer, not a dependency)

### The backend, as a container rather than a dependency

```yaml
# docker-compose.yml
phoenix:
  image: arizephoenix/phoenix:latest
  ports: ["6006:6006", "4317:4317"]      # 6006 = UI + OTLP/HTTP · 4317 = OTLP/gRPC
  environment:
    PHOENIX_SQL_DATABASE_URL: postgresql://…   # or PHOENIX_WORKING_DIR + a volume
```

⚠️ **Without one of those two persistence settings, traces live in the container and die with
it** — which would silently destroy the evidence behind every past row of the version table.

---

## 5. `pyproject.toml`

```toml
[project]
name = "touchstone"
requires-python = ">=3.12"
dependencies = [
  "langgraph~=1.2", "langgraph-checkpoint-sqlite~=3.1", "langchain-core~=1.5",
  "claude-agent-sdk~=0.2", "pydantic~=2.13", "typer~=0.27", "rich~=15.0",
  "opentelemetry-api~=1.44", "opentelemetry-sdk~=1.44", "opentelemetry-exporter-otlp~=1.44",
  "openinference-instrumentation-langchain~=0.1", "openinference-instrumentation-anthropic~=1.1",
  "openinference-semantic-conventions~=0.1",
  "arize-phoenix-otel~=0.17", "arize-phoenix-client~=3.1",
  "mcp~=1.24", "langchain-mcp-adapters~=0.3.2",   # ⛔ not ~=2.0 and not ~=0.3 — D-031
  "fastapi~=0.141", "uvicorn~=0.52", "httpx~=0.28",
]

[project.optional-dependencies]
fallback = ["cerebras-cloud-sdk~=1.91", "langchain-cerebras~=0.8", "langchain-ollama~=1.1"]

[dependency-groups]
dev = ["pytest~=9.1", "pytest-asyncio~=1.4", "arize-phoenix-evals~=3.4", "ruff~=0.16"]

[project.scripts]
touchstone = "touchstone.cli:app"
```

⛔ **Commit `uv.lock`.** The version table is a comparison across time; an unpinned tree makes
every past row a claim about a dependency set nobody can reconstruct.

---

## 6. `touchstone doctor` — phase 0, and it is the first thing to write

One command, run before anything else, that fails loudly rather than producing a quietly wrong
number. **This is real output, 2026-08-14** — the same block is pasted in D-001:

```
touchstone doctor
  ✓ claude CLI         2.1.232  (~/.local/bin/claude)
  ✓ subscription auth  ~/.claude/.credentials.json present (mode 600)
  ✓ ANTHROPIC_API_KEY  absent
  ✓ model              claude-sonnet-4-6  (pinned, answered by a live call, $0.0035 total)
  ✓ setting_sources    [] — 0 memory files, 0 agents, 0 MCP tools (11382 ctx tokens)
  ⚠ CEREBRAS_API_KEY   absent   — path B unavailable, the judge has no fallback
  ⚠ ollama             http://localhost:11434/api/tags unreachable   — path C unavailable
  ⚠ phoenix            http://localhost:6006 unreachable   — `docker compose up -d phoenix`
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
| **A local model as the default** | An earlier draft chose it, and it answers the wrong question. The comparison this project exists to make is between *versions of the agent*; a weak default model compresses every version difference toward noise, so the instrument stops resolving what it was built to resolve. Kept as path C, where a local model is a fallback rather than the baseline |
| **LiteLLM as a universal router** | One config for three providers, and ⚠️ **it drops `think: False` on ollama and returns empty content** — measured here before. Three thin adapters beat one leaky abstraction |
| **The SDK's own subagents instead of LangGraph** | The SDK can orchestrate. Then the graph is Claude Code's, not yours, and there is nothing versionable to put in the table. **LangGraph owns orchestration; the SDK is transport** |
| 🔴 **MLflow** | Its job here was *comparing versions*, which is **exactly what `results/*.json` and the README table already do** — from committed artifacts, in git, readable in a diff. **Two stores answering one question, and the one being cut is the one nobody can read in a diff.** ⚠️ Not a judgement on MLflow; a judgement on a second store for already-versioned data |
| 🔴 **DeepEval** | Chosen for pytest-native gating — and the judge here never gates (`docs/05`), so the one thing it is best at is the one thing this project forbids. ✅ Actively maintained; health was never the problem |
| **Raw `gen_ai.*` semantic conventions** | Development status, no 1.0, and moved out of the main semconv repo on 2026-06-12 into a repo with no tags. Instrumenting to a moving vocabulary means re-labelling spans mid-project, which would break the scorer against its own history. OpenInference instead, plus `touchstone.*` for our fields |
| **LangSmith as the backend** | Genuinely good, and hosted, account-required, and LangChain-shaped. ✅ Kept as a proof instead of a dependency: the exporter is one env var, so `docs/04` ships a swap-the-backend check. Demonstrating vendor-neutrality is worth more than picking a vendor |
| **Langfuse** | Same reasoning, and also OTLP-compatible — the same one-line swap. **The point is that the choice is reversible, not that it was hard** |
| ⛔ **mem0 / Zep / Letta as agent memory** | Rejected as infrastructure, admitted as a candidate. Persistent memory across attempts makes `all_k` measure recall; across cases it leaks the frozen benchmark; across versions it makes v4's score depend on v1–v3 — and the version comparison is the product. What v5 became instead (D-023) is a frozen corpus of past resolved incidents carried by the *environment*, plus planted false precedents. ⛔ That needs no memory library: a read-only corpus needs retrieval, which `search_runbooks` already does at the same scale, while extraction and consolidation only exist on a write path. And the write path does not want one either (D-027) — mem0's ADD/UPDATE/DELETE is *an LLM deciding whether a new fact contradicts an old one*, a second inference step that fails silently and in the direction of confidence. The promotion rule already refuses a memory that breaks a passing case, which is a gate rather than a guess, and the store is `langgraph.store.BaseStore` — already pinned, zero new dependencies. [docs/08](08-memory.md) §9 |
| **Eraser MCP as a runtime dependency** | ⛔ Never in `pyproject.toml`. An authoring tool used before code, not a package the agent imports. Its free-tier limits are unpublished, so a build that needed it could stall on somebody else's quota. The gate in [`docs/07`](07-diagrams.md) requires an approved diagram, not an Eraser one — Mermaid in the repo is the always-available fallback |
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
| Phoenix, not MLflow | `get_spans_dataframe()`; duplication with `results/` | D-018 |
| MCP into phase 2 | The tools already carry schemas — a thin adapter, not a rewrite | D-019 |
| `arize-phoenix-evals`, not DeepEval | Annotations land on the judged span; the judge never gates | D-020 |
| Diagram approved before any code | A process gate, not a tool choice | D-021 |
| Memory as candidate v5, not as infrastructure | Measurement independence | D-022 |
| History as a second frozen corpus + planted false friends | The cost side of memory is the unmeasured half, and the per-case gate already catches it | D-023 |

⚠️ **The subset denominator moved from 851 to 883 on 2026-08-14** and 851 was discarded as
unreproducible. **No decision changed** — the numerators were re-derived and matched. If a
figure anywhere in this repo is still divided by 851, it is stale.
