"""The invariants of [docs/01] §6 that can be asserted without running anything — P1.4.

Static, and deliberately so. The invariants that need a run (3, 8, 15, 16) need machinery
that does not exist yet, and a test that imports τ² costs 1.71 s against a 2-second gate for the
whole suite. What is here instead is the half that a source can answer: which module is
allowed to reach a model, and which fields our code may never read. Both fail on the edit that
would break them rather than on the run that would reveal it.

`ast`, never `grep`. A substring is not a symbol — `evaluation_criteria` appears in this
docstring, and a text scan would flag the file that enforces the rule. The parser sees names.

Coverage of §6 from here, stated so the gaps are visible rather than implied:

    1           covered at our boundary, by test_no_module_reads_the_answer_key
    7           covered elsewhere: scripts/freeze-benchmark.py --check, test_benchmark_freeze.py
    3, 8, 15, 16    need a run; they land with loop/score.py (P1.5) and the gates (phase 2)
    11, 12      vacuous until the gauntlet fills the regression manifest (D-030)
    13, 14      need specialist spans; un-retired by D-071, not yet buildable
    new         no model in any gating path, by test_only_the_seam_and_the_doctor_may_reach_a_model
    new         no credential in CI (D-014), by test_ci_carries_no_credential_and_calls_no_model
    new         one span vocabulary (D-017), by
                test_no_span_attribute_is_named_outside_the_openinference_vocabulary
"""

import ast
import io
import re
import subprocess
import tokenize
from collections.abc import Iterator
from pathlib import Path

from touchstone.config import ROOT

SRC = ROOT / "src" / "touchstone"

# rglob, not `SRC.glob`, and keyed on the dotted path, not `p.stem`: two `__init__.py` files
# share a stem, so a dict keyed on it silently dropped a module from every assertion (DEF-069).
MODULES = {
    str(p.relative_to(SRC).with_suffix("")).replace("/", "."): ast.parse(p.read_text(), p.name)
    for p in sorted(SRC.rglob("*.py"))
}
assert len(MODULES) == len(list(SRC.rglob("*.py"))), "a module was swallowed by a key collision"


def test_no_comment_block_buries_its_argument_in_a_paragraph() -> None:
    """The argument goes to the ledger; the comment says what you need at the line — D-101.

    Two caps, because one is evadable and the other is the thing that actually rots:

        lead    at most 6 unstructured lines before the first indented point. A paragraph
                is what nobody re-reads and what silently goes stale.
        run     at most 14 lines total. Without this the lead cap is dodged by prefixing
                every line with a dash.

    A point is any `#` line indented three or more spaces past the marker, which covers
    both `- like this` and the labelled form `SPLIT — like this`.

    Docstrings are exempt: they carry the contract, and capping them pushes detail back
    into comments, which is the failure this rule exists for. `scripts/` is in scope — it
    was not on the first pass, and the three longest runs in the repo were sitting there.
    A guard's scope is a claim about where the rule holds, so an unlisted directory reads
    as exempt.
    """
    lead_cap, run_cap = 6, 14
    bad = []
    for d in ("src", "tests", "scripts"):
        for path in sorted((ROOT / d).rglob("*.py")):
            lines, i = path.read_text().splitlines(), 0
            while i < len(lines):
                if not lines[i].strip().startswith("#"):
                    i += 1
                    continue
                j = i
                while j < len(lines) and lines[j].strip().startswith("#"):
                    j += 1
                block = lines[i:j]
                points = [k for k, b in enumerate(block) if b.strip()[1:].startswith("   ")]
                lead = points[0] if points else len(block)
                if lead > lead_cap:
                    bad.append(f"{path.name}:{i + 1} lead {lead} > {lead_cap}")
                elif len(block) > run_cap:
                    bad.append(f"{path.name}:{i + 1} run {len(block)} > {run_cap}")
                i = j
    assert not bad, f"lead with the point, then list; the argument goes to a ledger: {bad}"


# Emoji and the marker glyphs, not the arrows and rules: `->` and box-drawing are typography.
MARKUP = re.compile(
    r"[\U0001F300-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F]"
    r"|\*\*|(?<![\w*`])\*[^*\s][^*]*\*(?![\w*`])"
)


