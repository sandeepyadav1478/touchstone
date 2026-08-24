# 03 — The agent and its tools

> ⚠️ **Specification, phase 0.** This describes the design; it is not a description of shipped code. `touchstone doctor` is the only implemented command today — see the [README](../README.md) for what runs and what does not. ⛔ **And the specimen changed under it.** D-062 replaced the self-authored infra-RCA corpus with **τ²-bench retail** — 114 tasks, MIT, deterministic DB-state-diff reward. Where this file still says *incident*, *root cause*, *affected service* or *escalate*, it is describing the **archived** specimen (branch `incident-specimen`), not what touchstone measures. **The loop is unchanged; that is the claim the swap was for.**

**The agent is the specimen, not the point.** It exists to be a thing touchstone can measure
versions of. Keep it small enough that a change is attributable.

**Two agents are in play, and conflating them is the mistake this file exists to prevent.**
τ²-bench ships one — `LLMAgent`, upstream, unmodified — and it is **v1, the baseline**. Ours is a
LangGraph graph (§1) that competes against it on τ²'s own 114 tasks, scored by τ²'s own DB-state
diff. ⛔ **We write an agent; we never write the exam.**

🔴 **§1 and §2 were marked `archived` from 2026-08-19 to 2026-08-20, and that was wrong.** D-062's
subject was the corpus; it took the orchestration with it as an unstated side effect, which left
`claude-agent-sdk` as the only thing orchestrating — **the one option [docs/00](00-stack.md) §7
explicitly rejected.** D-071 restores the graph and records how it was lost. §5 is unaffected:
every SDK constraint in it survived both swaps unchanged.

---

## 1. The graph — 🆕 rebuilt, and pointed at retail

**LangGraph owns orchestration; `claude-agent-sdk` is transport** ([docs/00](00-stack.md) §7).
That was decided against thirteen alternatives on the grounds that matter here: *"the SDK can
orchestrate — then the graph is Claude Code's, not yours, and there is nothing versionable to put
in the table."* D-071.

⚠️ **This section described an archived incident-triage graph until 2026-08-20, and the archiving
was a side effect rather than a decision.** D-062 changed the specimen and took the orchestration
with it without saying so. The graph below is the same architecture pointed at retail; what
changed is the three questions, not the reasoning — `D-025`, `D-026`, `D-012` and `D-039` are
unchanged and live.

```
        ┌─────────────┐
        │  supervisor │◀────────────┐
        └──────┬──────┘             │ ONE per hop, up to `config.MAX_HOPS`
     ┌─────────┼─────────┐          │
     ▼         ▼         ▼          │
 identity  catalogue   policy ──────┘
   READ       READ     no domain tool
     └─────────┼─────────┘
               ▼  (after the loop exits)
        ┌─────────────┐
        │ synthesizer │  ⛔ the ONLY node that may call a WRITE tool
        └──────┬──────┘
               ▼
              END
```

⛔ **There is no gate node and no node waits on anything.** Every path from `supervisor` reaches
`END` without leaving the process — D-040.

⚠️ **The three arrows are a choice of one, not a fan-out.** Exactly one specialist runs per hop and
control returns to the supervisor. `max_hops` bounds the loop and is a **versioned parameter** —
quoted from `config.MAX_HOPS`, never restated here, for the reason DEF-003 records about `k`
(D-039). **The bound is a hypothesis and the loop is instrumented to break it**: `hops_exhausted`
fires when the edge exits because `hops ≥ max_hops` rather than because the supervisor emitted
`done`, told apart by the last `touchstone.node.supervisor` span's `next`.

### The three questions, and why they are these three

**The split is read off the measured tool surface, not invented.** Retail ships **16 tools — 7
`READ`, 7 `WRITE`, 2 `GENERIC`** — typed by upstream's own `is_tool` decorator, listed with their
counts in [docs/01](01-spec.md) §5.

| node | its one question | tools |
|---|---|---|
| `identity` | who is this, and what did they buy? | `find_user_id_by_name_zip`, `find_user_id_by_email`, `get_user_details`, `get_order_details` |
| `catalogue` | what exactly is this item, and what could replace it? | `get_product_details`, `get_item_details`, `list_all_product_types`, `calculate` |
| `policy` | what does the policy permit for an order in **this** state? | ⛔ **none of τ²'s** — it reads the 6.5 KB policy document through our own MCP server (D-019) |
| `synthesizer` | commit it | the 7 `WRITE` tools + `transfer_to_human_agents` |

🎯 **Confining every mutation to one node is the load-bearing choice**, and it pays three ways:

