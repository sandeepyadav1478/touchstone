# docs/

Eleven documents and the diagram set. ⚠️ **Specification, phase 0** — they describe the design.
`doctor`, `run` and `score` are implemented; ⛔ **only `doctor` has ever been executed.**

| Doc | What it covers |
|---|---|
| [00-stack](00-stack.md) | Every dependency pinned and why, the five model pins, `touchstone doctor` |
| [01-spec](01-spec.md) | The τ² task model, what a case is, the benchmark manifest, the live invariants |
| [02-gates](02-gates.md) | The gauntlet's three gates, the corpus and its splits, the acceptance rule, case provenance |
| [03-agent-and-tools](03-agent-and-tools.md) | The adapter at the model seam, what we may and may not change about the τ² agent |
| [04-observability](04-observability.md) | Span schema, OpenInference conventions, why the scorer reads spans |
| [05-scoring](05-scoring.md) | Reward, `pass^k`, cost per success, and why a judge can never gate |
| [06-api](06-api.md) | CLI, HTTP surface, compose |
| [07-diagrams](07-diagrams.md) | The gate: no code before an approved structural diagram |
| [08-memory](08-memory.md) | Where agent memory legitimately goes, and the anchoring failure it is planted to catch |
| [09-schemas](09-schemas.md) | Every remaining type, the `benchmark_hash` algorithm, the file map, prompt and tool contracts |
| [10-loop](10-loop.md) | The three agents, the critic's two tools, the loop's four rules |
| [../diagrams/](../diagrams/README.md) | The structural flowchart and the run sequence — **the gate artifact, and it wins if a doc disagrees** |

⚠️ **The deferred comparison half is specified in the present tense, deliberately** — those
sections describe the design it revives to, not code that runs.

## Limits

⚠️ **Read this before quoting any number this repo produces.** These are properties of the
**design**, so they hold whether or not a run has happened. Reasoning: [05-scoring](05-scoring.md).

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
| ⛔ **No distributed tracing claim** | One service, one machine ([04-observability](04-observability.md) §7) |
| ⛔ **No auth on the HTTP surface** | Nothing served is worth protecting; the scope was chosen rather than run out of ([06-api](06-api.md) §4) |
| ⚠️ **The tasks are public** | A model may have seen them in training — a ceiling on the absolute number, not on a version-to-version delta ([03-agent-and-tools](03-agent-and-tools.md) §3) |

## Working files

`DECISIONS.md`, `DEFECTS.md` and `ROADMAP.md` are local by design and **not in this repository** —
the decision register, the defect log and the phase plan. That is why `D-084` and the like are
cited in backticks throughout and never as links; `scripts/check-links.py` fails the build on a
link to one of them.