def _prose(path: Path) -> Iterator[tuple[int, str]]:
    """Yield (lineno, text) for each run of prose in `path` — a docstring, or a comment block.

    Runs, not lines, because an italic span that wraps a line is invisible to a per-line
    match: the opening `*` and its partner sit on different lines and neither looks like
    markup alone. Found in `check-diagram.py`'s own module docstring, where the guard had
    been green over it.

    Real string literals are excluded on purpose: `doctor.MARK` and `check-diagram.BAR_GLYPHS`
    are glyphs the program prints, not prose about the program.
    """
    src = path.read_text()
    docstring_lines: set[int] = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            first = node.body[0] if node.body else None
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
                and first.value.end_lineno is not None
            ):
                docstring_lines.update(range(first.value.lineno, first.value.end_lineno + 1))
    comments = {
        t.start[0]
        for t in tokenize.generate_tokens(io.StringIO(src).readline)
        if t.type == tokenize.COMMENT
    }
    run: list[str] = []
    start = 0
    for i, line in enumerate([*src.splitlines(), ""], 1):
        if i in docstring_lines or i in comments:
            start = start or i
            run.append(line)
        elif run:
            yield start, " ".join(run)
            run, start = [], 0


def test_no_comment_or_docstring_carries_markdown_or_emoji() -> None:
    """Python prose is plain sentences, not rendered markup — D-101.

    The markdown here came from the files this code is documented in, where it renders; in a
    `.py` it renders nowhere and costs a reader the decoding. Emoji and the bold and italic
    markers are the three that recur.
    """
    styled = [
        f"{path.name}:{n}: {line.strip()[:60]}"
        for d in ("src", "tests", "scripts")
        for path in sorted((ROOT / d).rglob("*.py"))
        for n, line in _prose(path)
        if MARKUP.search(line)
    ]
    assert not styled, f"plain prose, no markup: {styled}"


def _runtime_nodes(node: ast.AST) -> Iterator[ast.AST]:
    """Walk `node`, skipping the body of any `if TYPE_CHECKING:` block.

    A `TYPE_CHECKING` import is not a reach. `config.py` names `SettingSource` under one,
    and that block never executes — the annotation is a string at runtime. Adding `config` to the
    allowed set below would have made this test pass and would have been a false statement about
    the design: config would then be permitted a real SDK import forever, silently. The
    cheapest way to fix a failing invariant is to widen it, which is the one repair that cannot be
    detected later.
    """
    yield node
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.If) and "TYPE_CHECKING" in ast.dump(child.test):
            for orelse in child.orelse:
                yield from _runtime_nodes(orelse)
            continue
        yield from _runtime_nodes(child)


def imported(tree: ast.AST) -> set[str]:
    """Every top-level package name this module imports at runtime.

    The walk matters. Both places that reach the SDK do it inside a function — deferred
    so `doctor` can report that the import itself failed, and so the 1.7 s is not paid at
    startup. A check that read only module-scope imports would pass on every one of them.

    Args:
        tree: A parsed module.

    Returns:
        Root package names, e.g. `claude_agent_sdk` for `from claude_agent_sdk import tool`.
    """
    names: set[str] = set()
    for node in _runtime_nodes(tree):
        if isinstance(node, ast.Import):
            names |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            names.add(node.module.split(".")[0])
    return names


def attributes(tree: ast.AST) -> set[str]:
    """Every attribute name read anywhere in the module — `x.foo` yields `foo`."""
    return {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}


def strings(tree: ast.AST) -> set[str]:
    """Every string literal in the module."""
    return {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)}


