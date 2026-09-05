# touchstone

**An eval-repair loop for agentic systems.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](pyproject.toml)
[![Status: in progress](https://img.shields.io/badge/status-in%20progress-orange.svg)](#status)

An agent is only as good as the evals judging it, and an eval can be wrong in two directions: it
misses real failures, and it refuses correct fixes. touchstone reads failing traces, mines them
into new eval cases, and puts every candidate through mechanical gates before it can join the
suite.

The loop is the product. The domain is a specimen, and it is deliberately someone else's —
[τ²-bench](https://github.com/sierra-research/tau2-bench) retail (MIT), 114 customer-service tasks
with a scorer that has no model in it. A project that owns both the agent and the answer key can
improve either one, and you cannot tell from the outside which it did.

## Status

In progress. `doctor`, `run` and `score` are implemented, and **only `doctor` has ever been
executed** — `run` spends quota. The loop itself is specified and not built. The docs and the
structural diagrams that gate implementation are complete.

Comparing candidate versions is deferred, because a comparator needs a second version and there
isn't one. The claim this repo is built to make is **precision and recall** — *the gate fires on
these traces and is silent on those* — not *the gate made the agent better*.

## The loop

One failing trace in. Up to `MAX_ATTEMPTS` attempts. Out comes either a candidate eval case or a
recorded refusal. Three agents, and never a fourth.

```mermaid
flowchart LR
  T(["a failing<br/>trace"]) --> R["<b>router</b><br/>worth mining?<br/>4 criteria"]
  R --> CU["<b>curator</b><br/>which rule broke?<br/>rule → predicate"]
  CU <-.-> CR["<b>critic</b><br/>judges it,<br/>then decides"]
  CR <-.-> RP{{"<b>run_predicate</b><br/>fires on the trace, silent on the control set<br/>evidence, not a verdict"}}
  CR <-.->|"may I keep going?"| BUDGET{{"<b>attempt_budget</b><br/>the one reader of MAX_ATTEMPTS<br/>its reply is the exit"}}
  BUDGET -.->|"only if an agent ignores the exit"| U(["force-terminate<br/><i>expected: never</i>"])
  CR -->|"hands over"| AD{{"<b>the gauntlet</b> — three gates, all must hold<br/>reproducible · distinct · justified<br/>no model, ever"}}
  AD --> S(["regression<br/>suite"])

  classDef m fill:#f9731622,stroke:#ea580c,stroke-width:1.5px,color:#ea580c
  classDef d fill:#3b82f622,stroke:#2563eb,stroke-width:1.5px,color:#3b82f6
  classDef io fill:#94a3b81a,stroke:#94a3b8,stroke-width:1.2px,color:#94a3b8
  class R,CU,CR m
  class RP,BUDGET,AD d
  class T,S,U io
```

Orange decides, blue verifies, grey is where a trace ends up. **No orange box clears anything.**

**The router** asks whether a trace is worth mining at all, on four criteria: is it anomalous, does
it map to a written rule, is the failure visible in the process rather than only in the end state,
and is it specific enough to write a predicate over. This is the expensive half of the design —
whatever the router skips becomes the control set a candidate must stay silent on. Its first
criterion duplicates τ²'s own signals and is not editable, so agreement with that answer key is a
measurable error rate for the router, and no result from this loop is reportable without it.

**The curator** decides whether the failure is worth an eval, which rule it broke, and what the
predicate should say — always against the suite that already exists, never in a vacuum. Cleared
predicates are run against the trace first, and the suite index goes into the prompt, so two cases
cannot encode one rule in different words.

**The critic** is the only thing that judges that call, and it is the loop's decision point. It
reads the candidate, may test it, and chooses: bounce, hand over, or give up. Testing is a choice
rather than a step — a candidate that quotes a task id is refused on the reading alone, and the
attempt it would have cost is still there for one worth testing. A bounce has to carry the specific
finding; *"this seems weak"* costs an attempt and teaches the curator nothing. Giving up is a
result and not an error: *the agent was not smart enough* has no rule to translate, and a miner
that has never given up has never been pointed at a failure it should refuse.

The critic holds two tools and nobody else holds either, for one reason between them: **the graph
reads a recorded call, never a model's account of one.** `run_predicate` fires the candidate at the
trace and at the control set and hands back what happened — evidence, not a verdict.
`attempt_budget` is the only reader of `MAX_ATTEMPTS`; the critic asks whether it may continue and
is never told the number in a prompt, because a number in a prompt is a word and does not change
when the config does. A tool cannot break a loop, so the break is a conditional edge placed after
the tool, calling the same function the tool calls — two places that know the cap are two places
that can disagree about it. The edge writes an `exit_reason` on every trace, because a rate you
cannot decompose is not a signal: a cap-exhausted trace and a critic that quit early look identical
without it.

So inside the loop there is no mechanical gate at all — every branch is a model's. That is
deliberate; repeated argue-run-revise puts more reasoning on one trace than a single test can. But
effort is not correctness. A loop can iterate its way to a confident wrong answer and nothing
inside it can tell, which is what the last boundary is for.

### The gauntlet

**Nothing enters the suite except through a mechanical gate.** Three boolean checks, downstream of
the loop, with no model in them and nothing to prompt. Each refuses a specific way a bad case
poisons a suite you have to trust for months.

| gate | the check | what it refuses |
|---|---|---|
| **reproducible** | the case fails **all four** of τ²'s trials, not some — and those trials carry four distinct seeds, so they are four draws rather than one copied | A flaky failure. Clear a three-of-four case and the suite fails your agent at random, and you debug a regression that never happened. It clears **34 of the 456** (file, task) pairs in the full shipped retail set — 7.5%, and that yield is the honest cost of the rule |
| **distinct** | no two cases share a `task_id`. A failure-signature check sits beside it and records `duplicate_of` rather than refusing | A suite that grows without covering more. The signature half does not refuse because it is a bucketing heuristic with one to two orders of magnitude of error, and a refusal is undoable while a recorded suspicion is not |
| **justified** | `why`, `added` and `origin` are all non-empty | A case nobody can ever delete. Six months on, one fails: real regression, or something mined in a hurry? Without the rule it encodes, when it arrived and which version produced it, you keep it forever |

The gauntlet runs on a finished candidate and the loop is what produces one, so it is backlog by
dependency rather than by choice. That is safe exactly as long as nothing is being cleared into the
suite.

The [flowchart](diagrams/loop.png) in [`diagrams/`](diagrams/README.md) is the gate artifact and
wins if it and the summary above ever disagree. No code lands before an approved structural
diagram.

## Why the specimen is someone else's

τ²'s `DB` check replays a task's gold actions on a fresh environment and diffs the agent's end
state against the result. It is mechanical, and any path reaching an equivalent state passes —
which means it compares final state and is blind to how that state was reached. An agent that skips
a required confirmation and still writes the correct row scores `DB == 1`.

Over the 1,712 simulations τ² ships for retail, **371 sessions pass the `DB` check and fail an
action check**. Selecting on `DB == 0` alone leaves them in the silence set — the population a new
predicate must be quiet on — so a predicate *correctly* catching a confirmation violation would be
thrown out as a false positive, by an answer key that was itself wrong. **A broken eval does not
just miss failures; it refuses the fix.** That is the whole reason the miner reads three signals
instead of one.

The right reading is *blind to process*, not *the benchmark is broken*. Grading final state is
correct for a gate and wrong for a selector, which is why `DB` stays the gating metric while the
miner feeds on the union. One number cannot do both jobs. Full derivation:
[docs/02](docs/02-gates.md).

The corpus is those 1,712 simulations over **107 of retail's 114 tasks** — the ones whose gold
actions are unchanged between the shipped runs and the current task file. The other seven are
excluded rather than repaired, and the two numbers travel together. It is a corpus and never a
baseline: the simulations came from four third-party agents behind a `gpt-4.1` user simulator, and
their scores are quoted nowhere here. It is also a different population from the 456 pairs above,
which span all 114 tasks — the two never divide into each other.

## Quick start

```bash
git clone git@github.com:sandeepyadav1478/touchstone.git && cd touchstone
uv sync
uv run touchstone doctor     # asserts ANTHROPIC_API_KEY is *absent* — if it is set,
                             # runs quietly bill an API account, not the subscription
uv run touchstone run v1     # the frozen ten through τ², k=3
uv run touchstone score v1   # → results/v1.json, no model call
```

`uv sync` does not put `touchstone` on your `PATH`; use `uv run touchstone …` or activate `.venv`
first. `run` needs `TAU2_DATA_DIR` and writes into that tree rather than this one — `doctor` tells
you whether it resolves. The rest of the CLI is specified in [docs/06](docs/06-api.md) and not yet
implemented.

The agent runs on Claude through
[`claude-agent-sdk`](https://github.com/anthropics/claude-agent-sdk-python), which drives the
`claude` CLI as a subprocess and inherits its login, so a run goes through a Claude Code
subscription rather than a metered API key. Running a suite k times per task is the point of this
repo, and that is what makes it affordable. **Anthropic models only, in every role**; five roles
are pinned separately, and every id came from a live call rather than a config file. Manifest:
[docs/00](docs/00-stack.md).

## Limits

Read this before quoting any number this repo produces. These are properties of the design, so they
hold whether or not a run has happened. The full list is in [docs/05](docs/05-scoring.md).

- **Nothing here has been run by this project, and the traces it reasons over are someone else's.**
  A gate that fires on their failures is not thereby shown to fire on ours.
- **The customer is a language model.** τ²'s user side is a simulator, so a failure it causes is
  attributed to the agent unless something measures it — and because the corpus was already run, we
  cannot measure its fabrication rate ourselves.
- **Enforcement is tested by replay and has never run against a live environment.** *Wired but
  never seen to fire* reads exactly like *works*.
- **The gate is a component, not the whole reward.** touchstone gates on `reward_breakdown["DB"]`
  because retail's composite includes an LLM-judged `NL_ASSERTION` on 112 of 114 tasks. Both are
  reported, and a `DB` figure and a composite figure are different measurements.
- **The agent does not learn and carries nothing between sessions.** Nothing trains, fine-tunes or
  updates weights, and agent memory is designed ([docs/08](docs/08-memory.md)) and unbuilt.
  *"It improves itself"* fuses two loops and is false on the half that matters — what iterates is
  the ruler, never the thing being measured.
- **A run covers ten of retail's 114 tasks.** The subset is frozen and recorded with the hash it was
  read at, so it cannot be re-sampled to flatter a result, and it is still a tenth of the exam. A
  number from here is not a τ²-bench retail score.
- **Nothing compares two versions.** `compare`, the run record and the version table are unbuilt,
  because a comparator with no second operand is scaffolding.
- **A benchmark task is cleaner than a real ticket** — gold actions known, small database, a right
  answer. That makes the reward an upper bound on a harder problem. No claim about
  time-to-resolution, ticket volume, or comparison against a human agent.

## Documentation

| Doc | What it covers |
|---|---|
| [docs/00-stack.md](docs/00-stack.md) | Every dependency pinned and why, the five model pins, `touchstone doctor` |
| [docs/01-spec.md](docs/01-spec.md) | The τ² task model, what a case is, the benchmark manifest, the live invariants |
| [docs/02-gates.md](docs/02-gates.md) | The gauntlet's three gates, the two tiers, the acceptance rule, case provenance |
| [docs/03-agent-and-tools.md](docs/03-agent-and-tools.md) | The adapter at the model seam, what we may and may not change about the τ² agent |
| [docs/04-observability.md](docs/04-observability.md) | Span schema, OpenInference conventions, why the scorer reads spans |
| [docs/05-scoring.md](docs/05-scoring.md) | Reward, `pass^k`, cost per success, and why a judge can never gate |
| [docs/06-api.md](docs/06-api.md) | CLI, HTTP surface, compose |
| [docs/07-diagrams.md](docs/07-diagrams.md) | The gate: no code before an approved structural diagram |
| [docs/08-memory.md](docs/08-memory.md) | Where agent memory legitimately goes, and the anchoring failure it is planted to catch |
| [docs/09-schemas.md](docs/09-schemas.md) | Every remaining type, the `benchmark_hash` algorithm, the file map, prompt and tool contracts |
| [diagrams/](diagrams/README.md) | The structural flowchart and the run sequence |

The docs specify the deferred comparison half in the present tense, deliberately: wherever they
reason about comparing a candidate against an incumbent, they describe the design that half revives
to, not code that runs. Nothing was deleted, because the arguments are why each piece is shaped the
way it is.

### Working files

`DECISIONS.md`, `DEFECTS.md` and `ROADMAP.md` are the decision register, the defect log and the
schedule. They are **local by design and not in this repository**, so `D-084` and the like are
cited in backticks and never as links — a link to them would 404 for every reader. The reasoning
that survives is in `docs/`.

## Prior work this builds on

- [τ²-bench](https://github.com/sierra-research/tau2-bench) (MIT) — the specimen: the corpus, the
  environment and the evaluator. We drive it; we do not fork it. Pinned at commit `a2c024725189`,
  not at `1.0.1` — that string names two different trees.
- [`tracebench`](https://github.com/sandeepyadav1478/tracebench) — reliability over OTel spans;
  where the `pass^k` framing came from.
- [`evalloop`](https://github.com/sandeepyadav1478/evalloop) — mining eval sets from traces, and the
  health guard that refuses to report drift from a dead window.

## Citation

If you refer to this work, cite it as software, and state the commit — the design is under active
revision, and what was read at that commit changes what the claim means.

```bibtex
@software{yadav2026touchstone,
  author  = {Yadav, Sandeep},
  title   = {touchstone: an eval-repair loop for agentic systems},
  year    = {2026},
  url     = {https://github.com/sandeepyadav1478/touchstone},
  license = {MIT},
  note    = {Work in progress; cite the commit you read}
}
```

If you use anything measured here, cite τ²-bench too. The corpus, the environment and the evaluator
are theirs, and every number on this page derives from simulations they produced and shipped.

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
