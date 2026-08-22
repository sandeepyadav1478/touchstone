# touchstone

**An eval-repair loop for agentic systems.** An agent is only as good as the evals judging it,
and an eval is wrong in two directions: it misses real failures, and it refuses correct fixes.
touchstone mines failures into new eval cases, admits them through mechanical gates, and
enforces them — so the suite keeps getting stricter and the agent has to keep passing it.

⛔ **THE INVARIANT: anything that gates is mechanical; anything with a model in it cannot gate.**
A model's only job is **translation** — turning a written policy constraint into a predicate over
the database. The **verdict** is always a predicate, never a judgement. τ² ships a judged reward
component and it stays out of the gate ([docs/05](docs/05-scoring.md) §5, D-064, D-069).

**The loop is the product; the domain is a specimen.** touchstone measures agents; it does not
define what a good answer is — a project that owns both the agent and the answer key can improve
either one, and you cannot tell from the outside which it did. So the specimen is a third
party's: **[τ²-bench](https://github.com/sierra-research/tau2-bench) retail**, MIT, 114
customer-service tasks with a scorer that has **no model in it**.

> ### ⚠️ Status: phase 0 — specified, not yet built
>
> **Here now:** the specification (`docs/00`–`09`), the structural diagrams that gate
> implementation, and `touchstone doctor`, which runs. **Not here:** the loop.
>
> 🔴 **The candidate-comparison half is deferred (D-080)** — running 114 tasks to produce v1…v5
> and deciding whether one beats the last. Running the benchmark is τ²'s own work, done well,
> and a comparator needs a second version that does not exist. What is being built is the other
> half: **mine a mechanical gate out of a trace, and enforce it.**
>
> **So the claim this repo will make is precision and recall** — *the gate fires on these traces
> and is silent on those* — ⛔ **not** *the gate made the agent better*, which needs the deferred
> half. Both are real; they are not the same sentence.

---

## The finding that shaped the design

τ²'s `DB` check replays the task's gold actions on a fresh environment and diffs the agent's end
state against the result. It is mechanical, and any path reaching an equivalent state passes.

**It compares final state, so it is blind to how that state was reached.** An agent that skips a
required confirmation and still writes the correct row scores `DB == 1`. Measured over the corpus:

```
834 anomalous = 407  the DB check failed
              + 371  DB PASSED, action_check failed
              +  56  a WRITE nobody confirmed, which action_checks cannot see
878 clean     = none of the three — THE SILENCE SET
```

🔴 **Those 371 are why the miner reads three signals and not one.** Selecting on `DB == 0` alone
leaves them in the silence set — the population a new predicate must be quiet on to be admitted —
so a predicate **correctly** catching a confirmation violation would have been thrown out as a
false positive, by an answer key that was itself wrong. **A broken eval does not just miss
failures; it refuses the fix.**

⚠️ **Say *blind to process*, never *the benchmark is broken*.** Grading final state is **correct
for a gate** and wrong for a selector — that is exactly why `DB` stays the gating metric (D-069)
while the miner feeds on the union. ⛔ **One number cannot do both jobs**, and using the gating
label to select was the most expensive defect in this design.

⚠️ **The 56 is an upper bound.** It comes from a regex over the most recent user message before
each WRITE, so it over-counts. It is enough to justify widening the selector and is **not a
figure to quote**.

---

## The corpus

**1,712 simulations τ²-bench already ships**, over **107 of retail's 114 tasks** — the ones whose
gold actions are unchanged between the shipped runs and the current task file. ⛔ **The other
seven are excluded, not repaired, and the two numbers travel together — never write 114.**

⛔ **This is a corpus, never a baseline.** Those simulations were produced by four third-party
agents (`claude-3-7-sonnet`, `gpt-4.1`, `gpt-4.1-mini`, `o4-mini`) behind a `gpt-4.1` user
simulator. **Their scores are quoted nowhere in this repo**; putting them beside a number of ours
would fuse two environments.

