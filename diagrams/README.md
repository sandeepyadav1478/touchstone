# diagrams/

**The gate artifacts.** D-021:
no implementation starts without an approved structural diagram, and the bar
([docs/07](../docs/07-diagrams.md) §2) is *"someone who has never seen the code could implement
from it and get the structure right."*

⛔ **The source text is the artifact.** `touchstone.eraser` is committed and diffable; a picture is
not. The PNG is committed alongside so the file renders for a reader who will not clone —
[docs/07](../docs/07-diagrams.md) §5 rule 2.

| file | shows | gates |
|---|---|---|
| [`touchstone.eraser`](touchstone.eraser) | **The whole system, in numbered sections, on one canvas** — the upstream corpus · the adapter at the seam · the three gate tiers · the process boundaries · how a simulation ends · telemetry · the scorer · **the acceptance conditions** · the case lifecycle, `open → locked` one-way · the version ladder · **the phase exit gates, and the diagram gate that blocks every phase's start** | phase 1, and phase 2 |
| [`loop.png`](loop.png) | The render of the above. **A convenience, never the record** — rebuilt **2026-08-21**, twice: once for the nine silent decisions, once for the `Dev`/`Human` withdrawal. ⚠️ *This cell read 2026-08-20 through both of them* — the row that names a render is the row nothing sweeps backwards to | — |
| [`sequence.eraser`](sequence.eraser) | **One simulation, and every boundary it crosses** — lifelines ordered by distance from the developer's process. It draws the three things a flowchart structurally cannot: the **order** of the telemetry wiring steps, the checkpoint landing after every step, and the scorer running later, in another process, from a file. **Its load-bearing element is a message that is not there** | phase 1 |
| [`sequence.png`](sequence.png) | The render of that. Same status, rebuilt in the same pass | — |
| [`phase1.mmd`](phase1.mmd) | 🆕 **The attachment diagram** — where touchstone joins τ²-bench: the adapter seam at `llm_utils.py:355` and the enforcement point at `Environment.make_tool_call()`. **Mermaid, and local by choice** — it names symbols in another repo, and drawing them as unnamed boxes would hide the only structure it exists to show. It is why D-068 had to widen the approved-repo set | phase 1 |

## ✅ Both PNGs were rebuilt on 2026-08-20 — and what the rebuild found

They had been behind their sources by 3 and 2 commits respectively (`DEFECTS.md` DEF-034),
and those commits were the D-062 specimen swap and the D-069 reward correction, so the pictures
named a corpus that no longer exists and a gating number that was wrong.

⚠️ **Milestone 7 passed on both the whole time, and that is the finding worth keeping.** The
guard measures *clipping* — four clear edges, content filling 98%+ of the frame — which is a
property of the export, not of the content. **A perfectly-rendered picture of the wrong system
passes every instrument in this repo.**

**The procedure is CREATE-then-delete, never update**: `manually_create_diagram` from the
committed file, diff the round-trip, delete the old hosted diagram *after* the new one exists,
export at `imageQuality: 1` twice until the content-addressed URL settles, then **open it and
look**. Creating first is deliberate — a failed create then leaves the stale diagram standing
rather than nothing at all.

**What the looking found, in order:**

1. ⛔ **A sixth `DEFECTS.md` DEF-036 artefact, in the flowchart's phase-1 exit gate** — it
   still asserted `reward_breakdown is {DB, COMMUNICATE}`. Caught by reading the DSL line by line
   before porting it, not by any guard. **A picture is not a place a claim goes to be safe.**
2. 🟡 **`DEFECTS.md` DEF-038, extending DEF-029: the renderer wraps labels mid-token**, and
   `llm_utils.py:355` renders as `llm_utils.py:35` + `5` — a wrong citation that *resolves*.
   Pre-existing, accepted, and the mitigation is that the DSL is the authority: **read a line
   number off the `.eraser` file, never off the PNG.**
3. ✅ **The two unlabelled empty rectangles are gone.** They were carried forward as an open
   observation precisely so the next picture would be checked for them; the current render has
   none, so they belonged to a group the D-062 rewrite deleted.
4. 🔴 **The flowchart was asserting a defect in a file that had already been fixed**, and it did
   so in a **rendered label** — the `NoOther` box said a README line contradicted the
   Anthropic-only rule and was wrong. The README's Limits section had been corrected first, so
   the *diagram* was the stale document. Forced a second port the same day. **A pointer at
   another file's error is a claim with a shelf life**, and nothing in this repo sweeps backwards
   from a fix to the documents pointing at it.

| render | extent | ink | vs. the render it replaced |
|---|---|---|---|
| `loop.png` | 4722 × 8889 | 4.28% | was 6439 × 9606 at 2.86% — smaller canvas, denser, four sections cut |
| `sequence.png` | 3032 × 3457 | 10.63% | was 5069 × 6252 at 14.36% — redrawn, 13 lifelines against 11 |

⚠️ **Ink and extent are measured, not eyeballed** — a shrinking canvas with rising ink is a
diagram that got tighter, and a shrinking canvas with falling ink is one to go and look at. Both
were looked at.

⛔ **Both were exported at `imageQuality: 1`, which contradicts the dated table below.** That
table's *The quality that works* row says `sequence.png` needs **2**, because **1** had returned a
0.07%-ink blank on 2026-08-18. On 2026-08-20 quality **1** returned a 10.63%-ink render of the
redrawn diagram. **Quality 2 was not retried**, so this is not evidence the old row was wrong —
`DEFECTS.md` DEF-028 already says the setting behaves per *diagram*, and the sequence diagram was
rewritten between the two dates. **Measure ink before trusting either number**; the failure mode
is a silent blank, not an error.

**Five tracked files, and that is the whole directory.** `touchstone.html` — a hand-written HTML poster that
drew the same system in six encodings — **was deleted 2026-08-15** by
D-036, which also records why, and what it cost. `.check.log` is a run log,
gitignored.

⚠️ **The second diagram is a REPLACEMENT, and that is what keeps this directory from becoming the
poster again.** [docs/04](../docs/04-observability.md) §4a carried a Mermaid `sequenceDiagram` of
the same run until 2026-08-17. It is gone and §4a points here. **The count went two → four because
one drawing moved and got a render, not because a third view was added** — D-036 deleted the poster
for having six encodings of one system, and adding sequence-as-a-second-source would have been the
same mistake at a smaller scale.

⚠️ **`phase1.mmd` made it five on 2026-08-19, and it is the first file since the poster that needs
its own justification.** It is not a fifth encoding of the same system: it draws the *boundary*
between two systems, and it is the one drawing whose node names live in someone else's repo.
[docs/07](../docs/07-diagrams.md) §5 carries the split table — every file that is not a section of
`touchstone.eraser` states why in one row, which is the mechanism that stops the count drifting
back up.

### ✅ Both renders were refreshed 2026-08-18 — and looking at them is what earned it

Both PNGs carried rendered text that D-052, D-053 and **DEF-027** had changed, so both went the
full way round: delete the hosted diagram → `manually_create_diagram` from the committed file →
**diff the round-trip** → export → measure ink and extent → **open it and look**.

⛔ **The looking is not ceremony — it is the step that found DEF-027, after every instrument had
passed the picture.** Nine labels opened with a `⛔` or a `🔴`; the flowchart font has no colour
emoji, so each one rendered as an identical featureless black bar. The DSL round-tripped byte for
byte, the hash settled, the extent read 98.4% — and the drawing carried nine marks that meant
nothing to a reader. Finding 8. The same glyph in the **sequence** diagram rendered as *zero
pixels*, which is why finding 8 is two failures and not one.

✅ **And "comments do not render" is now measured rather than asserted — 2026-08-18.** The rule at
the head of [`touchstone.eraser`](touchstone.eraser) says the re-upload trigger is a change to
*rendered* content, so a comment-only edit needs no new PNG. That had never been tested. The hosted
flowchart was found two comment edits behind the committed file, deleted, recreated from the file,
and exported twice to a settled hash — and the result came back **6439 × 9505, ink 1.14%, padding
46 / 61 / 61 / 58: every figure identical to the committed `loop.png`**, with **878 pixels differing
at all (0.0014%) and four differing by more than 8 levels**. That is antialiasing jitter, not a
drawing. ⛔ **So `loop.png` was deliberately NOT replaced** — swapping 2.8 MB of git history for four
pixels is churn, and the honest record is that the picture did not move. The *hosted* copy was
replaced, because that one had genuinely drifted.

