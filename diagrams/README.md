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
| [`loop.png`](loop.png) | The render of the above. **A convenience, never the record** — rebuilt **2026-08-24 for D-089…D-094**: `attempt_budget()` joins §8b as the critic's second tool, the force-terminate edge arrives red, and `unmineable` is demoted from an exit to an alarm. ⚠️ **The rebuild was triggered by a measurement, not by a hunch** — `git show ed86f41:diagrams/touchstone.eraser \| grep -vE '^\s*//'` against the current comment-stripped file showed **57 changed rendered lines**. Comments do not render, so the diff that matters is the stripped one; a bare `git log` answers a different question. Before that it was rebuilt **2026-08-23, twice in one day**. The first rebuild carried the `c1dd762` revert, which restored `a2c024725189` in the DSL while the committed render still read `tau2 1.0.1`, the one string DEF-055 exists to warn against. The second carried **D-082**: eleven edits to §8a and §8b that make the router the selector, hang `Cal` off it, and turn τ²'s three signals into the answer key. 🔴 **This cell has now gone stale five times** — 2026-08-20 through two 08-21 rebuilds, 08-21 through the revert rebuild, the revert rebuild through the D-082 rebuild **on the same day**, and that one through this. **A source file and its render are two artifacts; correcting one is not correcting the other.** The row that names a render is the row nothing sweeps backwards to, and saying so in the row has not once been enough | — |
| [`sequence.eraser`](sequence.eraser) | **One simulation, and every boundary it crosses** — lifelines ordered by distance from the developer's process. It draws the three things a flowchart structurally cannot: the **order** of the telemetry wiring steps, the checkpoint landing after every step, and the scorer running later, in another process, from a file. **Its load-bearing element is a message that is not there** | phase 1 |
| [`sequence.png`](sequence.png) | The render of that. Same status. **Rebuilt 2026-08-24 for D-089…D-094** — the `Budget` lifeline, its two messages inside the `config.MAX_ATTEMPTS` block, the two post-loop exits, and a corrected `Gauntlet > CLI` line: **38 changed rendered lines**, same stripped-diff method as the row above. 🎯 **And the hosted copy confirmed its own staleness independently** — the DSL Eraser held still read `n = 5 attempts` and had no `Budget` participant at all. Two sources for one conclusion is what makes it a measurement. Before that it was **rebuilt 2026-08-23 for D-082** — six mining-loop lifelines and thirteen messages joined the DSL, so the diff stopped being empty and the render had to follow. 🔴 **This cell said the opposite earlier the same day**, and it was *right when written*: `git diff 6509bae HEAD -- diagrams/sequence.eraser` was empty at that hour, the revert having restored the file byte-for-byte, so a bare `git log` made the source look newer than its PNG while nothing had actually moved. ⚠️ **A `NOT rebuilt` note is a measurement with a shelf life of one edit** — it records a diff that was empty, never a file that will stay still. **Check the diff, not the log, and check it again rather than reading this cell** | — |
| [`agents.mmd`](agents.mmd) | 🆕 **The mining loop's three agents — D-082.** router (rubric) → curator (writes the predicate) ⇄ qa/critic (runs it, checks the work), then the gauntlet's three mechanical gates. **All three agents propose; none of them gates** — the one green node is the only thing that decides, which is the invariant drawn at its smallest. Mermaid, local, no hosted copy | phase 3 |
| [`phase1.mmd`](phase1.mmd) | 🆕 **The attachment diagram** — where touchstone joins τ²-bench: the adapter seam at `llm_utils.py:355` and the enforcement point at `Environment.make_tool_call()`. **Mermaid, and local by choice** — it names symbols in another repo, and drawing them as unnamed boxes would hide the only structure it exists to show. It is why D-068 had to widen the approved-repo set | phase 1 |

## How a render is rebuilt, and what rebuilding has found

**CREATE-then-delete, never update** (DEF-034):

1. `manually_create_diagram` from the committed file — **creating first is deliberate**, because a
   failed create then leaves the stale diagram standing rather than nothing at all
