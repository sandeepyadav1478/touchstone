# touchstone

**An eval-repair loop for agentic systems.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](pyproject.toml)
[![Status: in progress](https://img.shields.io/badge/status-in%20progress-orange.svg)](#status)

| | |
|---|---|
| **The problem** | An eval is wrong in two directions: it misses real failures, and it refuses correct fixes |
| **What it does** | Reads failing traces → mines them into eval cases → gates every candidate before it joins the suite |
| **The invariant** | ⛔ Nothing enters the suite except through a gate with **no model in it** |
| **The specimen** | [τ²-bench](https://github.com/sierra-research/tau2-bench) retail (MIT) — 114 customer-service tasks, scorer has no model in it. Deliberately someone else's: a project that owns both the agent and the answer key can improve either one, and you cannot tell from outside which it did |

## Status

| | |
|---|---|
| Implemented | `doctor`, `run`, `score` |
| Ever executed | ⛔ **`doctor` only** — `run` spends quota |
| Specified, not built | the loop, the gauntlet, the rest of the CLI |
| Complete | the docs, and the structural diagrams that gate implementation |
| Deferred | comparing versions — a comparator needs a second version and there isn't one |
| **The claim it is built to make** | **precision and recall** — *the gate fires on these traces and is silent on those*. ⛔ Not *the gate made the agent better* |

## The loop

```
one failing trace  →  up to MAX_ATTEMPTS attempts  →  a candidate eval case, or a recorded refusal
```

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

Orange decides · blue verifies · grey is where a trace ends up. **Three agents, and never a fourth.**

- **router** — is this trace worth mining? What it skips becomes the control set, which makes it the expensive half of the design.
- **curator** — which rule broke, and what should the predicate say. Always against the suite that already exists.
- **critic** — bounces, hands over, or gives up. The loop's decision point, and the only thing that judges the curator.

🔴 **Inside the loop there is no mechanical gate at all — every branch is a model's.** That is
deliberate, and it is why the last boundary matters: ⛔ **no orange box clears anything.** The
gauntlet is three boolean checks with no model in them, and nothing reaches the suite around it.

📐 **Detail:** [docs/10](docs/10-loop.md) — the router's four criteria, the critic's two tools, the
loop's four rules. [docs/02](docs/02-gates.md) — the gauntlet's three gates and their yields.
[`diagrams/loop.png`](diagrams/loop.png) is the gate artifact and **wins if any of them disagree.**

## Why the specimen is someone else's

τ²'s `DB` check replays a task's gold actions on a fresh environment and diffs the end state. Any
path reaching an equivalent state passes — **so it is blind to how that state was reached.**

```
an agent skips a required confirmation
  and still writes the correct row      →  DB == 1   (passes)

of the 1,712 retail simulations τ² ships:
  371  pass DB and fail an action check →  invisible to a `DB == 0` selector
```

🔴 **A predicate correctly catching that violation would be thrown out as a false positive, by an
answer key that was itself wrong.** A broken eval does not just miss failures; it refuses the fix —
which is why the miner reads three signals and not one, and why the specimen has to be a third
party's. ⚠️ The reading is *blind to process*, **never** *the benchmark is broken*: grading final
state is correct for a gate and wrong for a selector. Derivation, corpus and both population
splits: [docs/02](docs/02-gates.md).

## Quick start

```bash
git clone git@github.com:sandeepyadav1478/touchstone.git && cd touchstone
uv sync
uv run touchstone doctor     # asserts ANTHROPIC_API_KEY is *absent* — if it is set,
                             # runs quietly bill an API account, not the subscription
uv run touchstone run v1     # the frozen ten through τ², k=3
uv run touchstone score v1   # → results/v1.json, no model call
```

| | |
|---|---|
| `PATH` | `uv sync` does not install the entry point — use `uv run touchstone …`, or activate `.venv` first |
| `TAU2_DATA_DIR` | `run` needs it, and writes into **that** tree rather than this one. `doctor` tells you whether it resolves |
| the rest of the CLI | specified in [docs/06](docs/06-api.md), **not implemented** |
| models | Claude via [`claude-agent-sdk`](https://github.com/anthropics/claude-agent-sdk-python), which inherits the `claude` CLI's login — a **subscription rather than a metered API key**, which is what makes k runs per task affordable. ⛔ **Anthropic only, in every role**; five roles pinned separately ([docs/00](docs/00-stack.md)) |

## Limits

⚠️ **Read this before quoting any number this repo produces.** These are properties of the
**design**, so they hold whether or not a run has happened. Reasoning: [docs/05](docs/05-scoring.md).

| limit | what it does to a number |
|---|---|
| 🔴 **Nothing here has been run by this project** | The traces are someone else's. A gate that fires on their failures is not shown to fire on ours |
| **The customer is a language model** | A failure τ²'s user simulator causes is charged to the agent, and the corpus was already run, so we cannot measure its fabrication rate ourselves |
| **Enforcement has never run live** | Replay only. ⚠️ *Wired but never seen to fire* reads exactly like *works* |
| **The gate is a component, not the reward** | Gates on `reward_breakdown["DB"]`; the composite adds an LLM-judged `NL_ASSERTION` on 112 of 114 tasks. ⛔ Different measurements |
| **The agent does not learn** | No training, no weights, nothing carried between sessions. ⛔ *"It improves itself"* fuses two loops — **what iterates is the ruler** |
| 🔴 **A run covers ten of 114 tasks** | Frozen and hash-recorded so it cannot be re-sampled to flatter a result, and still a tenth of the exam. ⛔ **Not a τ²-bench retail score** |
| **Nothing compares two versions** | `compare`, the run record and the version table are unbuilt. A comparator with no second operand is scaffolding |
| **A benchmark task is cleaner than a ticket** | Gold actions known, small database, a right answer — the reward is an **upper bound** on a harder problem |

## Documentation

| Doc | What it covers |
|---|---|
| [00-stack](docs/00-stack.md) | Every dependency pinned and why, the five model pins, `touchstone doctor` |
| [01-spec](docs/01-spec.md) | The τ² task model, what a case is, the benchmark manifest, the live invariants |
| [02-gates](docs/02-gates.md) | The gauntlet's three gates, the corpus and its splits, the acceptance rule, case provenance |
| [03-agent-and-tools](docs/03-agent-and-tools.md) | The adapter at the model seam, what we may and may not change about the τ² agent |
| [04-observability](docs/04-observability.md) | Span schema, OpenInference conventions, why the scorer reads spans |
| [05-scoring](docs/05-scoring.md) | Reward, `pass^k`, cost per success, and why a judge can never gate |
| [06-api](docs/06-api.md) | CLI, HTTP surface, compose |
| [07-diagrams](docs/07-diagrams.md) | The gate: no code before an approved structural diagram |
| [08-memory](docs/08-memory.md) | Where agent memory legitimately goes, and the anchoring failure it is planted to catch |
| [09-schemas](docs/09-schemas.md) | Every remaining type, the `benchmark_hash` algorithm, the file map, prompt and tool contracts |
| [10-loop](docs/10-loop.md) | 🆕 The three agents, the critic's two tools, the loop's four rules |
| [diagrams/](diagrams/README.md) | The structural flowchart and the run sequence |

⚠️ **The docs specify the deferred comparison half in the present tense, deliberately** — they
describe the design that half revives to, not code that runs. **Working files:** `DECISIONS.md`,
`DEFECTS.md` and `ROADMAP.md` are local by design and not in this repository, which is why `D-084`
and the like are cited in backticks and never as links.

## Prior work this builds on

| | |
|---|---|
| [τ²-bench](https://github.com/sierra-research/tau2-bench) (MIT) | The specimen — corpus, environment, evaluator. **We drive it; we do not fork it.** Pinned at commit `a2c024725189`, ⛔ not at `1.0.1`, which names two different trees |
| [`tracebench`](https://github.com/sandeepyadav1478/tracebench) | Reliability over OTel spans; where the `pass^k` framing came from |
| [`evalloop`](https://github.com/sandeepyadav1478/evalloop) | Mining eval sets from traces, and the health guard that refuses to report drift from a dead window |

## Citation

Cite it as software, **and state the commit** — the design is under active revision. ⛔ **If you use
anything measured here, cite τ²-bench too:** the corpus, the environment and the evaluator are
theirs, and every number on this page derives from simulations they produced and shipped.

<details>
<summary>BibTeX — touchstone, τ²-bench, τ-bench</summary>

```bibtex
@software{yadav2026touchstone,
  author  = {Yadav, Sandeep},
  title   = {touchstone: an eval-repair loop for agentic systems},
  year    = {2026},
  url     = {https://github.com/sandeepyadav1478/touchstone},
  license = {MIT},
  note    = {Work in progress; cite the commit you read}
}

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

</details>

## License

MIT. See [LICENSE](LICENSE).