### The settled renders — `sequence.png` measured 2026-08-21, `loop.png` re-measured the same day after the Dev/Human deletion

| | `loop.png` | `sequence.png` |
|---|---|---|
| Frame | 5264 × 10283 — **54.1 MP** | 3032 × 3457 — **10.5 MP** |
| On disk | 3.00 MB | 0.73 MB |
| Padding, L / T / R / B — **background-difference bbox, the guard's own comparator** | 40 / 64 / 37 / **63** | 14 / 14 / 20 / 11 |
| Content fills — `min(bboxW/w, bboxH/h)`, same comparator, milestone 7 | **98.5%** of the frame | **98.9%** |
| Ink — pixels with `convert("L") < 200`, as a share of the frame | **1.64%** | **3.25%** |
| ⚠️ Ink needs its method stated | The first pass of these two numbers read **2.95%** and **13.76%** — a *looser threshold*, not a different image. Two measurements of the same PNG disagreed by 3×, and the figure is meaningless without the comparator. **Extent was unaffected**, which is why it is the check the guard runs. ⛔ **AND THE SWEEP STOPPED ONE ROW SHORT — found 2026-08-18, on the pass that recreated the hosted flowchart.** The two rows above use a *third* comparator (`ImageChops.difference` against the corner pixel), not `< 200` and not the loose threshold, and neither said so. Measured at `< 200` the same padding reads **65 / 61 / 61 / 62** and **28 / 28 / 40 / 30**; at the loose threshold, **46 / 61 / 61 / 58** and **27 / 27 / 40 / 23**. Three comparators, three answers, one unlabelled row. The bottom cell also read **59** against a measured **58** — an off-by-one that no threshold explains and that survived because the row it sits in had no method to check it against |
| Method | ⛔ **delete the hosted diagram** → `manually_create_diagram` from the committed file → export twice → **keep the new one**, per finding 1. Then the four-edge check in finding 2a **and the extent check in finding 7** | same, and it ran twice — the first render was missing a message the DSL contained, finding 4 |
| Export settings | ⛔ `background: true, theme: light, imageQuality: **1**` — quality 2 returns `{"note":"Error rendering diagram"}`, finding 7 — ⚠️ **and quality 2's failure changed shape on 2026-08-21; see the row below.** The content-addressed URL is keyed on the render, so **a failed export poisons its own cache entry**: re-requesting quality 3 returned the same 0-byte object at the same `x-goog-generation`, and only a different quality produced a different key. ⛔ **Retrying an export is not retrying a render** | ⛔ `background: true, theme: light, imageQuality: **2**` — quality 1 returns a **0.07%-ink blank**, finding 9 |
| ⚠️ The quality that works | **1** — re-confirmed 2026-08-21 at 5.46% ink, four edges clear. ⚠️ **But its two failure modes both got QUIETER on that date.** Quality **2** no longer returns `{"note":"Error rendering diagram"}`; it returns a **0.03%-ink blank** — 2.9 MB, correct dimensions, every pixel of content in the top-left corner (bottom padding 14563 of 15266). Quality **3** returns a **0-byte object under HTTP 200**, `md5=1B2M2Y8AsgTpgAmY7PhCfg==`, which is the hash of the empty string. ⛔ **Both would have committed as a healthy PNG.** An error string is a gift; a 2.9 MB blank is what this table exists to catch | **2**, and 1 is a silent blank |
| Hosted | ⛔ **one diagram per Eraser file** — they shared a file until 2026-08-17 and **rendered on top of each other** (DEF-022, finding 6). `no-link-access`. The workspace and file IDs are deliberately not printed here — they name objects in a private account, and a reader can check nothing with them | ⬑ |

🔴 **Every cell in the two columns above was re-measured 2026-08-21 and every one of them had gone stale — including `sequence.png`, which nothing in this session touched.** The `loop.png` column described a 6439 × 9505 render; the file on disk was 4873 × 7633 before this edit and is 6574 × 9769 after it. The `sequence.png` column described 5069 × 6252 / 1.88 MB against a file that is 3032 × 3457 / 0.73 MB. **This is rule 22 — nothing sweeps backwards from a re-export to the table that measured it** — and the giveaway is that the *stale* column belongs to a diagram no edit in this session went near. ⚠️ A metrics table with no owner goes stale on somebody else's commit.

⛔ **`background: true` is not cosmetic, and omitting it produces a failure that reads as a
different failure.** The default is a transparent canvas. `PIL`'s `.convert("RGB")` turns every
transparent pixel **black**, so `scripts/check-diagram.py` milestone 7 finds content on all four
edges and reports the render as **CLIPPED** — sending you to re-render a diagram that rendered
perfectly. Measured 2026-08-17: `sequence.png` came back 0/0/0/0 instead of 27/23/27/40. The guard
now checks the alpha channel first and says `nobg`, because *a guard that fails for the wrong
reason costs more than one that does not fire.*

⚠️ **Every row above is superseded, not corrected**, and the history is kept because *the reflow
is the finding*. Every figure below was taken at the same `imageQuality` — see finding 3, which is
the only reason they are comparable at all. *(This sentence said "all five figures" until 2026-08-21,
when the table had nine live rows. A count in prose beside a table it does not derive from is the
same defect as the one the row above records — so it is a description now, not a tally.)*

| render | edit that produced it | frame | Δ width | Δ height |
|---|---|---|---|---|
| D-039 | one node's label | ⟨not recorded⟩ | **0** | +80 |
| D-039 → D-040 | **a node removed** from inside a group | 6437 × 13066 → 6752 × 12674 | **+315** | **−392** |
| D-040 → D-043 | **five labels grew**, no node added or removed | 6752 × 12674 → 6792 × 13470 | +40 | **+796** |
| D-043 → D-045 | **two nodes and two edges added** | 6792 × 13470 → 6313 × 14683 | **−479** | **+1213** |
| D-045 → D-046 | one node moved between groups, one duplicate edge deleted | ~~6313 × 14683 → 7300 × 10742~~ | ~~+987~~ | ~~−3941~~ |
| the audit fixes | **+2 nodes** (`Inv`, `Regr`), **+3 edges**, one legend row, one node recoloured | 7343 × 10742 → **7887 × 12420** | **+544** | **+1678** |
| the gate audit | **+13 declarations, +2 groups, +6 edge lines** — §14's `DiagGate` and four exit gates, `Insuf`, the five admission gates broken out of a label | 7887 × 12420 → **7953 × 16738** | **+66** | **+4318** |
| the completeness audit | **+8 nodes, +8 edges** — `BudgetFlag`, `DoctorPy`, `Log`, and §15's `Guards` with its four scripts (DEF-023, DEF-025) | 7953 × 16738 → **12864 × 19056** | **+4911** | **+2318** |
| D-074 · Phoenix → `mlflow ui` | **one node renamed and relabelled, one edge retargeted** — no node added or removed | 4873 × 7633 → **4873 × 7633** | **0** | **0** |
| D-071 · D-078 · D-079 — the nine decisions the picture was silent about | **+14 declarations**, two of them groups (§11b `AgentGraph`, §8c `Curator`) plus ~~`Human`~~ *(deleted one day later — row eleven)*, `DeepEval`, `MCrit`; **+16 edge lines, −2** (`MT > MTest` and the four-rung ladder chain, both re-routed) | 4873 × 7633 → **6574 × 9769** | **+1701** | **+2136** |
| D-079 part 3 **WITHDRAWN** — `Dev` and `Human` deleted | **−2 declarations, +1** (`Immutable`); **−5 edge lines, +1** — the two person-shaped nodes and every edge into them | 6574 × 9769 → **5264 × 10283** | **−1310** | **+514** |
| `NCat`'s tool typing corrected | **one label**, no node or edge touched — `catalogue`'s four tools are 3 `READ` + `calculate`, which upstream types `GENERIC` | 5264 × 10283 → **5264 × 10283** | **0** | **0** |

✅ **Row ten is measured against row nine at the same quality — both `imageQuality: 1` — so it is a live comparison, not a derived one.** It is also the largest single edit in the table by node count, and the frame grew on *both* axes, which only rows three, six, seven and eight did. ⚠️ **Ink fell from 5.53% to 4.02% while the frame grew 1.73× in area.** That is what a real content addition looks like here — the 0.03%-ink quality-2 blank of finding 7 is two orders of magnitude below it, which is the only reason the ink measurement separates the two cases at all.