2. diff the round-trip
3. delete the old hosted diagram, *after* the new one exists
4. export twice, until the content-addressed URL settles
5. **open it and look**

⚠️ **The re-export trigger is a change to a *rendered label*, and only `git diff` on the `.eraser`
answers it.** Two cases that look identical in the commit log and were decided opposite ways: on
2026-08-18 a comment-only edit round-tripped to a render differing in **878 pixels (0.0014%)** —
antialiasing, not a drawing — so `loop.png` was deliberately **not** replaced; on 2026-08-23 the
`c1dd762` revert changed two label lines (`tau2 1.0.1` → `commit a2c024725189`) and it **was**.
⛔ **File mtime, commit count and byte delta all say "changed" for both.** They are not the test.

✅ **CLOSED 2026-08-26 — both hosted diagrams were recreated from the committed `.eraser` files,
both PNGs were re-exported, and the metrics table below is re-measured.** Five rendered labels had
moved across P1.1 and P1.2: `touchstone.eraser:209` (`adapter.py — P1.1 ✅ shipped`, plus D-095 on
the same node), `:254` (`telemetry.py — P1.2 ✅ shipped`, plus the mlflow/OTel correction), `:255`
(the `D063` node, which described P1.1 in the future tense after it had shipped),
`sequence.eraser:98` and `:101`. Create-then-delete in that order, per DEF-034.

⚠️ **The deferral was written on 2026-08-25 with an explicit trigger, and the trigger fired the
next day** — which is the only reason it was a deferral rather than a skip. It read: *"P1.2
(`telemetry.py`) edits the same three labels again … one rebuild after P1.2 costs one
create-then-delete cycle, two rebuilds cost two, and the intermediate render would assert a span
that emits nothing."* That was right, and it is now **spent**. ⛔ **A deferral whose trigger has
fired and which gets rolled forward anyway is just a skip with better paperwork**, which is the
failure this whole file is a record of. The rebuild was named as the next diagram action, and it
was the next diagram action.

🎯 **What the open window cost, stated because the departure was knowing.** Across the two commits
between P1.1 and this rebuild the committed `.eraser` was the only current source: the hosted
copies and both PNGs asserted `P1.1` and `P1.2` as unshipped. **The guard does not catch this** —
`check-diagram.py` reads the `.eraser`, so it went green on the very labels that made the PNGs
stale. Same shape as the 🔴 row above — *a perfectly-rendered picture of the wrong system passes
every instrument in this repo* — with the difference that this one was recorded before the fact
rather than found after it.

🔴 **AND IT IS OPEN AGAIN, same day, now TWO labels — read the trigger before adding a third.**
P1.3 shipped `suite/benchmark/manifest.json`, so `touchstone.eraser:263`'s `Bench` node now says
`P1.3 ✅ shipped` and carries D-098's selection rule. **P1.5 then shipped `loop/score.py`, and
`ScorePy` (`:275`) took its shipped marker and D-099 the same day — exactly as the paragraph below
predicted it would**, and **the same label grew two more lines the same day for D-100** (the
payload is four `TypedDict`s; a *misspelt* termination reason passes mypy and every test).
⚠️ **That is one label edited three times, not three labels — the drift count is a count of
labels, not of edits**, and quoting it the other way would make a two-node redraw sound like a
six-node one. 🆕 **Seven labels behind as of 2026-08-26**, not two, and the number is
**derived rather than stepped**: `git diff <the commit that last wrote loop.png> -- touchstone.eraser`
names `Adapter`, `Bench`, `CliPy`, `Doctor`, `ReportPy`, `RunPy`, `ScorePy`. ⚠️ **A hand-incremented
drift count is the one number in this file that decays silently**, so re-run that command before
quoting it.

D-102 accounted for three of them by splitting three files. `Doctor` was the load-bearing one — its
label read `doctor.py`, and milestone 4 **failed on it**, because `docs/09 §9` had already been
updated to `doctor/`. `ScorePy` and `Adapter` no guard would have caught: nothing checks that a
label naming a file still *describes* what is in it. D-103 then added the rest — `CliPy` and
`RunPy` edited, and ⛔ **`ReportPy` is not a stale label at all, it is a node the render does not
contain**, which is a different kind of drift and the kind a reader cannot detect by looking. ⛔
**The sequence diagram is still NOT affected** — it has none of the seven — so one of the two
renders is stale, and re-exporting both would be the reflex, not the fix.

