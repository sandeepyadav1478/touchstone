# 07 — Diagrams first: the gate no phase starts without

> ⚠️ **Specification, phase 0.** This describes the design; it is not a description of shipped code. `touchstone doctor` is the only implemented command today — see the [README](../README.md) for what runs and what does not.

**This is a process rule, and it is the only one in this repo that blocks work.** Everything
else here describes what to build. This describes **when you are allowed to start.**

> **No implementation begins until a structural diagram of the change has been drawn,
> reviewed and approved. For every phase, and for every later change.**

D-021. Not skippable, not "for the big ones", not retroactive.

---

## 1. Why a gate and not a habit

A habit is what you drop at 11pm on the phase you are excited about. The reason this one is a
hard gate is specific to what this project *is*:

**The loop measures one change at a time.** A candidate is a delta — v3 is v2 plus a runbook
tool, and the whole value of the results table is that you can attribute a score movement to
that one thing. **The failure mode is not building the wrong thing; it is building three things
and reporting them as one.** By the time that shows up it shows up as a number you cannot
explain, and the honest fix is to throw the run away.

**A diagram is the cheapest place to find out that "add memory to the supervisor" is actually
four edits.** Drawing it costs twenty minutes. Discovering it after a 250-call suite run costs
the run, and — worse — you might not discover it at all.

Three more things fall out of it, and they are not the reason but they are real:

- **The diagram is the review artifact.** Reviewing a diagram is possible; reviewing an
  intention is not. "Where does the checkpointer sit?" is a question somebody can actually ask.
- **It is checkable after the fact.** A design reviewed before it was built looks different from
  one drawn afterwards, and the git history settles which it was — the diagram commit precedes
  the implementation commit, or the gate did not run.

---

## 2. What counts as "in-depth" — the acceptance bar

A box labelled *"agent"* with an arrow to a box labelled *"tools"* is not a diagram, it is a
gesture. **The bar is: someone who has never seen the code could implement from it and get the
structure right.**

Every diagram must show, and be *checkable* on:

| Must show | Because |
|---|---|
| **Every node, named exactly as it is named in code** | A diagram whose names drift from the code stops being reviewable the first time it is wrong |
| **Every edge, and what makes it fire** | Conditional edges are where LangGraph bugs live. `supervisor → synthesizer` is not an edge; *"supervisor → synthesizer when hops ≥ max_hops or supervisor emits done"* is |
| **Every store, and who writes to it** | Checkpointer, span store, results files, both suite manifests — and ⚠️ the two are not symmetric: `suite/benchmark/` has no writer at all after generation, `suite/regression/` has exactly one (`touchstone suite review`). Two writers to one store is a design question and it must be visible |
| **Every boundary the change crosses** | Process, container, network, subscription. Each one is a failure mode and a cost |
| **State: what is in it and which fields are reduced** | D-012 says `findings` uses a reducer and nothing else does. **That is a diagram fact**, and it is the kind that silently changes |
| **State: which node reads which key** | ⚠️ This row was missing, and the gap had already cost something. A reducer is the write side; D-025 is a decision about the read side, and the doc that should have carried it had a picture saying fan-out over a sentence saying routing. A key with two writers is a design question; a key with an unintended reader is a silent one — the reader inherits framing and nothing in the run reports it. ✅ [docs/03](03-agent-and-tools.md) §1 |
| **What is *not* changing** | Greyed out, explicitly. **The delta is the claim** — a diagram that shows only the new part hides whether anything else moved |
| **The failure paths** | Parse failure, tool error, interrupt, void run (429). ⛔ **A happy-path-only diagram is the single most common way this gate gets faked** |

**And one line of prose above it, always:** *"this changes X so that Y; nothing else moves."*
If that sentence needs an "and", the change is two changes and gets two diagrams.

---

## 3. Which diagram, for what

Four kinds, and the change decides which. Most changes need one; a phase usually needs two.

| Kind | Use it for | Eraser type |
|---|---|---|
| **Graph / flowchart** | The agent graph, any node or edge change, the scoring pipeline | `flowchart-diagram` |
| **Sequence** | Anything crossing a boundary — a suite run, the MCP round trip, the interrupt-and-resume path, a fallback provider switch | `sequence-diagram` |
| **Entity / schema** | The two suite manifests, the span attributes, the results file, `Verdict` | `entity-relationship-diagram` |
| **Infrastructure** | The compose topology, the CI job, where Phoenix and the MCP server live | `cloud-architecture-diagram` |

⚠️ **The sequence diagram is the one that earns its keep.** The graph picture is easy and
usually already right in your head; the *ordering* across the SDK, LangGraph, the checkpointer,
the span exporter and Phoenix is where a design turns out to be wrong. **When only one diagram
is drawn, draw that one.**

