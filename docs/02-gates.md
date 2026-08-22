# 02 — The gates

> ⚠️ **Specification, phase 0.** This describes the design; it is not a description of shipped code. `touchstone doctor` is the only implemented command today — see the [README](../README.md) for what runs and what does not. ⛔ **And the specimen changed under it.** D-062 replaced the self-authored infra-RCA corpus with **τ²-bench retail** — 114 tasks, MIT, deterministic DB-state-diff reward. Where this file still says *incident*, *root cause*, *affected service* or *escalate*, it is describing the **archived** specimen (branch `incident-specimen`), not what touchstone measures. **The loop is unchanged; that is the claim the swap was for.**

**This is the project. Everything else is the specimen it operates on.**

A touchstone never changes. A candidate version of the agent ships only if it is better on
something and worse on nothing that mattered before.

---

## 0. Three decisions, and why this file stopped being called "the promotion gate"

**This file was `02-promotion.md` until D-064 and D-065.** The old name was wrong in two ways at
once: it named **one** decision where there are **three**, and the one it named is not the
interesting one.

| | the decision | where it is made | what makes it | ships |
|---|---|---|---|---|
| **1** | refuse a **tool call** | `Environment.make_tool_call()`, at runtime | an extracted constraint plus a mechanical check | **P3.1** |
| **2** | reject a **candidate version** | `loop/compare.py`, at compare time | the five conditions in §2 | 🔴 **DEFERRED — `D-080`** |
| **3** | admit a **mined case** into the regression suite | `touchstone suite admit` | the three admission gates in §5 ([D-084](../DECISIONS.md#d-084)) | **P3.5** |

🔴 **Decision 2 is specified here and not built.** `D-080` deferred it: it
compares a candidate against an incumbent, and until a second version exists it has **no second
operand**. ⛔ **This section is left standing in full rather than cut** — it is the specification
the row revives from, and the five conditions in §2 are load-bearing for §5's admission gates,
which *do* ship. ⚠️ **Read every sentence about decision 2 in the present tense as a design, not a
description of running code.**

⛔ **All three are mechanical, and that is the invariant this file exists to protect:**

> **Anything that gates is mechanical. Anything with a model in it cannot gate.**

**D-064 is where the model *is* allowed to sit, and the distinction is narrow on purpose.** The
model's only job is **translation** — turn a constraint the customer *stated* into a predicate over
the database. The verdict is then a mechanical evaluation of that predicate against the proposed
call. ⛔ **The gate never judges "did the agent do well."** The moment it does, the gate is an
opinion, and an opinion that blocks a write is the worst of both.

### Why the vocabulary changed at all

"Promote" described a world with one candidate and one decision. It collapsed under the specimen
swap (D-062) because **decision 1 has no analogue in it** — there is nothing to promote when the
question is *"does this tool call execute, right now, before the row is written?"*

⚠️ **Decision 3 was drawn everywhere and built nowhere for four passes, and it is scheduled now
(D-070).** D-030 cut mining as the fast route's largest single cut; what that cut turned out to be
is the **inner loop** (§5) — the only mechanism here that makes the measurement grow instead of
reporting it. **It stayed fully specified throughout the deferral**, because this project has
already had one mechanism specified in full and scheduled by no row (DEF-009 (`DEFECTS.md`)) — and
that is precisely why it was still findable when it turned out to be the core. **All three ship.**

---

## 1. The two tiers — and why only one of them freezes

**D-024.** The suite is in two parts, and conflating them is what makes a growing eval
set either dishonest or unusable.

| | **Benchmark** | **Regression suite** |
|---|---|---|
| Size | small — n=10, then 30 | grows forever, never shrinks |
| Purpose | 📊 ***comparing*** candidates → the version table | 🔒 ***gating*** → "did anything that worked stop working?" |
| Changes | rarely, deliberately | ✅ **every reviewed mined failure** |
| Cost of adding a case | ⛔ **the baseline resets** — every prior comparison is void | **nothing** |
| Hash requirement | ⛔ must match to compare | none — it is not a comparison |

**The asymmetry is the whole idea.** A *score* across two different case sets means
nothing, so the benchmark must freeze. A *binary* over "has this ever passed" is well defined
however many cases you add, so the regression suite can grow without corrupting anything —
there is no denominator to corrupt. **Same reason adding a `pytest` test does not invalidate
yesterday's test run.**

⚠️ **The original design had one tier, and that was a defect**: adding a mined case cost the
entire baseline, which prices the mechanism so high it would never run. **A safety mechanism
too expensive to use is the 3-byte-state-file failure in a different costume** (§3).

### The acceptance rule

A candidate **C** is accepted against incumbent **I** if and only if all five hold:

| # | Condition | Why it is there |
|---|---|---|
| 1 | `benchmark_hash(C) == benchmark_hash(I)` | ⛔ **Refuse to compare across different benchmarks.** Otherwise "improvement" can be produced by editing a case, which is the most likely way this project would quietly lie |
| 2 | **No per-case regression on the benchmark** — no case that was `pass^k` under I is less than `pass^k` under C | Aggregate improvement can hide a broken case. This is the condition that does the work |
| 3 | **Strict improvement** on at least one of: mean reward, `pass^k`, cost per success | Prevents accepting a no-op and calling it progress. ⚠️ **Escalation F1 was the fourth axis here and it is cut** — its τ² analogue is `transfer_to_human_agents`, named in **4 of 114** retail tasks and contributing nothing to reward (`ToolType.GENERIC`, returns a constant string) |
| 4 | **No budget breach** — cost per success and p95 latency within the declared budget | An agent that gets better by calling ten more tools has not gotten better |
| 5 | **No `locked` regression case fails** — see below | The one-way condition: what has ever worked keeps working, across every version, forever |

Anything else is a **reject**, and a reject is written to `results/` exactly like an accept — ⛔ **the rejection is the more valuable of the two.**

### `open` → `locked`: why a mined case cannot gate on arrival

🔴 **DELETED by `D-080` — not deferred, and the difference is the point.**
`locked` is set *"automatically, the first time an accepted version scores it `pass^k`"*, and with
decision 2 deferred **no version is ever accepted**, so the second state is unreachable. ⛔ **A
two-state field whose second state cannot be reached reads exactly like one that works.** Until
P2.4 ships, a mined case carries no status and **the control described below does not exist** —
say so wherever admission is reported. It is restored **in the same commit as P2.4**, because a
case admitted under the weaker rule would otherwise start gating on a predicate nothing confirmed.

**A mined case is by definition one the agent just failed.** If it gated immediately, every
mined case would block every candidate forever and the loop would be unusable. So each
regression case carries a status:

| status | Behaviour | Set by |
|---|---|---|
| `open` | ✅ Reported in `results/`, ⛔ **does not gate** | on entry — the agent cannot pass it yet |
| `locked` | 🔒 **Gates from here on** | **automatically**, the first time an *accepted* version scores it `pass^k` |
| `quarantined` | Reported, does not gate, reason required | human, per §4 |
| `superseded` | Excluded; points at its replacement | human, on a label correction |

⛔ **A `locked` case never unlocks** except through the recorded override path in §4. **The
lock is what makes it one-way** — it is what makes "better on something, worse on nothing"
hold across the whole history rather than only against the previous version.

```bash
touchstone compare v7 --against v6
#   benchmark  ✓ 9f2a1c… matches
#   case 01    3/3 → 3/3  ok
#   case 07    3/3 → 2/3  REGRESSION                     ← blocks (benchmark)
#   case 09    1/3 → 2/3  improved (not decisive)
#   regression 41 locked · 6 open
#     r-018    3/3 → 1/3  REGRESSION  locked at v5       ← blocks
#     r-044    0/3 → 3/3  now passing → LOCKS at v7
#   verdict REJECT — 2 regressions, 1 improvement, 1 new lock
```

### ⚠️ What "passed" means for a stochastic agent — the honest version

Each case runs **k times** (default 3 — `config.K`, D-030). Comparing two three-sample draws is
a statistical question, and treating it as a binary would be the exact failure this repo's whole
discipline exists to prevent.

**So the gate fires on one transition only: `pass^k` → not `pass^k`.** A case the agent used to
get right on every attempt, and now does not.

- **Sharpest at the top.** `3/3 → 2/3` is the transition the gate acts on, and the one the
  sample size resolves best. ⚠️ **It is not a significance test**, and it is *less* resolvable
  at k=3 than it was at 5 — the answer to that is k, not a cleverer rule.
- ⚠️ **Deliberately blind in the middle.** `2/3 → 1/3` is *reported* and never blocks, because
  k=3 has no power to resolve it. **State this out loud rather than implying the gate is
  sharper than it is.**
- 📈 **The upgrade path is k**, not a cleverer statistic. Raising k to 20 buys real power and
  costs wall-clock; the default is 3 because the loop has to be cheap enough to actually run.
  ⚠️ **D-030 cut it from 5 on the grounds that "a per-case binary gate does not spend the extra
  resolution" — the cost of that cut is a wider blind middle**, and it is paid here.

**The rule in one sentence:** the gate fires only on the transition the sample size can
actually resolve, and everything else is reported without being acted on.

---

## 2. The stages

```
       ┌─── the OUTER loop — once per candidate · 🔴 DEFERRED, D-080 ───┐
  run ──▶ score ──▶ compare ──▶ accept ──▶ record
   ⋮        ⋮          ⋮          ⋮           ⋮
   └────────┴──────────┴──────────┴───────────┘  none of this runs
                        │
   1,712 shipped τ² simulations ──▶ select ──▶ 834 anomalous · 878 clean
                        │            ⛔ NOT `DB == 0` alone — D-080 §C
                        └──── mine ◀─┘
                                 │
                                 │  the INNER loop — up to n times per TRACE
                                 └─▶ translate ⇄ test ─▶ admit ─▶ regression suite
                                                    └─▶ unmineable
```

⚠️ **`promote` was the fourth verb here and it is retired.** The stage still exists — a candidate
that clears §1's five conditions becomes the incumbent — but the word named a single decision in a
project that has three (§0), and it named the least interesting one. **`accept` is the verb, and
its counterpart `reject` is the deliverable**: a candidate that gets refused, with the task that
refused it named, is the strongest artifact this project can produce.

🎯 **The two loops nest, and the inner one is the point.** The outer loop runs once per candidate
version and answers *is this better?* The inner loop runs up to `n` times **on a single failing
trace** and answers *what check would have caught this?* — the outer loop reports a number, the
inner loop is what makes the number cover more.

🔴 **`D-080` deferred the outer loop and the nesting is what changed.** The
inner loop needed *a failing trace and a control set*, and that is the **only** thing the outer
loop was supplying it — so it is fed from **τ²'s own shipped runs** instead of from ours: 1,712
simulations over the 107 tasks with unchanged gold actions, split into **834** anomalous and
**878** clean. ⛔ **The inner loop did not change. Its input did.** ⚠️ **What is genuinely lost is
the return edge** — `mine` no longer feeds a next candidate, so the picture is a pipeline until
P2.4 ships, and calling it a loop out loud would be a claim about code that is not there.

⚠️ **One naming rule, because two words were drifting apart in this file.** `mine` is a **stage**
— a verb, a step of the inner loop, the module `mine.py`. **The curator** is the **component** that
runs it and, unlike the stage, **holds state across traces**: the rule registry, what has already
been admitted, what has already been tried and refused. 🎯 **The distinction is not cosmetic — it is
the whole reason the component needed a name of its own.** A stage is stateless by construction and
can be described entirely by its inputs and outputs; the thing that stops the loop re-deriving the
same rule from the fiftieth instance of one failure cannot. **The registry and its two phases are
specified in [docs/08](08-memory.md).**

⛔ **Do not rename `mine`, `mine.py` or "mining" to match.** They are the stage and they were never
wrong. This paragraph exists because the file said *"a bug in the miner"* exactly once, which read
as a synonym for the stage and is not one.

### 1. `run`

Executes candidate C against **every case in both tiers** — the frozen benchmark and the whole
regression suite — **k times each**, emitting spans. Writes nothing but traces.
Idempotent per `(version, case, attempt)` so an interrupted run resumes.

⚠️ **The regression tier is what makes a run get slower over time**, and that is the cost the
two-tier design accepts on purpose: it buys a gate that never forgets. When it stops fitting
the quota, §4 says what gives — sample the `open` cases, seeded and declared, and ⛔ **never
the `locked` ones.**

### 2. `score`

Reads the **spans**, not the prose ([docs/04](04-observability.md)). Produces
`results/<version>.json`: per case, per attempt — reward and its `reward_breakdown` split, `termination_reason`, tool calls,
tokens, latency; then the aggregates.

### 3. `compare`

Applies §1 against the incumbent. Emits a per-case table and a verdict.

### 4. `accept`

Writes the version into `results/index.json` as the new incumbent. **In CI this is the gate**
— a rejected candidate fails the job.

⚠️ **Accepting is the cheap half.** The stage exists so that *rejecting* has somewhere to happen,
and §3 is the check that it can.

### 5. `mine` — the inner loop

**This is the loop the project is arranged around, and it is the only stage that runs more than
once.** Everything above it *measures*: one candidate, one pass, one verdict. This stage takes
**one failing trace** and works it **repeatedly**, up to `n` attempts, until it has produced
something that would have caught it. The outer loop asks *is this version better?* The inner loop
makes the thing that answers.

| | |
|---|---|
| **In** | one **anomalous** τ² retail session, drawn from the **834** selected out of 1,712 shipped simulations — `D-080` §C |
| **Out** | a **mechanical predicate** that fires on that session and is silent on every session that passes |
| **Or** | *unmineable* — the **one** terminal, after `n` attempts, with every attempt and its counterexample. A result, **not an error** (`D-081`) |

🔴 **`reward_breakdown["DB"] == 0` was the input and it was wrong.** The DB check compares **final
database state** to the gold actions and is blind to *how* the state was reached, so an agent that
skips a required confirmation and still writes the correct row scores `DB == 1`. Measured on the
corpus: **407** traces fail DB, and a further **371** pass DB with a failed `action_check`, plus
**56** with an unconfirmed WRITE that `action_checks` cannot see. ⛔ **Those 371 were sitting in
the silence set** — the *is it quiet on what passes?* half of the test below — so a correct
predicate catching a confirmation violation would have been **rejected as a false positive**. The
selector is the **union** of the three signals: **834** in, **878** clean.

⚠️ **Selection is not gating, and one number cannot be both.** `reward_breakdown["DB"]` remains the
**gate's** metric (`D-069`) precisely because it is mechanical; it is a poor
*selector* for the same reason — it cannot see process. 🔴 **The 56 is an upper bound from a regex
over the most recent user message before each WRITE, and the error runs one way (over-counting).**
It is enough to show `action_checks` has a blind spot and ⛔ **not a figure to quote.**

**The loop does not try to fix everything, and `run_predicate()` is what decides that** — not a
pre-check. A gate can only be written against something that was **written down**: retail's
`policy.md` (136 lines, `tau2-bench` at commit `a2c024725189` — `DEF-055`) and the
tool contracts the environment already enforces. A failure that maps to a stated rule — a refund
outside the stated window, a mutation without authentication, a restriction the agent was told and
stepped over — is mineable. A failure that is only *the agent was not good enough* has no rule to
point at, so no candidate survives `TEST`, and after `n` attempts it lands on **unmineable**.
Trying to gate capability is exactly how a suite fills with cases that punish correct behaviour
(§4) — and `TEST` is where that is caught, mechanically, because a predicate that fires on any of
the 878 clean sessions is rejected.

🔴 **A scope filter stood here until 2026-08-22 and it is deleted — `D-081`,
`DEF-056`.** It asked *"does this trace break a rule someone wrote down?"*,
routed a `no` to a second terminal, and **this paragraph used to call it mechanical.** It named no
file, no predicate and no model. ⛔ **It could not have been mechanical:** a mechanical answer to
*"was a stated rule broken?"* **is** the predicate `translate` produces, so the filter required the
loop's output as its own input. ⚠️ **What deleting it costs:** up to `n` model calls on a trace
with no rule to find. That is unpaid today, and the exhaustion records *are* the measurement of
it — revive the filter only if those records show a majority sharing a signal `select` already
computes, which would make it a route on an existing label rather than a judge.

#### The iteration, and where it stops

```
   anomalous session (D-080 §C — ⛔ not `DB == 0` alone)
             │
             ▼
     ┌──▶ 1. TRANSLATE ─── model reads the trace and policy.md, names the stated
     │       (D-064)       rule this session broke, and writes it as a predicate
     │                     over DB state and tool calls. A MODEL IS ALLOWED HERE,
     │           │         because it is producing a candidate, not a verdict.
     │           ▼
     │    2. TEST ──────── mechanical, no model, and this IS the whole verdict:
     │                       fires on the target session?       must be YES
     │                       fires on any always-pass session?  must be NO
     │           │
     │           ├──▶ both hold ──▶ 3. ADMIT ──▶ regression suite (🔴 no status — D-080)
     │           │                  the three admission gates below still apply
     │           │
     │           └──▶ either fails ──▶ hand back the COUNTEREXAMPLE: the passing
     └───────────────── session it wrongly fired on, or the fact that it missed
                        the target. Attempt i+1 sees what attempt i got wrong.

   after n attempts (n = 5) ──▶ UNMINEABLE — every attempt and its counterexample
                                recorded. ⚠️ NOT an error and NOT retried forever:
                                a trace nobody can write a rule for is a finding
                                about the policy, not a bug in the curator.
```

**Why the stopping rule is that and not a score.** *Fires on the failure, silent on what passes*
is precision and recall over a set that **already exists** — it needs no judge, no threshold and
no new labels, so it holds the invariant that anything which gates is mechanical. It is also the
defence against the obvious cheat: a predicate that merely quotes the failing session
(`task_id == 47`) satisfies the first half and fails the second the moment it meets a session
that passes.

⚠️ **The always-pass set is the control, so it has to be earned rather than picked** — 🆕 with
P1.7 superseded it is the **878 corpus traces that are clean on all three signals**
(`D-080`), not the sessions our v1 passed on every one of `k`. ⛔ **Clean
means clean on the selector, which is a stronger bar than `DB == 1`** — that is the whole of §C.

⚠️ **And silent-on-the-passing-set is a claim about the sessions that were run, never about the
domain.** Same shape as `pass^k` in [docs/05](05-scoring.md): a predicate can be quiet on all of
them and still be wrong about a task nobody has run. That is why an admitted case arrives `open`
and cannot gate until it has been quiet under an accepted version — `open → locked` above is the
second, slower control, and it exists precisely because this one is not sufficient. 🔴 **And
`D-080` deleted that second control.** ⛔ **Say this out loud with every
admitted case**: the slower check that this section calls necessary is **not running**, so an
admitted predicate rests entirely on the corpus it was tested against.

#### Which failure goes in — clustering picks the trace

A case that failed carries a trace showing *how*. The mine stage clusters failures by the
**way** the session failed. For τ²-bench retail that taxonomy is not invented here — it is the ten
`TerminationReason` values (`data_model/simulation.py:1254` in [tau2-bench](https://github.com/sierra-research/tau2-bench) at commit **`a2c024725189`**, MIT) crossed with **whether the mechanical `DB` component came back zero** (D-069), and it proposes cases that isolate that confusion.

⛔ **Cluster on `reward_breakdown["DB"]`, never on the composite reward.** Retail declares `reward_basis = ["DB", "NL_ASSERTION"]` on 112 of its 114 tasks, so the composite has a judge in it and cannot gate — D-069. The `DB` key is written separately by `evaluator_env.py:153` and is mechanical. *(An earlier pass here said the two live components were `DB` and `COMMUNICATE`; that was measured off 1,824 leaderboard simulations run against the superseded task set — `DEFECTS.md` DEF-036.)*

⚠️ **This paragraph described generating new incidents with a planted root cause, and that
capability left with the specimen (D-062, D-066).** τ²'s 114 retail tasks are upstream and are
**never** regenerated here — mining selects and annotates, it does not author. That is a real
reduction in what `mine` can do, and it is the price of not owning the corpus, which is the whole
point of the swap.

> This is [`evalloop`](https://github.com/sandeepyadav1478/evalloop)'s idea with a real domain
> under it. Cite it; it predates this project.

```mermaid
flowchart TB
  SCORE["1,712 shipped τ² simulations<br/>🔴 not our own run — D-080"] --> FAIL["select · 834 anomalous<br/>DB==0 ∪ failed action_check ∪ unconfirmed WRITE"]
  FAIL --> PICK["cluster · pick one anomalous session"]
  PICK --> TRANS["1. TRANSLATE — model writes a candidate predicate<br/>D-064 · candidate, never verdict<br/>🔴 no scope pre-check — D-081 deleted it"]
  TRANS --> TEST{"2. TEST — mechanical, no model<br/>fires on the target · silent on the 878 clean"}
  TEST -->|"either fails · attempt < n"| TRANS
  TEST -->|"either fails · attempt = n"| UNM["UNMINEABLE · every attempt recorded<br/>⚠️ a result, not an error"]
  TEST -->|both hold| PROP["suite/proposed/<br/>each case carries why · when · origin · the trace"]
  PROP --> ADMIT{"⛔ admission gates — all three, mechanical<br/>reproducible · distinct · justified"}
  ADMIT -->|any one fails| DROP["discarded · the failing gate is recorded, not the case"]
  ADMIT -->|all three hold| REG["regression suite<br/>🔴 no status — open/locked deleted, D-080"]
  REG -.->|"🔴 DEFERRED with P2.4 — no version is ever accepted"| LOCK["status: locked · gates from here"]
  ADMIT -->|"lift into the benchmark · rare, a deliberate edit"| BENCH["benchmark vN+1<br/>⛔ baseline resets"]
```

#### ⛔ Admission is mechanical, and no human is a step in it

A wrong case gates *correct* behaviour forever, and you would debug it as an agent regression.
§4 calls a wrong label the most valuable defect this project can produce. **So the last stage
before a case can gate anything is the strictest one — it is just not a person.**

⚠️ **This used to be a batch human review, and the argument for it was that "a wrong label
entering silently is poison."** That is true and it is why the step existed. It does not apply
here, for a reason specific to this domain: **nothing is labelled at mine time.** A mined case
carries τ²'s own `reward_breakdown` as its label — computed by the benchmark's evaluator, not by
us and not by a judge (§2), so the label was correct before the failure happened. There is no labelling act to get wrong —
which this document already said: *review is a batch approval over machine-prepared cases,
never a labelling task.*

**What that review was actually doing is admission control** — *is this failure worth locking
into the suite forever?* — and every one of its criteria is computable from artefacts the
pipeline already produces:

| Admission gate | The check | Where it comes from |
|---|---|---|
| **Reproducible** | fails on **every** one of k trials, not some — `all(reward_breakdown["DB"] == 0)` over k=4, and ⚠️ **the 4 trials carry 4 distinct seeds** (456 of 456 (file,task) pairs). ⛔ **Replay identity is unverified** — a seed exists, whether it reproduces byte-identically does not follow, because model sampling may not be seeded. **Admits 34 of 456** on the shipped retail set | `pass^k` — [docs/05](05-scoring.md) §2, [D-084](../DECISIONS.md#d-084) |
| ~~**Not flaky**~~ | 🔴 **MERGED into Reproducible — [D-084](../DECISIONS.md#d-084).** *"Re-run reproduces the failure"* **is** *"fails 4/4 across 4 seeds"*: there is no second run, the outer loop is deferred and the agent is never called. Two names, one predicate | — |
| ~~**Not a void**~~ | 🔴 **DROPPED — [D-084](../DECISIONS.md#d-084).** `termination_reason` is `user_stop` on **1,824 of 1,824** shipped retail simulations. One value, zero variance, nothing to refuse. ⛔ **A gate that cannot fail reads exactly like a gate that passes.** Returns with P2.4, when a run of *ours* can produce a void at all | the four attempt statuses, [docs/09](09-schemas.md) §6 |
| **Distinct** | no two cases share a `task_id` — ⛔ **refuses**. Plus a **failure-signature** check ([D-078](../DECISIONS.md#d-078) §11.2, same function, `sig_version`) which ✅ **admits and records** `duplicate_of` rather than refusing ([D-083](../DECISIONS.md#d-083)). ⚠️ **The one gate that can pass while reporting a problem** — an over-merged signature would refuse a real failure permanently, and a bucketing heuristic measured at 1–2 OOM of error must not hold an undoable refusal | [docs/01](01-spec.md) §6, [D-083](../DECISIONS.md#d-083) |
| **Justified** | non-empty `why`, `added`, `origin` | [docs/01](01-spec.md) §6, invariant 11 |

**Four of the five were already specified machinery**, which is the tell: the reviewer was
applying criteria that were written down. `origin` records `mined` and the version that
produced it; **`admitted_by` records the gate set that admitted the case, not a name.**

⚠️ **The field was `reviewed_by` and it is renamed, for the same reason `APPROVAL_THRESHOLD`
was ([docs/09](09-schemas.md) §10).** A field named after a person is read as a person having
looked, and the first draft of this section kept the prose above while the JSON below still
said `"reviewed_by": "sandeep"` — the rename is what stops that recurring. It is **free**: the
provenance fields are outside `benchmark_hash` by construction ([docs/09](09-schemas.md) §5).

⚠️ **The cost, stated rather than hidden.** A degenerate case that passes all three is now
admitted with nobody having looked at it. The recovery path is the regression tier itself: if
it ever refuses a candidate on a case that inspection shows should not have been admitted,
review comes back as an **offline batch that quarantines** — never as a step a run waits on.
D-040.

#### Provenance — every case says why it exists and when it arrived

**A suite you cannot read the history of is a suite you will eventually stop trusting.** So
every case carries its own record, in its `manifest.json` entry:

⚠️ **This example is a *future* entry and shows the fields as they will be once P2.4 ships.** Under
`D-080` an entry written today has **no `status`, no `locked_at`, and no
`mined_from.version`** — there are no versions. ⛔ **Every other field ships**, and `why` /
`admitted_by` / `history` are the ones that carry the weight.

```json
{
  "id": "r-018",
  "tier": "regression",
  "task_id": "47",
  "domain": "retail",
  "status": "locked",
  "added": "2026-09-02",
  "added_in": "regression v7",
  "origin": "mined",
  "why": "v6 zeroed reward_breakdown[DB] on 4 of 4 trials for task 47 — it cancelled the wrong order line after the user corrected itself mid-conversation. termination_reason was user_stop every time, so it finished confidently.",
  "mined_from": {
    "version": "v6", "case": "inc-009",
    "confusion": ["cache_stampede", "db_pool_exhausted"],
    "trace_id": "4bf92f35…"
  },
  "admitted_by": ["reproducible", "distinct", "justified"],
  "admitted": "2026-09-02",
  "locked_at": "v7",
  "supersedes": null, "superseded_by": null,
  "history": [
    {"date": "2026-09-14", "change": "quarantined",
     "why": "oscillates 3/3 ↔ 2/3 across identical runs — a coin flip in the case, not the agent"},
    {"date": "2026-09-21", "change": "unquarantined",
     "why": "cause was an unseeded jitter in the metric renderer; fixed in generate.py, seed now reproduces"}
  ]
}
```

| Field | Rule |
|---|---|
| `origin` | `seeded` · `mined` · `correction` · `manual` — **four kinds, and they read differently** |
| `why` | ⛔ **Required, prose, non-empty — CI fails on a blank one.** Without this the schema decays into fields nobody fills |
| `added` / `reviewed` | Dates, always. *"When did this start gating?"* must be answerable |
| `mined_from` | The trace that produced it. **A mined case links to the failure that justified it** — that is the audit trail the whole loop rests on |
| `history[]` | **Append-only.** Status changes and their reasons; entries are never edited or removed |
| `supersedes` / `superseded_by` | ⛔ A case is **never edited in place.** A wrong label is fixed by adding a corrected case and pointing the two at each other |

**And `suite/CHANGELOG.md`** — one human-readable entry per suite version: what was added, why,
which failures drove it, and what the agent could not do at the time. ⚠️ **Generated from the
manifests, then reviewed** — a hand-maintained changelog is how a reason outlives the fact.

```bash
touchstone suite log              # the changelog, from the manifests
touchstone suite show r-018       # one case: why, when, origin, lock point, full history
touchstone suite diff v6..v7      # what changed between two suite versions, and why
```

**`touchstone suite show` is the payoff.** *"Why is this case here?"* has an answer that names a
date, a version, a trace and a sentence a human wrote — never *"somebody added it at some
point."*

### 6. `record`

Regenerates the README's version table from `results/`. **The table is generated, never hand
written** — a hand-maintained results table is how a number outlives the run that produced it.

---

## 3. 🔴 The negative control — prove the gate can reject

**A gate that has never blocked anything is indistinguishable from no gate.**

The common shape of this failure is a loop that was designed, wired, documented and never
actually ran — the tell is a state file a few bytes long, months after it was built. **This
project must not be able to make that mistake silently.**

**So: `results/negative-control.md` is a required artifact before v0.1.0.** It contains a
deliberately damaged candidate — remove a tool, truncate the context window, corrupt the domain
policy handed to the agent — run through the full pipeline, with:

- the `compare` output showing the regression,
- the CI run that failed, **linked**,
- one sentence on which case broke and what the trace showed.

- [ ] The suite can go red on demand
- [ ] CI actually blocks on it
- [ ] The artifact is committed

⚠️ **Do this at phase 2, not at the end.** A negative control run after everything works is a
performance; run before you trust a single green result.

---

## 4. When the gate is wrong

It will be. Write these in `DEFECTS.md` as they happen.

| Failure | Symptom | What to do |
|---|---|---|
| **Overfitting to the benchmark** | Every candidate improves, real behaviour does not | The benchmark is ten cases. Say so, always, and never quote the correctness number without n. ⛔ `mine` is not the fix — it emits *regression* cases, which gate but never enter the version table, so the comparison stays exactly as easy as it was. A harder comparison needs a new benchmark version, which resets the baseline and costs a re-run of every prior candidate (D-024) |
| **A flaky case** | One case oscillates between 3/3 and 2/3 across identical runs | Not a regression — a case with a coin-flip in it. Quarantine it: `touchstone suite quarantine --why` for a regression case, a hand edit to `suite/benchmark/manifest.json` plus a `DECISIONS.md` entry for a benchmark one. ⚠️ **The benchmark path is deliberately the harder one** — quarantining a benchmark case changes what the table measures |
| **A wrong label** | The agent is right and the key is wrong | **The most valuable defect this project can produce.** Add a corrected case and set `superseded_by` — never edit the frozen one |
| **Gate blocks a real improvement** | A better agent regresses one case | This is the gate working as designed. Override is a human decision, recorded in `DECISIONS.md` with the reason |
| **The regression suite rots** | Locked cases accumulate; some now block for reasons nobody remembers | ⚠️ This is the risk auto-growth adds, and provenance is the answer — `touchstone suite show` gives every locked case a date, a trace and a sentence. ⛔ Never bulk-unlock; quarantine individually, with a reason |

⚠️ **The override path must exist and must be logged.** A gate with no override gets deleted
the first time it is inconvenient; a gate whose overrides are recorded stays honest. **An
override on a `locked` regression case is the strongest form of this** — it is a decision to
ship something that used to work and no longer does, and it belongs in `DECISIONS.md` with the
trace, not in a commit message.

---

## 5. What touchstone is not

- ⛔ **Not learning.** The agent does not update from failures. A human writes each candidate;
  this decides whether it ships. **Never say "self-improving."**
- ⛔ **No auto-tuner** (D-044). Closed-loop designs elsewhere end with a diagnoser that rewrites
  prompts automatically. **The reason for declining it is D-013, not principle:** a candidate is
  `(graph, prompts, parameters, provider, model)` and the version table means something only
  because **one thing changes per version.** A prompt rewrite is an unbounded number of changes at
  once, and it **generates candidates faster than the gate can attribute them** — more rows,
  less information. ✅ **Revival trigger:** an automated generator is admissible the moment its
  output is *one describable change* that fits the table's **what changed** column — a single
  parameter, a single named prompt section. **A free-text rewrite never qualifies.**
- ⚠️ **The *suite* grows automatically; the *agent* does not.** `mine` makes the measurement
  harder, not the agent better — and the two loops turn at different speeds, on purpose. Saying
  "it improves itself" fuses them, and the fused version is the one that is false.
- ⛔ **Not statistical significance testing.** k=3 with a per-case binary gate. §1 states the
  ceiling; do not dress it up.
- ⛔ **Not a general eval framework.** It scores one agent against one benchmark, plus a
  regression suite that only ever answers yes or no.
