# 01 — Spec: the case, the run, the reward

> ⚠️ **Specification, phase 0.** This describes the design; it is not a description of shipped code. `touchstone doctor` is the only implemented command today — see the [README](../README.md) for what runs and what does not. ⛔ **And the specimen changed under it.** D-062 replaced the self-authored infra-RCA corpus with **τ²-bench retail** — 114 tasks, MIT, deterministic DB-state-diff reward. Where this file still says *incident*, *root cause*, *affected service* or *escalate*, it is describing the **archived** specimen (branch `incident-specimen`), not what touchstone measures. **The loop is unchanged; that is the claim the swap was for.**

**There is no corpus to write.** That is the largest single consequence of D-062, and it is
worth stating before anything else: this file used to open with *"write this file's code first,
before any agent exists"*, because the answer key was ours to build. **It is not ours any more.**
The 114 retail tasks, their gold action sequences and their reward machinery all ship in
`tau2-bench`, MIT, and touchstone reads them without writing a line of them.

⚠️ **That is a smaller repo and a stronger claim at the same time.** A self-authored corpus
scored by its own author is a benchmark nobody outside can check; a published one has a
leaderboard to sit beside. What we gave up is control over the specimen — see §4, which is now
mostly a record of what was cut.

---

## 1. The shape of the problem

A **case** is one τ² task: a customer with a goal, a policy the agent must follow, and a
database the agent can change. A run is a conversation between three parties, and the score is
what the database looks like afterwards.

```
  Task ──▶ [ user simulator ] ⇄ [ agent ⇄ 16 retail tools ] ──▶ final DB
                                                                  │
  gold `actions` replayed on a fresh env ──────────────────────▶ diffed
```

**The domain is online retail** — 50 products, 500 users, 1,000 orders
(`data/tau2/domains/retail/db.json`). Cancel a pending order, exchange delivered items, change
an address, modify a payment method. ⛔ **Nothing about it is specific to any employer**, which
is the same property the archived specimen had and the reason either one could stand in for the
other. **The domain is a specimen; the loop is the product.**

⚠️ **The user is a model, and that is the load-bearing limitation of the whole design.** τ²'s
user simulator plays the customer, so every case is a conversation with something that can
misremember its own goal. It is pinned (`claude-haiku-4-5-20251001`, D-067) precisely so that it
is *apparatus* rather than a variable — a frozen instrument that is imperfect in the same way
for every version. **A pinned wrong ruler still measures differences.**

---

## 2. Domain model — and touchstone defines none of it

⛔ **`src/touchstone/domain.py` does not exist and will not be written.** Every type below is
upstream, in `tau2-bench`, and the file:line is the citation.

| Type | Where | What it carries |
|---|---|---|
| `Task` | `data_model/tasks.py:560` | `id`, `description`, `user_scenario`, `ticket`, `initial_state`, `evaluation_criteria` |
| `UserScenario` | `data_model/tasks.py:52` | the persona and instructions handed to the simulator — **the agent never sees it** |
| `EvaluationCriteria` | `data_model/tasks.py:366` | the answer key — §3 |
| `Action` | `data_model/tasks.py:116` | one gold tool call: `name`, `arguments`, `requestor`, `compare_args` |
| `RewardInfo` | `data_model/simulation.py:1073` | `reward`, `reward_basis`, **`reward_breakdown`**, plus the per-check detail |
| `RewardType` | `data_model/tasks.py:237` | **five** members: `DB`, `ENV_ASSERTION`, `NL_ASSERTION`, `ACTION`, `COMMUNICATE` |
| `TerminationReason` | `data_model/simulation.py:1254` | **ten** members — the mining taxonomy, [docs/02](02-gates.md) §5 |

**What touchstone writes instead** is the thin layer that attaches to those: the adapter at the
`generate()` seam, the gate evaluator, the telemetry, the results file. [docs/09](09-schemas.md)
§9 has the file map.

⚠️ **The old §2 described `Incident`, `Alert`, `GroundTruth` and `Verdict` in Pydantic, and
those models were real work.** They are on branch `incident-specimen`, and the reason to look at
them is not the specimen — it is that the *hidden-answer-key* structure they encode is the same
structure τ² encodes with `evaluation_criteria`, arrived at independently. **That convergence is
the strongest evidence the swap kept the design intact.**

---

## 3. The answer key space

**Not a closed set of eleven classes any more — a per-task list of checks.** τ²'s
`EvaluationCriteria` (`data_model/tasks.py:366`) carries four:

| Field | What it asserts | Model in it? |
|---|---|---|
| `actions` | the gold tool calls, **replayed on a fresh environment**; the resulting DB is diffed against the agent's | none |
| `env_assertions` | `EnvAssertion` calls that must hold on the final environment | none |
| `nl_assertions` | natural-language claims about what the agent said | 🔴 **yes** — a judge |
| `communicate_info` | strings that must appear in some assistant message | none |