---

## 4. The tool: Eraser MCP — and why the gate does not depend on it

**Eraser is diagram-as-code with a first-party MCP server.** Prompt it in the editor, get DSL
back, commit the DSL. Verified 2026-08-14 from `docs.eraser.io`:

```bash
claude mcp add --transport http eraser https://app.eraser.io/api/mcp
# headless / CI — API key is the documented path for agentic use:
claude mcp add --transport http eraser https://app.eraser.io/api/mcp \
  --header "Authorization: Bearer $ERASER_API_KEY"
```

| | |
|---|---|
| Transport | HTTP, remote — nothing to install or run |
| Auth | OAuth by default; **API key recommended for agentic pipelines, CI and headless** |
| Can | Generate and edit diagrams, read/search files and folders, apply presets, export PNG/JPEG |
| Cost | Free to use, "subject to the same free tier limits as in-app usage" — ⚠️ the limits are not published as a number, and AI generation consumes account credits |

⛔ **So the gate is defined on *an approved diagram*, never on *an Eraser diagram*.** A blocking
process rule must not be able to stall on somebody else's unpublished quota. **Mermaid in a
fenced block is the always-acceptable fallback**, it renders on GitHub, it costs nothing, and it
diffs. Eraser is the better authoring experience for the big ones; Mermaid is the floor.

⚠️ **Eraser is not a dependency.** It never enters `pyproject.toml` — it is a tool the developer
uses before writing code, not a package the system imports. The manifest count in
[`docs/00`](00-stack.md) §4 does not change.

### 🔒 The confidentiality line, because this is a new egress path

A hosted diagram service means **describing an architecture to a third party**. For this project
that is fine by construction — everything here is public, and the simulated environment is
generic by design.

⛔ **Nothing belonging to an employer or a client goes through it, including structure.** A
diagram of an internal system is exactly as disclosing as a description of it; being a picture
changes nothing about what it says. If a diagram would need a name from that side of the
boundary, it is drawn in Mermaid, locally, or it is not drawn.

---

## 5. The artifact: what gets committed

```
diagrams/
  README.md                  # index: file → what it shows → which phase/change
  touchstone.eraser          # source, committed, diffable — THE artifact
  loop.png                   # export, committed alongside — never instead
```

⚠️ **That is the whole directory, and the shape is deliberate — it is not the shape this
section used to describe.** The tree here once listed `phase-1-graph.eraser`,
`phase-2-mcp-sequence.eraser` and `v5-memory-graph.mmd`, one file per change per rule 3
below. **One file draws both phases instead**, because a reviewer holding two pictures
cannot see a contradiction that spans them — which is exactly how the verdict edge and the
`no arrow here` note coexisted for a whole draft ([`../diagrams/README.md`](../diagrams/README.md),
finding 2). ⛔ **Rule 3 still binds the moment a second file appears**; what changed is that
the second file has not been needed, not that the rule was dropped.

**Rules, each with a reason:**

1. ⛔ **The source text is the artifact. A link to a hosted workspace is not.** A diagram that
   lives only in a SaaS account is not evidence — it disappears with the subscription and it
   cannot be reviewed in a diff. **Same rule as everything else in this repo: if it is not in
   git, it does not exist.**
2. **Export the PNG and commit it too**, so the README renders for a reader who will not clone.
   ⚠️ **The PNG is a convenience, never the record** — a picture cannot be diffed, and a
   structural change that is invisible in review is the thing this gate exists to prevent.
3. **One file per change, named for the change**, not `architecture-v2-final.eraser`.
4. **The diagram commit precedes the implementation commit.** That ordering is the proof the
   gate ran, and it is free.
5. **When code and diagram disagree, the diagram is a bug.** Fix it in the same PR. ⚠️ A stale
   diagram is worse than none — it is an aspirational document that will be read as a factual
   one, and it carries the authority of having been approved.

---

## 6. The approval protocol

**Four steps. It is meant to take one exchange, not a meeting.**

1. **Draw it** — one prose line (*"this changes X so that Y; nothing else moves"*), the diagram,
   and an **open-questions list**. The open questions are the point of the exercise; a diagram
   with none is usually a diagram that has not been thought about.
2. **Present it for approval** — the rendered diagram plus the prose line. ⛔ **Do not start
   implementing while waiting.** That is the gate; everything else here is formatting.
