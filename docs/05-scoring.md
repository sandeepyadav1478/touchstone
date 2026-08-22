# 05 — Scoring

> ⚠️ **Specification, phase 0.** This describes the design; it is not a description of shipped code. `touchstone doctor` is the only implemented command today — see the [README](../README.md) for what runs and what does not. ⛔ **And the specimen changed under it.** D-062 replaced the self-authored infra-RCA corpus with **τ²-bench retail** — 114 tasks, MIT, deterministic DB-state-diff reward. Where this file still says *incident*, *root cause*, *affected service* or *escalate*, it is describing the **archived** specimen (branch `incident-specimen`), not what touchstone measures. **The loop is unchanged; that is the claim the swap was for.**

Three gating metrics, all mechanical. **The judged dimension is reported beside them and gates nothing — [§5](#5-the-judged-dimension--and-why-it-can-never-gate) says why that is an invariant rather than a threshold.**

---

## 1. Reward — mechanical, no judge

**touchstone does not define correctness. τ²-bench does, and it does it without a model.**
That is the whole reason this specimen was chosen (D-062): the answer key is a database, not
an opinion.

A simulation's reward is the **product** of the components named in the task's
`evaluation_criteria.reward_basis` — `evaluator.py:223` starts at `1.0` and multiplies each one
in, so **any single zeroed component zeroes the reward.** That is what makes *"which component
came back zero"* the natural failure class.

| Component | How it is checked | Model in it? | In retail's basis? |
|---|---|---|---|
| `DB` | the task's gold `actions` are replayed on a fresh environment, and the agent's **end state** is diffed against the result. **Any path reaching an equivalent end state passes** | none | **all 114 tasks** |
| `NL_ASSERTION` | a judge is asked whether each written assertion holds, via `generate()` on `DEFAULT_LLM_NL_ASSERTIONS` (`evaluator_nl_assertions.py:121`) | 🔴 **yes** | **112 of 114** |
| `COMMUNICATE` | each required string must appear, lowercased, as a **substring** of some assistant message (`evaluator_communicate.py:69`) | none | ⛔ **zero** — this is the *original τ-bench* basis, not retail's |

🔴 **So touchstone gates on `reward_breakdown["DB"]`, not on the composite reward (D-069).**
`evaluator_env.py:153` writes `DB` as its own key on every task, independent of what the
composite multiplies together — so the mechanical half is available per simulation without
editing anything upstream. **The composite is reported next to it, unmodified**, because that is
the number the leaderboard is in.

⚠️ **`RewardType` declares five components** — `DB`, `ENV_ASSERTION`, `NL_ASSERTION`, `ACTION`,
`COMMUNICATE`. Across the **1,824 shipped retail simulations** in `data/tau2/results/final/`,
`reward_breakdown` is exactly `{DB, COMMUNICATE}` — **and that is a fact about a task set this
repo will never run.** Those leaderboard runs predate the retail rewrite; the file a run loads
today declares `{DB, NL_ASSERTION}` on 112 of 114 tasks.

⛔ **A report JSON is authoritative for the run that produced it and for nothing else.** Both
files ship in the same checkout, the stale one has a four-digit `n`, and the claim it produced
reached four artefacts before anyone opened `tasks.json`. `DEFECTS.md` DEF-036.

🔴 **`COMMUNICATE` is a substring match, and upstream says so itself** — the line carries
`# TODO: This could be improved!`. It strips commas from the haystack and nothing else, so an
agent that says the right number inside the wrong sentence still scores. **Do not repair it.**
Our figures have to be comparable with the published leaderboard, and a scorer we quietly
improved is a scorer nobody can check us against. Record the brittleness; keep the metric.

### The partial-credit rule survives the swap

**Partial credit is reported, never gated.** `results/` carries the `reward_breakdown` split
alongside the scalar, because *"got the database right, never said the number"* is a different
failure from *"did the wrong thing"*, and the version diff is more legible with both. **The
acceptance rule uses the scalar only** — one number to gate on, the rest for reading.

### Stratified by memory condition, for the memory candidate (D-023)

**Not a new metric — a group-by.** Reward and `pass^k` are additionally reported per memory
condition, because a memory candidate's average hides the thing worth knowing: memory should
*help* where a prior session carried a usable fact and be flat where it did not.

⛔ **Counts, never percentages, at this n.** A stratum holds a handful of tasks; `2/2 → 0/2` is a
fact and *"memory costs 40%"* is a number invented from two data points. The gate result is
valid at this n — one per-task regression is one regression — the rate is not.
[docs/08](08-memory.md) §7.

⚠️ **The `precedent` / `false_friend` stratification this section used to describe was a property
of the authored corpus** — we planted the precedent, so we could label it. **τ² tasks carry no
such label and we do not get to add one**, so the stratification is now over a condition we
control (memory on/off) rather than a corpus property we cannot see. That is a real loss of
resolution, recorded rather than papered over.

---

## 2. `pass^k` — reliability

Each task runs **k times** (default 3 — `config.K`, D-030).

⛔ **This metric is not ours and its name is not a choice.** τ²-bench computes it at
`metrics/agent_metrics.py:113`:

```python
def pass_hat_k(num_trials: int, success_count: int, k: int) -> float:
    return math.comb(success_count, k) / math.comb(num_trials, k)
```

**Read that carefully — it is not "the fraction of tasks that passed every attempt."** It is the
probability that **k trials drawn without replacement from this task's n trials all pass**,
averaged across tasks. With `k == num_trials` the two coincide; with `k < num_trials` they do
not, and the difference is a per-task probability rather than a 0/1 indicator.

| Metric | Definition |
|---|---|
| `pass^1` | mean success rate over all trials — the lenient reading, one attempt |
| `pass^k` | `C(successes, k) / C(trials, k)` per task, averaged — **the headline** |

An agent right 80% of the time on each of four independent attempts clears `pass^4` on about
four tasks in ten. **`pass^1` describes a demo; `pass^k` describes something you would put on
call.** Both go in the README, even when they differ — especially when they differ.

⚠️ **Infrastructure errors have two conventions and they disagree.** `get_metrics_df` filters
`INFRASTRUCTURE_ERROR` simulations out entirely (`agent_metrics.py:145`), while the published
leaderboard convention counts them as **failed trials** (τ²-bench `RELEASE_NOTES.md`). ⛔ **Say
which one a number used, in the same sentence.** We follow the leaderboard convention, because a
run that died is a run the operator did not get an answer from.

🆕 **This retires D-041 by adopting upstream's name instead of coining one.** The old metric was
called `all_k`, with a standing ⛔ never to call it `pass@k` — because `pass@k` conventionally
means *at least one of k succeeded*, and a reader seeing the familiar name reads the gate as
weaker than it is. `pass^k` is τ²-bench's own name for its own metric, and **the caret is the
distinction**: `pass@k` is lenient, `pass^k` is strict. The rule that produced D-041 held; what
changed is that we no longer have to enforce it ourselves.

> The reliability framing came from [`tracebench`](https://github.com/sandeepyadav1478/tracebench). Cite it.

---

## 3. ⛔ Escalation F1 — cut, and why

**This section measured whether the agent knew when to give up**, over cases labelled
`insufficient_evidence`. It was a good metric for a corpus we authored, because we chose how
many of those cases to plant.

**τ²-bench retail has an analogue and it will not carry a metric.** `transfer_to_human_agents`
exists (`domains/retail/tools.py:732`), but:

- it is named in **4 of 114** tasks — an F1 over four positives is a number that moves when one
  attempt flips;
- it is a `ToolType.GENERIC` tool that **returns a constant string** and touches no state, so it
  contributes **nothing** to `DB`, and therefore nothing to reward;
- there is no per-task ground truth for *"should have transferred"* — only the four tasks that
  mention it.

⛔ **So it is cut, not weakened.** The old text required *"quote n alongside it, always"*; at
n=4 the honest application of that rule is to delete the metric. **A metric kept at an n that
cannot support it is worse than no metric, because it still moves and someone still reads it.**

---

## 4. Cost per success

```
cost_per_success = sum(ResultMessage.total_cost_usd) / n_successful_trials
```

**Measured, not computed.** The Agent SDK reports `total_cost_usd` per call, plus a
per-model breakdown carrying `cacheReadInputTokens` — so **tokens × list price would be wrong,
and wrong in the flattering direction**, because prompt caching is not in the list price.

🔴 **But it was not billed.** The runs go through the Claude Code subscription, so the honest
sentence is: *"what the run would have cost at API list prices — it came out of a subscription
quota, not an invoice."* Both halves are load-bearing. ⚠️ Record the **model id** next to it —
that comes from the run and is what distinguishes the paths; `provider` is a config label
(D-033), and `"auth": "subscription"` is a precondition `touchstone doctor` asserts.

🔴 **And the quota rejects rather than bills.** The account reports
`overage_status='rejected'` on a `five_hour` window, so exhausting it **kills a run in flight**
rather than producing a larger number here. A cost figure from a truncated run is not a cheap
run — check `termination_reason` before reading this metric at all.

**The denominator is the design choice.** Cost per *trial* rewards an agent that gives up
quickly. Cost per *success* is the unit an operator actually has — and an agent that
is cheap and wrong scores badly, which is right.

⚠️ **Renamed from "cost per correct triage".** *Triage* was the specimen's verb, not the
metric's; the arithmetic is unchanged.
---

## 5. The judged dimension — and why it can never gate

**τ²-bench ships a judged reward component, and we do not turn it on.** `NL_ASSERTION` is a
declared member of `RewardType`; `evaluator_nl_assertions.py:121` scores it by calling
`generate()` — **the same seam every other model role crosses** — on
`DEFAULT_LLM_NL_ASSERTIONS`. Across the 1,824 shipped simulations it appears in
`reward_breakdown` **zero** times.

⛔ **THE INVARIANT: anything that gates is mechanical; anything with a model in it cannot
gate.** D-064 puts the model in **translation** — turning a written constraint into a predicate
over the database — and leaves the **verdict** mechanical. D-065 says a gate runs in shadow or
in enforce, and in both modes the thing that decides is a predicate, not a judgement.

⚠️ **This section previously said the rubric was not a gate *yet*, and gave a threshold for
promoting it.** The argument was: the reason is `n`, not a view about rubrics — a rubric averages
out beautifully as a dense RL reward over thousands of episodes, and a gate is the opposite
regime (one decision, no averaging, a 90%-reliable judge corrupting one case in ten, which is the
entire margin between adjacent versions). **That argument was correct and it has been
superseded.** D-064 did not raise the threshold; it removed the axis. A judge is now excluded by
*construction*, not by an `n` it might one day clear. 🎯 **The old text is kept here rather than
deleted, because a threshold that was quietly removed reads, later, as a threshold that was
quietly met.**

🔴 **The judge does not run on Cerebras, and this section said it did.** The constraint is
**Anthropic models only**, stated by the user and not negotiable; `ollama` and Cerebras remain
`touchstone doctor` diagnostics and are **never model sources** — the earlier text named
`arize-phoenix-evals` on Cerebras under D-016, and **the doc was what was wrong**. What survives
is the reason the offload was attractive in the first place: *the quota goes to the thing being
measured, not to a metric that cannot block anything.* With the judge excluded by the invariant
rather than by cost, that trade no longer needs making.

### What replaces it: the cross-check, which needs no judge at all

**The evidence cross-check was always the better half of this section**, and it survives the
specimen swap intact because it is structural:

- the transcript names a fact — an order id, a price, a policy clause;
- the tool spans say whether the agent ever fetched it;
- **a citation with no fetch behind it is detectable without asking anyone's opinion.**

That is a real check against a real failure mode, it is mechanical, and it is therefore
**eligible to gate**. It is the same shape as the `DB` component: replay what should have
happened, diff it against what did.

### If the judged column is ever reported, three things are recorded with it (D-041)

Reported, never gated — and the fields live inside §6's `diagnostics` object, with `compare.py`
asserted never to read it (D-045). **That guarantee is a test, not this sentence.**

| Recorded | Why |
|---|---|
| `judge_model` | A score whose judge is not on the record is a number with no provenance. §6 carries `judge: {provider, model}` — D-041 makes it **required**, not illustrative |
| `rubric_hash` | **The rubric is part of the measurement.** Edit a criterion and every past score becomes a different claim — the same argument [docs/09](09-schemas.md) §5 makes about the benchmark hash |
| `criterion_1_agreement` | The calibration: criterion 1 duplicates the mechanical cross-check above, so **the agreement rate between them is the judge's measured error rate on this corpus**, computed against an answer already known |

⛔ **The remaining criteria are not reportable on a run whose criterion-1 agreement is not also
reported.** Not because they are wrong — because with no human anywhere in this loop (D-040),
nothing else in the system can tell you whether they are right.

🔴 **Built at P2.6a at the earliest, and possibly never** (DEF-009). This section specified a
judge in full while no roadmap row built it, for as long as it has existed. **The placement is
the finding:** a metric that cannot gate cannot block the loop, so it comes after the gate it is
not part of — and under the invariant, "after" may mean "not at all."

### ⛔ Two gates that call the same judge are one gate

A gate stack's strength is the number of **uncorrelated** failure modes in it, never the number of
rows in the table. Four layers here are independent, and the reason is nameable for each:

| Layer | Cannot fail the way the others do |
|---|---|
| The invariants ([docs/01](01-spec.md) §6) | No model call at all — it cannot hallucinate |
| The evidence cross-check, above | Structural: the span says fetched, or it does not |
| τ²'s mechanical reward (§1) | `DB` state diff — upstream's code, not ours. ⛔ **The `DB` key alone**: the composite has `NL_ASSERTION` in it on 112 of 114 tasks, and a judge in a gate is the one thing this table exists to forbid (D-069) |
| The acceptance conditions ([docs/02](02-gates.md) §1) | Arithmetic over the three above |

**A judged column would be a fifth entry but not a fifth layer** — it shares its model with any
other judged check, so they fail together. ⚠️ **A list of seven gates that share one judge is a
single point of failure wearing a table**, and counting them separately is how a gate stack gets
impressive without getting stronger.
---

## 5a. ⛔ The *supervisor* router — cut by D-062, and its argument is the one to keep

⚠️ **Name collision, and it is worth reading twice.** `D-082` introduced a **router agent** in the
mining loop — a rubric that decides which shipped τ² session is worth mining. **That is not this
one.** This section is about the *supervisor* router of the archived agent graph, which picked the
next specialist. The `D-082` router still exists and is live; the one below does not.

**There is no supervisor router.** The supervisor that picked the next specialist is archived with the graph
([docs/03](03-agent-and-tools.md) §1), so `required_specialist`, the per-specialist precision and
the `next` attribute are all gone. D-042 is retired.

⚠️ **The hole it was closing is still open, in a different shape.** The complaint was that *a
failing version could not be attributed to "routed wrong" versus "synthesised wrong"* — and today
it cannot be attributed to *"the agent misread the policy"* versus *"the user simulator never said
the thing"*. **A wrong answer in a two-party conversation has two authors**, and the reward says
which run failed, never which party. `hallucination_review` (§6, upstream's reviewer at
`hallucination_reviewer.py:196`) is the nearest instrument and it reads only one side.

⛔ **The rule that outlived the metric, and it is the more valuable half:** *a metric that measures
**which mechanism** produced an answer must never gate.* Gating on a mechanism forbids a version
that reaches the right answer a different way, which is the opposite of what the version table is
for. That is why §6's `diagnostics` object is a **boundary** rather than a heading, and why the
test that perturbs every value inside it survives D-062 intact while the field that motivated it
does not.

🔴 **And one warning transfers verbatim.** The old note said adding a key to the answer key after
the benchmark freezes is *a benchmark version bump that orphans every past score*. **That is now
someone else's file** — `tasks.json` is upstream — so the risk inverted: we cannot add a key at
all, and an upstream one arriving is a CI failure by invariant 7. **Losing the ability to make
that mistake is worth more than the metric was.**

---

## 6. The results file

`results/v4.json` — every number in the README comes from one of these.

```json
{
  "version": "v4",
  "benchmark_hash": "9f2a1c…",                          // sha256 of tasks.json — invariant 7
  "benchmark_version": "v2",
  "regression_version": "v7",
  "k": 3,
  "domain": "retail",                                   // ⛔ τ² task ids are bare integers and
                                                        //    are NOT unique across domains
  "tau2_commit": "a2c024725189",                        // the scorer is upstream's; pin it
                                                        // ⛔ the COMMIT, not the version — the
                                                        // string "1.0.1" names two trees (DEF-055)
  "model": "⟨the model_usage key, from the run — D-033⟩",
  "provider": "subscription",                           // ⛔ Anthropic only; cerebras/ollama are
                                                        //    doctor diagnostics, never model sources
  "auth": "subscription",
  "aggregate": {
    "reward_mean": 0.0, "pass_hat_1": 0.0, "pass_hat_k": 0.0,
    "reward_breakdown_zeroed": {"DB": 0, "NL_ASSERTION": 0}, // which component killed the reward
                                                             // ⛔ NL_ASSERTION, not COMMUNICATE —
                                                             //    retail declares zero of it (DEF-036)
    "infra_error_convention": "counted_as_failed",           // ⛔ leaderboard convention, §2
    "cost_per_success_usd": 0.0, "tool_calls_mean": 0.0, "p95_latency_s": 0.0,
    "budget_exceeded": 0, "void_attempts": 0,
    "termination_reasons": {                                 // ⛔ ALL TEN, always, even at zero —
      "user_stop": 0, "agent_stop": 0, "max_steps": 0,       //    a key that appears only when it
      "timeout": 0, "too_many_errors": 0, "agent_error": 0,  //    fires cannot be read as "never
      "user_error": 0, "infrastructure_error": 0,            //    fired" vs "not recorded"
      "context_window_exceeded": 0, "unexpected_error": 0
    }
  },
  "cases": [{"id": "47", "success_k": 5, "attempts": [...]}],   // attempt record: docs/09 §6

  // ⛔ compare.py NEVER reads inside this object, and one test proves it (D-045).
  //    Everything an acceptance depends on is above this line.
  "diagnostics": {
    "judge": null,                                      // ⛔ excluded by the invariant, §5 — not
                                                        //    "not yet"; NL_ASSERTION stays off
    "criterion_1_agreement": null,
    "evidence_cross_check": {"cited_without_fetch": 0}, // mechanical, and therefore gate-eligible
    "hallucination_review": null                        // upstream's reviewer, D-067 — a model
                                                        // reads the transcript; it never gates
  },

  "regression": {
    "locked": 41, "open": 6, "quarantined": 1,
    "locked_failed": [],
    "newly_locked": ["r-044"],
    "cases": [{"id": "r-018", "status": "locked", "correct_k": 5, "attempts": [...]}]
  }
}
```

⛔ **Written by `touchstone score`, never by hand.** The README table is generated from these
files ([docs/02](02-gates.md) §2.6). Per-attempt records and the four `status` values:
[docs/09](09-schemas.md) §6.

🎯 **`diagnostics` is a boundary, not a heading (D-045).** Both things inside it are opinions about
*how* an answer was produced — a judge's read of the reasoning, and upstream's hallucination
reviewer's read of the transcript — and §5 promises, in prose, never to gate on them. **A promise in prose is
worth what the next reader knows about it.** So the fields move inside one named object and
`test_compare_ignores_diagnostics` asserts that perturbing **every value in it** leaves the
promotion decision byte-identical. ⚠️ **The point is not that the judge is trustworthy. It is that
the gate cannot be affected by whether it is** — the same construction that keeps `truth.json` from
the agent by a directory boundary rather than by an instruction.

⛔ **`max_hops`, `hops_exhausted` and `runbook_hash` were removed by D-062, and each for its own
reason rather than as a batch.** The first two named a supervisor's routing budget and there is no
supervisor; the third hashed a runbook corpus that is archived. ⚠️ **What the hop bound was *for*
does not go away**: it caught an agent that wanders, and that failure now lands on
`cost_per_success_usd` and on `max_steps` in `termination_reasons` — τ²'s own bound, enforced by
τ²'s own orchestrator. **Two detectors replaced by two detectors is the honest description; "we
dropped a metric" is not.**

⛔ **`aggregate` covers the benchmark and nothing else, and the regression block carries no
aggregate at all.** That asymmetry is deliberate and it is the whole reason the suite can grow
(D-024): **an average over a case set that changes between runs is not comparable to itself**,
so the regression tier reports counts and a fail list instead. `locked_failed` non-empty blocks
the acceptance; `newly_locked` names the cases this run just locked shut.

⚠️ **Never put a regression pass rate in the version table.** It would move for two reasons at
once — the agent changed, and the denominator changed — and a ratio whose denominator moves
between rows is not comparable down the column, which is the only thing that table is for.

---

## 7. What is deliberately not measured

- ⛔ **Wall-clock "time to resolution".** No humans, no baseline, and τ² user turns are a
  simulator's, not a customer's. **The most tempting number here and the least defensible.**
- ⛔ **Anything against a human agent.** There is no comparison group.
- ⛔ **A repaired `COMMUNICATE` check.** §1 says why: a scorer we quietly improved is a scorer
  nobody can compare us against.
- ⛔ **Answer "helpfulness" as a headline.** A judge scoring vibes is what this design exists
  to avoid; it appears once, in §5, clearly bounded.