⚠️ **Since D-082 §B the three signals are the ANSWER KEY, not the selector.** A **router** agent
reads every one of the 1,712 and answers *is this worth mining?*; `criterion_1_agreement` scores
its verdict against the 834/878 split. ⛔ **No result is reportable without that figure.** If it
comes back poor, the rubric drops to a diagnostic and selection reverts to mechanical.

### The result table

**The shape of the output, until there are mined gates to fill it.** Every cell comes from a
committed artifact under `results/`, which is empty at phase 0.

| gate | the stated rule it came from | fires on | of the clean | attempts | unmineable |
|---|---|---|---|---|---|
| ⟨…⟩ | ⟨`policy.md` line, or a tool contract⟩ | ⟨…⟩ / 834 | ⟨…⟩ / 878 | ⟨…⟩ / 5 | — |

**The second column is worth more than the third** — a rule that catches everything catches the
clean ones too. **The empty table is deliberate:** every cell is filled from a committed run
artifact or left blank, and there is no path here for a number that was not measured.

---

## How it works

📐 **The structural diagram is the artifact** — [`diagrams/`](diagrams/README.md), source in
[`touchstone.eraser`](diagrams/touchstone.eraser), rendered as [`loop.png`](diagrams/loop.png)
so the page shows something to a reader who will not clone. No code lands before an approved diagram
([docs/07](docs/07-diagrams.md)). What follows is the prose version.

**Two attachment points, both upstream, both one function.**

| point | where | why it is the only one |
|---|---|---|
| the model seam | `tau2/utils/llm_utils.py` `generate()` | **all four** of τ²'s model roles cross it — agent, user simulator, hallucination reviewer, NL-assertion evaluator. One adapter puts the Claude Agent SDK behind every one without touching a call site |
| the enforcement point | `tau2.environment.Environment.make_tool_call()` | every tool execution already passes through it, and it already knows which tools mutate state |

**The inner loop — one routed trace, up to 5 attempts, seconds.** It replays stored spans, and
there is **zero model call in its verdict**.

```
router ─▶ curator ⇄ critic ─▶ run_predicate ─▶ admission ─▶ suite
```

- **router** — a rubric reads one session and answers *is this worth mining?* Skips join the
  control set. 🔴 This is the expensive half: a model now helps define what counts as clean, and
  the price is a measured error rate.
- **curator** — reads the trace and the retail policy document, turns a **stated rule** into a
  predicate. A candidate, never a verdict (D-064). Owns the two memories (D-078).
- **critic** — attacks the candidate *before* anything runs: does it quote a `task_id`? does it
  restate the trace instead of the rule? One bounce per attempt, then the loop runs what it has.
- **`run_predicate`** — mechanical, and **this is the whole verdict**: fires on the routed trace
  (yes) and on none of the control set (no). ⛔ **All three agents propose; only this decides.**
  A scope filter stood in front of it until **D-081** and it named no mechanism — it had been
  *called* mechanical — so it was deleted rather than fixed.
- **admission** — **three** mechanical gates: reproducible, distinct, justified. Five were
  specified; measuring them against the **1,824** simulations shipped across all 114 tasks cut
  two (D-084). ⚠️ **1,824 and 1,712 are different denominators** — 4 result files × 114 tasks × 4
  trials versus the 107-task corpus above. Never write them in one sentence.
- **unmineable** — the one terminal, always by exhaustion. *The agent was not smart enough*
  arrives here too: a capability failure has no rule to translate. **A result, not an error**, and
  the P3 exit gate **requires** at least one — a miner that has never given up has never been
  pointed at a failure it should refuse.

**The curator's registry — two memories, and only one can be exact (D-078).** ⛔ Not the agent's
memory: the agent's is frozen and reset per attempt because it is the thing being measured; this
one grows. It answers *has this already been dealt with?* — without it, fifty instances of one
failure buy one rule instead of fifty.

- **positive** — rules already admitted. **Exact**, because it is a set membership test: you
  query it by running it.
- **negative** — traces already refused. A **signature** over a backward dynamic slice from the
  violating write, never the raw trace. **Heuristic, and it says so** — its false positive is a
  real failure silently skipped, which is why it is never allowed to pretend to be exact
  ([docs/08](docs/08-memory.md) §11.1).