⚠️ **The prediction landing is what makes the deferral cheap, and it is worth naming.** The
trigger below was chosen because two named rows were going to move two named labels. One of them
has now moved, on the day forecast, at the line number forecast — so the batch is doing what it
was defended as doing, rather than quietly becoming an excuse. 🆕 **Both rows have now landed** —
`CliPy` (`:269`) took its shipped marker at P1.6 on 2026-08-26, at the line forecast. ⚠️ **The
prediction was right about the labels and wrong about the count**: P1.6 also *added* a node
(`ReportPy`) and two edges, which no row of the forecast anticipated, because the forecast was
built by reading which labels named files and no file existed to name yet. **A drift forecast can
only see the nodes that are already drawn.**

**Trigger: the phase-1 exit gate.** Not "the next build row", and the reason is arithmetic
rather than convenience: **two more rows flip a label on this same flowchart.** `CliPy` (`:269`)
says *"P1.6 adds run · score · suite"* — a future-tense claim P1.6 falsifies outright — and
`ScorePy` (`:275`) will need a shipped marker the moment `loop/score.py` is on disk, because
milestone 5 demands one for every `src/` file a label names. ⚠️ **P1.4 flips nothing**: checked,
`tests/unit/test_invariants.py` appears only in a `//` comment at `:55`, and comments do not
render. So the count is **two**, not three — the first draft of this paragraph said three and was
reading a comment as a node. One rebuild at the gate costs one create-then-delete cycle; three
rebuilds cost three, and every intermediate render is stale the moment the next row lands. ⚠️ **The previous deferral made exactly
this argument and was honoured, which is the only evidence that this shape works here.**

⛔ **What makes this a deferral rather than a skip, restated because the last block says the
distinction is the whole file:** the trigger is a named event, the stale label is named by file and
line, and the diff is one node. **A reader who needs the current picture has it in three lines
above** — which is what the departure has to buy to be worth taking.

**What the looking has found — and not one of these by a guard:**

- 🔴 **A perfectly-rendered picture of the wrong system passes every instrument in this repo.**
  Milestone 7 measures *clipping* — four clear edges, content filling 98%+ — which is a property
  of the export, not of the content. Both PNGs passed it the whole time they were 3 and 2 commits
  behind their sources, naming a corpus that no longer existed and a gating number that was wrong.
- ⛔ **A picture is not a place a claim goes to be safe.** The flowchart's phase-1 exit gate still
  asserted `reward_breakdown is {DB, COMMUNICATE}` long after that was corrected — found by reading
  the DSL line by line before porting it (DEF-036).
- ⛔ **A pointer at another file's error is a claim with a shelf life.** A rendered label asserted
  that a README line contradicted the Anthropic-only rule; the README had been fixed first, so the
  *diagram* was the stale document. **Nothing here sweeps backwards from a fix to the documents
  pointing at it.**
- 🔴 **Nine labels opening with `⛔` or `🔴` rendered as identical featureless black bars** in the
  flowchart, and as *zero pixels* in the sequence diagram — after the DSL round-tripped byte for
  byte, the hash settled and the extent read 98.4% (DEF-027). **Now milestone 9**, so it is checked
  rather than remembered.
- ⚠️ **Ink and extent are measured, never eyeballed.** A shrinking canvas with rising ink got
  tighter; a shrinking canvas with falling ink is one to go and look at. ⛔ **State the comparator**
  — the same render reads 10.63% loose and 3.25% at `convert("L") < 200`.

**Five tracked files, and that is the whole directory.** `touchstone.html` — a hand-written poster
drawing the same system in six encodings — **was deleted 2026-08-15** by D-036, which records why
and what it cost. `.check.log` is a run log, gitignored.

