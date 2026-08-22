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
touchstone mine  --from results/final     # one anomalous trace → a candidate predicate
touchstone suite admit  r-018             # three mechanical gates → the regression suite
touchstone run   --enforce                # the predicate refuses the call before it executes
```

> ### ⚠️ Status: phase 0 — specified, not yet built
>
> **What is here now:** the full specification (`docs/00`–`09`), the acceptance rule, the
> structural diagrams that gate implementation, and `touchstone doctor`, which runs.
> **What is not here:** the loop. Today `doctor` is the only implemented verb — see
> [Quick start](#quick-start), which says so per command.
>
> 🔴 **The scope narrowed on 2026-08-22, deliberately, and the version table below went with
> it.** The **candidate-comparison half** — running the benchmark to produce v1…v5 and deciding
> whether one beats the last — is **deferred**. Running 114 tasks and scoring them is τ²-bench's
> own work, done well, and comparing two versions needs a second version that does not exist.
> What is being built is the other half: **mining a mechanical gate out of a trace, and enforcing
> it.** Its input is the **1,712 simulations τ²-bench already ships**.
>
> **So the claim this repo will make is precision and recall** — *the gate fires on these traces
> and is silent on those* — and ⛔ **not** *the gate made the agent better*, which needs the
> deferred half. Both are real; they are not the same sentence.
>
> **The empty table is deliberate and it is the point.** Every cell is filled from a committed
> run artifact or left blank; there is no path here for a number that was not measured. A repo
> that shows its schedule before its results is the honest version of one that shows results
> it cannot reproduce.
---

## The result table

**This table is the point of the repository** — the shape of it, until there are mined gates to
fill it. Every cell comes from a committed artifact under `results/`, which is empty at phase 0.

| gate | the stated rule it came from | traces it fires on¹ | of the clean² | attempts | unmineable |
|---|---|---|---|---|---|
| ⟨…⟩ | ⟨policy.md line, or a tool contract⟩ | ⟨…⟩ / 834 | ⟨…⟩ / 878 | ⟨…⟩ / 5 | — |

¹ The **834** anomalous traces out of τ²-bench's 1,712 shipped retail simulations — the union of
*the DB check failed*, *an `action_check` failed*, and *a WRITE with no confirmation before it*.
⛔ **Not the 407 that merely fail the DB check**: 371 of the others **pass** it, because the DB
check compares final state and cannot see how the state was reached. ⚠️ **Since `D-082` §B these
three signals are the ANSWER KEY, not the selector** — a **router agent** reads every one of the
1,712 and answers *is this worth mining?*, and `criterion_1_agreement` is its verdict scored
against this split. **No result is reportable without that figure.**

² The **878** with none of those three signals, **plus every session the router SKIPPED**. **A gate
that fires here is a false positive**, and the second column is worth more than the third — a rule
that catches everything catches the clean ones too. ⚠️ The 878 is mechanical and free; the skips
are not, which is what `criterion_1_agreement` exists to price.

⚠️ **Both denominators come from the same 107 tasks** — the ones whose gold actions are unchanged
between the shipped runs and the current task file. **107 of 114**, and the seven are excluded
rather than repaired.

⛔ **This is a corpus, never a baseline.** Those simulations were produced by four third-party
agents (`claude-3-7-sonnet`, `gpt-4.1`, `gpt-4.1-mini`, `o4-mini`) behind a `gpt-4.1` user
simulator. **Their scores are not quoted anywhere in this repo** and putting them beside a number
of ours would fuse two environments.

<details>
<summary>🔴 <b>The version table that was here, and why it is deferred</b></summary>

It had five rows — v1 baseline, v2 gate-in-shadow, v3 and v4 enforcing, v5 a different agent —
scored on mean reward, `pass^3`, tool calls and $/success. **Every one of them required running
the benchmark.**

Deferred 2026-08-22: running 114 tasks × k and scoring them is τ²-bench's own work, already done,
and the comparator that would decide *did v(N) beat v(N−1)?* has **no second operand** until a
second version exists. ⛔ **A comparator with nothing to compare is scaffolding.**

**What is given up, stated plainly:** *the gate made the agent better* is unsayable, and so is any
number of ours. ⛔ **`pass^k` does not appear in the table above** — it is a property of repeated
attempts we did not run.

**It comes back on one event:** a second candidate version exists. Not on having time.
</details>

---

## Why the numbers mean something

Most agent demos score themselves with a language model judging their own output. This one
does not, and the reason is structural rather than clever: **we do not own the answer key.**

**τ²-bench's reward is a database diff.** The task ships with a list of gold actions; the
scorer replays them on a fresh environment and compares the resulting state to the state the
agent left behind. Any path that reaches an equivalent end state passes. There is no rubric, no
judge, and no argument about whether an answer was good enough.

**What this buys, concretely:** a label nobody here chose. Every trace the miner reads was scored
by τ²-bench's own evaluator before this project existed, so *which traces are failures* is not a
call we made — and a gate mined from them cannot be tuned against a key we control.

⚠️ **The DB diff is the gate's metric and a poor selector, and those are different jobs.** It
compares **final state** and is blind to how the state was reached: an agent that skips a required
confirmation and still writes the right row scores a pass. **371 of the traces it passes have a
failed action check.** So the miner reads the union of three signals and the gate still reads the
DB diff alone — ⛔ **one number cannot do both jobs**, and using the gating label to select was the
defect that cost this the most.

**And it buys one thing a self-authored corpus cannot buy at all:** the failures are a third
party's, in a domain we did not write. **What it costs** is in [Limits](#limits), and it is real.
🔴 **What it no longer buys is comparability to a published leaderboard** — that needed a run of
our own, and there is none.

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
   ══ THE OUTER LOOP ══ 🔴 DEFERRED · specified, not built · D-080 ═══════════════════
      It ran 114 tasks × k per candidate and REPORTED a number. Deferred because
      running the benchmark is τ²'s work, already done, and the comparator below has
      no second operand until a second version exists. Drawn in full because this is
      what it revives to. ⛔ Nothing in this block executes.

   v(N) ─▶ run ─▶ attempt ──┬─▶ void · incomplete · parse_failure ─▶ counts toward
    ▲                       │      a run that never produced a comparable      NOTHING
    │                       │      number. parse_failure is scored WRONG,
    │                       │      never retried (D-013).
    │                       │
    │                       └─▶ scored ─▶ score ─▶ compare ─┬─▶ ACCEPT ─▶ record
    │                                       │         ▲     │   WHY: all five held,
    │                                       │         │     │   and v(N) is the champion
    │                                       │         │     │
    │                                       │         │     └─▶ REJECT ── a TERMINAL.
    │                                       │         │         Nothing on this page
    │                                       │         │         receives it. WHY NOT:
    │                                       │         │         which task regressed —
    │                                       │         │         the rejection IS the result
    │                                       │   benchmark — frozen, hashed
    │                                       │   ⛔ changing it resets every comparison
    │                                       │
    └── v(N+1) ── the loop turns when a NEXT candidate is put in front of it, accepted
        or rejected. ⛔ ONE thing changes per rung, and NOTHING here tunes itself: a
        person writes every candidate version (D-044). That is the one turn of the
        crank a human makes, and it is upstream of the loop, not a state inside it.

   ══ THE FEED ══ 1,712 simulations τ² ALREADY SHIPPED · 107 of 114 tasks ════════════
      ⛔ It does NOT come from the block above. That is why the inner loop survives
      the deferral: its input was the only thing the outer loop owed it.

      1,712 ─▶ ROUTER ─┬─▶ ENHANCE ─▶ the curator, below. D-082 §A: a rubric reads
       every one        │              ONE session and answers is this worth mining.
                        │              It replaced `analyst`, the mechanical `select`
                        │              and the unbuilt rubric judge — three components
                        │              asking one question.
                        │
                        └─▶ SKIP ─────▶ joins the CONTROL SET. 🔴 This is the expensive
                                        half: a model now helps define what counts as
                                        clean, and the price is a measured error rate.

      τ²'s OWN signals still split the corpus — 834 ANOMALOUS / 878 CLEAN — but since
      D-082 §B they are the ANSWER KEY rather than the selector. `criterion_1_agreement`
      scores the router's verdict against them over all 1,712, and ⛔ NO RESULT IS
      REPORTABLE WITHOUT IT. If it comes back poor the rubric drops to a diagnostic and
      selection reverts to being mechanical — the reasoning below is why it would work:

        834 = 407  the DB check failed
            + 371  DB PASSED, action_check failed
            +  56  a WRITE nobody confirmed, which action_checks cannot see
        878 = none of the three. THE SILENCE SET. A gate that fires here is a false
              positive, and that column is worth more than the other one.

      🔴 The 371 are why there are three signals and not one. DB compares FINAL STATE —
      an agent that skips a required confirmation and writes the right row scores a
      PASS. Feeding on DB==0 alone left those 371 in the silence set, where a CORRECT
      rule would have been thrown out as a false positive (D-080).
                                          ▼
   ══ THE INNER LOOP ══ up to n = 5 attempts on ONE routed trace · seconds ═══════════
      it replays stored spans, and there is ZERO model call in its verdict. It is the
      only stage that runs more than once per input, and the only one that makes the
      measurement BIGGER instead of reporting it (P3.4).

      ⛔ THREE AGENTS AND THREE MECHANICAL STEPS — D-082 §D fixes the chain:
         router ─▶ curator ⇄ critic ─▶ run_predicate ─▶ admission ─▶ suite
      All three agents PROPOSE. `run_predicate()` is the only thing that decides, and
      it holds no model — a scope filter stood in front of it until D-081 and it named
      no mechanism, so it was deleted rather than fixed.

      mine ──┬─▶ curator ── reads the trace and the retail policy document, and turns
       one     │     a STATED rule into a predicate. A candidate, never a verdict
      routed   │     (D-064). It owns the two memories (D-078).
      trace    │          │
               │          ▼
               │   critic ── attacks the candidate BEFORE anything runs: does it quote
               │       a task_id? does it restate the trace instead of the rule? It
               │       hands back an ARGUMENT, and there is ONE bounce per attempt —
               │       then the loop runs whatever it has. ≤5 critic calls per trace.
               │          │
               │          ▼
               │   run_predicate ── mechanical, and this IS the whole verdict — the
               │       only decision the loop makes, and it holds no model:
               │       fires on the routed trace?         YES
               │       fires on one of the control set?    NO
               │          │
               │          ├─▶ both ──▶ admission ──▶ regression
               │          │            3 gates       suite
               │          │            reproducible · distinct
               │          │            · justified. FIVE were
               │          │            specified; measuring them
               │          │            against 1,824 shipped
               │          │            simulations cut two (D-084)
               │          │
               └──────────┘ else, hand back the COUNTEREXAMPLE and try again —
                            attempt i+1 sees what i got wrong. ≤5 predicate runs.

                  after n ──▶ UNMINEABLE. The ONE terminal, and *the agent was not
                    smart enough* arrives here too — a capability failure has no
                    rule to translate, so nothing it proposes survives the predicate.
                    WHY NOT: every attempt and its counterexample, recorded — and
                    every UNMINEABLE has at least one run_predicate result behind it.
                    ⚠️ A RESULT, not an error.
                    🎯 The P3 exit gate REQUIRES at least one recorded unmineable —
                    a miner that has never given up has never been pointed at a
                    failure it should refuse.

   ══ THE CURATOR'S REGISTRY ══ two memories, and only one can be exact (D-078) ══════
      ⛔ NOT the agent's memory. The agent's is FROZEN and reset per attempt, because
         it is the thing being measured; this one GROWS. Conflating the two is the
         failure docs/08 §11 exists to prevent — same word, different object.
      🎯 It answers one question: *has this already been dealt with?* Without it the
         inner loop re-derives one rule from the fiftieth instance of one failure, and
         n iterations buy one rule instead of n.

      positive ── the rules already admitted ──▶ read by `mine` before it translates
        EXACT, because it is a set membership test — you query it by RUNNING it
              ▲
              └── every admitted rule lands here

      negative ── the traces already refused ──▶ read by `mine` before it starts
        a SIGNATURE, taken over a backward dynamic slice from the violating write —
        never over the raw trace, or fifty irrelevant turns split one bucket into two.
        HEURISTIC, and it says so. A RECOMPUTABLE VIEW, derived and never stored: a
        `sig_version` bump rebuilds it rather than migrating it. ⚠️ Its false positive
        is a real failure silently skipped, which is why it is never allowed to
        pretend to be exact — every shipped system that did was out by orders of
        magnitude (docs/08 §11.1).
              ▲
              └── every UNMINEABLE lands here — ONE terminal since D-081, always by exhaustion
```