def test_only_the_seam_and_the_doctor_may_reach_a_model() -> None:
    """The invariant the specimen swap created — no model appears in any gating path.

    Set equality, not a subset check: a third module reaching the SDK fails here and has to be
    argued for out loud. `adapter` is the single seam (D-095); `doctor` asserts the pin took,
    which is diagnostics and gates nothing.

    Stated as the rule — the seam, or anywhere under `doctor` — rather than as a list of two
    module names. Splitting `doctor.py` into a package failed this on `doctor.runtime`, which
    is the same doctor and always was; a guard that has to be edited every time a file moves
    trains you to edit it, and the edit that relaxes it looks identical to the edit that
    renames a file.

    `gate.extract` is the third and `loop.agents` the fourth, and both are named rather than
    ruled because they are exceptions and should read as ones — D-107, and D-086 §A one level
    along. `loop.agents` holds the router, the curator and the critic; `gate.extract.ask` is
    the one query loop all three come through, so the pair is the proposing path entire: it
    turns a written rule into a predicate and hands it to `predicate.evaluate()`, which
    decides. What kept this guard honest was never the count, it was that no model reaches
    that decision, and that is now
    asserted where it actually lives: `test_no_model_in_gating_path` walks `predicate.py` too.
    Widening this without that walk would have been the edit this docstring warns about.
    """
    seams = {"adapter", "gate.extract", "loop.agents"}
    allowed = {n for n in MODULES if n in seams or n.split(".")[0] == "doctor"}
    reach = {name for name, tree in MODULES.items() if "claude_agent_sdk" in imported(tree)}
    assert reach <= allowed and "adapter" in reach, (
        f"{reach - allowed} reaches a model. The gate is mechanical — "
        "reward_breakdown['DB'] — and a model anywhere near it makes the number unfalsifiable"
    )


# Import names, not words. `doctor` NAMES both Cerebras and ollama on purpose -- it reads
# `CEREBRAS_API_KEY` and pings `OLLAMA_URL` -- and that is the distinction D-067 draws: naming a
# provider is a diagnostic, importing one is a model source. A word ban would have to exempt the
# one file that is allowed to say the words, and the exemption is where the next one gets in.
NOT_ANTHROPIC = frozenset(
    {"openai", "cerebras", "langchain_cerebras", "cerebras_cloud_sdk", "ollama", "groq",
     "mistralai", "cohere", "litellm", "transformers", "vllm"}
)
SCRIPTS = ROOT / "scripts"


def repo_trees() -> dict[str, ast.Module]:
    """Every shipped module, `src/` and `scripts/` both. Tests are excluded deliberately.

    `scripts/` is in because that is where the breach was: a `ChatCerebras(...).invoke(...)` sat
    in `p0-probe.py` after D-067 banned it, in the one directory no guard reads. Tests are out
    because this file has to name the banned packages in order to ban them.

    Working tree, not `git ls-files` -- eleven scripts here and nine in CI, because `.gitignore`
    excludes `scripts/p0-*` (DEF-081). The gap is deliberate: a tracked-files scan would invert
    it and miss the untracked file entirely, and untracked is where the next one gets written.
    """
    scripts = {f"scripts.{p.stem}": ast.parse(p.read_text(), p.name) for p in SCRIPTS.rglob("*.py")}
    return dict(MODULES) | scripts


def test_no_provider_outside_anthropic_is_imported() -> None:
    """D-067 — Anthropic models in every role, and the rule had no mechanism until now.

    The polarity is the whole point and it is easy to get backwards: `doctor` asserts these keys
    are ABSENT, so the words belong in this repo and the packages do not. What is forbidden is a
    module that could call one.

    Ceiling: `google.generativeai` is not in the ban list, because `imported()` answers with the
    top-level name and `google` is also protobuf's. It would be a ban that fires on the wrong
    thing, which trains someone to relax it.
    """
    reaching = {
        name: found
        for name, tree in repo_trees().items()
        if (found := imported(tree) & NOT_ANTHROPIC)
    }
    assert not reaching, (
        f"{reaching} imports a provider that is not Anthropic's. D-067 allows no other model in "
        "any role, and the quota window rejects rather than bills, so a second provider is a "
        "second bill rather than a fallback"
    )


def test_the_provider_check_can_fail() -> None:
    """Absence again, and the same answer -- run the detector on a planted import."""
    assert imported(ast.parse("from langchain_cerebras import ChatCerebras")) & NOT_ANTHROPIC
    assert imported(ast.parse("import litellm")) & NOT_ANTHROPIC
    assert not imported(ast.parse("from claude_agent_sdk import query")) & NOT_ANTHROPIC
    assert "scripts.p0-probe" in repo_trees() or any(
        n.startswith("scripts.") for n in repo_trees()
    ), "scripts/ contributed nothing, so the scan above read src/ only"


SPAN_VOCABULARY = ("llm.", "touchstone.")