**`reward_basis` (`:427`) says which of those actually count**, and it is per task. In retail:
**112 of 114 declare `["DB", "NL_ASSERTION"]`, 2 declare `["DB"]`, and zero declare
`COMMUNICATE`.** `evaluator.py:223` starts the reward at 1.0 and multiplies each declared
component, so **one zeroed component zeroes the reward** — which is why a judge sits inside the
published composite.

⛔ **touchstone gates on `reward_breakdown["DB"]` and never on the composite** (D-069). The
composite is reported beside it, unmodified, so the number stays comparable with the public
leaderboard. [docs/05](05-scoring.md) §1 is the full argument; the one-line version is **the
invariant**: *anything that gates is mechanical, anything with a model in it cannot gate.*

⚠️ **`insufficient_evidence` has no counterpart here, and its argument is worth keeping.** The
old §3 carried a class whose correct answer was *escalate*, because a suite where escalation is
never right and a suite where it always is are both trivially gameable. Retail has
`transfer_to_human_agents` (`domains/retail/tools.py:732`) — but it is `ToolType.GENERIC`,
returns a constant string, is named in **4 of 114 tasks** and contributes to no reward
component. **Escalation F1 was cut on that evidence** ([docs/05](05-scoring.md) §3). The
gameability argument was correct and it now has nothing to measure.

---

## 4. ⛔ The generator — cut by D-062

**This section was ~165 lines: two tiers, a seeded renderer, a frozen manifest, a `history/`
corpus for v5, and a read of three upstream RCA datasets to source realistic shapes.** All of
it is on branch `incident-specimen` at `109c424`. **None of it runs.**

What survives the cut, in one line each:

- **The two-tier split (D-024)** — benchmark cases measure, regression cases gate — is *not*
  specimen-dependent and moves intact onto the 114 tasks. [docs/02](02-gates.md) §4.
- **Invariant 11** — every case carries a `why`, an `added` date and an `origin` — still binds,
  and now applies to *mined* cases rather than generated ones, since mining is the only way a
  case enters. ⚠️ **Case admission is specified and unbuilt until P3.5**, so today the answer is
  *all 114, no selection*, and that is the honest state.
- **The `history/` corpus for v5** is cut twice over: by D-062 with the generator, and by D-030
  with v5 itself.

🔴 **One correction belongs in the record rather than on the branch, because it was published
here and was wrong.** The old §4 said the RCAEval corpus was **MIT** and that its schema was
unreachable. Both are false: it is **CC-BY-4.0**, and it is mirrored on Zenodo where the schema
reads fine. The claim was never load-bearing — the generator did not ship — but a licence
misattribution in a public repo is the class of error that is worst to leave standing, and
"the code was cut anyway" is not a reason to leave it. **A wrong licence is wrong whether or not
anyone acted on it.**

---

## 5. The mutation boundary — where enforce gates

Retail's 16 tools split by `ToolType` (`domains/retail/tools.py`), and the split is not
decoration: `is_tool` defaults `mutates_state` to `tool_type == ToolType.WRITE`
(`environment/toolkit.py:83`), and `Environment._is_mutating_tool()`
(`environment/environment.py:130`) reads it back.

| Type | Count | Tools |
|---|---|---|
| `READ` | 7 | `find_user_id_by_email`, `find_user_id_by_name_zip`, `get_user_details`, `get_order_details`, `get_product_details`, `get_item_details`, `list_all_product_types` |
| `WRITE` | 7 | `cancel_pending_order`, `exchange_delivered_order_items`, `return_delivered_order_items`, `modify_pending_order_address`, `modify_pending_order_items`, `modify_pending_order_payment`, `modify_user_address` |
| `GENERIC` | 2 | `calculate`, `transfer_to_human_agents` |

⛔ **The seven `WRITE` tools are the entire blast radius, and `make_tool_call()`
(`environment/environment.py:158`) is the one place they all pass through.** A gate in
**enforce** mode refuses the call there, *before* it executes — which is the difference from the
archived design, where nothing executed and escalation was a flag on a verdict nobody acted on.
[docs/02](02-gates.md) §2 for the two modes.

⚠️ **`_is_mutating_tool()` falls back to `True` when it cannot resolve a tool** — assume
mutation. That default is upstream's and it is the right one: an unrecognised tool is exactly
when you want the conservative branch.

---

## 6. Invariants

Each one gets a test in `tests/unit/`. **These are the assertions that keep the numbers meaning
what they say.** ⛔ **Numbers are never reused or closed up** — they are cited by number across
`docs/`, so a retired invariant keeps its slot and says why.