1. **The enforcement point gets exactly one caller.** `gate/enforce.py` hooks `make_tool_call()`;
   with writes fanned across three specialists, a refusal is attributable to no node.
2. **It restores retired invariant 2 in the only form retail allows.** *"Every tool is read-only"*
   inverted at D-062 because the mutation **is** the measurement. *"Every **specialist** is
   read-only"* is the same property one scope down, and it is assertable.
3. **`policy` holding no domain tool makes it a reasoning node by construction** — it cannot
   answer its question by fetching state instead of reading the rule.

### State: who writes, who reads

| Key | Written by | Read by |
|---|---|---|
| `task` | the runner, once | everyone |
| `findings` | **each specialist, append-only** (`Annotated[list, add]`, D-012) | ⛔ **the synthesizer only** |
| `hops` | supervisor | supervisor |

⛔ **A specialist never reads another specialist's finding.** Its prompt is the task plus its own
prior tool results. The supervisor sees finding *headers* — who has reported and whether it claims
an answer — because that is what routing needs and nothing more.

**The reason is the failure this project measures, one scope smaller.** A blackboard every
specialist reads is memory with a one-run TTL: `identity` reports *"the order is `pending`"*,
`policy` reads it before checking, inherits the framing, stops looking. It also destroys the one
thing three specialists are for — once `policy`'s output depends on `identity`'s, a correctness
movement is attributable to neither. D-025.

⚠️ **`add` concatenates disagreement rather than resolving it, and that is deliberate.** A reducer
that de-duplicated or picked a winner would hide the disagreement, and specialist disagreement is
the strongest signal available that a task is being got wrong.

⚠️ **Invariants 13 and 14 come out of retirement with this section** ([docs/01](01-spec.md) §6).
They were retired with *"there are no specialists"*, and 14's note kept its argument for *"the day
something does"* fan out. **An orchestration bug wearing the costume of the thing being measured
is still the worst defect this design can have** — and now there is something to assert it
against.

---

## 2. Tools — τ²'s sixteen, and our one

**We define none of τ²'s.** Retail ships 16, typed `READ` / `WRITE` / `GENERIC` upstream; the list,
the counts and the mutation boundary are [docs/01](01-spec.md) §5. `_is_mutating_tool()` at
`environment/environment.py:130` already splits read from write — ⛔ **do not re-derive it.**

**What we do define is one tool, and it belongs to `policy`:** a search over the retail policy
document, shipped as an MCP server over stdio (D-019, `mcp` pinned to 1.x by D-031). It is an
**internal** tool — τ² never sees it, and it touches no environment state, so it cannot move the
DB diff that scores the run.

⚠️ **The inversion from the archived design is worth naming.** Every tool there was read-only by
construction, and that was invariant 2. Retail's seven `WRITE` tools *are* the measurement, so the
invariant flipped from *"nothing may mutate"* to *"a shadow gate may not interfere with a
mutation"* (invariant 15). **The archived agent could not have had an enforce mode at all**,
because there was nothing to refuse.

## 3. Escalation — ⛔ archived, and cut on evidence

> ⛔ `verdict.escalate` was a field on a model that no longer exists. Retail's
> `transfer_to_human_agents` (`domains/retail/tools.py:732`) is the nearest thing and it is
> named in **4 of 114 tasks**, is `ToolType.GENERIC`, returns a constant string and contributes
> to no reward component — so **escalation F1 was cut** ([docs/05](05-scoring.md) §3).
>
> **The one line to keep**: *no human is ever a state in this machine.* It was true of the
> archived graph and it is true of the τ² orchestrator, and it is why an `enforce` gate refuses
> a call rather than pausing for approval. A gate the measured run routes around is not a safety
> property; it is an untested branch.

---

## 4. Prompts

**Retail's policy is upstream** (`domains/retail/`), handed to the agent by τ², and we do not
write it. What touchstone versions is **the adapter's own configuration** — the system prompt it
adds, if any, and the SDK parameters in §5.

- ⛔ **No few-shot examples drawn from the 114 tasks.** That is leakage, and it is the easiest
  way to accidentally publish a great number. ⚠️ **The risk changed shape rather than going
  away**: the tasks are *public*, so a model may have seen them in training. That is a ceiling on
  the absolute number, not on the version-to-version delta, and it is stated in the README's
  limits rather than hedged away here.
- **A prompt is a candidate under a version number**, not a document. Wording lives in git under
  a version, never in a doc ([docs/09](09-schemas.md) §11).

---

## 5. Models

**Claude, through `claude-agent-sdk` on the Claude Code subscription.** Full manifest, the
auth reasoning and the wrapper: [docs/00](00-stack.md) §1–2.