⚠️ **`budget_exceeded` is a flag, never a fifth status.** It lands *beside* whichever of the
four an attempt reached, never instead of one — a run can be both `scored` and over budget, and
collapsing the two loses the case where the number is real but cost too much to get.

**One function is the whole integration.** Every model role τ² runs — the agent, the user
simulator, the hallucination reviewer, the NL-assertion evaluator — imports the same
`generate()`. Replacing it with an adapter that dispatches on `model` puts the Claude Agent SDK
behind all four without touching a call site. ⚠️ **With the outer loop deferred nothing drives
that seam end to end** — it is built, and it is exercised by one smoke test rather than by a run. **Enforcement attaches at a second point**,
`Environment.make_tool_call()`, which every tool execution already passes through and which
already knows which tools mutate state.

⛔ **No human is a step in that picture, and none is a state in the agent.** A person writes
each candidate version (D-044) — 🔴 **the part that is deferred** — and that is *upstream* of the
loop — inside it nothing pauses for
approval: a gate is a predicate, and a mined case is admitted by three mechanical gates
([docs/02](docs/02-gates.md) §5) rather than by somebody signing off on a batch. **People
improve this system by rewriting it** — reading traces, changing prompts, adding cases — which
is what everything below is instrumented for.

⚠️ **That paragraph was false about the picture directly above it until 2026-08-21**, which is
worth more than the correction. The diagram routed `REJECT` *back to the developer*, so the
prose asserted an invariant the drawing three inches above it broke. **A claim about a picture
has to be checked against the picture** — and the structural flowchart carried the same defect
in a heavier form, as two person-shaped nodes that no decision had ever authorised. Both are
terminals now: a rejection is recorded, and nothing on the page consumes it.

