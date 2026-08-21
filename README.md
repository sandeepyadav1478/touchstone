# touchstone

**An agent-improvement loop that is required to prove the improvement.**

Every change to the agent is a *candidate version*. Every candidate is scored against a
**frozen benchmark**, and a candidate is accepted only if it **regresses nothing it previously
passed** — average improvement is not enough. Every failure becomes a permanent case in a
**regression suite that only grows**: once a version passes a case, it is locked, and nothing
that breaks it ships again.

A touchstone never changes. That is the whole idea.

### The loop is the product; the domain is a specimen

**touchstone measures agents. It does not define what a good answer is** — because a project
that owns both the agent and the answer key can improve either one, and you cannot tell from
the outside which it did.

So the specimen is a third party's: **[τ²-bench](https://github.com/sierra-research/tau2-bench)
retail** — 114 customer-service tasks, MIT-licensed, with a scorer that has **no model in it**.
A task's reward is the product of its declared components:

**The gating number is the `DB` component**: the task's gold actions are replayed on a fresh
environment, and the agent's end state is diffed against the result. Any path reaching an
equivalent state passes. No model, no rubric, no argument.

⚠️ **τ²'s *composite* reward is not purely mechanical, and we do not pretend otherwise.** 112 of
retail's 114 tasks declare `reward_basis = ["DB", "NL_ASSERTION"]`, and `NL_ASSERTION` is scored
by a judge. So touchstone **gates on `DB` and reports the composite beside it** — nothing
upstream is edited, the leaderboard number stays computable, and the gate stays mechanical.
D-069.

⛔ **THE INVARIANT: anything that gates is mechanical; anything with a model in it cannot
gate.** A model's only job here is **translation** — turning a written policy constraint into a
predicate over the database. The **verdict** is always a predicate, never a judgement. τ² ships
a judged reward component and it stays out of the gate — [docs/05](docs/05-scoring.md) §5 says
why that is an invariant rather than a threshold.