⚠️ **Every file that is not a section of `touchstone.eraser` has to justify itself in one row**
([docs/07](../docs/07-diagrams.md) §5), and that is the mechanism stopping the count drifting back
toward the poster. `sequence.eraser` is a **replacement** — [docs/04](../docs/04-observability.md)
§4a carried a Mermaid `sequenceDiagram` of the same run until 2026-08-17, and it is gone.
`phase1.mmd` is the only one that draws a *boundary between two systems* rather than another view
of this one, which is why it needed D-068 to widen the approved-repo set.

### The settled renders — **both rebuilt for P1.1–P1.2, 2026-08-26**

| | `loop.png` | `sequence.png` |
|---|---|---|
| Frame | 6436 × 12462 — **80.2 MP** *(was 6411 × 12413, 79.6 MP)* — both axes grew, by 0.4% each, on a DSL that gained two lines of label text. ⚠️ **A ratio pair on the same side of 1.0 is the one case [ERASER-NOTES](ERASER-NOTES.md) finding 3 does NOT call a layout change** — this is the content reading, and it is the smallest one in this table. Both exports ran at `imageQuality: 1`, so quality was held constant | 9182 × 11400 — **104.7 MP**, byte-frame **identical** to the previous rebuild *(was 9182 × 11400)*. Two labels grew and the frame did not move at all: the sequence renderer sizes lifeline columns off the widest label, and neither edit took its column's widest slot |
| On disk | 4.17 MB *(was 4.12 MB)* | 4.98 MB *(was 4.94 MB)* — the 2026-08-23 jump from 0.77 MB was **5.7×** and it was content, not quality: the DSL went from 13 lifelines to 19, and is 20 now |
| Padding, L / T / R / B — **background-difference bbox, the guard's own comparator** | 46 / 75 / 42 / **74** *(was 46 / 75 / 42 / 73)* | 27 / 27 / 23 / 23 — **now identical across three consecutive rebuilds**, two of which changed the content *(was 27 / 27 / 23 / 23)* |
| Content fills — `min(bboxW/w, bboxH/h)`, same comparator, milestone 7 | **98.6%** of the frame — **unchanged across all five rebuilds**, and this one moved both axes in opposite directions underneath it. That is what makes it the guard's comparator rather than extent | **99.5%** *(was 99.4%)* |
| Ink — pixels with `convert("L") < 200`, as a share of the frame | **1.44%** *(was 1.41%)* — ink and area both rose, which is the plain content reading and the one this table sees least often | **3.61%** *(was 3.60%)* — a frame that did not move and ink that rose by 0.01 pt: 73,980 pixels differ from the previous render out of 104.7 M, **0.07%**, and that is the two edited labels plus the reflow around them |
| ⚠️ The frame moved BOTH WAYS inside one day | The revert rebuild came back **4.8 MP smaller with ink up 0.14 pt** on a DSL that grew by 6 characters; the D-082 rebuild hours later came back **10.1 MP larger with ink down 0.11 pt** on a DSL that grew by 916 rendered characters. ⛔ **Neither direction is a content signal on its own.** Per finding 1, a freshly created diagram is laid out tight and a long-edited one carries its accumulated canvas — so extent tracks *the age of the hosted object* at least as much as the drawing. **Extent is only comparable between two diagrams of the same age**, which is a strange sentence and a true one. What did hold across every rebuild is the fill: 98.6%, four clear edges, `check-diagram.py` milestone 7. 🆕 **2026-08-24 is the first rebuild here where the direction question has an answer**, and it is not this cell's answer — it is finding 3's. The axes moved **opposite in sign** (0.979 wide, 1.194 tall), and a ratio pair straddling 1.0 is a layout change by a rule that was already written down. ⛔ **This cell hedged the question for four rebuilds while the test for it sat two files away.** The lesson is not about canvases: *before hedging a measurement, check whether a recorded method already decides it* — rule 12. The fill held at 98.6% underneath it either way | ⛔ **This cell used to read "the control: nothing touched this file"** — and the control is gone, because D-082 touched it. Six lifelines and thirteen messages arrived, the frame went 2.9× wider, and ink fell 0.08 pt: **more content, spread over more canvas.** A column kept as a control is a control until the next decision needs it |
| ⚠️ Ink needs its method stated | The first pass of these two numbers read **2.95%** and **13.76%** — a *looser threshold*, not a different image. Two measurements of the same PNG disagreed by 3×, and the figure is meaningless without the comparator. **Extent was unaffected**, which is why it is the check the guard runs. ⛔ **AND THE SWEEP STOPPED ONE ROW SHORT — found 2026-08-18, on the pass that recreated the hosted flowchart.** The two rows above use a *third* comparator (`ImageChops.difference` against the corner pixel), not `< 200` and not the loose threshold, and neither said so. Measured at `< 200` the same padding reads **65 / 61 / 61 / 62** and **28 / 28 / 40 / 30**; at the loose threshold, **46 / 61 / 61 / 58** and **27 / 27 / 40 / 23**. Three comparators, three answers, one unlabelled row. The bottom cell also read **59** against a measured **58** — an off-by-one that no threshold explains and that survived because the row it sits in had no method to check it against. 🔴 **AND A FOURTH COMPARATOR APPEARED ON 2026-08-24, on the pass that filled in the row above.** The first measurements of these two renders read **5.658%** and **14.248%** — `abs(p − bg) > 24` on a 4× downscale, a comparator no row here uses. Against this row's `< 200` the same two files read **1.41%** and **3.60%**: a **4.0×** and **4.0×** gap, on bytes nobody touched in between. ⛔ **Four comparators now, four answers, one PNG.** The number in an ink cell is a property of the measurement and not of the render, which is why the cell above is titled with its threshold and this one exists at all |
| Method | ⛔ **delete the hosted diagram** → `manually_create_diagram` from the committed file → export twice → **keep the new one**, per finding 1. Then the four-edge check in finding 2a **and the extent check in finding 7** | same, and it ran twice — the first render was missing a message the DSL contained, finding 4 |
| Export settings — ⚠️ **`theme` was OMITTED on both 2026-08-26 exports** and both rendered light, so the default is light; the cells below name it because earlier passes passed it explicitly | ⛔ `background: true, theme: light, imageQuality: **1**` — quality 2 returns `{"note":"Error rendering diagram"}`, finding 7 — ⚠️ **and quality 2's failure changed shape on 2026-08-21; see the row below.** The content-addressed URL is keyed on the render, so **a failed export poisons its own cache entry**: re-requesting quality 3 returned the same 0-byte object at the same `x-goog-generation`, and only a different quality produced a different key. ⛔ **Retrying an export is not retrying a render** | ⛔ `background: true, imageQuality: **2**` — and **finding 9 is now disproved as a property of the setting.** On 2026-08-26 quality 1 rendered this diagram *correctly*: 4591 × 5700, **3.55% ink**, four clear edges — exactly half the quality-2 frame on both axes, which is finding 3's linear-multiplier property behaving as documented. 🔴 **`imageQuality` is a scale factor, not a render mode**, so a blank at one setting can never have been *caused* by the setting; it was one attempt that failed. ⚠️ **Quality 2 is still what ships here** — half-scale is a real render and an unreadable one at this label density |
| ⚠️ The quality that works | **1** — re-confirmed 2026-08-21 at 5.46% ink, four edges clear. ⚠️ **But its two failure modes both got QUIETER on that date.** Quality **2** no longer returns `{"note":"Error rendering diagram"}`; it returns a **0.03%-ink blank** — 2.9 MB, correct dimensions, every pixel of content in the top-left corner (bottom padding 14563 of 15266). Quality **3** returns a **0-byte object under HTTP 200**, `md5=1B2M2Y8AsgTpgAmY7PhCfg==`, which is the hash of the empty string. ⛔ **Both would have committed as a healthy PNG.** An error string is a gift; a 2.9 MB blank is what this table exists to catch. 🔴 **AND ON 2026-08-23 IT FLIPPED BACK.** Quality 2 on the D-082 rebuild returned `{"note":"Error rendering diagram"}` again — the loud form, two days after this cell recorded it going quiet. ⛔ **So the failure mode is not a property of the setting; it is a property of the render attempt.** A cell that says *how* an export fails cannot be relied on to predict the next one — only *that* it fails can, and only after measuring. Quality 1 then worked first try, 4 clear edges, 1.52% ink. ✅ **Re-confirmed 2026-08-24 on the D-089…D-094 rebuild** — quality 1, first try, four clear edges, 1.41% ink, and **no failure of any shape was provoked**, because quality 2 was not attempted. ⚠️ *Not re-testing a known-failing setting is the cheap choice and it is also why this cell can only ever describe the last attempt* | **2** — ⚠️ **re-confirmed 2026-08-23 on the D-082 rebuild**, which was the first time this diagram's setting had been retested since it was written, and **again 2026-08-24**: quality 2, first try, four clear edges, 3.60% ink. 🔴 **2026-08-26 broke the pattern in both directions at once.** Quality 2 returned `{"note":"Error rendering diagram"}` **twice**, then rendered correctly on the **third** attempt with nothing changed between them; quality 1, tried in between as a fallback, produced a **valid half-scale render** where this cell had recorded a blank. ⛔ **So neither half of the old sentence survives: 1 is not a blank, and 2 is not reliable — it is retryable.** The rule that does survive is two rows up: the failure mode belongs to the *attempt*. ⚠️ **Two identical calls disagreeing means a single failed export is not evidence about a setting** — it takes a third call to tell a broken setting from a bad attempt, and this table spent two entries not knowing that |
| ✅ Hosted is byte-identical to its file — **the open item cleared itself, 2026-08-24** | This row read *"hosted is ONE COMMENT EDIT BEHIND, on purpose"* and named its own trigger: *the next rendered-label change recreates the hosted copy from the file*. D-089…D-094 was that change. 🎯 **Verified rather than assumed** — the create response's `.code` diffed against the committed file: **43,242 characters and 45,188 bytes on both sides, `diff` clean.** The verification was free, and it only happened because the MCP response overflowed and had to be re-read from disk with `jq` — ⚠️ *an inconvenience produced a stronger check than the one that was planned* — ✅ **and it held on 2026-08-26 too: 43,349 characters / 45,497 bytes, `jq -r .code | diff` clean**, on a DSL transcribed by hand out of four `sed` chunks, which is the most error-prone path this file has ever used to reach the API | ⬑ same check, same result: **13,492 characters, 14,658 bytes, `diff` clean.** ⛔ **It was worth running separately rather than inferring from the loop column** — this file's hosted DSL was known stale before the rebuild, still carrying `n = 5 attempts` and no `Budget` lifeline, so *"created from the committed file in the same operation"* was an assumption until it was diffed. ⚠️ **And the first read of it was off by one character**: 13,491 against a file of 13,492, because a raw write of the JSON string drops the trailing newline that `jq -r` restores. **The gap was in the reader, not the file** — which is the same shape as the off-by-one recorded two rows up. ✅ **2026-08-26: 13,540 characters / 14,712 bytes, identical.** 🎯 **And the method is now general** — this response did *not* overflow, so there was no file to `jq`; the create response was recovered from the **session transcript JSONL** instead, which carries every tool result whether or not it was persisted. ⛔ **There is therefore no longer an excuse to infer this row rather than measure it** |
| Hosted | ⛔ **one diagram per Eraser file** — they shared a file until 2026-08-17 and **rendered on top of each other** (DEF-022, finding 6). `no-link-access`. The workspace and file IDs are deliberately not printed here — they name objects in a private account, and a reader can check nothing with them | ⬑ |

