# 05 — Scoring

> ⚠️ **Specification, phase 0.** This describes the design; it is not a description of shipped code. `touchstone doctor` is the only implemented command today — see the [README](../README.md) for what runs and what does not.

Four metrics, one of them judged. **The three that gate promotion have no model in them.**

---

## 1. Correctness — exact match, no judge

A verdict is **correct** iff:

```python
if truth.resolvable:
    correct = (verdict.root_cause_id  == truth.root_cause_id
           and verdict.affected_service == truth.affected_service
           and verdict.escalate is False)
else:                                    # `insufficient_evidence` cases
    correct = verdict.escalate is True
```

**Both halves matter.** Naming the right failure in the wrong service is not a triage; and
confidently answering an incident that has no determinable cause is the failure that wakes
people up at 3am for nothing.

⚠️ **Partial credit is reported, never gated.** The results file carries `root_cause_only` and
`service_only` alongside the strict number, because *"right cause, wrong service"* is a
different diagnosis from *"no idea"* and the version diff is more legible with both. **The
promotion rule uses the strict conjunction only** — one number to gate on, the rest for
reading.

### Stratified by `precedent`, for v5 (D-023)

**Not a new metric — a group-by.** `correct` and `all_k` are additionally reported per
`precedent` label (`true` / 🔴 `false_friend` / `none`, [docs/01](01-spec.md) §4), because a
memory candidate's average hides the thing worth knowing: memory should *help* on `true`, *hurt*
on `false_friend`, and be flat on `none`.

⛔ **Counts, never percentages, at n=10.** A stratum holds two or three cases; `2/2 → 0/2` is a
fact and *"memory costs 40%"* is a number invented from two data points. The gate result is
valid at this n — one per-case regression is one regression — the rate is not.
[docs/08](08-memory.md) §7.

---

## 2. `all_k` — reliability

Each case runs **k times** (default 3 — `config.K`, D-030).

| Metric | Definition |
|---|---|
| `pass@1` | Mean correctness across all attempts |
| `all_k` | **Fraction of cases correct on *every* attempt** |

`all_k` is the headline. An agent right 80% of the time on each of five independent attempts
fully succeeds on about a third of cases — `pass@1` describes a demo, `all_k` describes
something you would put on call.

**Both go in the README, even when they differ — especially when they differ.**

⛔ **Never call `all_k` "pass@k".** They are opposite ends of strictness: pass@k conventionally
means *at least one of k succeeded*; `all_k` means *all k succeeded*. A reader who sees the
familiar name assumes the lenient metric, and **the gate reads weaker than it is.** `pass@1` above
is the conventional metric and is correctly named. *(D-041 — the confusion arrived by comparison
with a published closed-loop eval design that reports pass@k, and it got within one sentence of
these docs.)*