*The previous specimen — a self-authored production-incident triage corpus — is archived on the
[`incident-specimen`](https://github.com/sandeepyadav1478/touchstone/tree/incident-specimen)
branch at `109c424`: 1,954 lines across 20 files, removed from `main`. **The loop is unchanged
across that swap, and that is the claim the swap was for.** D-062, D-066.*

```bash
touchstone run   v4                 # run the suite, k times each, emit spans
touchstone score v4                 # score from the spans, write results/v4.json
touchstone compare v4 --against v3  # per-task verdict → accept or reject
```

> ### ⚠️ Status: phase 0 — specified, not yet built
>
> **What is here now:** the full specification (`docs/00`–`09`), the acceptance rule, the
> structural diagrams that gate implementation, and `touchstone doctor`, which runs.
> **What is not here:** the loop. No run has happened, so there are no artifacts under
> `results/` — the directory is created by the first run — and the version table below has no
> data in it.
>
> Those three commands above are the specified interface, not a working one. Today `doctor`
> is the only implemented verb — see [Quick start](#quick-start), which says so per command.
>
> **The empty table is deliberate and it is the point.** Every cell is filled from a committed
> run artifact or left blank; there is no path here for a number that was not measured. A repo
> that shows its schedule before its results is the honest version of one that shows results
> it cannot reproduce.
---

## The version history

**This table is the point of the repository** — the shape of it, until there are runs to fill
it. Every cell comes from a committed artifact under `results/`, which is empty at phase 0.

| version | what changed | mean reward | `pass^3` | tool calls | $/success¹ | accepted |
|---|---|---|---|---|---|---|
| v1 | baseline — the τ² agent, driven through our seam | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ | — |
| v2 | + a gate in shadow | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ |
| v3 | + the tier-1 gate, enforcing | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ |
| v4 | + the tier-2 gate, enforcing | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ |
| v5 | a different agent — ours, four nodes | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ |

⚠️ **v1–v4 are one agent gaining capabilities; v5 is a different agent.** That is a different
kind of row and the table does not distinguish them — read v5's delta as *"does another
architecture help?"*, never as *"does another capability help?"*. **v5 is allowed to lose**, and a
loss is a result rather than a reason to keep tuning until it wins.

¹ From the Agent SDK's own cache-aware `total_cost_usd` — a real per-call figure, drawn from a
subscription quota rather than billed. **Not an invoice** — see [Limits](#limits).

⛔ **`pass^k` is τ²-bench's metric, computed by τ²-bench's code**, and it is the *strict* one:
`C(successes, k) / C(trials, k)`. It is **not** `pass@k`, which conventionally means *at least
one of k succeeded*. The caret is the distinction. [docs/05](docs/05-scoring.md) §2.

**The rejections get written up here, next to the table.** When a candidate is refused, this
section gains two sentences: what looked better, which task regressed, and what the trace
showed. A gate that never visibly refuses anything is not a gate, so the refusals are the part
worth reading.

---

## Why the numbers mean something

Most agent demos score themselves with a language model judging their own output. This one
does not, and the reason is structural rather than clever: **we do not own the answer key.**

**τ²-bench's reward is a database diff.** The task ships with a list of gold actions; the
scorer replays them on a fresh environment and compares the resulting state to the state the
agent left behind. Any path that reaches an equivalent end state passes. There is no rubric, no
judge, and no argument about whether an answer was good enough.

**What this buys, concretely:** a regression is a fact rather than a judgement. If task 47
passes at v2 and fails at v4, CI blocks the acceptance — there is nothing to interpret and
nobody to overrule.

**And it buys one thing a self-authored corpus cannot buy at all:** the numbers are comparable
to a published leaderboard we had no hand in. **What it costs** is in [Limits](#limits), and it
is real.

---

## How it works

```
   ┌──────── τ²-bench retail — third party, MIT ────────┐
   │  114 tasks · gold actions · user simulator         │
   │  Environment.make_tool_call()  ◀── the gate acts here
   └───────────────────────┬────────────────────────────┘
                           │  llm_utils.generate()  ◀── THE SINGLE SEAM
                           │  all four model roles cross this one function
                           ▼
              ┌─── our adapter ───▶ Claude Agent SDK ───┐
              └───────────────────┬─────────────────────┘
                                  │ traces (mlflow.start_span)
                                  ▼
   run ──▶ attempt ──┬─▶ void · incomplete · parse_failure ──▶ counts toward NOTHING
                     │      a run that never produced a comparable number.
                     │      parse_failure is scored WRONG, not retried (D-013).
                     │
                     └─▶ scored ──▶ score ──▶ compare ──┬─▶ ACCEPT ──▶ record
                                      │          ▲      │   WHY: all five conditions held
                                      │          │      │
                                      │          │      └─▶ REJECT ──▶ back to the developer
                                      │          │          WHY NOT: which task regressed,
                                      │          │          and the rejection IS the result
                                      │   benchmark — frozen, hashed
                                      │   ⛔ changing it resets every comparison
                                      │
                                      └─▶ mine ──▶ THE INNER LOOP, and the only stage that
                                         one         runs more than once per input (P3.4):
                                         failing
                                         trace       ┌──▶ translate ── a model turns the STATED
                                                     │      rule the trace broke into a predicate.
                                                     │      A candidate, never a verdict (D-064).
                                                     │           │
                                                     │           ▼
                                                     │    test ── mechanical, and this is the
                                                     │      WHOLE verdict:
                                                     │        fires on the failing trace?  YES
                                                     │        fires on one that passes?    NO
                                                     │           │
                                                     │           ├─▶ both ──▶ admission ──▶ regression
                                                     │           │            5 gates       suite
                                                     │           │            WHY: it caught a real
                                                     │           │            failure and nothing else
                                                     │           │
                                                     └───────────┘ else, hand back the counterexample
                                                                   and try again — up to n = 5

                                                     after n ──▶ UNMINEABLE. WHY NOT: no written
                                                       rule covers this trace, so there is nothing
                                                       to translate. ⚠️ A RESULT, not an error.
```

⚠️ **`budget_exceeded` is a flag, never a fifth status.** It lands *beside* whichever of the
four an attempt reached, never instead of one — a run can be both `scored` and over budget, and
collapsing the two loses the case where the number is real but cost too much to get.

**One function is the whole integration.** Every model role τ² runs — the agent, the user
simulator, the hallucination reviewer, the NL-assertion evaluator — imports the same
`generate()`. Replacing it with an adapter that dispatches on `model` puts the Claude Agent SDK
behind all four without touching a call site. **Enforcement attaches at a second point**,
`Environment.make_tool_call()`, which every tool execution already passes through and which
already knows which tools mutate state.

⛔ **No human is a step in that picture, and none is a state in the agent.** Nothing pauses for
approval: a gate is a predicate, and a mined case is admitted by five mechanical gates
([docs/02](docs/02-gates.md) §5) rather than by somebody signing off on a batch. **People
improve this system by rewriting it** — reading traces, changing prompts, adding cases — which
is what everything below is instrumented for.

**Two tiers, and only one of them freezes.** The benchmark produces the table above, so it
must not move. The regression suite only ever answers *"did something that used to work stop
working?"* — a binary with no denominator to corrupt, so it can grow forever without
invalidating anything. **That asymmetry is what makes the inner loop safe to run at all** — a
mined predicate can only land in the tier that has nothing to distort, and it arrives `open`, so
it cannot gate until it has been quiet under a version that was already accepted.
[docs/02](docs/02-gates.md) §1.

⛔ **The benchmark stores task ids and a hash, never task bytes.** τ²'s corpus is upstream's and
stays upstream; vendoring it would fork the answer key, which is the exact thing this design
exists to avoid.

**The spans are the score.** The scorer does not read prose — it reads the trace: which tools
were called, how many tokens, what the reward decomposed into, why the session terminated.
Instrumentation is not a dashboard here; it is the measurement substrate — and with nobody
standing inside a run, it is also the **only** place a person can see what happened.

| Doc | What it covers |
|---|---|
| [docs/00-stack.md](docs/00-stack.md) | Every dependency pinned and why, the five model pins, `touchstone doctor` |
| [docs/01-spec.md](docs/01-spec.md) | The τ² task model, what a case is, the benchmark manifest, 13 live invariants numbered to 14 |
| [docs/02-gates.md](docs/02-gates.md) | ⛔ **The three decisions**, the two tiers, the acceptance rule, the stages, case provenance |
| [docs/03-agent-and-tools.md](docs/03-agent-and-tools.md) | The adapter at the seam, what we may and may not change about the τ² agent |
| [docs/04-observability.md](docs/04-observability.md) | Span schema, OpenInference conventions, why the scorer reads spans |
| [docs/05-scoring.md](docs/05-scoring.md) | Reward, `pass^k`, cost per success — and why a judge can never gate |
| [docs/06-api.md](docs/06-api.md) | CLI, HTTP surface, compose |
| [docs/07-diagrams.md](docs/07-diagrams.md) | ⛔ **The gate: no code before an approved structural diagram** — every phase, every change |
| [docs/08-memory.md](docs/08-memory.md) | Where agent memory legitimately goes, and the **anchoring failure it is planted to catch** |
| [docs/09-schemas.md](docs/09-schemas.md) | Every remaining type, the `benchmark_hash` algorithm, the file map, and the prompt and tool contracts |

⚠️ **Three working files are kept out of this repo on purpose** — `DECISIONS.md`, a dated
record of every choice and what was rejected; `ROADMAP.md`, a phase schedule; and `DEFECTS.md`,
a running bug log. **They are how the project steers itself, and none of them is an outcome.**

One consequence a reader should know rather than discover: **the `D-xxx`, `DEF-xxx` and `Pn.n`
tags throughout the docs above are labels, not links.** They mark the places where a choice was
made deliberately and can be asked about — `D-030` is a real decision with a real argument
behind it — but the argument itself stays local. Where a reason is load-bearing for
understanding the design, it is written out in the doc rather than delegated to a tag.

---

## Quick start

```bash
git clone git@github.com:sandeepyadav1478/touchstone.git && cd touchstone
uv sync
uv run touchstone doctor                # ✅ works today — CLI, login, model pin, no stray API key
```

⚠️ `uv sync` does not put `touchstone` on your `PATH`. Use `uv run touchstone …`, or activate
the environment with `source .venv/bin/activate` first. The blocks below drop the prefix for
readability.

The rest of the interface is specified in [docs/06](docs/06-api.md) and **not yet
implemented**. It is listed here because the spec is fixed, not because it runs:

```bash
touchstone suite freeze --domain retail  # ⬜ pin the task ids and hash them
touchstone run v1 --k 3                 # ⬜ the frozen subset × 3 attempts
touchstone score v1                     # ⬜ → results/v1.json
touchstone compare v2 --against v1      # ⬜ → accept or reject, per task
```

### Models

The agent runs on **Claude, through [`claude-agent-sdk`](https://github.com/anthropics/claude-agent-sdk-python)**,
which drives the `claude` CLI as a subprocess and inherits its login — so a suite run goes
through a **Claude Code subscription rather than a metered API key**. Running the same suite k
times per task per candidate is the whole point of this repo, and that is what makes it
affordable.

```bash
touchstone doctor   # checks the CLI, the login, and the AGENT pin — by live call
                    # ⛔ and asserts ANTHROPIC_API_KEY is *absent* — if it is set,
                    #    runs quietly bill an API account instead of the subscription
                    # ⚠️ ONE of the five pins is probed. The other four have no live
                    #    caller until phase 1, and a check with nothing behind it
                    #    would report green on a pin that was never resolved.
```

⛔ **Anthropic models only, in every role.** `ollama` and Cerebras are reachable from this
machine and `doctor` reports on them; they are **diagnostics, never model sources**. *(An earlier
version of this section said the judge runs on Cerebras to keep it off the constrained quota.
That was the doc being wrong, not the constraint being flexible.)*

⚠️ **The quota rejects rather than bills.** It is a **five-hour window** whose overage status is
`rejected`, with overage disabled at the org level — so exhausting it does not produce a larger
invoice, it **kills a run in flight.** That shapes the model pins more than price does.

**Five roles, pinned separately** (D-067) — τ² runs four of them and touchstone adds one:

| Role | Pin |
|---|---|
| agent under test | `claude-sonnet-5` |
| user simulator | `claude-haiku-4-5-20251001` — **frozen apparatus**, deliberately not the agent's model |
| NL-assertion evaluator | `claude-opus-5` — runs, but **outside the gate** (D-069) |
| reviewer / hallucination checker | `claude-opus-5` — opt-in, `--auto-review` |
| touchstone's own rubric judge | `claude-haiku-4-5-20251001` — reported, **never gates** |

**Every id comes from a live call rather than a config file** — `doctor` asks the running CLI
what it actually answered as, because the id is part of a candidate's identity and a config file
can disagree with reality. ⛔ **A provider or model switch *inside* a run voids that run rather
than mixing it.** Full manifest and reasoning: [docs/00-stack.md](docs/00-stack.md).

---

## Reliability, not accuracy

Each task runs **k times**. The headline reliability number is **`pass^k`** — τ²-bench's own
metric, `C(successes, k) / C(trials, k)` per task, averaged — and it is the **strict** one.

An agent that is right 80% of the time on each of four attempts is not an 80% agent; it clears
`pass^4` on about four tasks in ten. **`pass^k` is the number you would use to decide whether to
put something on call.**

⛔ **It is not `pass@k`**, which conventionally means *at least one of k succeeded*. The caret is
the distinction, and a reader who skims past it reads the gate as far weaker than it is.

> The reliability framing came from [`tracebench`](https://github.com/sandeepyadav1478/tracebench),
> an earlier harness that scores CrewAI runs on OpenTelemetry spans. **The metric itself is
> τ²-bench's, computed by τ²-bench's code** — we adopted the name rather than coining one.

---

## Limits

**Read this before quoting any number this repo ever produces.** These are properties of the
design, so they hold whether or not a run has happened yet.

- **The tasks are a simulation, and the customer is a language model.** τ²-bench's user side is
  a simulator, not a person. A failure it causes is attributed to the agent unless something
  measures it — which is why the user simulator is a **frozen** pin and why `--auto-review
  --review-mode user` is a phase-1 exit box rather than an optional extra. D-067.
- **A benchmark task is cleaner than a real ticket.** The gold actions are known, the database
  is small, and there is a right answer. Real customer service has ambiguous requests and
  sometimes no correct resolution. **That makes the reward an upper bound on a harder problem.**
- **The gate is a component, not the whole reward.** touchstone gates on
  `reward_breakdown["DB"]` because retail's composite reward includes an LLM-judged
  `NL_ASSERTION` on 112 of 114 tasks (D-069). Both numbers are reported. ⛔ **A `DB` figure and a
  composite figure are different measurements** — quoting one as the other is the mistake this
  design is most likely to invite.
- ⛔ **`COMMUNICATE` is a substring match and we did not fix it.** Upstream's own code carries
  `# TODO: This could be improved!`. A scorer we quietly improved is a scorer nobody can compare
  us against, so the brittleness is recorded and kept.
- **The agent does not learn.** Nothing here trains, fine-tunes or updates weights. A human
  writes each candidate version; the gate only decides whether it ships. ⛔ **"It improves
  itself" fuses two loops and is false on the half that matters** — what iterates is the
  **ruler**, never the thing being measured. ⚠️ **The suite does grow, and that is the inner
  loop above** — but it is unbuilt at this tag, so today the bar rises only when a human
  raises it.
- **The benchmark is a frozen *subset* of τ² retail's 114 tasks, not all of them.** ⚠️ **At that
  n every figure here is a count, not a rate** — ⛔ no percentage is quoted from a double-digit
  task set. Widening the subset is the deferred item that attacks the biggest stated limit.
- **We do not own the corpus, and that is deliberate — but it cuts both ways.** τ² can change
  its tasks under us; it already has (`CHANGELOG:214` rewrote two tasks' `reward_basis`). The
  benchmark therefore stores **task ids and a hash**, so a corpus that moved is detectable
  rather than silent. ⛔ **No task bytes are vendored here.**
- **Cost figures are measured but never billed.** They come from the Agent SDK's own
  `total_cost_usd`, which is cache-aware — so they are a real per-call figure and not
  tokens × list price. But runs go through a **Claude Code subscription**, so the number is
  *what the run would have cost at API list prices*, drawn from a quota rather than an
  invoice. Both halves of that sentence are load-bearing.
- **Rate-limited attempts are void, not failed.** A 429 means the attempt did not happen;
  scoring it as wrong would let a quota limit look like a regression. `void_attempts` is
  reported in every results file, and τ²'s own `INFRASTRUCTURE_ERROR` is handled the same way
  — ⛔ **say which convention a `pass^k` used**, because upstream has two.
- **Single service, single machine.** The traces are not distributed.
- **No claim about time-to-resolution, ticket volume, or comparison against a human agent.**
  There is no baseline to compare against and none is implied.

---

## Prior work this builds on

- [`tracebench`](https://github.com/sandeepyadav1478/tracebench) — reliability over OTel spans.
- [τ²-bench](https://github.com/sierra-research/tau2-bench) (MIT) — the specimen: the corpus,
  the environment and the evaluator. **We drive it; we do not fork it.**
- [`evalloop`](https://github.com/sandeepyadav1478/evalloop) — mining eval sets from traces,
  and the health guard that refuses to report drift from a dead window. The
  [`mine`](docs/02-gates.md#5-mine) stage is that idea with a real domain under it.

## License

MIT. See [LICENSE](LICENSE).