🔴 **Every cell in the two columns above was re-measured 2026-08-21 and every one of them had gone stale — including `sequence.png`, which nothing in this session touched.** The `loop.png` column described a 6439 × 9505 render; the file on disk was 4873 × 7633 before this edit and is 6574 × 9769 after it. The `sequence.png` column described 5069 × 6252 / 1.88 MB against a file that is 3032 × 3457 / 0.73 MB. **This is rule 22 — nothing sweeps backwards from a re-export to the table that measured it** — and the giveaway is that the *stale* column belongs to a diagram no edit in this session went near. ⚠️ A metrics table with no owner goes stale on somebody else's commit.

⛔ **`background: true` is not cosmetic, and omitting it produces a failure that reads as a
different failure.** The default is a transparent canvas. `PIL`'s `.convert("RGB")` turns every
transparent pixel **black**, so `scripts/check-diagram.py` milestone 7 finds content on all four
edges and reports the render as **CLIPPED** — sending you to re-render a diagram that rendered
perfectly. Measured 2026-08-17: `sequence.png` came back 0/0/0/0 instead of 27/23/27/40. The guard
now checks the alpha channel first and says `nobg`, because *a guard that fails for the wrong
reason costs more than one that does not fire.*

🔴 **And it was skipped anyway on 2026-08-22 — by the reader of this file, four days after it was written.** Both PNGs were exported without the flag, came back at `alpha255` **11.6%** and **10.5%**, and were only caught because the ink measurement read **89.54%** and **53.31%** — `.convert("L")` on RGBA drops alpha, so the transparent pixels measured as solid black. ⚠️ **The instrument that caught it was not the one aimed at it**: milestone 7's `nobg` check never ran, because the re-export happened before the guard did. A recorded step is not a mechanism, and this is the second time on this file that a paragraph failed to prevent what it describes.

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
| the gate audit | **+13 declarations, +2 groups, +6 edge lines** — §14's `DiagGate` and four exit gates, `Insuf`, the gauntlet's five gates broken out of a label | 7887 × 12420 → **7953 × 16738** | **+66** | **+4318** |
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
that shipped is `imageQuality: 1` — quality 2 has not rendered this diagram since 2026-08-17
(finding 7), and ⚠️ **it has not been re-tried since either**, so read that as untested rather than
settled: the same error on the sequence cleared on a third identical call on 2026-08-26 —
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
# 109 declarations · 17 groups · 96 edge lines · 20 of the 109 carry no colour · 24,243 rendered chars
# re-derived 2026-08-24, AFTER D-089…D-094 added MBudget, MEdge and four edges to §8b. It read
# 107 · 17 · 92 · 20-of-107 · 21,912 the day before, 106 · 17 · 88 · 20-of-106 earlier THAT day,
# and 86 · 15 · 57 · 39-of-86 before that. Twice in one day is the point: this line goes stale on
# the edit that is being made, not on some later one.
body() { grep -vE '^\s*//' diagrams/touchstone.eraser; }
body | grep -E '^\s*[A-Za-z][A-Za-z0-9_]*\s*\[' | grep -v '^legend' | wc -l   # declarations
body | grep -E '^\s*[A-Za-z][A-Za-z0-9_]*\s*\[' | grep -v '^legend' | grep -c '{[[:space:]]*$'
body | grep -cE '^[A-Za-z][A-Za-z0-9_]* *(<>|-->|>)'                          # edge lines
body | grep -E '^\s*[A-Za-z][A-Za-z0-9_]*\s*\[' | grep -oE 'color: [a-z]+' | sort | uniq -c
body | wc -m                                  # rendered chars — the re-export trigger
```

🔴 **BOTH CENSUS LINES WERE STALE WHEN RE-RUN ON 2026-08-23, AND THAT IS THE FINDING.** The
flowchart's read `86 · 15 · 57` against a measured `106 · 17 · 88` — the diagram grew sections 8a,
8b, 8c and 11b and no one re-ran the command the comment exists to hold. ⛔ **A recorded command
does not run itself.** The comment above it says *"re-derive it, never step it by hand"*, and the
failure was neither: it was **not derived at all** on the four edits since. **Writing the command
down solves the reproducibility problem and not the freshness problem** — those are two problems,
and only the first one has been solved here. *(Cross-check: `check-diagram.py` milestone 8 prints
`47 message labels scanned in sequence.eraser`, independently confirming both earlier figures were
wrong. It printed `34` for the whole of the week the census claimed `26`.)*

⚠️ **`legend` is excluded and that is the whole reason this has to be written down.** It matches
the declaration shape exactly, so counting it gives **87**, and 86 versus 87 is precisely the kind
of drift nobody can adjudicate a week later. The legend is a key, not a node. **A census figure
that cannot be reproduced from a recorded query should be discarded rather than corrected.**

And for `sequence.eraser`, where the same trap is waiting under a different name:

```bash
# 20 participants · 51 messages · 8 of them self · 15 dashed returns · 5 blocks · 7,853 rendered chars
# re-derived 2026-08-24, AFTER D-089…D-094 added the Budget lifeline and its four messages. It read
# 19 · 47 · 8 · 13 · 5 · 6,870 the day before, 13 · 34 · 6 · 9 · 4 · 4,402 earlier THAT day, and
# 11 · 26 · 6 · 6 · 4 · 3,716 before that — the third of those was stale on a file NO commit since
# 6509bae had touched, which is the point: a census goes stale on ITS OWN history as readily as on
# someone else's.
# ⛔ THE SELF-MESSAGE FIGURE HAD NO COMMAND FOR THREE PASSES. It has one now, below. A figure in a
# comment that names no query is the thing this section says to discard rather than correct.
body() { grep -vE '^\s*//' diagrams/sequence.eraser; }
body | grep -E '^[A-Za-z][A-Za-z0-9_]* *\[' | grep -vE '^(loop|alt|else) ' | wc -l   # participants
body | grep -cE '^\s*[A-Za-z][A-Za-z0-9_]* *(-->|>) *[A-Za-z]'                       # messages
body | grep -cE '^\s*[A-Za-z][A-Za-z0-9_]* *--> *[A-Za-z]'                           # dashed returns
body | awk '{ if (match($0, /^[ \t]*[A-Za-z][A-Za-z0-9_]*[ \t]*(-->|>)/)) {
  split($0, f, /[ \t]*(-->|>)[ \t]*/); gsub(/^[ \t]+/, "", f[1]);
  split(f[2], g, /[^A-Za-z0-9_]/); if (f[1] == g[1]) c++ } } END { print c+0 }'   # self-messages