**Two tiers, and only one of them freezes.** The benchmark is the fixed population every gate is
scored against, so it must not move. The regression suite only ever answers *"did something that used to work stop
working?"* — a binary with no denominator to corrupt, so it can grow forever without
invalidating anything. **That asymmetry is what makes the inner loop safe to run at all** — a
mined predicate can only land in the tier that has nothing to distort.
[docs/02](docs/02-gates.md) §1. 🔴 **A second control is missing while the outer loop is
deferred**: a mined case used to arrive `open` and gate only once an *accepted* version had been
quiet on it, and with no accepted versions that status is unreachable — so it was deleted rather
than left looking like it worked. **An admitted predicate now rests entirely on the corpus it was
tested against.**

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
| [docs/01-spec.md](docs/01-spec.md) | The τ² task model, what a case is, the benchmark manifest, **10 live invariants numbered to 16** — six are retired in place, four of them by the specimen swap |
| [docs/02-gates.md](docs/02-gates.md) | ⛔ **The three decisions**, the two tiers, the acceptance rule, the stages, case provenance |
| [docs/03-agent-and-tools.md](docs/03-agent-and-tools.md) | The adapter at the seam, what we may and may not change about the τ² agent |
| [docs/04-observability.md](docs/04-observability.md) | Span schema, OpenInference conventions, why the scorer reads spans |
| [docs/05-scoring.md](docs/05-scoring.md) | Reward, `pass^k`, cost per success — and why a judge can never gate |
| [docs/06-api.md](docs/06-api.md) | CLI, HTTP surface, compose |
| [docs/07-diagrams.md](docs/07-diagrams.md) | ⛔ **The gate: no code before an approved structural diagram** — every phase, every change |
| [docs/08-memory.md](docs/08-memory.md) | Where agent memory legitimately goes, and the **anchoring failure it is planted to catch** |
| [docs/09-schemas.md](docs/09-schemas.md) | Every remaining type, the `benchmark_hash` algorithm, the file map, and the prompt and tool contracts |
| [diagrams/](diagrams/README.md) | 📐 **The gate artifacts themselves** — the structural flowchart ([`loop.png`](diagrams/loop.png), source in [`touchstone.eraser`](diagrams/touchstone.eraser)) and the run sequence. ⛔ **The source text is the artifact**; the PNG is committed so the page renders for a reader who will not clone |