**Two tiers, and only one freezes.** The benchmark is the fixed population every gate is scored
against, so it must not move. The regression suite only answers *did something that used to work
stop working?* — a binary with no denominator to corrupt, so it can grow forever. **That
asymmetry is what makes the inner loop safe to run at all.** 🔴 **A second control is missing
while the outer loop is deferred:** a mined case used to arrive `open` and gate only once an
*accepted* version had been quiet on it, and with no accepted versions that status is
unreachable — so it was deleted rather than left looking like it worked. **An admitted predicate
now rests entirely on the corpus it was tested against.** ⛔ **The benchmark stores task ids
and a hash, never task bytes** — vendoring τ²'s corpus would fork the answer key, which is the
thing this design exists to avoid.

⛔ **No human is a step in that picture.** A person writes each candidate version (D-044) — the
deferred part — and that is *upstream* of the loop. Inside it nothing pauses for approval: a gate
is a predicate, and a mined case is admitted by three mechanical gates, not by somebody signing
off on a batch.

**The spans are the score.** The scorer does not read prose — it reads the trace: which tools were
called, how many tokens, what the reward decomposed into, why the session terminated.

---

## Quick start

```bash
git clone git@github.com:sandeepyadav1478/touchstone.git && cd touchstone
uv sync
uv run touchstone doctor     # ✅ the only verb implemented today: CLI, login, model pin
                             # ⛔ and asserts ANTHROPIC_API_KEY is *absent* — if it is set,
                             #    runs quietly bill an API account, not the subscription
```

⚠️ `uv sync` does not put `touchstone` on your `PATH` — use `uv run touchstone …`, or activate
`.venv` first. The rest is specified in [docs/06](docs/06-api.md) and **not yet implemented**;
listed because the spec is fixed, not because it runs:

```bash
touchstone suite freeze --domain retail   # ⬜ pin the task ids and hash them
touchstone mine --from results/final      # ⬜ one anomalous trace → a candidate predicate
touchstone suite admit r-018              # ⬜ three mechanical gates → the regression suite
touchstone run --enforce                  # ⬜ the predicate refuses the call before it runs
```

🔴 **`run vN` / `score vN` / `compare` are deferred**, not merely unimplemented — they belong to
the candidate-comparison half, and their spec stands in [docs/02](docs/02-gates.md) §2 against the
day a second version exists.

### Models