✅ **Row twelve is the SECOND zero-zero row, and it makes row nine less of a curiosity.** Both were label-text-only edits and both moved neither axis; row one was a label-text-only edit that moved height by +80. **Two of three label edits now reflow nothing** — still not a rule, but no longer a single sample. ⚠️ Padding, extent and ink came back byte-for-byte identical to row eleven as well, and the file differs by 1,482 bytes. **The render is the same picture with one string swapped**, which is the only case in this table where that can be said.

✅ **Row eleven is the case the ink measurement was introduced for: the canvas SHRANK 16% in area and the ink ROSE, 1.40% → 1.64% at the same `< 200` comparator.** That is the "diagram got tighter" reading named at the top of this section, and it is the first row in the table to show it — every earlier shrink came with falling ink. ⚠️ **It also shrank on one axis and grew on the other**, which is why removing three nodes and four net edges did not simply give back what row ten took: Eraser re-packed the columns, so a deletion bought width and spent it on height.

⛔ **Row nine's two zeros are real, and its *starting* frame has no row above it.** The frame went **12864 × 19056 → 4873 × 7633** somewhere between row eight and row nine — the D-068 redraw, which cut sections 1–4 with the specimen — **and that row was never written**. It is left missing rather than reconstructed: row eight's figure is derived at quality 2 and row nine's is measured at quality 1, and finding 3 says a quality mismatch invalidates the comparison. **A row assembled from two qualities would look like the eight real ones.**