def _attribute_names(tree: ast.AST) -> Iterator[ast.expr]:
    """Every first argument handed to a `.set_attribute(...)` call."""
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "set_attribute"
            and node.args
        ):
            yield node.args[0]


def _literal_name(arg: ast.expr) -> str | None:
    """The attribute name when it is a plain string literal, and None when it is built."""
    return arg.value if isinstance(arg, ast.Constant) and isinstance(arg.value, str) else None


def test_no_span_attribute_is_named_outside_the_openinference_vocabulary() -> None:
    """D-017 wants OpenInference names and not the `gen_ai` ones, and nothing checked it.

    The phase plan states this box as `git grep gen_ai src/` returning nothing, and it never
    will: adapter.py names that convention in the comment explaining why we do not emit it,
    so the grep is answered by the sentence enforcing the rule. Deleting the comment to quiet
    the grep is the wrong direction. Reading the EMITTED name instead lets the explanation
    stay at the line a reader needs it, which is the same trade the provider ban above makes.

    A name that is not a literal fails rather than being skipped. One attribute assembled at
    runtime is one this test cannot read, and an allow-list with a blind spot is not one.

    Ceiling: our spans only. The SDK's instrumentor emits its own and we do not rename them
    (docs/04 §2) -- what is pinned here is the vocabulary we choose, never the one we receive.
    """
    wrong = []
    for name, tree in repo_trees().items():
        for arg in _attribute_names(tree):
            if (literal := _literal_name(arg)) is None:
                wrong.append(f"{name}:{arg.lineno} name is built, so it cannot be read here")
            elif not literal.startswith(SPAN_VOCABULARY):
                wrong.append(f"{name}:{arg.lineno} {literal}")
    assert not wrong, (
        f"{wrong} -- a span attribute is OpenInference `llm.` or our own `touchstone.`. D-017 "
        "rejects the `gen_ai` convention outright so the scorer reads one vocabulary, and a "
        "second one costs every reader of a trace the question of which span they are holding"
    )


def test_the_span_vocabulary_check_can_fail() -> None:
    """Absence again, so run the detector on a planted attribute."""

    def names(source: str) -> list[ast.expr]:
        return list(_attribute_names(ast.parse(source)))

    banned = _literal_name(names("span.set_attribute('gen_ai.request.model', m)")[0])
    assert banned is not None
    assert not banned.startswith(SPAN_VOCABULARY)

    built = names("span.set_attribute(prefix + '.model', m)")
    assert _literal_name(built[0]) is None, "a computed name must not read as a literal"

    kept = _literal_name(names("span.set_attribute('llm.model_name', m)")[0])
    assert kept is not None
    assert kept.startswith(SPAN_VOCABULARY)

    found = [a for tree in repo_trees().values() for a in _attribute_names(tree)]
    assert found, "no set_attribute call in the repo, so the scan above read nothing"


def test_the_model_pins_live_in_config_and_nowhere_else() -> None:
    """One place to change a pin, and one place to read one off.

    A hardcoded model string is the version of the failure above that no import check sees:
    it needs no new import, because the module that calls the SDK is already allowed to.
    """
    for name, tree in MODULES.items():
        if name in {"config", "__init__"}:
            continue
        hardcoded = {s for s in strings(tree) if s.startswith(("claude-", "anthropic/", "openai/"))}
        assert not hardcoded, f"{name}.py hardcodes {hardcoded} — the pins live in config.py"


CAP = "MAX_ATTEMPTS"


def cap_reads(tree: ast.AST) -> int:
    """How many times this subtree names the attempt cap, as an attribute or a bare name."""
    return sum(
        1
        for n in ast.walk(tree)
        if (isinstance(n, ast.Attribute) and n.attr == CAP)
        or (isinstance(n, ast.Name) and n.id == CAP)
    )