body | grep -cE '^\s*(loop|alt|else) *\['                                            # blocks
body | wc -m                                          # rendered chars — the re-export trigger
```

⛔ **`loop`, `alt` and `else` are the `legend` of this file.** They open with `[` and match the
participant shape exactly, so counting without the exclusion gives **24 declarations for 20
lifelines** — and 20 is independently confirmed by the colour tally in the check below. ⚠️ **24,
not 25, because the count is anchored at column 1 and one of the five blocks is nested** — which is
its own small lesson: the exclusion and the anchor are two filters, and quoting the difference as
*"the block count"* would fuse them. **Two files, two different keywords, the same
off-by-a-keyword**; the parallel is the reason both commands are printed rather than described.

✅ **Two independent cross-checks, and both hold at 2026-08-24.** The colour tally sums to
`blue 5 · green 3 · grey 3 · orange 6 · red 3` = **20**, matching the participant count from a
different query. And `scripts/check-diagram.py` milestone 8 reports *"51 message labels scanned"*
from an independent parser, matching the message count. *(2026-08-23 they read 19 and 47; the two
agreed then too, which is what makes their agreeing now worth something.)* **Two counts derived by different code
agreeing is worth more than either one stated twice.**

🎯 **The last line is the one that gets used most.** Comments render no pixels, so a re-export is
triggered by a change to `body`, **never by a change to the file**. Compare it against
`git show HEAD:diagrams/touchstone.eraser | grep -vE '^\s*//' | wc -m`; if they match, `loop.png`
and the hosted copy are both still correct and re-uploading buys nothing.

⚠️ **It is a column you scroll**, so read it top to bottom; section 1 is the corpus and every later
section follows the order an attempt actually moves through. ⛔ **That figure was taken under the
two-export settle rule below** — a single export can return the *previous* render, and a figure
taken any other way is not comparable to this one.

---

## Eraser tool findings — moved

📄 **[ERASER-NOTES.md](ERASER-NOTES.md)** — ten findings about the diagramming tool, each one
bought by a wrong artifact. Two of them are enforced by `scripts/check-diagram.py` rather than
by being read. **They are not about touchstone**, which is why they are no longer in this file.

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