3. **Approval is explicit.** Silence is not approval. Changes requested → redraw → re-present.
4. **Commit the approved source before the first line of implementation**, and record the change
   in `DECISIONS.md` if it decided anything non-obvious. **The diagram is not
   a substitute for a decision record** — a picture shows *what*, D-format captures *why* and
   *what was rejected*, and the rejected alternatives never appear in a diagram.

### When the gate is annoying, which is the point

⚠️ **A one-line approval with no questions, twice in a row, means the granularity is wrong** —
the changes being drawn are too small to be worth a diagram, and the gate is becoming a rubber
stamp. **Fix the granularity, not the gate.** Batch a phase into one diagram; do not stop
drawing.

⚠️ **The reverse is also a signal.** A diagram that cannot be drawn without three "it depends"
notes is telling you the design is not ready, and that is worth more than the twenty minutes it
cost.

---

## 7. Where the gate sits in the roadmap

**Every phase in `ROADMAP.md` starts with step 0: the diagram.** It is not a
numbered step in the phase's own list because it is not optional work to be scheduled — it is
the precondition for the phase existing.

| Phase | The diagram that gates it | Kind |
|---|---|---|
| **0 — foundation** | Repo and compose topology: what runs where, what talks to what, which processes exist. ✅ Drawn: [docs/06](06-api.md) §3 — and it earned its keep, since **the checkpointer volume and the absent `suite/` arrow are both visible only in the picture** | infra |
| **1 — the loop closes** | The v1/v2 graph *and* the run→span→score sequence. Two, and the sequence is the important one. ✅ **Sequence drawn**: [docs/04](04-observability.md) §4a, where the load-bearing element is an arrow that is *not* there. ✅ **Graph drawn, and this row is CLEARED** by [`diagrams/touchstone.eraser`](../diagrams/touchstone.eraser) §2, §3 and §6 — the failure paths [docs/03](03-agent-and-tools.md) §1 said were missing are section 6's four terminal statuses, the state read/write edges are section 3's five, and **D-025 and D-026 are cited on the elements that carry them** rather than named in a caption — D-025 on the `findings → supervisor` edge, D-026 on the supervisor node itself. ⚠️ **This cell said "the two edges" until 2026-08-16**, and D-026 was never on an edge; the wording came from the shape the sentence wanted rather than from the file. It is the same error the citation checker exists to catch, in the one place the checker does not read. ⚠️ **Cleared 2026-08-15, after reading as cleared for a day while this cell still said no** — DEF-007 | graph + sequence |
| **2 — measurement** | The MCP round trip and the Phoenix span path, end to end | sequence |
| **3 — the promotion gate** | The CI gate: what runs, what it reads, what makes it block | flowchart |
| **3 — the mine loop (D-024)** | `score → mine → proposed → review → regression → locked`, showing which edges reset the baseline and which do not. ✅ Drawn: [docs/02](02-promotion.md) §5 | flowchart |
| **4 — the one option** | Whichever option is chosen — and for v5-memory it must show the reset boundary explicitly (D-022). ✅ Drawn: [docs/08](08-memory.md) §5 | graph |
| **any later change** | Whatever it touches. **No exemption for small ones** | — |

**The v5-memory diagram carries a specific burden**: it must show where the memory store is
read, where it is written, and **where it is cleared** — because the whole validity of that
experiment is the reset, and *"the store is reset per candidate"* is a claim a picture can make
checkable.

**It is drawn, in [docs/08](08-memory.md) §5, and drawing it changed the design** — which is
the first evidence this gate does anything. The written and cleared edges turned out to be
*banned* rather than located, and once the picture had to show two edges that must not exist,
memory stopped being agent state and became a frozen corpus the environment carries (D-023).
⚠️ **That is a spec diagram, not the committed artifact.** It stays where it is; if v5 is ever
built it earns a section in [`diagrams/touchstone.eraser`](../diagrams/touchstone.eraser),
committed before the v5 implementation commit. ⛔ **It does not become
`diagrams/v5-memory-graph.mmd`** — that filename was promised here and in
[docs/08](08-memory.md) §5 and will never exist (D-036, DEF-006). **v5 is cut by D-030
besides**, so this is a conditional, not a plan.

---

## 8. What this gate does not do

- **It does not replace `DECISIONS.md`.** A diagram shows structure; it cannot show what was
  rejected, and the rejected alternatives are what make a decision record worth reading.
- **It does not make the design right.** An approved diagram of a bad design is a bad design
  everyone agreed to. It bounds *surprise*, not *quality*.
- **It is not documentation.** Documentation describes what exists. **This constrains what gets
  built**, and the difference is entirely in the ordering.
- ⛔ **It earns no claim on its own.** Diagramming before building is a work habit, not an
  engineering result. It shows up in the commit order or it does not show up at all.
