# Eraser — what the tool actually does

**None of this is about touchstone.** These are findings about the diagramming tool, kept
because every one of them cost a wrong artifact first: the tool accepts something, echoes it
back unchanged, and renders nothing. **Split out of [README.md](README.md) on 2026-08-23** —
that file is the index for the diagrams, and a tool notebook is not an index.

⛔ **Findings 5 and 8 are enforced in code, not by this page.** `scripts/check-diagram.py`
milestone 8 rejects an opening `[` in a sequence message label, and milestone 9 rejects a `⛔`
or `🔴` in any rendered label. **A finding that only lives in prose is a finding you will
rediscover.** The rest of this page is the argument behind those checks, plus the ones no
static check can make.

---

## The ten findings

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

🔴 **Third measurement, 2026-08-23, flowchart, and it inverted again.** Diagram
`b_gZk32ZtUtP9GgrmqOt`, minutes old, `background: true`, no `theme` passed:

| quality | result |
|---|---|
| **3** | 🔴 `{"note":"Error rendering diagram"}` — **twice, identically** |
| **1** | ✅ 5608 × 10345, ink 1.63% at `< 200`, four edges clear |

Two days earlier quality **3** rendered this same content at 11217 × 20662 and quality **1** was
the mode that had failed before that. **Three measurements, three different verdicts, one
flowchart.** ✅ The loud `{"note": ...}` string is back, which is the good failure mode — the
2026-08-21 row above records the same setting failing *silently*, as a 2.9 MB blank.

⛔ **So the table at the top of this finding is not a lookup — it is the evidence that there is
nothing to look up.** Reading a quality out of it is the exact mistake finding 9 exists to
document.

**The rule: export at both qualities, measure ink and extent, keep the one that passes. Never
carry a quality forward from another diagram, or from this diagram last week.** The flowchart's
quality-2 error reproduced on a diagram ID created minutes earlier, so it is a property of the
content, not of a long edit history — and that means it can change when the content does.

⚠️ **And measure ink against the MODAL grey level, not a fixed threshold, if the theme can vary.**
`< 200` reads a dark-theme export as 99.999% ink. `abs(p - mode) > 24` over a 4× downscale is
correct on both themes. The `< 200` figures in this file are all light-theme exports and stay
comparable to each other — ⛔ **do not compare them against a dark one.**

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

### 11. The renderer wraps labels mid-token, producing a wrong citation that *resolves*

DEF-038, extending DEF-029. `llm_utils.py:355` renders as `llm_utils.py:35` + `5` on the next
line. 🔴 **The failure is that the truncated form is a valid line number**, so it does not look
wrong — it looks like a different, real place in the file.

Pre-existing and accepted; no static check can catch it, because the DSL is correct and only the
render is not. ⛔ **The mitigation is a reading rule: take a line number off the `.eraser` file,
never off the PNG.**