def test_the_attempt_cap_has_exactly_one_reader() -> None:
    """D-091 §C, and the invariant is the absence, not the presence.

    That `attempts_exhausted()` exists proves nothing. What the decision asks for is that the
    graph's loop condition and the critic's `attempt_budget` tool get the same answer, and the
    only way to have that is for neither to know the number. So this counts reads across the
    whole source rather than asserting anything about one function.

    Stated as two claims because they fail differently: a second module reading the cap is a
    drift, and `budget.py` reading it outside `attempts_exhausted()` is the same drift arriving
    one file earlier. Ceiling: `import MAX_ATTEMPTS as X` would evade this. A rebinding
    import is worth a guard when one appears; today none does, and a check that chases every
    alias is a check nobody reads.
    """
    owner = "loop.budget"
    skip = {"config", owner}
    elsewhere = {
        name: n for name, tree in MODULES.items() if name not in skip and (n := cap_reads(tree))
    }
    assert not elsewhere, f"{sorted(elsewhere)} reads {CAP}; only {owner}.attempts_exhausted may"

    tree = MODULES[owner]
    reader = next(
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name == "attempts_exhausted"
    )
    assert cap_reads(tree) == cap_reads(reader) > 0, (
        f"{owner} names {CAP} outside attempts_exhausted() — the cap is back in two places"
    )


def test_no_module_reads_the_answer_key() -> None:
    """Invariant 1, asserted where we can actually break it.

    Upstream already keeps the key out of the agent's context; what this repo can do wrong is
    merge them — read a task's grading fields and let them reach a prompt. τ² hands our seam
    `messages`, so any code here touching these names has gone and fetched the key.
    """
    banned = {"evaluation_criteria", "user_scenario", "reward_basis"}
    for name, tree in MODULES.items():
        assert not (found := attributes(tree) & banned), (
            f"{name}.py reads {found} — that is the answer key, and the seam is handed messages"
        )