The agent runs on **Claude, through [`claude-agent-sdk`](https://github.com/anthropics/claude-agent-sdk-python)**,
which drives the `claude` CLI as a subprocess and inherits its login — so a run goes through a
**Claude Code subscription rather than a metered API key**. Running a suite k times per task is
the whole point of this repo, and that is what makes it affordable.

⛔ **Anthropic models only, in every role.** `ollama` and Cerebras are reachable from this machine
and `doctor` reports on them; they are **diagnostics, never model sources**.

⚠️ **The quota rejects rather than bills** — a five-hour window with overage disabled at the org
level, so exhausting it does not produce a larger invoice, it **kills a run in flight**. That
shapes the pins more than price does.

**Five roles, pinned separately** (D-067) — τ² runs four, touchstone adds one:

| Role | Pin |
|---|---|
| agent under test | `claude-sonnet-5` |
| user simulator | `claude-haiku-4-5-20251001` — **frozen apparatus**, deliberately not the agent's model |
| NL-assertion evaluator | `claude-opus-5` — runs, but **outside the gate** (D-069) |
| reviewer / hallucination checker | `claude-opus-5` — opt-in, `--auto-review` |
| the three mining-loop agents | `claude-opus-5` (`LOOP_MODEL`) — router · curator · critic |

**Every id comes from a live call, not a config file** — `doctor` asks the running CLI what it
actually answered as, because the id is part of a candidate's identity and a config file can
disagree with reality. ⛔ **A provider or model switch *inside* a run voids that run rather than
mixing it.** Full manifest: [docs/00-stack.md](docs/00-stack.md).

⚠️ **`doctor` probes one of the five pins.** The other four have no live caller until phase 1, and
a check with nothing behind it would report green on a pin that was never resolved.

---

## Limits

**Read this before quoting any number this repo ever produces.** These are properties of the
design, so they hold whether or not a run has happened.

- 🔴 **Nothing here has been run by this project, and the traces it reasons over are somebody
  else's.** ⛔ A corpus, not a baseline; a gate that fires on their failures is not thereby shown
  to fire on ours.
- **The customer is a language model.** τ²'s user side is a simulator. A failure it causes is
  attributed to the agent unless something measures it — and ⚠️ **that risk changed owner rather
  than going away**: the corpus's simulator was someone else's choice, already run, so **we can no
  longer measure its fabrication rate ourselves.** The single largest thing the deferral gave up.
- **Enforcement is built and its effect is unmeasured.** It attaches at `make_tool_call()` and is
  tested by replay; it has **never run against a live environment**, and *wired but never seen to
  fire* reads exactly like *works*.
- **A benchmark task is cleaner than a real ticket** — gold actions known, small database, a right
  answer. **That makes the reward an upper bound on a harder problem.**
- **The gate is a component, not the whole reward.** touchstone gates on `reward_breakdown["DB"]`
  because retail's composite includes an LLM-judged `NL_ASSERTION` on **112 of 114** tasks
  (D-069). Both are reported. ⛔ **A `DB` figure and a composite figure are different
  measurements** — quoting one as the other is the mistake this design most invites.
- ⛔ **`COMMUNICATE` is a substring match and we did not fix it.** Upstream's own code carries
  `# TODO: This could be improved!`. A scorer we quietly improved is a scorer nobody can compare
  us against, so the brittleness is recorded and kept.
- **The agent does not learn.** Nothing trains, fine-tunes or updates weights. ⛔ **"It improves
  itself" fuses two loops and is false on the half that matters** — what iterates is the
  **ruler**, never the thing being measured. ⚠️ The suite does grow, but it is unbuilt at this
  tag, so today the bar rises only when a human raises it.
- **`action_checks` has a blind spot and the probe for it is a regex** — see the 56 above.
- **τ² can change its tasks under us; it already has** (`CHANGELOG:214` rewrote two tasks'
  `reward_basis`). Storing ids and a hash makes a moved corpus detectable rather than silent.
- **Cost figures are measured but never billed.** From the Agent SDK's `total_cost_usd`, which is
  cache-aware — a real per-call figure, not tokens × list price. But runs go through a
  subscription, so it is *what the run would have cost at API list prices*, drawn from a quota
  rather than an invoice. **Both halves are load-bearing.**
- **Rate-limited attempts are void, not failed.** A 429 means the attempt did not happen; scoring
  it wrong would let a quota limit look like a regression. ⛔ **Say which convention a `pass^k`
  used** — upstream has two.
- 🔴 **No `pass^k` figure appears anywhere in this repo.** It needs repeated attempts by *our*
  agent and there are none. The metric is τ²-bench's, computed by τ²-bench's code; ⛔ it is **not**
  `pass@k`, and a reader who skims past the caret reads the gate as far weaker than it is.
- **Single service, single machine.** The traces are not distributed.
- **No claim about time-to-resolution, ticket volume, or comparison against a human agent.**

---

## The documents

| Doc | What it covers |
|---|---|
| [docs/00-stack.md](docs/00-stack.md) | Every dependency pinned and why, the five model pins, `touchstone doctor` |
| [docs/01-spec.md](docs/01-spec.md) | The τ² task model, what a case is, the benchmark manifest, **10 live invariants numbered to 16** — six retired in place |
| [docs/02-gates.md](docs/02-gates.md) | ⛔ **The three decisions**, the two tiers, the acceptance rule, the stages, case provenance |
| [docs/03-agent-and-tools.md](docs/03-agent-and-tools.md) | The adapter at the seam, what we may and may not change about the τ² agent |
| [docs/04-observability.md](docs/04-observability.md) | Span schema, OpenInference conventions, why the scorer reads spans |
| [docs/05-scoring.md](docs/05-scoring.md) | Reward, `pass^k`, cost per success — and why a judge can never gate |
| [docs/06-api.md](docs/06-api.md) | CLI, HTTP surface, compose |
| [docs/07-diagrams.md](docs/07-diagrams.md) | ⛔ **The gate: no code before an approved structural diagram** |
| [docs/08-memory.md](docs/08-memory.md) | Where agent memory legitimately goes, and the **anchoring failure it is planted to catch** |
| [docs/09-schemas.md](docs/09-schemas.md) | Every remaining type, the `benchmark_hash` algorithm, the file map, prompt and tool contracts |
| [diagrams/](diagrams/README.md) | 📐 **The gate artifacts** — the structural flowchart and the run sequence |

🔴 **`docs/` still specifies the deferred half in the present tense, deliberately.** Wherever they
reason about the version table or comparing a candidate against an incumbent, they describe **the
design P2.4 revives to**, not code that runs. ⛔ **Nothing was deleted** — the arguments are why
each piece is shaped the way it is, and they would have to be re-derived otherwise.

⚠️ **`DECISIONS.md`, `ROADMAP.md` and `DEFECTS.md` are kept out of this repo on purpose.** They are
how the project steers itself, and none of them is an outcome. The `D-xxx`, `DEF-xxx` and `Pn.n`
tags throughout the docs are **labels, not links** — they mark where a choice was made
deliberately. Where a reason is load-bearing, it is written out rather than delegated to a tag.

*The previous specimen — a self-authored production-incident triage corpus — is archived on the
[`incident-specimen`](https://github.com/sandeepyadav1478/touchstone/tree/incident-specimen) branch
at `109c424`: 1,954 lines across 20 files. **The loop is unchanged across that swap, and that is
the claim the swap was for.** D-062, D-066.*

---

## Prior work this builds on

- [τ²-bench](https://github.com/sierra-research/tau2-bench) (MIT) — the specimen: the corpus, the
  environment and the evaluator. **We drive it; we do not fork it.** Pinned at commit
  `a2c024725189`. ⛔ **Not `1.0.1`** — that string names two different trees (DEF-055).
- [`tracebench`](https://github.com/sandeepyadav1478/tracebench) — reliability over OTel spans;
  where the `pass^k` framing came from.
- [`evalloop`](https://github.com/sandeepyadav1478/evalloop) — mining eval sets from traces, and
  the health guard that refuses to report drift from a dead window. The
  [`mine`](docs/02-gates.md#5-mine) stage is that idea with a real domain under it.

---

## Citation

If you refer to this work, cite it as software — ⚠️ **and state the commit**, because the design
is under active revision and the phase it was read at changes what the claim means.

```bibtex
@software{yadav2026touchstone,
  author  = {Yadav, Sandeep},
  title   = {touchstone: an eval-repair loop for agentic systems},
  year    = {2026},
  url     = {https://github.com/sandeepyadav1478/touchstone},
  license = {MIT},
  note    = {Phase 0: specification and \texttt{doctor}; the mining loop is specified, not built}
}
```

⛔ **If you use anything measured here, cite τ²-bench too** — the corpus, the environment and the
evaluator are theirs, and every number on this page is derived from simulations they produced and
shipped.

```bibtex
@misc{barres2025tau2,
  title         = {$\tau^2$-Bench: Evaluating Conversational Agents in a Dual-Control Environment},
  author        = {Victor Barres and Honghua Dong and Soham Ray and Xujie Si and Karthik Narasimhan},
  year          = {2025},
  eprint        = {2506.07982},
  archivePrefix = {arXiv},
  primaryClass  = {cs.AI},
  url           = {https://arxiv.org/abs/2506.07982}
}

@misc{yao2024tau,
  title         = {$\tau$-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains},
  author        = {Shunyu Yao and Noah Shinn and Pedram Razavi and Karthik Narasimhan},
  year          = {2024},
  eprint        = {2406.12045},
  archivePrefix = {arXiv},
  primaryClass  = {cs.AI},
  url           = {https://arxiv.org/abs/2406.12045}
}
```

## License

MIT. See [LICENSE](LICENSE).