✅ **What row nine does establish is the zero.** Every prior row changed at least one axis; this is the first edit measured to move neither. It changed **label text only** — which is exactly what row one (D-039, one node's label) moved +80px of height for. So label text alone can reflow and can also not reflow, and nothing here predicts which.

⚠️ **Row eight's frame is DERIVED, and it is the first one in this table that is.** The render
that shipped is `imageQuality: 1` — quality 2 does not render this diagram any more (finding 7) —
and finding 3 says a quality mismatch invalidates every dimension comparison. So the figure above is
the settled 6432 × 9528 quality-1 render **doubled**, which finding 3's linear-multiplier property
licenses and which was re-measured this pass at **exactly 2.0000 on both axes**. ⛔ It is *not* the
blank quality-2 export's reported frame, even though that number is identical — a failed render's
self-report is not a measurement of anything.

✅ **Row seven is the second pair, and having two of them is worth more than the second one is.**
Both were taken the same way, so for the first time this table can compare a comparison. **It kills
the per-node reading with data rather than with caution:** row six added 2 declarations for +1678px
of height and row seven added 13 for +4318 — **839px per declaration against 332**, a factor of 2.5
apart. Whatever the height is a function of, it is not the node count, and the warning under row six
("do not read +1678 as a per-node cost") now has a measurement behind it instead of a hedge.
⚠️ **Width did almost nothing** — +66px on the edit that added the most content of any row here —
so the two axes are not responding to the same thing, and nothing here says what either responds to.

⛔ **The sequence diagram has a before/after too, and it stays OUT of this table.** Adding the
`Tools` lifeline and its three messages took `sequence.png` from **4629 × 5554 to 5069 × 6252** —
+440 wide, +698 tall. It is a clean pair, taken by the same method, and it belongs to a **different
layout engine**: a sequence diagram's width is a function of participant count and its height of
message count, which is precisely the per-node relationship the rows above spent three renders
failing to find in the flowchart. **Putting both in one table would produce an average of two
things that do not average** — the same fused-denominator error the citation guard exists for,
committed on the apparatus instead of on the claims.

✅ **Row six is the first pair in this table that is a pair.** Both frames were taken the same
way — create fresh, export twice, confirm the hashes match, check all four edges — so this is the
first row where the *before* and the *after* were measured by the same method and neither came off
a long-edited diagram. Rows 1–4 name no method at all and row five was withdrawn for having the
wrong one. ⚠️ **That is all it establishes: one honest sample, not a rule.** Do not read +1678 as a
per-node cost — row four added two nodes and came out *narrower*, and nothing here says which of the
five changes moved the height.

🔴 **Row five is WITHDRAWN, and it is the most instructive row in the table.** It was written up as
*"−3,941px of height, 27% less to scroll, which group a node is in is a bigger layout input than how
many nodes there are"* — a confident mechanism, from two numbers that do not compare. **Both
renders were exported from the long-edited hosted diagram**, which finding 1 directly below says is
a record of edit history rather than of content. The rule was already written, in this file and in
the diagram's own header, and it was not followed. Worse: the D-046 export was also **clipped**
(finding 2a), so the 10742 was not even that render's own height. **Re-measured under the stated
method — create fresh, export twice, check all four edges — the settled frame is 7343 × 10742.**
There is no honest before/after left **for that edit**, because the *before* would have to be
re-measured the same way and that diagram is gone. ✅ **Row six is the one that is honest**, and it
only exists because the settled 7343 × 10742 above became a *before* the moment the next edit
landed. The withdrawal is what made the next comparison possible.

⛔ **Ten live rows, ten unrelated reflow shapes — so there is no stable-layout claim left to
make.**
⚠️ **That count is `grep -c '^| ' ` on the table minus its header minus the one struck row — derive it,
never step it.** It read *six* until 2026-08-21, three rows after it stopped being true.
The paragraph this replaced said the layout was stable on the strength of the first row alone.
**One stable re-export is one sample.** ⚠️ **Rows three and four are the ones that should change how
you read the first two.** Row three added no node and moved no edge, yet moved the height **ten
times further** than the row that deleted a node. Row four *added* two nodes and came out **479px
narrower**. **The size of a diagram edit in the DSL predicts neither the size nor the sign of the
reflow** — Eraser re-wraps labels and re-packs columns, and a canvas that grows in content can
shrink in an axis.

⚠️ **Rows one to four do not name the method they were taken under, and that is now a defect in
this table rather than a footnote.** Row five was withdrawn precisely because its method was wrong,
and nothing recorded here says whether the others were created-fresh or exported from a diagram
mid-edit. **Treat them as suggestive and not as comparable** until a row can say how it was taken.
✅ **Rows six and seven can say it** — row six was the first that could, which is why they are
marked and rows one to five are not.
🎯 **The fix is a column, not a re-measurement** — any future row that cannot fill it does not go
in.

🎯 **The reason this table is kept rather than overwritten each time is that it is the only
falsifiable thing in this file** — and row five is the proof, because it was falsified. Everything
else here is an argument; these are measurements, each re-derivable from a committed PNG's IHDR
chunk. **A withdrawn row left visible is worth more than four kept ones**, since it is the only
entry that records how the error was made.

⚠️ **The content bounding box is no longer recorded here.** It came from Eraser's own canvas
readout, and a figure that cannot be re-derived from the committed PNG is a figure that goes stale
without anyone noticing. **The frame is measured from `loop.png`'s IHDR chunk** and anyone can
re-run that.

⚠️ **The hosted copy is a renderer, not the artifact.** ⛔ **Do not read a figure off it and do not
edit it**; an edit there is invisible in every diff this repo has.

🔴 **A correction, and it is the same failure as row five.** This paragraph said the hosted copy is
"deliberately not the same bytes" and that what gets pushed is the file **with every `//` line
stripped** — 9,800 chars against 29,662. **Measured 2026-08-16, that is false: the upload is the
file, verbatim, comments included**, byte-identical across all 49,289 of them. Eraser strips the
comments *on render*, which is why the picture looks the same and why the claim survived. ⚠️ **The
two figures were also both stale** — the strip is now 13,391 chars of 47,250 — so the sentence was
wrong about the mechanism *and* about the numbers, and the numbers going stale is what got it
looked at. **The comment-strip is a diffing tool, not the transport**: it is how you decide whether
a re-export is needed (below), and nothing more.

### Re-deriving the census, because the diagram tells you to

`touchstone.eraser`'s convention 1 quotes a node census and says **"re-derive it from the DSL
before quoting it, never step it by hand — the command is in `diagrams/README.md`."** ⛔ **It was
not, for one edit.** A pointer to a command that does not exist is worse than no pointer, because
it reads as though someone checked. Here it is:

```bash
# 86 declarations · 15 groups · 57 edge lines · 39 of the 86 carry no colour
body() { grep -vE '^\s*//' diagrams/touchstone.eraser; }
body | grep -E '^\s*[A-Za-z][A-Za-z0-9_]*\s*\[' | grep -v '^legend' | wc -l   # declarations
body | grep -E '^\s*[A-Za-z][A-Za-z0-9_]*\s*\[' | grep -v '^legend' | grep -c '{[[:space:]]*$'
body | grep -cE '^[A-Za-z][A-Za-z0-9_]* *(<>|-->|>)'                          # edge lines
body | grep -E '^\s*[A-Za-z][A-Za-z0-9_]*\s*\[' | grep -oE 'color: [a-z]+' | sort | uniq -c
body | wc -m                                  # rendered chars — the re-export trigger
```

⚠️ **`legend` is excluded and that is the whole reason this has to be written down.** It matches
the declaration shape exactly, so counting it gives **87**, and 86 versus 87 is precisely the kind
of drift nobody can adjudicate a week later. The legend is a key, not a node. **A census figure
that cannot be reproduced from a recorded query should be discarded rather than corrected.**

And for `sequence.eraser`, where the same trap is waiting under a different name:

```bash
# 11 participants · 26 messages · 6 of them self · 6 dashed returns · 4 blocks · 3,716 rendered chars
body() { grep -vE '^\s*//' diagrams/sequence.eraser; }
body | grep -E '^[A-Za-z][A-Za-z0-9_]* *\[' | grep -vE '^(loop|alt|else) ' | wc -l   # participants
body | grep -cE '^\s*[A-Za-z][A-Za-z0-9_]* *(-->|>) *[A-Za-z]'                       # messages
body | grep -cE '^\s*(loop|alt|else) *\['                                            # blocks
body | wc -m                                          # rendered chars — the re-export trigger
```

⛔ **`loop`, `alt` and `else` are the `legend` of this file.** They open with `[` in column 1 and
match the participant shape exactly, so counting without the exclusion gives **14 participants for
11 lifelines** — and 11 is independently confirmed by the colour tally, which sums to
`blue 7 · grey 2 · orange 1 · red 1`. **Two files, two different keywords, the same
off-by-a-keyword**; the parallel is the reason both commands are printed rather than described.

✅ **The message count cross-foots against the guard**: `scripts/check-diagram.py` milestone 8
reports *"26 message labels scanned"* from an independent parser. **Two counts derived by different
code agreeing is worth more than either one stated twice.**

🎯 **The last line is the one that gets used most.** Comments render no pixels, so a re-export is
triggered by a change to `body`, **never by a change to the file**. Compare it against
`git show HEAD:diagrams/touchstone.eraser | grep -vE '^\s*//' | wc -m`; if they match, `loop.png`
and the hosted copy are both still correct and re-uploading buys nothing.

⚠️ **It is a column you scroll**, so read it top to bottom; section 1 is the corpus and every later
section follows the order an attempt actually moves through. ⛔ **That figure was taken under the
two-export settle rule below** — a single export can return the *previous* render, and a figure
taken any other way is not comparable to this one.

---

## Ten findings about the tool, and nearly every one is the same failure

**None is about touchstone. They are here because the tool accepts something, echoes it back
unchanged, and renders something else** — and every check that reads the *source* or the
*reproducibility* of the render passes while it happens. That is this project's own thesis landing
on its own documents.

⚠️ **Findings 1–3 are about a number that was wrong. Findings 4–5 are about content that was
absent**, and the second kind is worse: a wrong number gets re-derived by anyone who quotes it,
while a missing message has nothing to be re-derived *from*. Both were found by eye, on a render,
after every automated check had passed.

🔴 **Finding 6 is a third kind, and it is the one that got furthest.** Nothing was wrong with the
number, the source or the export — the content was **present, correct and unreadable**, and it was
found by *the reader*, after the render had been checked pixel by pixel and handed over for
approval. It is the only finding here that no amount of care on the exported PNG could have
reached, because it is not a property of the export.

### 1. Eraser's canvas size is a record of edit history, not of content

A hosted diagram **keeps its element positions across updates and only lays out fully when it is
created.** So a diagram you have been editing carries every layout it has ever had, and no amount
of further editing walks it back.

| | content bbox | area |
|---|---|---|
| a diagram created once | 6388 × 12786 | **81.7 MP** |
| a diagram updated ~8 times, **byte-identical DSL** | 9338 × 16401 | **153.2 MP** |

**Same bytes. 88% more area.** ⚠️ **Those two are of each other, not of the render above** — they
were taken before the specialist labels gained their tool line, which is the 0.5 MP between 81.7
and the settled 82.2. **A pair is only a pair against the DSL it was measured on**, which is the
whole reason the earlier figures had to be withdrawn. ⛔ **The rule: delete the hosted diagram,
`manually_create_diagram` from the committed file, export from the new one — and KEEP it.** Never
`manually_update_diagram`, and never export from a diagram you have been editing.

🔴 **This rule used to end "delete it", and that was wrong in a way that took a fortnight to show
up.** It optimised for the export and said nothing about the workspace, so the hosted diagram was
simply left behind: on **2026-08-16** it sat **seven fixes** behind `touchstone.eraser` — no `Inv`,
no `Regr`, no purple legend row — and it is the copy that *looks* canonical when someone opens the
workspace. ⛔ **A stale renderer nobody has marked stale is worse than no renderer**, because the
file being the real artifact is a fact about this repo that the workspace does not display.
**Delete-and-recreate is the same call sequence with the delete moved to the front**, so keeping
both copies honest costs nothing.

⚠️ **The trigger is a change to RENDERED CONTENT, not a change to the file.** Comments do not render.
Strip `//` lines from both versions and compare — if they match, the PNG *and* the hosted copy are
still correct and re-uploading buys nothing. That check is what established that the convention-1
correction needed no re-export at all. 📐 The **file** ID is stable across a replace and only the
**diagram** ID changes, so a workspace bookmark keeps working.

It is cheap precisely because the file is the artifact and the hosted copy is only a renderer.

### 2. Export races the re-render, so every measurement needs two of them

Export URLs are content-addressed — `.../elements%3A<sha256>.png`. ⛔ **Export twice and compare the
URLs; an identical hash means the render has settled.** Before this was understood, two exports of
one *unchanged* diagram came back at 82.6 MP and 156.2 MP.

### 2a. …and settled is not the same as complete. **The settle rule cannot see a clipped export.**

**2026-08-16.** The D-046 render was exported twice, both calls returned the **identical** hash, it
was downloaded, committed, pushed, and offered for D-021 approval. It was **missing the whole of
section 13 and the bottom of section 8** — content ran straight off the bottom edge. *A user
noticed, on the picture. No check here did.*

⛔ **Two identical hashes prove the render is not STALE. They say nothing about whether it is
COMPLETE, because a truncated render is perfectly reproducible** — export it a third time and the
same clipped bytes come back, which is exactly what happened. **The two failure modes look
identical through the rule that was written for one of them.**

🎯 **The check that does separate them needs no second export and no service.** A complete Eraser
export has whitespace padding on all four sides; content touching an edge means the canvas was
clipped there. That is one pixel row and one pixel column per side:

```python
im = Image.open("diagrams/loop.png").convert("RGB")
w, h = im.size
for box in ((0, 0, w, 1), (0, h - 1, w, h), (0, 0, 1, h), (w - 1, 0, w, h)):
    assert not any(p != (255, 255, 255) for p in im.crop(box).get_flattened_data())
```

⛔ **It is milestone 7 of `scripts/check-diagram.py`, and it was negative-controlled against the
exact PNG that shipped** — the guard fails on it and passes on the replacement. **The first six
milestones all check the source; this is the only one that looks at the render**, which is the half
a reader actually receives.

⚠️ **Note what the clipping did to a measurement, not just to a picture.** The clipped frame was
`7300 × 10742` and the settled one is `7343 × 10742` — the *height* matched, so the number looked
plausible and got written into a reflow row and a decision. **A truncated export does not
necessarily produce an obviously wrong figure.**

### 2b. `<` and `>` in a label render as `&lt;` and `&gt;`

`results/spans/<version>.jsonl` printed on the canvas as `results/spans/&lt;version&gt;.jsonl` —
the escape, literally, in four labels. It had been that way for the whole life of the diagram and
was only seen when the bottom strip was examined at full resolution for the clipping above. **Now
written `(version)`.** ⚠️ **That change had to be made in `scripts/check-diagram.py` at the same
time**: its path regex had `<>` in the character class *on purpose*, so switching to parens would
have silently stopped extracting those four paths and dropped the citation count with no failure —
the script's own documented failure mode, twice over. Count held at 74 across the change, which is
how that was confirmed rather than assumed.

⚠️ **Every before/after pixel figure this file used to carry is withdrawn — not corrected,
withdrawn**, along with the mechanism they argued for (*"fat labels act as walls the auto-layout
routes around"*). Each was taken one-export-per-push on a long-edited diagram, so each was
plausibly measuring the previous draft's canvas plus its accumulated layout. **The pairs cannot
establish a direction, so the direction goes with the digits.** The conventions those numbers were
used to justify all survive on their other reasons, which is the only reason this is a footnote
rather than a redraw.

⚠️ **The exports are public-read and unauthenticated**, in Eraser's own GCS bucket. That is fine
here — this repo is public by construction — and it is worth stating, because "a hosted service"
sounds like "sent to a vendor" and actually means "rendered to a public bucket."

---

### 3. `imageQuality` is a linear scale multiplier, and it silently invalidates every pixel comparison

The D-039 render came back **9656 × 19599 — 189.2 MP**, against a previous settled figure of
6437 × 12986. **2.26× the area for one added node**, which reads exactly like the layout bloat in
finding 1 and is nothing of the kind: the export had been requested at `imageQuality: 3` and the
previous one at 2. Re-exported at 2 it is 6437 × 13066 — same width, +80px.

🎯 **The test that separates the two, and it is one division:** a quality change scales **both axes
by the identical factor** (here 1.500077 and 1.500000); a layout change does not. Run it against
finding 1's pair — 6388 × 12786 → 9338 × 16401 is 1.462 and 1.283 — and that finding survives,
which is why it is still stated above rather than withdrawn.

✅ **The D-040 render is a third data point and the test calls it correctly.** 6437 × 13066 →
6752 × 12674 is **1.049 and 0.970** — not merely unequal but *opposite in sign*, which no
`imageQuality` change can produce. **A ratio pair that straddles 1.0 is a layout change and
nothing else**, and it is the cheapest check in this file.

⛔ **So `imageQuality` joins `background` and `theme` as a setting that must be stated with any
figure taken from an export.** Three settings now, and each one was found the same way: a number
came out wrong and the tool, not the diagram, turned out to be the variable. **That is three for
three** — every measurement problem in this file has been the apparatus.

### 4. `note over` is accepted, stored, echoed back, and rendered as nothing

Measured 2026-08-17, on a live probe before any of it reached `sequence.eraser`. A sequence diagram
containing `note over A,B: …` and `note over B: …` was created without an error, the API's own
`code` field returned **both lines verbatim**, and the render contained **zero pixels** for either.

⚠️ **This mattered because the port was about to happen.** The Mermaid in
[docs/04](../docs/04-observability.md) §4a carried **four** `Note over` lines, and **three of them
were the load-bearing claims** — invariant 1 (ground truth stays shut), invariant 14 (no two
specialist spans overlap), and *"no arrow here — the verdict is never returned to the scorer."* A
faithful-looking port would have kept every arrow, dropped every reason, and passed the citation
guard, the settle rule and the four-edge check, because **nothing we run reads a render for
meaning**. Each note is now a message label or a block label, marked ⛔ in the source where it lands.

📐 **What is supported, all probed on a live render before use:** participant attributes (`icon`,
`color`), `>`, `-->`, self-messages, `loop`, `alt`/`else`. `opt` renders and is not used.

⚠️ **`title` is a third directive that does not reach the PNG.** `sequence.eraser` opens with
`title touchstone — one attempt, and every boundary it crosses`, and the export's first content row
is the participant boxes — top padding 27px, no caption. The line is kept because it names the
diagram in the hosted workspace and reads as a header in the source, but ⛔ **nothing a PNG reader
sees says what the picture is.** If the drawing ever needs to be self-describing when detached from
this repo, that has to be a participant or a block label, like everything else here.

### 5. 🔴 An opening `[` in a message label deletes the whole message

**The sharpest finding in this directory, and the only one no existing check could have caught.**
Measured on a five-message probe: a label containing `setting_sources=[]` rendered **nothing**, a
label containing a lone `[` rendered **nothing**, a label containing a lone `]` rendered **fine**,
and the plain labels either side rendered fine. The parser reads `[` as the start of an attribute
block and swallows the line.

⛔ **It bit `sequence.eraser` on its first render, on the single most important message in it:**
`Models > Claude` — the process boundary, which is the whole reason a sequence diagram was drawn
rather than a second flowchart. And:

- the DSL **round-tripped verbatim** in the API response,
- **two exports returned an identical content hash** — the render had settled,
- **all four edges were clear** — the render was complete,
- the citation guard **passed**.

**A whole message vanished and every check in this repo passed it.** It was found by counting arrows
in the picture.

🎯 **So `scripts/check-diagram.py` milestone 8 is a static grep of the source**, and it has to be:
every other milestone reads the render or reads a document, and the render is a picture of the wrong
thing that looks entirely correct. The check is deliberately **asymmetric** — `]` is measured
harmless, and making it symmetric "to be safe" would flag correct labels and teach people to ignore
it.

⚠️ **Same family as DEF-015**, where a `]` in a flowchart label truncated this guard's own regex —
but that was a *reader* and this is the *renderer*, and **truncation leaves evidence while deletion
does not**.

### 6. 🔴 Two diagrams in one Eraser file share one canvas, at the same origin

**Measured 2026-08-17, and reported by the reader rather than by any check here.** `sequence.eraser`
was created into the same Eraser file as the flowchart. Eraser lays every diagram in a file onto
**one canvas starting at the same origin**, so the two drawings rendered **on top of each other** and
neither could be read in the app. There is no position parameter anywhere in the MCP —
`manually_create_diagram` takes `fileId`, `diagramType` and `code`, and that is the whole surface.

⛔ **The fix is one Eraser file per diagram**, and it is the only separation the API offers. The
flowchart kept its file; the sequence moved to a new one, was re-created from the committed
`.eraser`, and the new export is **pixel-identical** to the committed `sequence.png` —
`ImageChops.difference(...).getbbox()` is `None`, so the move changed nothing about the picture. The
old copy was deleted only *after* that comparison passed. ⚠️ The PNG bytes differ while the pixels
do not; **byte-comparing two PNGs of the same drawing is not a valid check** — encoder metadata
alone will fail it.

🎯 **The lesson, and it is about what "verified" covered.** Every check in this repo reads the
**exported PNG**, which is per-diagram and was perfect. The overlap exists only in the **app canvas**,
which is the thing a human is sent to open. *The artifact that was verified and the artifact that
was handed over were not the same rendering* — and the gap is invisible from the side that was
checked. ⛔ The same asymmetry as findings 4 and 5: the check and the failure live in different
representations.

### 7. 🔴 Past a size, `imageQuality: 2` stops rendering — and it fails by returning a **blank page**, not an error

Measured 2026-08-17, on the flowchart immediately after §15 was added. Four export calls, same
diagram, same parameters:

| call | `imageQuality` | result |
|---|---|---|
| 1 | 2 | `{"note":"Error rendering diagram"}` |
| 2 | 2 | `{"note":"Error rendering diagram"}` |
| 3 | 2 | ✅ a PNG — **12864 × 19056, and 0.013% ink** |
| 4 | 2 | `{"note":"Error rendering diagram"}` |
| 5, 6 | 1 | ✅ **6432 × 9528, 4.811% ink, identical hashes** |

⛔ **Call 3 is the dangerous one.** The frame is exactly right — 2.0000× the quality-1 render on both
axes — and the only content is the legend, in a 447 × 666 box in one corner. It **settled** under
finding 2 (calls made before and after returned the same content hash), it **passed** the four-edge
clip test of finding 2a, and it passed every DSL milestone, because the DSL was never wrong. It was
copied over `loop.png` and was one commit away from being the artifact offered for D-021 approval.

**Two consequences, and the second is the durable one.**

1. **`loop.png` ships at `imageQuality: 1`.** For this diagram the setting the table above called
   load-bearing is now the setting that breaks it. `sequence.png` is far smaller and stays at 2.
2. **`check-diagram.py` milestone 7 gained a content-extent check.** Eraser crops to its content, so
   a complete render's bounding box fills the frame bar the padding — **98.3%** and **98.7%** for the
   two committed PNGs, **3.5%** for the blank. ⛔ **Ink fraction would be the wrong test** — density
   varies between diagrams, and a sparse diagram is not a broken one. Extent is what a failed render
   loses. Confirmed by feeding the blank back in and watching it fail.

🎯 **The lesson, and it generalises past Eraser: every check in this directory was measuring
reproducibility, and reproducibility is not correctness.** The settle rule compares a render to
itself. The clip test compares a render to its own edges. The transcription diff compares source to
source — all 779 lines matched, because the source was fine. **Nothing asked whether the picture had
a picture in it.** ⛔ Same shape as finding 6 and DEF-021, one layer further out, and the same
answer: **open the render and look at it.**

### …and the one that is not a tool finding: the port dropped a participant

Neither of the two above caught the real defect in `sequence.eraser`. **The first version had no
`tools/` lifeline at all** (DEF-021) — the Mermaid it replaced had one, `touchstone.tool.*` is one
of the four span families in [docs/04](../docs/04-observability.md) §2, and two scored metrics are
computed from spans the picture did not draw. Every milestone passed, because milestones 1–5 check
that what **is** written resolves and milestone 8 catches what the renderer **ate**. *Nothing checks
for a participant nobody typed.*

🎯 **The rule it produced: a replacement is audited against the thing it replaces, not against the
spec.** The spec agreed with both versions — it always will, which is exactly why it cannot referee.

### 8. 🔴 A `⛔` or `🔴` at the start of a label is not text — and what it becomes depends on the diagram type

Measured 2026-08-18, by opening the PNG. Nine labels across the two files opened with `⛔` or
`🔴`, because that is how this repo's prose marks a hard rule. In the DSL they are ordinary
characters: they round-trip byte for byte, they pass milestone 1–6, they raise the extent, and
they are **invisible to every check that reads the source**.

| where | what the reader sees |
|---|---|
| `touchstone.eraser` — flowchart | one **featureless black bar**, identical for every glyph. Eraser's flowchart font has no colour emoji, so it draws the fallback box. Nine labels, nine bars, no information |
| `sequence.eraser` — sequence | **zero pixels.** The glyph is dropped silently — the same family as `note over` in finding 4. `Score`'s label opened with `⛔`; cropping the old render at the `Score` header shows no bar and no gap |

⛔ **The two failures look nothing alike and have the same cause**, which is why neither one
generalises from the other. A bar is at least *visible* wrongness; a silent drop leaves a label
that reads as if it were never marked.

**What does render, verified by cropping:** `⚠`, `✅`, `→`, `≥`, `·`, `—`, `–`. The ASCII-adjacent
punctuation and the two glyphs Eraser has real artwork for are safe; the rest are not. **The fix
was to delete the glyph and open with the words** — `P2Gate` now reads *"THE WEAKEST GATE, AND IT
IS THE ONE THAT SHIPS v0.1.0"*, which was the whole meaning of the bar anyway.

🎯 **Milestone 9 is this finding**: it greps the DSL for `⛔` and `🔴` inside a rendered label and
fails the build. It cannot be a render check — a black bar and a legitimate filled shape are the
same pixels, and an automated solid-block scan run over the *old* renders found **zero** blobs at
the two sites where the bars provably were. The detector that cannot see a known-positive is not
evidence, so the check lives in the source.

⚠️ **Comments are exempt.** `//` lines never reach the canvas, so the glyphs stay in them — which
is where the rules about the glyphs are written.

### 9. 🔴 The working `imageQuality` is **per diagram**, and it inverts between these two

Finding 7 says quality 2 stops rendering past a size. That was measured on the flowchart and
generalised — wrongly. Measured 2026-08-18 on both diagrams, **freshly created**, same parameters
otherwise:

| | `imageQuality: 1` | `imageQuality: 2` |
|---|---|---|
| flowchart | ✅ 6439 × 9505, ink 1.14%, extent 96.8% | 🔴 `{"note":"Error rendering diagram"}` |
| sequence | 🔴 2534 × 3126, **ink 0.07%**, **extent 1.2%** — a near-blank frame with margins 122 / 10 / 2137 / 2776 | ✅ 5069 × 6252, ink 4.50%, extent 97.7% |

⚠️ **Ink is quoted at one threshold — `convert("L") < 200`, share of all pixels — and the first
pass of this table used a looser one, reading 2.95 / 0.21 / 13.76.** Nothing about the images
changed; the comparator did. **The extent column was identical under both**, and that is exactly
why extent, not ink, is what `scripts/check-diagram.py` milestone 7 asserts. *A ratio needs the
command that produced it named in the same table.*

⛔ **Both blanks settle.** Two consecutive exports of the sequence at quality 1 returned the
*identical* content-addressed URL — a failed render is perfectly reproducible, so finding 2's
settle rule confirms it and finding 7's extent check is the only thing that rejects it. The
flowchart at least errors out loud; the sequence hands back a real PNG of nothing.

**The rule: export at both qualities, measure ink and extent, keep the one that passes. Never
carry a quality forward from another diagram, or from this diagram last week.** The flowchart's
quality-2 error reproduced on a diagram ID created minutes earlier, so it is a property of the
content, not of a long edit history — and that means it can change when the content does.

### 10. A sequence participant box is a fixed ~13-character column, and the font's `9` reads as `q`

Found 2026-08-18 the only way any of these are found — someone read the picture and asked what
`P1.q` meant. It was `P1.9`, a `ROADMAP.md` build row. Eraser's render font draws `9` with a
curled descender and `0` slashed, so a bare roadmap-row citation is genuinely ambiguous to the
person who **wrote the roadmap**.

⛔ **And the box does not widen for its content.** Measured off the same crop: `tools/read.py`
(13 chars) fits on one line, `agent/graph.py` (14) breaks as `agent/graph.p` / `y`, and
`tools/runbooks.py` (17) breaks as `tools/runbook` / `s.py`. The wrap is by *character*, not by
word, so **any token over ~13 characters splits mid-path**.

**What was fixed:** the digit now travels with the words that identify it — `cli.py — P0` /
`shipped \`doctor\`` / `roadmap row P1.9` / `adds the other four`. Even misread, "roadmap row"
says where to look it up.

⛔ **What was deliberately not fixed: the mid-token path breaks.** The obvious repair — an explicit
`\n` inside the path — is the one thing that must not be done. The guard unescapes `\n` to a space
before matching citations (`scripts/check-diagram.py:118`), and its own comment records the day a
newline silently dropped the citation count 62 → 61 with no failure reported. **A cosmetic wrap is
cheaper than a citation the guard can no longer see.** Six labels carry an over-long path and all
six stay whole.

⚠️ **Milestone 5 caught the first attempt at this fix.** Rewriting `P0` as "phase 0" made the label
read better and broke the check that `cli.py` must state what shipped, which greps for the literal
`P0`. *The guard rejected an edit made to improve the drawing* — which is the whole point of having
one.

---

## Why one node-link graph, and not six encodings on one canvas

D-036 reversed an earlier decision, and **the earlier argument was not
wrong** — it is recorded here because it will be made again.

The claim was that this system states ten kinds of fact and a node-link graph is the right shape
for one of them, so the poster used a matrix, a sankey, a flame graph, an AND-chain, a heatmap, a
state machine, a grid and a timeline. What actually happened when each was reconsidered:

| the poster's encoding | what it was for | where it went |
|---|---|---|
| **matrix** — which specialist may call which tool | six crossing edges, and an **empty cell is a claim** | **flattened into the labels.** Each specialist names its own two ([docs/03](../docs/03-agent-and-tools.md):135–137), `read.py` says there are four — three names of two out of four *is* the matrix, empty cells included |
| **AND-chain** — the five promotion conditions | a chain is not a graph problem | drawn as a chain, `C1 > C2 > C3 > C4 > C5`. It was always a graph |
| **state machine** — `open → locked → quarantined` | the one-way property **is** a missing edge | drawn as a state machine. Section 11 |
| **grid** — the module layout | a tree | [docs/09](../docs/09-schemas.md) §9 owns the tree, and always did |
| **timeline** — P1.1 → P2.10 | schedule | the legend's phase colours, plus a `Pn.n` on every label. ROADMAP.md is the authority; a second timeline drifts |
| **sankey** — how an attempt ends | proportion between four outcomes | four sibling boxes. ⛔ **The proportions are runtime data and there is none yet** |
| **flame graph** — the trace | nesting and duration | not drawn. [docs/04](../docs/04-observability.md) defines the span vocabulary, and a drawing of nesting cannot be checked against anything |
| **heatmap** — does v4 beat v3? | per-case results | not drawn, and it should never have been. `loop/record.py` **generates** that table from committed artifacts (P2.10) |

🎯 **Three of the eight were displaying data, not structure.** At gate time there is no data, so
they were drawn from nothing — and a structural diagram that shows invented proportions is worse
than one that omits them, because the picture cannot say which of its cells were measured. **The
encoding argument was sound and it was applied one step past where it held.**

**The cost, stated plainly:** the matrix's crossing edges are gone rather than solved, and a reader
now reconstructs the tool assignment from three labels instead of reading it off a grid. That is a
real loss, taken deliberately, in exchange for one file that can be checked by a script and diffed
in review.

**ONE file, deliberately.** An earlier pass produced five Mermaid files — `v1-graph`, `v2-graph`,
`v2-state`, `attempt-outcomes`, `phase-1-run-score-sequence` — and a reviewer had to hold five
pictures in their head to see one system. The status taxonomy got drawn twice and started to drift
within the hour. ⚠️ **Finding 2 below is the same failure caught by the same fix**: a contradiction
that spans two pictures is invisible in both.

---

## How it is drawn — four rules, each one bought by a failed draft

⚠️ **The boxes carry the rule, the comments carry the argument.** Draft 1 put every justification in
a node label; ten paragraph-sized boxes made a canvas nobody read. The rule now stays on the picture
in one or two lines and the reasoning lives in `//` comments in the same file, where anyone reading
the source is already looking. *(This rule was once justified by pixel counts. They are withdrawn
above; **one line is what a reader takes in from a box** carries it on its own, which is why the
conclusion did not move.)*

⚠️ **A node earns its place only if an edge in or out of it carries meaning its own label cannot.**
Draft 2 read as a circuit board — **59 nodes, ~60 edges**. The cause was not depth, it was
**inventory drawn as wiring**: `domain.py > Corpus`, `cli.py > generate.py`, four `get_*` tools each
wired to two specialists — edges carrying a listing that [docs/09](../docs/09-schemas.md)'s tree
already carries. Those left; every rule stayed. **Nesting** did the rest: the specialists became a
group inside `agent/`, and the promotion conditions a group inside the gate, which turned thirteen
wires into four and made the hop cycle legible for the first time. **The current file is 104 labels
and 65 checked citations.**

⚠️ **That label count jumped from 76 without the picture changing**, and the reason is a defect
the checker had all along: it read `label: "…"` only, so **edge** labels — written `A > B: text` —
were invisible to it. `D-025`, `results/<version>.json` and `D-039` sat on three real edges and
resolved against nothing. Fixed 2026-08-16. 🎯 **It is the same shape as the `\n` bug recorded in
the script: silent, and it fails in the *passing* direction** — and it was the worse of the two,
because [docs/07](../docs/07-diagrams.md) §2 is explicit that the edge is where the claim lives.
A guard that read only the boxes was checking the least load-bearing half of the picture.

⛔ **Emoji in the comments, words on the picture.** Eraser's renderer has no glyph for ⛔ or 🎯 —
at 1:1 they came out as **black striped fallback boxes on about twenty labels**, and ⛔ is what
marks every invariant here. Labels now carry words — `RULE`, `NEVER`, `WHY`, `OPEN`, `INVARIANT n`.
🎯 **The scaled overview hid this completely; only a 1:1 crop showed it** — which is the reusable
part, and the same reason [docs/07](../docs/07-diagrams.md) §5 wants the export committed and
looked at rather than assumed. *(Confirmed safe in labels: `§ · – — → ≥`.)*

⚠️ **The four style lines under `direction` are not decoration.** Eraser's **default `typeface` is
`rough`**, a hand-drawn sketch face, and every early render of this file was in it, unset.
`typeface clean` is most of what makes this read as an architecture diagram rather than a napkin.
⚠️ **`direction right` was tried and measurably does nothing here** — pixel-identical content
bounding box, 0.237% of pixels differing at all. The reasoning behind trying it was good; it is
recorded in the file as a disproof so nobody re-derives it as a reason to switch.

⛔ **Eraser is a tool here, never a dependency** ([docs/07](../docs/07-diagrams.md) §4: a blocking
gate must not be able to stall on somebody else's unpublished quota). It never enters
`pyproject.toml`, and **Mermaid in a fenced block remains the always-acceptable fallback.**

**Convention 3 is mechanically checked rather than trusted, because the thing that used to enforce
it was configuration.** Every node name must be a file or symbol that exists in this repo: decision
and defect IDs against the heading that *defines* each one — a decision can be referenced in twenty
places and defined in none — phase IDs against the roadmap, paths against
[docs/09](../docs/09-schemas.md) §9, and, inverted, that no file already on disk is labelled with
only a future phase. **65 citations, all resolving, at the last run.**

⚠️ **The checker itself is a local development tool and is deliberately not published.** It is
scaffolding for this file, not part of what touchstone is. Two of its own bugs are recorded in its
source rather than fixed quietly, both the same shape: a pattern that silently *matched nothing*
and dropped the citation count without reporting a failure. **A guard whose blind spot is "the
start of a line" is worse than no guard**, and it is worth saying out loud that the guard needed
guarding.

**Spec diagrams live in the docs and are not artifacts**: [docs/03](../docs/03-agent-and-tools.md) §1
(state, partial — no failure paths), [docs/04](../docs/04-observability.md) §4a (the run→span→score
sequence), [docs/06](../docs/06-api.md) §3 (compose topology), [docs/02](../docs/02-gates.md) §5
(the mine loop), [docs/08](../docs/08-memory.md) §5 (v5 memory).

---

## What drawing it found

⚠️ [docs/07](../docs/07-diagrams.md) §6: *"a diagram with none is usually a diagram that has not
been thought about."* Eleven things came out of drawing this and then checking it, and **none of
them were visible to any other mechanism in the repo**. ⚠️ **Two of the eleven were the diagram's
own errors** — 3 and the citation inside 10 — and both are left in place, because a findings list
that only ever finds other people's defects is the marketing document
DEFECTS.md refuses to be. **Four of the eleven became numbered defects —
DEF-002, DEF-003, DEF-004, DEF-005 — and all four are now fixed.**

1. ✅ **DEF-002 — fixed 2026-08-15.** `models` was declared as a file, a
   package and a directory in three places, and phase 0 had already committed the directory. Found
   by the rule that every node name must be a file that exists. Nothing else could have caught it:
   all three readings are plausible and none is executable yet. **The fix that mattered was the
   `mkdir -p` line** — the two prose corrections would have been undone by the next person to run
   the setup block.
2. 🔴 **`KVerdict > ScorePy` contradicted the diagram's own `NoArrow` note.** The state section drew
   the verdict going straight to the scorer while the gate section said in bold that no such
   arrow exists. Fixed: the verdict leaves as a **span**, and the scorer reads
   `results/spans/<version>.jsonl`. **The contradiction was only visible because both were on one
   canvas** — which is the argument for one file, made by the file.
3. 🔴 **This list said the checkpointer's SQLite path was unspecified. It was wrong.**
   `config.py`:22 has `CHECKPOINTS = ROOT / ".touchstone" / "checkpoints.db"`, with the comment
   saying it is deliberately *not* shared with the container's — and [docs/06](../docs/06-api.md)
   §3 draws both. The gap was invented by a search that read the **docs** and never opened the
   **committed phase-0 code**. ⚠️ **An absence is a claim and needs the same evidence as a
   presence**; "drawn as a gap, a name was not invented" sounded like rigour and was the opposite.
4. ⚠️ **The gate is not phase 1.** An earlier draft coloured it as phase 1, but `compare.py` is
   P2.4 — in phase 1 there is one version and nothing to compare it to. Phase colour is now
   load-bearing throughout, and it is convention 1 in the file.
5. ✅ **[docs/09](../docs/09-schemas.md) §9's file map called `read.py` "the five read-only tools"** while
   `search_runbooks` lives separately in `runbooks.py`. The split is 4 + 1, the diagram said so, and
   the tree now does too — the fifth is labelled **v3's whole delta**, which is what the split is
   *for*. ⚠️ Every other "five tools" in the repo is correct: five is the system total.
6. 🔴 **A span name was invented, and the correction then died with the file that made it.** The
   poster's flame graph named a `touchstone.attempt` span; the vocabulary in
   [docs/04](../docs/04-observability.md) has no such thing and the per-attempt span is
   **`touchstone.triage`**. Two file names went the same way — `results/vN.json` and
   `spans/vN.jsonl` became `results/<version>.json` and `results/spans/<version>.jsonl`, which is
   how the docs write them. ⛔ **And the `vN` spelling came straight back in the `.eraser`**, because
   the only place the fix had ever been recorded was the poster, which was then deleted. Corrected
   2026-08-15 in the diagram *and* in the checker, so it now fails rather than drifting. ⚠️ **The
   reusable part is the first half**: the every-name-must-exist check is a property of the *pass*,
   not of the diagram — the second drawing of one system invented a name the first had not.
7. 🔴 **The box labelled `THIS IS THE PRODUCT` was drawn as a black box.** The spine labels
   `compare.py` *"five conditions"* and the first draft then drew exactly one of them — the
   per-case regression check, which is condition 2. Conditions 1, 3, 4 and **5** were nowhere, and
   with them went every metric the gate actually reads: `escalation.f1`, `p95_latency_s`,
   `cost_per_correct`, `pass@1`. Section 10 now draws all five as a chain, and section 11 the
   `open → locked → quarantined | superseded` lifecycle as the **state machine it literally is**.
   ⚠️ **The tell was a word.** The draft's title used `ratchet` — D-028 retired
   that name, and said where the idea went: *"it moved from the name into the prose: condition 5
   now states it outright instead of leaning on the title."* **The retired metaphor was standing in
   for the mechanism the picture never drew.** Reaching for a name the project deliberately dropped
   is a reliable signal that something is missing, not a slip of the pen — and the name was a
   US-slang liability on a public artifact besides.
8. ⚠️ **Condition 5 is vacuous through v4, and nothing said so.** The regression suite arrives with
   `mine` and the `suite` verbs, which are **P3.3–P3.6, deferred** — so no case ever enters, the
   `locked` set stays empty, and the fifth condition holds by having nothing to check. It is drawn
   *because* it is vacuous: **a condition with nothing to do is the one most likely to be quietly
   dropped.** ⛔ The honest sentence is *"four conditions ran, five are specified."*
9. ✅ **DEF-003 — `k` had two values in the spec at once. Fixed
   2026-08-15.** [docs/02](../docs/02-gates.md) and [docs/05](../docs/05-scoring.md) both said
   *"default 5"*; D-030 rejected k=5, ROADMAP P3.1 and [docs/06](../docs/06-api.md) say `--k 3`, and
   `docs/02` contradicted itself nine lines apart. Found by having to write `3/3 → 2/3` onto the
   picture. **Drawing forces a number to be one number**, which prose never does. ⚠️ **The sweep
   found four more k=5 examples than the first pass did**, including one inside `DECISIONS.md`
   D-008 six lines below a line an earlier pass had already corrected — *the correction fixed the
   sentence it was reading, not the paragraph it was in.*
10. ✅ **DEF-004 — P2.2 contradicted a decision, and behind it phase 1 had
    a scorer with nothing to score. Fixed 2026-08-15 by
    D-037.** Found by having to give `score.py` a phase **colour**: a box
    cannot be two colours. What the scorer *reads* turned out to be settled — **D-007**, spans,
    never return values — so ROADMAP P2.2's "re-point `score.py` at spans rather than return
    values" described a migration the design had already rejected by name. ⚠️ **The finding
    underneath it is the one that cost something:** `telemetry.py` was phase 2, so **phase 1 ended
    with a scorer that had never read a span the agent produced.** D-037 moves it to P1.5 and
    strikes P2.2. ⛔ **This entry was written twice and cited a nonexistent source once** — both are
    recorded in DEFECTS.md rather than smoothed away.
11. 🔴 **DEF-005 — the answer key was one directory above where its own
    hash reads it.** [docs/09](../docs/09-schemas.md) §9's file map put `truth.json` beside the
    tiers; §5's `benchmark_hash()` — **in the same file** — reads `suite_dir / "truth.json"`, and
    `suite_dir` is the tier. ⚠️ **The path is not the point.** Inside the tier, the answer key is
    inside `benchmark_hash`; beside it, **an edit to the answer key would not change the hash, and
    promotion condition 1 would not catch it** — the exact lie D-006 exists to prevent. Found by
    the name check, which flagged `suite/truth.json` for the wrong reason and was right anyway.
    **Refines DEF-002's rule: a definition a program would execute outranks a tree a person drew,
    even in the same document.**

⚠️ **Two more came from the drawing process rather than the drawing** — DEF-006 (the repo
recommended a diagramming tool the artifact did not use, and no decision recorded the switch) and
DEF-007 (the gate's own table still said phase 1 was not cleared). Both are fixed, and **both were
invisible to every check in this repo, because no import breaks and no test reddens when a document
describing a process goes stale.**

---

## Open questions

**1 and 2 are answered. They are kept because the answers are decisions, and a decision with no
question in front of it reads as an assumption.**

### 1. ✅ What does `score.py` read in phase 1? — D-037

**Spans, from day one, exported to `results/spans/<version>.jsonl`.** `telemetry.py` moves from
P2.1 into **P1.5**, and P2.2 — *"re-point `score.py` at spans rather than return values"* — is
struck rather than scheduled. Phoenix becomes a *viewer* over the same export in phase 2 rather
than a dependency of scoring, and D-014 (CI scores committed span JSONL with no credential) is
satisfied from phase 1 instead of phase 2.

The rejected option was to score return values now and re-point later. It costs nothing today and
rewrites **the one component everything else exists to make meaningful** — and every test written
against the old shape stays green through the rewrite, which is the part that makes it dangerous
rather than merely expensive.

### 2. ✅ Is v1's single node the `synthesizer` object itself? — D-038

**Yes — the same node, the same `prompts/synthesizer.md`, with `findings == []`.**

The payoff is attribution, which is the whole product: if the decision layer is byte-identical
across v1 and v2, then **v2 − v1 measures the investigation layer and nothing else.** A separate
`prompts/v1_oneshot.md` would make the delta *"routing, plus a different prompt"* — two changes,
which is the thing D-021 exists to catch.

⚠️ **The check that this stays honest:** the synthesizer prompt must read naturally with an empty
findings list. If writing it forces an *"if there are no findings…"* branch, the nodes are not the
same node and the answer flips to a separate v1 prompt, recorded as a new decision.

### 3. ✅ What is `max_hops` at v2, and is it in `results/<version>.json`? — D-039

**`config.MAX_HOPS = 6`, and yes — next to `k`, with no `--max-hops` flag.**

**Only half of this was ever a judgement call.** The results-file half falls straight out of D-013:
a candidate is `(graph, prompts, parameters, provider, model)`, `max_hops` is a parameter, so two
rows differing on it while claiming to differ on the graph is the unattributable diff this project
exists to refuse. The absent flag follows from the same place — a flag lets a candidate's identity
move without a commit, so **editing the constant *is* the version bump.** `k` keeps its flag
because `k` is a parameter of the measurement, not of the specimen.

The value is the judgement: three specialists, each reachable twice. ⚠️ **It is a hypothesis and
the picture says so rather than showing the number** — no run has happened, and the first run is
v2, so there was never a version that did not already depend on the answer. **Both directions are
instrumented:** too small shows up as `hops_exhausted` (the ceiling fired instead of the supervisor
stopping, read off the last supervisor span's `next`), too large as `cost_per_correct_usd`, which
is already a promotion metric. Neither is new machinery.

### 4. ✅ Closed — and the empty list is the good outcome

⛔ **A diagram with no open questions is usually one nobody thought about** ([docs/07](../docs/07-diagrams.md)
§6), which is why this section is not simply deleted. All three closed into decisions, and D-038
already rejected the alternative by name: *an "open" question nothing is waiting on is a decision
with the record missing.* What sits on the canvas now is not a fourth question but the **falsifier**
of the one answer that is not a measurement.

---

## What this diagram claims, in one line

Per [docs/07](../docs/07-diagrams.md) §2, *"this changes X so that Y; nothing else moves"*:

**It draws the loop with the agent inside it, so that phase 1 can be built without deciding
anything phase 2 has already decided — and nothing is implemented until it is approved.**