def _function(module: str, name: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    """One named function out of a module in `MODULES`."""
    kinds = (ast.FunctionDef, ast.AsyncFunctionDef)
    found = [n for n in ast.walk(MODULES[module]) if isinstance(n, kinds) and n.name == name]
    assert len(found) == 1, f"{module}.{name} is not there once — the guard below is asserting air"
    return found[0]


def test_no_prompt_carries_the_answer_key() -> None:
    """Rubric criterion 1 asks the router to derive what `Session.anomalous` already knows.

    D-082 §B is the whole reason the router is allowed to be a model: its verdict is scored
    against τ²'s own signals over the 1,712, and that disagreement rate is the only error bar
    anything downstream has. Hand it the flag and the agreement is 1.0 by construction.

    Asserted on `_transcript` rather than on the module, because `Verdict.anomalous` is the
    router's OWN answer and banning the word everywhere would ban the thing being measured.
    `_transcript` is the only function that turns a session into prompt text, so the reachable
    fields are the guard: `messages`, and nothing tau2 derived from a reward.
    """
    render = _function("loop.agents", "_transcript")
    read = {
        n.attr
        for n in ast.walk(render)
        if isinstance(n, ast.Attribute)
        if isinstance(n.value, ast.Name) and n.value.id == "session"
    }
    assert read == {"messages"}, (
        f"the transcript reads {read - {'messages'}} off the session — `anomalous` and "
        "`termination_reason` come from `reward_info`, and criterion_1_agreement dies on either"
    )


def test_only_the_critic_holds_a_tool() -> None:
    """D-085 §D: the blanket `allowed_tools=[]` became per-role, and a grep cannot see that.

    The old rule was one literal in one file. Now the router and the curator get nothing and
    the critic gets two, which is exactly the shape DEF-056 describes — a check that keeps
    passing while one role quietly gains a tool. So this reads the call, not the constant.
    """
    holders = {
        name
        for name in ("route", "curator", "critic")
        for call in ast.walk(_function("loop.agents", name))
        if isinstance(call, ast.Call)
        for kw in call.keywords
        if kw.arg == "allowed_tools"
    }
    assert holders == {"critic"}, (
        f"{holders} pass allowed_tools. The curator testing its own candidate is the "
        "self-review the critic exists to break (D-085 §C3)"
    )


def test_the_answer_key_check_can_fail() -> None:
    """A check nobody has watched fail is a check nobody has watched.

    Two of the four tests above are absence assertions, and an absence assertion passes just as
    happily when the thing that would detect the presence is broken. This runs the detector
    against a positive case.
    """
    assert attributes(ast.parse("task.evaluation_criteria")) == {"evaluation_criteria"}
    assert imported(ast.parse("def f():\n    from claude_agent_sdk import tool")) == {"claude_agent_sdk"}
    type_only = "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    from claude_agent_sdk import X"
    assert imported(ast.parse(type_only)) == {"typing"}, "a TYPE_CHECKING import is not a reach"
    assert strings(ast.parse('M = "claude-opus-5"')) == {"claude-opus-5"}


# Text, not `ast` -- a workflow is YAML, so there is no parse tree to ask for names and the
# substring rule that governs the tests above does not apply the same way. The banned words
# appear in this file as literals; the scan reads `.github/`, never itself.
CI_DIR = ROOT / ".github"
NO_CREDENTIAL = ("anthropic", "api_key", "api-key", "apikey", "secrets.", "openai", "cerebras")


def ci_files() -> list[Path]:
    """Every file under `.github/`, whatever its extension."""
    return [p for p in CI_DIR.rglob("*") if p.is_file()]


def banned_in(text: str) -> set[str]:
    """The forbidden tokens present in `text`, case-insensitively."""
    low = text.lower()
    return {w for w in NO_CREDENTIAL if w in low}


def test_ci_carries_no_credential_and_calls_no_model() -> None:
    """D-014 — CI that needs a secret is CI nobody can fork.

    The ROADMAP states this as `git grep -i 'ANTHROPIC' .github/` returning nothing. It is
    asserted here rather than as a workflow step because a workflow grepping its own directory
    is a check auditing itself, and it would pass in exactly the case that matters least: a
    credential added to a second workflow the first one never reads.
    """
    assert CI_DIR.is_dir(), "no .github/ -- P2.7 is unbuilt, and this test would pass vacuously"
    assert ci_files(), ".github/ exists but is empty, so the scan below reads nothing"
    for path in ci_files():
        found = banned_in(path.read_text(encoding="utf-8"))
        assert not found, f"{path.relative_to(ROOT)} names {found} -- CI holds no credential"


def test_the_credential_check_can_fail() -> None:
    """The test above is an absence assertion over files that happen not to contain the words.

    It would pass just as happily with a scanner that always returns nothing, so the scanner
    is run against a planted positive and against the shape it must not over-match.
    """
    assert banned_in("      ANTHROPIC_API_KEY: ${{ secrets.KEY }}") == {
        "anthropic", "api_key", "secrets.",
    }
    assert banned_in("- run: uv run pytest tests/unit -q") == set()


# The trailer and the session URL are two spellings of one leak, so one pattern reads both.
# Matched case-insensitively and on the whole raw message, because a trailer is conventionally
# last and nothing enforces that.
CLAUDE_TRAILER = re.compile(r"co-authored-by:.*claude|claude-session:", re.IGNORECASE)


def commit_messages() -> list[str]:
    """Every commit message in this repository, subject and body, newest first."""
    log = subprocess.run(
        ["git", "log", "--format=%B%x00"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    # Stripped, not just filtered: `%B` ends in a newline, so every message after the first
    # carries a leading blank line and its subject would report as the empty string.
    return [message.strip() for message in log.stdout.split("\0") if message.strip()]


def test_no_commit_carries_a_claude_trailer() -> None:
    """The repository is public, so authorship metadata is read before the code is.

    P0's exit gate asks this of the first commit. It is asserted over every commit instead,
    because the property the gate wanted is a property of the published history and a one-time
    check cannot hold it -- the trailer is re-proposed by tooling on every session, so the
    discipline needs a mechanism rather than a memory.

    Only as deep as the checkout: CI clones at depth 1, where this reads the pushed commit and
    nothing before it. That is the commit worth refusing, so the shallow case is the useful one
    and the full history is checked locally.
    """
    messages = commit_messages()
    assert messages, "no commit messages -- not a git checkout, and this test would pass vacuously"
    carrying = [m.splitlines()[0] for m in messages if CLAUDE_TRAILER.search(m)]
    assert not carrying, f"{carrying} carry a Claude trailer, and the repository is public"


def test_the_trailer_check_can_fail() -> None:
    """The same absence-assertion problem, and the same answer: run it on a planted positive."""
    assert CLAUDE_TRAILER.search("Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>")
    assert CLAUDE_TRAILER.search("Claude-Session: https://claude.ai/code/session_019")
    assert not CLAUDE_TRAILER.search("Co-Authored-By: a person <someone@example.com>")
    assert not CLAUDE_TRAILER.search("the gate had no caller, and claude is not in this line")
