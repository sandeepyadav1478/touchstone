# touchstone

> ⚠️ **The specimen is being replaced — 2026-08-19.** The incident-triage domain described
> below was archived to the [`incident-specimen`](https://github.com/sandeepyadav1478/touchstone/tree/incident-specimen)
> branch at `109c424` and deleted from `main`: `domain.py`, `incidents/`, the frozen
> `suite/benchmark/` and their tests, 1,954 lines. **The loop is unchanged** — frozen
> benchmark, growing regression suite, per-case no-regression — because the loop is the
> project and the domain is only the specimen it operates on. It becomes τ²-bench retail,
> whose corpus is a third party's and whose scorer is a deterministic DB-state diff, so the
> improvement numbers are no longer measured against a corpus we wrote ourselves.
>
> ⛔ **Everything below still describes the archived specimen** until the docs pass lands.
> D-062, D-066.

**A production-incident triage agent that is required to get better.**

Every change to the agent is a *candidate version*. Every candidate is scored against a
frozen benchmark of incidents whose root causes are known. **A candidate is promoted only if it
regresses nothing it previously passed** — average improvement is not enough.

And every failure becomes a permanent case: mined from the trace, admitted by five mechanical
gates with no human in the path, and added to a **regression suite that only grows**. Once a version passes a case, it is locked, and nothing
that breaks it ships again.

A touchstone never changes. That is the whole idea.

```bash
touchstone run   v4                 # triage the suite, k times each, emit spans
touchstone score v4                 # score from the spans, write results/v4.json
touchstone compare v4 --against v3  # per-case verdict → promote or reject
```

> ### ⚠️ Status: phase 0 — specified, not yet built
>
> **What is here now:** the full specification (`docs/00`–`09`), the promotion rule, the
> structural diagram that gates implementation, and `touchstone doctor`, which runs.
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

| version | what changed | correct | all_k(3) | escalation F1 | tool calls | $/correct triage¹ | promoted |
|---|---|---|---|---|---|---|---|
| v1 | baseline — one node, no tools | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ | — |
| v2 | + three specialists behind a supervisor | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ |
| v3 | + runbook retrieval | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ |
| v4 | v3 + a tool-call budget | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ | ⟨…⟩ |

¹ From the Agent SDK's own cache-aware `total_cost_usd` — a real per-call figure, drawn from a
subscription quota rather than billed. **Not an invoice** — see [Limits](#limits).

**The rejections get written up here, next to the table.** When a candidate is refused, this
section gains two sentences: what looked better, which case regressed, and what the trace
showed. A gate that never visibly refuses anything is not a gate, so the refusals are the part
worth reading.

---

## Why the numbers mean something

Most agent demos score themselves with a language model judging their own output. This one
mostly does not need to:

**Every incident in the suite was generated with its root cause planted.** The generator
decides that `billing-api` is failing because a migration dropped an index and the connection
pool is now saturating, then renders the logs, metrics, deploy history and alert text that
such an incident *would* produce. The answer key exists before the agent sees anything.

So the primary metric is **exact match on `root_cause_id`** — no judge, no rubric, no
argument about whether an answer was good enough. A judge appears in exactly one dimension
(explanation quality) and it is named in the results file.

**What this buys, concretely:** a regression is a fact rather than a judgement. If case 07
passes at v2 and fails at v4, CI blocks the promotion — there is nothing to interpret and
nobody to overrule.

**What it costs** is in [Limits](#limits), and it is real: a planted root cause is not an
ambiguous one, and real incidents are ambiguous.

---

## How it works

```
                  ┌──────────── the agent under test ────────────┐
  incident  ──▶   │  supervisor → { logs · metrics · deploys }    │  ──▶  verdict
   (suite)        │      ↓ specialists, LangGraph                 │       + escalate?
                  │  escalate = blast radius > threshold         │
                  └───────────────────┬──────────────────────────┘
                                      │ OpenTelemetry spans
                                      ▼
        run ──▶ score ──▶ compare ──▶ promote ──▶ record        the loop
                  │            ▲
                  │            │  benchmark — frozen, hashed, n=10
                  │            │  ⛔ changing it resets every comparison
                  │            │
                  └─▶ mine ──▶ admission ──▶ regression — grows, never shrinks
                     failures    5 gates,     ✅ adding to it resets nothing
                                 mechanical   🔒 a case locks the first time a
                                                 promoted version passes it
```

⛔ **No human is a step in that picture, and none is a state in the agent.** Nothing pauses for
approval: blast radius sets a scored `escalate` flag, and a mined case is admitted by five
mechanical gates ([docs/02](docs/02-promotion.md) §5) rather than by somebody signing off on a
batch. **People improve this system by rewriting it** — reading traces, changing prompts, adding
cases — which is what everything below is instrumented for.

**Two tiers, and only one of them freezes.** The benchmark produces the table above, so it
must not move. The regression suite only ever answers *"did something that used to work stop
working?"* — a binary with no denominator to corrupt, so it can grow forever without
invalidating anything. That asymmetry is what makes `mine` affordable enough to actually run.
[docs/02](docs/02-promotion.md) §1.

**The spans are the score.** The scorer does not read the agent's prose — it reads the trace:
which tools were called, how many tokens, what the verdict span carried, whether the agent
escalated. Instrumentation is not a dashboard here; it is the measurement substrate — and with
nobody standing inside a run, it is also the **only** place a person can see what happened.

| Doc | What it covers |
|---|---|
| [docs/00-stack.md](docs/00-stack.md) | Every dependency pinned and why, the three model paths, `touchstone doctor` |
| [docs/01-spec.md](docs/01-spec.md) | The incident model, the verdict, the generator, 13 live invariants numbered to 14 |
| [docs/02-promotion.md](docs/02-promotion.md) | The two tiers, the promotion rule, the six stages, case provenance, the negative control |
| [docs/03-agent-and-tools.md](docs/03-agent-and-tools.md) | The graph, three specialists, five read-only tools, escalation as a scored field |
| [docs/04-observability.md](docs/04-observability.md) | Span schema, OpenInference conventions, why the scorer reads spans |
| [docs/05-scoring.md](docs/05-scoring.md) | The four metrics, `all_k`, exact-match vs judged |
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
uv run touchstone doctor                # ✅ works today — checks the CLI, login and fallbacks
```

⚠️ `uv sync` does not put `touchstone` on your `PATH`. Use `uv run touchstone …`, or activate
the environment with `source .venv/bin/activate` first. The blocks below drop the prefix for
readability.

The rest of the interface is specified in [docs/06](docs/06-api.md) and **not yet
implemented**. It is listed here because the spec is fixed, not because it runs:

```bash
docker compose up -d phoenix            # ⬜ traces. ⚠️ that is all the loop needs — the five
                                        #    tools run over MCP stdio, in-process, no container

touchstone incidents generate --n 10    # ⬜ the suite, with planted root causes
touchstone run v1 --k 3                 # ⬜ 10 incidents × 3 attempts
touchstone score v1                     # ⬜ → results/v1.json
touchstone compare v2 --against v1      # ⬜ → promote or reject, per case
```

### Models

The agent runs on **Claude, through [`claude-agent-sdk`](https://github.com/anthropics/claude-agent-sdk-python)**,
which drives the `claude` CLI as a subprocess and inherits its login — so a suite run goes
through a **Claude Code subscription rather than a metered API key**. Running the same suite k
times per case per candidate is the whole point of this repo, and that is what makes it
affordable.

```bash
touchstone doctor   # checks the CLI, the login, the fallbacks
                    # ⛔ and asserts ANTHROPIC_API_KEY is *absent* — if it is set,
                    #    runs quietly bill an API account instead of the subscription
```

**Fallbacks:** Cerebras when rate-limited, ollama offline. ⛔ A provider switch *inside* a run
voids that run rather than mixing it — provider and model are part of a candidate's identity.
The **judge never runs on the Claude quota**; it cannot gate anything, so it is the cheapest
thing to move off the constrained provider.

**The model is pinned to `claude-sonnet-4-6`**, and that id comes from a live call rather than
a config file — `doctor` asks the running CLI what it actually answered as, because the id is
part of a candidate's identity and a config file can disagree with reality. Full manifest and
reasoning: [docs/00-stack.md](docs/00-stack.md).

---

## Reliability, not accuracy

Each case runs **k times**. The headline reliability number is `all_k` — the fraction of
cases that succeeded on *every* attempt — not `pass@1`.

An agent that is right 80% of the time on each of five attempts is not an 80% agent; it is an
agent that fully succeeds on roughly a third of cases. **`all_k` is the number you would use
to decide whether to put something on call.**

> This metric and its implementation come from [`tracebench`](https://github.com/sandeepyadav1478/tracebench),
> an earlier harness that scores CrewAI runs on OpenTelemetry spans. It was brought in rather
> than invented here.

---

## Limits

**Read this before quoting any number this repo ever produces.** These are properties of the
design, so they hold whether or not a run has happened yet.

- **The incidents are synthetic.** A generator writes them. This system has never seen a real
  alert, a real pager, or a real production system, and is not designed to.
- **A planted root cause is not a real one.** Real incidents have several contributing causes,
  ambiguous evidence, and sometimes no single correct answer. The suite is cleaner than
  reality, which makes the correctness number an upper bound on a harder problem.
- **Only five of the eleven failure classes can be shaped against real telemetry; six cannot.**
  The renderers are specified to be built after reading public fault-injection corpora —
  chiefly [RCAEval](https://github.com/phamquiluan/RCAEval) RE2 — but those inject at the
  infrastructure layer, so `db_pool_exhausted`, `slow_query_after_migration`, `cache_stampede`,
  `bad_deploy_regression`, `config_drift` and `insufficient_evidence` have to be built from the
  documented mechanism instead. ⛔ **No public data is loaded, imported or vendored here** — it
  is read to shape the renderers and nothing else (D-029, [docs/01](docs/01-spec.md) §4).
- **The agent does not learn, and the suite does not grow yet either.** Nothing here trains,
  fine-tunes or updates weights. A human writes each candidate version; the gate only decides
  whether it ships. **Mining a failure into a permanent regression case is designed and
  unbuilt** — the mechanism is D-024, the reason it is not in this tag is D-030, so the bar
  currently rises only when a human raises it. ⛔ **"It improves itself" fuses two loops, and
  the fused sentence is false on both halves.**
- **What is designed and deliberately not built**, each with the trigger that would revive it:
  the two-tier suite and case mining, the nightly
  run, an n=30 benchmark, agent memory as v5, and a second agent topology. ⚠️ **`n=10` and
  `k=3` mean every figure here is a count, not a rate** — ⛔ no percentage is quoted from ten
  cases.
- **Cost figures are measured but never billed.** They come from the Agent SDK's own
  `total_cost_usd`, which is cache-aware — so they are a real per-call figure and not
  tokens × list price. But runs go through a **Claude Code subscription**, so the number is
  *what the run would have cost at API list prices*, drawn from a quota rather than an
  invoice. Both halves of that sentence are load-bearing.
- **Rate-limited attempts are void, not failed.** A 429 means the attempt did not happen;
  scoring it as wrong would let a quota limit look like a regression. `void_attempts` is
  reported in every results file.
- **Single service, single machine.** The traces are not distributed.
- **The escalation threshold is a rule**, hand-written and stated in
  [docs/01-spec.md](docs/01-spec.md) §5. It does not adapt.
- **No claim about MTTR, incident volume, or comparison against human responders.** There is
  no baseline to compare against and none is implied.

---

## Prior work this builds on

- [`tracebench`](https://github.com/sandeepyadav1478/tracebench) — `all_k` over OTel spans.
- [`evalloop`](https://github.com/sandeepyadav1478/evalloop) — mining eval sets from traces,
  and the health guard that refuses to report drift from a dead window. The
  [`mine`](docs/02-promotion.md#5-mine) stage is that idea with a real domain under it.

## License

MIT. See [LICENSE](LICENSE).
