# 03 — The agent and its tools

> ⚠️ **Specification, phase 0.** This describes the design; it is not a description of shipped code. `touchstone doctor` is the only implemented command today — see the [README](../README.md) for what runs and what does not. ⛔ **And the specimen changed under it.** D-062 replaced the self-authored infra-RCA corpus with **τ²-bench retail** — 114 tasks, MIT, deterministic DB-state-diff reward. Where this file still says *incident*, *root cause*, *affected service* or *escalate*, it is describing the **archived** specimen (branch `incident-specimen`), not what touchstone measures. **The loop is unchanged; that is the claim the swap was for.**

**The agent is the specimen, not the point.** It exists to be a thing touchstone can measure
versions of. Keep it small enough that a change is attributable.

🔴 **D-062 took that further than intended: we do not write the agent at all any more.**
τ²-bench ships one, and touchstone attaches *behind* it. §1–§3 below describe the agent that was
archived; **§4 and §5 are live**, and §5 is the most load-bearing section in this file because
every SDK constraint in it survived the swap unchanged.

---

## 1. The graph — ⛔ archived

> ⛔ **There is no graph.** The supervisor, the three specialists and the synthesizer are on
> branch `incident-specimen` at `109c424`. τ² runs **one** agent — `LLMAgent.generate_next_message()`
> at `agent/llm_agent.py:128` — inside its own orchestrator (`orchestrator.py:260`), and
> touchstone's `adapter.py` sits at the `generate()` call that agent makes, not around it.
>
> **What survives is D-025 and D-026's argument, and it survives as a warning rather than a
> design.** No specialist may read another's finding; no two specialist spans may overlap. Both
> existed because *an orchestration bug wearing the costume of the thing being measured* is the
> worst defect this design can have. Nothing fans out today, so nothing asserts it — invariants
> 13 and 14 are retired in place ([docs/01](01-spec.md) §6) precisely so that the argument is
> still there the day something does.

## 2. The five tools — ⛔ archived

> ⛔ **Retail ships 16 and we define none of them**, typed `READ`/`WRITE`/`GENERIC` by upstream's
> own `is_tool` decorator. The list, the counts and the mutation boundary are
> [docs/01](01-spec.md) §5.
>
> ⚠️ **The inversion is worth naming.** Every tool here was read-only by construction, and that
> was invariant 2. Retail's seven `WRITE` tools *are* the measurement — the DB diff is the
> reward — so the invariant flipped from *"nothing may mutate"* to *"a shadow gate may not
> interfere with a mutation"* (invariant 15). **The archived agent could not have had an enforce
> mode at all**, because there was nothing to refuse.

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
| touchstone's rubric judge | `tests/evals/` | `claude-haiku-4-5-20251001` — **reported, never gates** |

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
- ⛔ **`allowed_tools=[]` on every SDK call.** The SDK ships Read/Bash/Glob; a model that can
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
