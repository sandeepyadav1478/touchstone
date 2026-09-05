# 10 — The loop

The mining loop: what each agent decides, what the critic may call, and the rules the graph holds
the agents to. The gauntlet that stands downstream of it is [docs/02](02-gates.md); this file stops
at the handover.

```
one failing trace  →  up to MAX_ATTEMPTS attempts  →  a candidate eval case, or a recorded refusal
```

⛔ **Three agents, and never a fourth.** The summary is on the [README](../README.md); the gate
artifact is [`diagrams/loop.png`](../diagrams/loop.png), and it wins if any of the three disagree.

## §1 The three agents

| agent | asks | and the catch |
|---|---|---|
| **router** | Is this trace worth mining? Four criteria (`D-086` §B): **anomalous** · maps to a **written rule** · failure visible in the **process**, not just the end state · **specific** enough to write a predicate over | 🔴 **The expensive half of the design.** What it skips becomes the control set a candidate must stay silent on. Criterion 1 duplicates τ²'s own three signals and is **not editable**, so agreement with the 778/934 answer key (`D-108`) **is** the router's measured error rate — ⛔ no result from this loop is reportable without that figure. If it comes back poor, the rubric drops to a diagnostic and selection reverts to mechanical |
| **curator** | Which rule broke, and what should the predicate say? | ⛔ **Against the suite that already exists, never in a vacuum** (`D-087`). A rule already gated is not worth mining twice, so an exact check runs the cleared predicates against the trace first, and the suite index goes into the prompt — two cases cannot encode one rule in different words |
| **critic** | Bounce, hand over, or give up? | The loop's **decision point** (`D-086`), and the only thing that judges the curator's call. It reads the candidate, **may** call `run_predicate`, and chooses. **The run is a choice, not a step** (`D-085` §F): a candidate that quotes a task id is refused on the reading alone, and the attempt it would have cost is still there for one worth testing |

The **curator** is the centre of gravity — it decides whether a failure is worth an eval at all,
which rule it broke, and what the predicate should say. The **critic** is the only thing that judges
that call.

## §2 The critic's two tools, and nobody else holds either

They exist for one reason between them (`D-085`, `D-089`): ⛔ **the graph reads a recorded call,
never a model's account of one.**

| tool | hands back | why it is shaped this way |
|---|---|---|
| `run_predicate` | fired at the trace and at the control set, with what happened | The loop's only mechanical step, and ⛔ **under `D-086` it is no longer a gate.** It supplies the evidence; the critic supplies the decision |
| `attempt_budget` | keep going, or exit now | The **only** reader of `MAX_ATTEMPTS`. Named for the job rather than the consequence (`D-092`). ⛔ The critic never counts attempts itself and is **never told the number in a prompt** — a number in a prompt is a word, and it does not change when the config does |

`attempt_budget` also records a give-up, and **may refuse one**: `D-082` wants at least one
`run_predicate` result behind every `unmineable`, and this is the moment that check can fire.
⚠️ **Refusing and terminating are different verbs** — a refused give-up costs an attempt and never
buys one.

## §3 The four rules the loop holds itself to

- **A bounce carries the specific bad finding**, never *"this seems weak"*. A vague objection costs
  one attempt and teaches the curator nothing.
- **Giving up is a result, not an error.** *The agent was not smart enough* has no rule to
  translate, and a miner that has never given up has never been pointed at a failure it should
  refuse. 🔴 **A model with a give-up button will press it** — a correct refusal and a lazy one
  produce the identical artefact, so the `unmineable` rate is watched against the router's agreement
  number rather than trusted on its own (`D-089` §D).
- **A tool cannot break a loop.** It returns to its caller, so the break is the graph's conditional
  edge placed *after* the tool node, calling the same `attempts_exhausted()` the tool calls. Two
  places that know the cap are two places that can disagree about it (`D-091`); putting the edge
  after the tool rather than after the critic also saves a model turn spent repeating back what the
  tool just said (`D-093`).
- **Every mined trace carries an `exit_reason`** — `handed_over`, `budget_exhausted` or `gave_up` —
  written by the edge, because the edge is what decided. ⚠️ **A rate you cannot decompose is not a
  signal**: without the split, a cap-exhausted trace and a critic that quit at attempt 2 look
  identical.

**Flags any agent raises land in the MLflow span**, and ⛔ **the loop does not branch on them** — a
loop that branches on a flag lets an agent extend its own run by raising one.

**`force-terminate` is a safety net, not an outcome** (`D-094`). It fires only when an agent is told
to exit and continues anyway, so ⛔ **it firing at all is a bug report against a prompt.**

## §4 Why there is no mechanical gate inside the loop

🔴 **Every branch in the loop is a model's, and that is deliberate.** Repeated argue-run-revise puts
**more** reasoning on one trace than a single test can (`D-087` §E).

⚠️ **But effort is not correctness.** A loop can iterate its way to a confident wrong answer, and
nothing inside it can tell. That is what the last boundary is for, and it is untouched:

⛔ **Nothing enters the suite without clearing the gauntlet** — `reproducible`, `distinct`,
`justified`, three boolean checks with no model in them and nothing to prompt (`D-084`). The
derivation, the yields and the two tiers are [docs/02](02-gates.md).

⚠️ **The gauntlet is backlog by dependency, not by choice.** It runs on a *finished candidate* and
the loop is what produces one, so its input does not exist yet — ⛔ **it cannot be built early even
if you want to.** Holding it there is safe exactly as long as nothing is being cleared into the
suite.