| # | Invariant | How it is enforced |
|---|---|---|
| 1 | The agent never sees the answer key | Render the full agent context for all 114 tasks and assert no `evaluation_criteria` or `user_scenario` field appears in it. ⚠️ **Upstream already separates these** — this asserts that *our adapter* did not merge them |
| 2 | ~~Every tool is read-only~~ | ⛔ **Retired by D-062, and it inverts.** Retail has 7 `WRITE` tools and the mutation is the point — it is what the DB diff measures. Its replacement is invariant 15 |
| 3 | Exactly one gate span per run | Span assertion in the run test |
| 4 | ~~Any `recommended_action` ≥ `restart_service` ⟹ `escalate=True`~~ | ⛔ **Retired by D-062** — `recommended_action` was a field on `Verdict`, and there is no `Verdict`. The §5 blast-radius table it walked is now a `ToolType` split upstream reads for itself |
| 5 | ~~Any action ≥ `restart_service` hits an interrupt before executing~~ | ⛔ **Retired by D-040**, before the specimen swap; kept in place for the same reason as the rest |
| 6 | ~~Same seed ⟹ byte-identical incident~~ | ⛔ **Retired by D-062** — nothing is generated. **Determinism did not go away, it moved**: the tasks are a committed JSON file, so invariant 7 covers what this covered |
| 7 | **The task file is never modified** | Hash `data/tau2/domains/retail/tasks.json` in CI. ⛔ **This is the one that replaces the manifest**, and it is stricter than the old version was: it guards a file we do not own, so a silent upstream update is a CI failure rather than a moved goalpost |
| 8 | Correctness never reads prose | The gate takes `reward_breakdown["DB"]` only. Asserted by scoring a run whose every assistant message is garbage but whose DB is correct, and requiring the DB component to be 1.0 |
| 9 | *(v5)* ~~`history/` is disjoint from both tiers~~ | ⛔ **Cut twice** — D-030 cut v5, D-062 cut `history/` |
| 10 | *(v5)* ~~Nothing is ever written to `history/`~~ | ⛔ **Cut twice**, same as 9 |
| 11 | **Every mined case has a non-empty `why`, an `added` date and an `origin`** | CI walks the regression manifest and fails on a blank field. ⛔ **A case nobody can justify does not get to gate anything** — D-024. ⚠️ Vacuous today: D-030 defers admission, so the manifest is empty |
| 12 | **A `locked` regression case only ever became locked by passing** | `locked_at` names a version, and `results/<that version>.json` shows it passing. A lock with no run behind it is a fabricated gate |
| 13 | 🆕 **No specialist's prompt contains another specialist's finding** | Render every `identity` / `catalogue` / `policy` prompt in a full run and assert no other node's finding text appears. ⚠️ **Retired by D-062 and un-retired by D-071** — it was retired because there were no specialists, and there are again ([docs/03](03-agent-and-tools.md) §1). A blackboard lets one node anchor the next, and then a correctness movement is attributable to neither |
| 14 | 🆕 **No two specialist spans overlap in time** | Assert over `touchstone.node.*` span timestamps that exactly one specialist is open at a time (D-026 — a merge order is a hidden variable). ⚠️ **Un-retired by D-071.** Its argument was kept in place for *"the day something does"* fan out: **an orchestration bug wearing the costume of the thing being measured is the worst defect this design can have** — and now something asserts against it |
| 15 | 🆕 **A gate in `shadow` mode never refuses a tool call** | Run the full suite with every gate in shadow and assert `make_tool_call()` returned for every call the agent made. ⛔ **This is what makes shadow data trustworthy**: a shadow gate that quietly changed a run is measuring its own interference. Replaces invariant 2 |
| 16 | 🆕 **The composite reward is reported unmodified** | Assert the results file's `reward_mean` equals what τ²'s own `get_metrics_df` computes over the same simulations. **We gate on a component; we do not get to publish a different headline** — D-069 |

⚠️ **Four of sixteen are retired, two more were cut with v5, and one is vacuous.** The invariants
that died are the ones that asserted over *our generator* — 2, 4, 6 — and they died because the
generator did. The ones that lived, 7, 8, 11 and 12, assert over the boundary between the loop and
whatever it is measuring, which is the part the specimen swap was supposed to leave standing.

🔴 **13 and 14 are back, and how they left is the lesson.** They were retired at D-062 with
*"there are no specialists"* — a true statement about a consequence **nobody had decided**
(D-071). An invariant retired on a side effect is the quietest way for a safety property to
disappear, because the retirement reads as reasoned. ⛔ **Numbers are never reused or closed up**
precisely so that this is recoverable: both kept their slots and their arguments, so restoring
them cost an edit rather than a redesign.

**Invariant 8 is what the headline number means.** Not *"the agent scored 0.8"* but *"the
agent's final database state matched a replayed gold sequence 0.8 of the time"* — prose quality
is a separate, separately reported dimension that gates nothing.

---

## 7. What is deliberately absent

- ⛔ **No corpus of our own.** The 114 tasks are upstream and stay upstream. Vendoring them
  would make touchstone the owner of a benchmark it exists to be scored by.
- ⛔ **No repair of upstream's checks.** `COMMUNICATE`'s substring match carries upstream's own
  `# TODO: This could be improved!` (`evaluator_communicate.py:69`) and **stays unrepaired** —
  fixing it would break comparability with the published leaderboard, which is the whole reason
  for using a published benchmark.
- ⛔ **No real storefront.** The retail DB is a JSON file loaded per run.
- ⛔ **No non-Anthropic models anywhere in the loop.** ollama and Cerebras are reachable from
  this machine and are `touchstone doctor` diagnostics only — **never model sources**.
- ⛔ **No multi-tenancy, no auth, no UI.**