🔴 **`docs/` still specifies the deferred half in the present tense, and that is deliberate.**
Wherever those files reason about *the version table*, *comparing a candidate against an
incumbent*, or a case moving `open → locked`, they are describing **the design P2.4 revives to**,
not code that runs. ⛔ **Nothing was deleted** — the arguments are why each piece is shaped the way
it is, and they would have to be re-derived otherwise. [docs/02](docs/02-gates.md) §0 and §2 carry
the deferral markers in place.

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
touchstone suite freeze --domain retail   # ⬜ pin the task ids and hash them
touchstone mine --from results/final      # ⬜ one anomalous trace → a candidate predicate
touchstone suite admit r-018              # ⬜ three mechanical gates → the regression suite
touchstone run --enforce                  # ⬜ the predicate refuses the call before it runs
```

🔴 **`touchstone run vN` / `score vN` / `compare` are deferred**, not merely unimplemented — they
belong to the candidate-comparison half, and the spec for them stands in
[docs/02](docs/02-gates.md) §2 against the day a second version exists.

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
| touchstone's three mining-loop agents | `claude-opus-5` (`LOOP_MODEL`) — router · curator · critic, **all propose, none gates** |

**Every id comes from a live call rather than a config file** — `doctor` asks the running CLI
what it actually answered as, because the id is part of a candidate's identity and a config file
can disagree with reality. ⛔ **A provider or model switch *inside* a run voids that run rather
than mixing it.** Full manifest and reasoning: [docs/00-stack.md](docs/00-stack.md).

---

## Reliability, not accuracy

🔴 **This section describes the deferred half and is kept because it is the spec that half revives
to.** `pass^k` needs repeated attempts by *our* agent; there are none, so ⛔ **no `pass^k` figure
appears anywhere in this repo** until the version table comes back.

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

- 🔴 **Nothing here has been run by this project, and the traces it reasons over are somebody
  else's.** Every gate is mined from and scored against **1,712 simulations τ²-bench ships**,
  produced by four third-party agents behind a `gpt-4.1` user simulator. ⛔ **It is a corpus, not
  a baseline**, their scores are quoted nowhere here, and a gate that fires on their failures is
  not thereby shown to fire on ours.
- **The tasks are a simulation, and the customer is a language model.** τ²-bench's user side is
  a simulator, not a person. A failure it causes is attributed to the agent unless something
  measures it. ⚠️ **That risk changed owner rather than going away** — the corpus's simulator was
  someone else's choice, already run, and **we can no longer measure its fabrication rate
  ourselves.** It was a phase-1 exit box and it is the single largest thing the deferral gave up.
  D-067.
- **Enforcement is built and its effect is unmeasured.** The gate attaches at
  `Environment.make_tool_call()` and is tested by replay; **it has never run against a live
  environment**, and *wired but never seen to fire* reads exactly like *works*.
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
  raises it. 🔴 **And the half that decides whether a candidate ships is deferred**, so at this
  tag *"the gate only decides whether it ships"* describes a specification, not running code.
- **The population is 107 of τ² retail's 114 tasks**, the ones whose gold actions are unchanged
  between the shipped runs and the current task file. **The other seven are excluded, not
  repaired**, and the two numbers travel together — ⛔ never write 114.
- **`action_checks` has a blind spot and the probe for it is a regex.** An agent can call the
  right tool with the right arguments and never have asked; the count of those (**56**) comes
  from matching the most recent user message before each WRITE, so it **over-counts** and is an
  upper bound. ⛔ **It is enough to justify widening the selector and is not a figure to quote.**
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