⛔ **Anthropic only. There are no fallbacks.** This section said *"fallbacks are Cerebras then
ollama, in that order"*; both are reachable from this machine and both are **`touchstone doctor`
diagnostics, never model sources**. A fallback chain inside a candidate would mean the version
table compares two different systems under one row.

**Five pins, four of them upstream roles** (D-067) — one adapter, dispatching on `model`:

| Role | Where it is called | Pin |
|---|---|---|
| agent | `agent/llm_agent.py:128` | `claude-sonnet-5` — **the thing under test** |
| user simulator | `user_simulator.py:235` | `claude-haiku-4-5-20251001` — ⛔ **frozen apparatus**, never a candidate |
| NL-assertion evaluator | `evaluator_nl_assertions.py:121` | `claude-opus-5` — in the composite, **outside the gate** (D-069) |
| hallucination reviewer | `hallucination_reviewer.py:196` | `claude-opus-5` — diagnostic |
| touchstone's three mining-loop agents | `loop/mine.py` | `claude-opus-5` (`LOOP_MODEL`) — **router** grades 4 rubric criteria and picks; **curator** decides what is worth encoding and writes it, ⛔ **against the existing suite** (`D-087`) — exact pre-check outside the agent, suite index in the prompt, still no tool; **critic** judges the curator and **decides the branch** (`D-086` §A). ⛔ **None of them clears anything** — the gauntlet is mechanical and downstream |

⚠️ **Only the first row may change between versions.** Moving the simulator's pin changes the
ruler, and every earlier row in the version table silently stops being comparable. That is why
it is listed as apparatus rather than as configuration.

⚠️ **The judge is the one apparatus role not on `claude-opus-5`, and the asymmetry is deliberate.**
The other two run rarely; the judge is the most numerous call in the loop, and quota here
**rejects rather than bills** — so a frontier pin there buys fewer iterations per five-hour
window and nothing else. It is affordable to weaken precisely because ⛔ **it cannot gate**: a
weaker judge costs accuracy on a *reported* number, never correctness on a promotion. The
ceiling travels with the pin — a smaller judge is a weaker judge (D-067, third amendment).

- The model id is a **versioned parameter** — changing it makes a new candidate, exactly like
  changing a prompt (D-013).
- ⛔ **`allowed_tools=[]` for the router and the curator; `["run_predicate", "record_unmineable"]`
  for the critic** (`D-085`, `D-089` — ⚠️ per-role since 2026-08-24 and the critic's list has
  **grown once already**, so ⛔ **grep the two lists, not the literal**). ⚠️ **`record_unmineable` is a
  tool rather than a field for exactly one reason, and 🔴 it is not the one `D-089` §B first
  gave**: `D-082` requires ≥1 `run_predicate` result behind every unmineable, and **a tool can
  refuse where a structured field cannot** (`D-090` §B). ⛔ **It is also the critic's attempt
  budget** — the critic asks it whether it may keep going and is told to exit, and never counts
  attempts itself (`D-091` §B). ⛔ **One function reads `config.MAX_ATTEMPTS`**; the tool and the
  graph's loop condition both call it, so no second place knows the cap. The
  SDK's own tools stay off in every role: the SDK ships Read/Bash/Glob; a model that can
  reach the filesystem can read the task file with the gold actions in it. **This is the leakage
  path that would produce a perfect score**, and it is one argument.
- ⛔ **`setting_sources=[]`** — 🔴 **not `None`, which is what this line said until 2026-08-14 and
  is the leaky value.** Under `None` the agent inherits this machine's `CLAUDE.md`, skills, MCP
  servers *and its model pin*, so every score depends on files outside the repo (D-034).
  `touchstone doctor` asserts it from the session's own reported context, not from the constant.
- ⛔ **No model routing, no fallback chains inside a candidate.** One model per candidate. A
  provider switch mid-suite voids the run (D-013) rather than mixing it.
- ⚠️ **The subscription cap is a five-hour window that *rejects*, not bills**
  (`overage_status='rejected'`). Exhausting it kills a run in flight, so the runner's `--resume`
  and attempt cache (D-015) are a requirement rather than a convenience.

⚠️ **`max_turns` is not a count of model calls** — D-032 measured that, and the archived design
set it to 2 because `output_format` spent a turn of its own. 🔴 **That value does not transfer.**
τ²'s agent runs a real multi-turn conversation with a simulated user and its own tools, so the
turn budget is upstream's orchestrator's, not ours. **`budget.py` must derive cost from measured
usage, never from a turn count** — which is the part of D-032 that was always the finding.