> From [`tracebench`](https://github.com/sandeepyadav1478/tracebench). Cite it.

---

## 3. Escalation F1

`escalate=True` is the positive class, over the labelled cases:

| | Should escalate | Should not |
|---|---|---|
| **Did** | TP | FP — cried wolf |
| **Did not** | FN — acted on a guess | TN |

**Both errors are real and they are not symmetric.** An FN means the agent confidently
recommended an action on an incident whose cause was undetermined. Report precision and
recall separately as well as F1. **Promotion gates on F1; the split is what tells you which way
a version moved**, and two versions with the same F1 can be opposite kinds of wrong.

⚠️ This metric only means something because 2–3 of 10 cases are `insufficient_evidence`
([docs/01](01-spec.md) §3). **Quote n alongside it, always.**

---

## 4. Cost per correct triage

```
cost_per_correct = sum(ResultMessage.total_cost_usd) / n_correct_attempts
```

**Measured, not computed.** The Agent SDK reports `total_cost_usd` per call, plus a
per-model breakdown carrying `cacheReadInputTokens` — so **tokens × list price would be wrong,
and wrong in the flattering direction**, because prompt caching is not in the list price.

🔴 **But it was not billed.** The runs go through the Claude Code subscription, so the honest
sentence is: *"what the run would have cost at API list prices — it came out of a subscription
quota, not an invoice."* Both halves are load-bearing. ⚠️ Record the **model id** next to it —
that comes from the run and is what distinguishes the three paths; `provider` is a config label
(D-033), and `"auth": "subscription"` is a precondition `touchstone doctor` asserts.

**The denominator is the design choice.** Cost per *attempt* rewards an agent that gives up
quickly. Cost per *correct* triage is the unit an operator actually has — and an agent that
is cheap and wrong scores badly, which is right.

⛔ **Void attempts are in neither term.** A 429 (`is_error` with `api_error_status`) means the
attempt did not happen; counting its cost or its failure would let a quota limit look like a
regression (D-015).

---

## 5. The judged dimension — explanation quality

`arize-phoenix-evals` (D-020), **on Cerebras — never on the Claude quota** (D-016). **Its
result is written back as an annotation on the span it judged**, so even the judged dimension
is read from the same substrate as everything else.

- Runs on `verdict.reasoning`: is the explanation supported by evidence the agent actually
  retrieved? (Cross-check the tool spans — a reason citing a metric it never fetched is
  a fabrication, and **that check is mechanical, not judged.**)
- ⛔ **Never gates promotion.** Reported beside the others, in its own column. 🆕 **And since
  D-045 that is a test rather than this sentence** — the fields live inside
  §6's `diagnostics` object and `compare.py` is asserted never to read it.
- 🔴 **Built at P2.6a, not in phase 1** (DEF-009). This section specified the judge
  in full while no roadmap row built it, for as long as it has existed. **The placement is the
  finding:** a metric that cannot gate cannot block the loop, so it comes *after* the gate it is not
  part of.
- ⚠️ **Ceiling: a smaller judge is a weaker judge.** State it, and state which model. The
  honest framing is the interesting one — *"the quota goes to the thing being measured, not to
  a metric that cannot block anything"* — and it is only honest if the trade is named.

**The evidence cross-check is the better half of this section** and it needs no judge at
all: the reasoning names a metric, the spans say whether it was fetched. **A hallucinated
citation is detectable structurally.**

### The rubric, and the three things recorded with every score (D-041)

The criteria are fixed, written down, and scored by an LLM on a **declared** model. A score
missing any of these is not reportable:

| Recorded | Why |
|---|---|
| `judge_model` | A rubric score whose judge is not on the record is a number with no provenance. §6 already carries `judge: {provider, model}` — D-041 makes it **required**, not illustrative |
| `rubric_hash` | **The rubric is part of the measurement.** Edit a criterion and every past rubric score becomes a different claim — the same argument [docs/09](09-schemas.md) §5 makes about `truth.json` |
| `criterion_1_agreement` | The calibration, below |

🎯 **Criterion 1 is deliberately a duplicate of the mechanical check above**, and that is what
makes the rest of the rubric safe to read. The cross-check answers *"does the reasoning cite a
metric the spans say was never fetched"* structurally, with no model. Criterion 1 asks the judge
the same question — so **the agreement rate between them is the judge's measured error rate on
this corpus**, computed on every run, against an answer that is already known.

⛔ **Criteria 2–4 are not reportable on a run whose criterion-1 agreement is not also reported.**
Not because they are wrong — because with no human anywhere in this loop (D-040), nothing else in
the system can tell you whether they are right.

### ⛔ Two gates that call the same judge are one gate

A gate stack's strength is the number of **uncorrelated** failure modes in it, never the number of
rows in the table. Four layers here are independent, and the reason is nameable for each:

| Layer | Cannot fail the way the others do |
|---|---|
| The invariants ([docs/01](01-spec.md) §6) | No model call at all — it cannot hallucinate |
| The evidence cross-check, above | Structural: the span says fetched, or it does not |
| The deterministic scorer (§1) | Exact match on `root_cause_id` + `affected_service` |
| The promotion conditions ([docs/02](02-promotion.md) §1) | Arithmetic over the three above |

**The rubric is a fifth entry but not a fifth layer** — it shares its model with any other judged
check, so they fail together. ⚠️ **A list of seven gates that share one judge is a single point of
failure wearing a table**, and counting them separately is how a gate stack gets impressive
without getting stronger.

---

## 5a. The router — measured, never gated (D-042)

**The supervisor is a router and nothing scored it.** It picks the next specialist, `next` is on
every supervisor span ([docs/04](04-observability.md) §2), and no metric read it — so **a failing
version could not be attributed to *routed wrong* versus *synthesised wrong*.** That is a hole in
the one thing this project sells.

It closes with **no judge and no labeller**, because the answer is already computed three times
over: [docs/01](01-spec.md) §3 gives each root cause its distinguishing evidence,
[docs/03](03-agent-and-tools.md) §1 assigns the tools to the specialists, and
[docs/02](02-promotion.md) §2's mine pre-check already tests *"signal present and fetchable"* — and
then throws the answer away. So `required_specialist` is **planted in `truth.json` by the
generator**, and router precision/recall per specialist is exact match against `next`. Invariant 1
is untouched: the agent never reads `truth.json`; only the scorer does.

⛔ **It never becomes a fifth promotion condition.** A router metric measures *which mechanism*
produced an answer, and gating on a mechanism forbids a version that reaches the right answer a
different way — the opposite of what the version table is for. It is a reported column, like the
judged one, for the same reason — and since D-045 it sits inside §6's
`diagnostics` object, where a test enforces what this paragraph asserts.

🔴 **The field has a deadline, and it is the reason this is not a phase-2 item.** `truth.json` is
inside `benchmark_hash` byte for byte ([docs/09](09-schemas.md) §5), so adding a key to it after
the benchmark freezes is **a benchmark version bump that orphans every past score.** It costs one
key in `generate.py` (P1.2) and is expensive at every later moment. ⚠️ **It is inert at v1** —
D-038 makes v1 the synthesizer alone, with no supervisor to route — and that is fine.

---

## 6. The results file

`results/v4.json` — every number in the README comes from one of these.

```json
{
  "version": "v4",
  "benchmark_hash": "9f2a1c…",
  "benchmark_version": "v2",
  "regression_version": "v7",
  "runbook_hash": "c41e7b…",
  "k": 3,
  "max_hops": 6,                                        // ⛔ null at v1 — no supervisor (D-038)
  "model": "⟨the model_usage key, from the run — D-033⟩",
  "provider": "⟨subscription | cerebras | ollama — from config; the model id is the evidence⟩",
  "auth": "subscription",
  "aggregate": {
    "correct": 0.0, "all_k": 0.0, "pass_at_1": 0.0,
    "escalation": {"precision": 0.0, "recall": 0.0, "f1": 0.0},
    "cost_per_correct_usd": 0.0, "tool_calls_mean": 0.0, "p95_latency_s": 0.0,
    "budget_exceeded": 0, "hops_exhausted": 0, "parse_failures": 0, "void_attempts": 0
  },
  "cases": [{"id": "inc-001", "correct_k": 5, "attempts": [...]}],   // attempt record: docs/09 §6

  // ⛔ compare.py NEVER reads inside this object, and one test proves it (D-045).
  //    Everything a promotion depends on is above this line.
  "diagnostics": {
    "judge": {"provider": "cerebras", "model": "⟨…⟩",         // ⛔ required, not illustrative (D-041)
              "rubric_hash": "7d13ae…"},
    "criterion_1_agreement": 0.0,                             // the judge's measured error rate (D-041)
    "explanation_quality": {"criterion_2": 0.0, "criterion_3": 0.0, "criterion_4": 0.0},
    "router": {"macro_f1": 0.0,                               // vs required_specialist (D-042)
               "per_specialist": {"timeline": {"precision": 0.0, "recall": 0.0}}}
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
files ([docs/02](02-promotion.md) §2.6). Per-attempt records and the four `status` values:
[docs/09](09-schemas.md) §6.

🎯 **`diagnostics` is a boundary, not a heading (D-045).** Both things inside it are opinions about
*how* an answer was produced — a judge's read of the reasoning, and which specialist the router
picked — and §5 and §5a each promise, in prose, never to gate on them. **A promise in prose is
worth what the next reader knows about it.** So the fields move inside one named object and
`test_compare_ignores_diagnostics` asserts that perturbing **every value in it** leaves the
promotion decision byte-identical. ⚠️ **The point is not that the judge is trustworthy. It is that
the gate cannot be affected by whether it is** — the same construction that keeps `truth.json` from
the agent by a directory boundary rather than by an instruction.

⚠️ **`max_hops` is here because it is part of the candidate's identity, not because it is
interesting** — D-013 makes a candidate `(graph, prompts, parameters, provider, model)`, and two
rows that differed on the bound while claiming to differ on the graph would be an unattributable
diff. It is config-sourced, like `provider` and unlike `model` (D-039), and falsifiable against
the run anyway: **no attempt can report `hops` above it.**

⛔ **`hops_exhausted` counts the attempts that stopped because the ceiling fired, not because the
supervisor emitted `done`** — the last `touchstone.node.supervisor` span named a specialist and the
synthesizer ran regardless. Scored attempts only; a `void` run stopped for a quota, not a bound.
**It is diagnostic and it is not a fifth promotion axis** — condition 3's four are closed (§1 of
[docs/02](02-promotion.md)). ⚠️ **It only catches the bound being too *small*.** Too large is a
supervisor that wanders, and that already lands on `cost_per_correct_usd`, which *is* a promotion
metric — so the two failure directions have separate detectors and neither needs a new one.

⚠️ **`runbook_hash` is separate from `benchmark_hash` because editing a runbook changes v3's
score and nothing else would record it.** The runbooks are not cases, so they are not in the
benchmark digest — but retrieval is a versioned capability, and a corpus that changed silently
between two rows would be indistinguishable from the agent improving.

⛔ **`aggregate` covers the benchmark and nothing else, and the regression block carries no
aggregate at all.** That asymmetry is deliberate and it is the whole reason the suite can grow
(D-024): **an average over a case set that changes between runs is not comparable to itself**,
so the regression tier reports counts and a fail list instead. `locked_failed` non-empty blocks
the promotion; `newly_locked` names the cases this run just locked shut.

⚠️ **Never put a regression pass rate in the version table.** It would move for two reasons at
once — the agent changed, and the denominator changed — and a ratio whose denominator moves
between rows is not comparable down the column, which is the only thing that table is for.

---

## 7. What is deliberately not measured

- ⛔ **MTTR.** No humans, no baseline, no real incidents. **The most tempting number here and
  the least defensible.**
- ⛔ **Anything against a human responder.** There is no comparison group.
- ⛔ **Answer "helpfulness" as a headline.** A judge scoring vibes is what this design exists
  to avoid; it appears once, in §5, clearly bounded.
