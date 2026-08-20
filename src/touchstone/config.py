"""Constants and paths. Everything env-dependent lives here, nowhere else.

Kept deliberately small: a config module that grows a value per feature becomes the
place bugs hide. See docs/09 §10.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # the SDK is a runtime dependency; this import is only for the annotation
    from claude_agent_sdk import SettingSource

ROOT = Path(__file__).resolve().parents[2]

SUITE = ROOT / "suite"
BENCHMARK = SUITE / "benchmark"
RESULTS = ROOT / "results"
PROMPTS = ROOT / "prompts"
DIAGRAMS = ROOT / "diagrams"

# The CLI's own checkpointer. ⛔ Not shared with the container's — docs/06 §3.
CHECKPOINTS = ROOT / ".touchstone" / "checkpoints.db"

# Attempts per case. The `--k` flag defaults to this and the docs quote the constant rather
# than restating the number — DEF-003 is what happens otherwise: k lived as prose in five
# files, D-030 lowered it to 3, and two of the five still said 5 alongside a worked example
# printed at 5/5. A number in five files has five chances to go stale.
K = 3

# ⛔ RUNBOOKS, INTERVAL_SECONDS and MAX_HOPS stood here and were deleted on 2026-08-20. All
# three were specimen-bound: runbooks/ and the sampling interval went with the infra-RCA
# corpus (D-066), and the hop bound belonged to the supervisor loop the retail rewrite
# retired. docs/05 §6 already recorded that D-062 removed `max_hops` and `hops_exhausted` —
# the source had simply never been swept to match, and MAX_HOPS's own comment named
# `hops_exhausted` as its falsifier, a results field that no longer exists.
#
# ⚠️ What the hop bound was FOR does not go away. An agent that wanders lands on
# `cost_per_success_usd`, and on `max_steps` in τ²'s own termination reasons. Two detectors
# replaced by two detectors is the honest description — not "the bound was dropped".

# ⛔ [] — NOT None. This is the single most misread flag in the Agent SDK.
#
#   None  →  "all sources are loaded (matches CLI defaults)", and project scope
#            pulls in every CLAUDE.md it can find.
#   []    →  SDK isolation mode. No settings.json, no CLAUDE.md, no skills.
#
# Quoted from claude_agent_sdk/types.py:1807. An agent under test that reads the
# developer's CLAUDE.md is not the agent that ships, and its scores measure the
# machine it ran on. `touchstone doctor` MEASURES this rather than trusting it:
# get_context_usage()['memoryFiles'] must come back empty. D-034.
# ⛔ NOT `list[str]`. The SDK's own annotation is `list[SettingSource] | None`, and mypy
# --strict rejected the loose one (D-054) — an isolation setting that type-checks against
# any string is one a typo can widen without complaint.
SETTING_SOURCES: list[SettingSource] = []

# Anthropic via the Claude Code subscription (D-001). Its absence is asserted, not hoped.
API_KEY_ENV = "ANTHROPIC_API_KEY"

# ⛔ Pinned, and pinned to a full id rather than the "sonnet" alias, which moves.
#
# This line exists because P0 measured its absence. The same trivial prompt answered as
# claude-sonnet-4-6 with setting_sources=None and as claude-haiku-4-5-20251001 with [] —
# the first was reading `"model": "sonnet"` out of the developer's ~/.claude/settings.json,
# the second was a CLI default. Neither was this project's choice, and D-013 makes the model
# part of a candidate's identity. An unpinned model means two rows of the version table can
# differ by whose machine ran them. D-034.
MODEL = "claude-sonnet-5"

# The other two roles, pinned separately and for a different reason (D-067).
#
# ⛔ USER_MODEL is measurement apparatus, not a participant. It is FROZEN the way the
# benchmark is frozen (D-024): change it and every pass^k number before the change becomes
# incomparable to every number after, because the agent was talking to a different customer.
# It is deliberately NOT `MODEL` — one model on both sides of the conversation shares its own
# blind spots, and tau2 itself tested Claude against a gpt-4.1 simulator rather than itself.
#
# ⚠️ This breaks comparability with tau2's four shipped retail baselines, all of which ran the
# simulator on gpt-4.1-2025-04-14. There is no OpenAI key here (D-001 asserts ANTHROPIC_API_KEY
# absent; nothing else is set either), so those runs are CONTEXT, never a reference line. Our
# own baseline gets measured, not inherited.
USER_MODEL = "claude-haiku-4-5-20251001"

# The judge only grades where a gate cannot be decided deterministically. Cheapest tier on
# purpose: quota is the binding constraint (see below), and a judge call is the most numerous
# call in the loop.
# Anthropic only — stated twice by the candidate, and it governs (D-067). ollama and Cerebras
# are reachable but are not on the table; `doctor` still probes them as diagnostics, not as
# model sources.
#
# Cheapest tier on purpose. The judge grades explanation quality and ⛔ CANNOT GATE ANYTHING
# (docs/05-scoring.md §5) — its output is an annotation on a span, never a decision — so a
# weaker judge costs accuracy on a reported number, not correctness on a promotion.
# ⛔ Not `MODEL`: sonnet-5 is the agent, and an agent grading its own explanation is not a
# measurement. Sharing a pin with USER_MODEL is safe here precisely because neither gates and
# the judge grades the *agent*, never the simulator.
# ⚠️ Ceiling, stated where the number is made: a smaller judge is a weaker judge.
#
# ✅ CLOSED 2026-08-20. This carried a 🔴 open conflict against README §Limits, which used to say
# "The judge never runs on the Claude quota ... the cheapest thing to move off the constrained
# provider". Under Anthropic-only it does draw on the same five-hour cap, so the constraint won
# and the README line went. Grepped before closing: the sentence is not in README.md any more.
# ⚠️ The comment outlived the conflict by a day and read as an open problem the whole time —
# a pointer at another file's error is a claim with a shelf life, and nothing re-runs it.
JUDGE_MODEL = "claude-haiku-4-5-20251001"

# τ²'s natural-language assertion evaluator — pinned defensively, because as configured it is
# DORMANT and it must stay that way.
#
# 🔴 THIS COMMENT WAS WRONG AND THE CORRECTION IS D-069 / DEF-036. It read: "measured across all
# four shipped retail baselines (1,824 simulations), reward_breakdown contains only
# {DB, COMMUNICATE}; NL_ASSERTION never appeared once, although 112 of 114 tasks list it in
# reward_basis" — and concluded that reward_basis was a mere declaration overridden by the
# execution record.
#
# ⛔ THE TWO NUMBERS ARE ABOUT DIFFERENT TASK SETS. data/tau2/results/final/ holds leaderboard
# runs made against the ORIGINAL τ-bench basis; data/tau2/domains/retail/tasks.json — the file a
# run loads today — declares ["DB", "NL_ASSERTION"] on 112 of 114 tasks, ["DB"] on 2 (CHANGELOG
# :214, tasks 33/34), and COMMUNICATE on ZERO. evaluator.py:223 multiplies in whatever the
# loaded task declares, so a run today DOES put a judge in the composite.
#
# ⛔ So touchstone gates on reward_breakdown["DB"] — evaluator_env.py:153 writes it as its own
# key on every task — and reports the composite beside it, unmodified. Nothing upstream is
# edited and the gate stays mechanical. This evaluator stays pinned defensively because it WILL
# fire: it is no longer dormant, it is simply outside the gate.
#
# ⚠️ Assert the shape of our own pilot's breakdown rather than assuming any of this carries
# over — that assertion is a P1 exit-gate box.
# ⚠️ τ² labels this evaluator "experimental/WIP" (evaluator/AGENTS.md).
NL_ASSERTION_MODEL = "claude-opus-5"

# τ²'s reviewer / hallucination checker (`--auto-review`, `--review-mode user`). Off by default
# and NOT part of reward — it grades the conversation qualitatively, including whether the *user
# simulator* fabricated facts. 🎯 This is the instrument that measures the D-067 simulator risk
# directly, so it is pinned rather than left to τ²'s own `claude-opus-4-5` default.
REVIEW_MODEL = "claude-opus-5"

# ⚠️ Quota is a ROLLING FIVE-HOUR WINDOW and overage is REJECTED, not billed. Measured
# 2026-08-19 from the SDK's RateLimitEvent: rate_limit_type='five_hour',
# overage_status='rejected', overage_disabled_reason='org_level_disabled'. Exhausting it does
# not cost money — it kills the run in flight. Any full-suite run (114 tasks x k trials,
# ~11k model turns) therefore needs checkpoint-and-resume across windows, and the cheap pins
# above are that constraint's doing, not a quality judgement.

PHOENIX_URL = os.environ.get("PHOENIX_URL", "http://localhost:6006")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
