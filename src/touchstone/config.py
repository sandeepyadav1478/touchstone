"""Constants and paths. Everything env-dependent lives here, nowhere else.

Kept deliberately small: a config module that grows a value per feature becomes the place bugs
hide. See docs/09 §10.

Each pin below carries a decision reference; the argument is in DECISIONS.md (D-101).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # annotation only — the runtime SDK import is policed by test_invariants
    from claude_agent_sdk import SettingSource

ROOT = Path(__file__).resolve().parents[2]

SUITE = ROOT / "suite"
BENCHMARK = SUITE / "benchmark"
REGRESSION = SUITE / "regression"
RESULTS = ROOT / "results"
PROMPTS = ROOT / "prompts"
DIAGRAMS = ROOT / "diagrams"

# A directory, not a URL — D-074 made MLflow the spine with no service.
MLRUNS = ROOT / "mlruns"
# `.as_uri()`, not an f-string: MLflow dispatches on the URI scheme.
TRACKING_URI = MLRUNS.as_uri()

# One experiment, not one per run — else the version table's rows land in separate namespaces.
EXPERIMENT = "touchstone"

# The CLI's own checkpointer. Not shared with the container's — docs/06 §3.
CHECKPOINTS = ROOT / ".touchstone" / "checkpoints.db"

# Attempts per case. `--k` and the docs quote this constant, never the number (DEF-003).
K = 3

# Attempts the mining loop spends on one trace. Read by attempts_exhausted() alone, which is
# what keeps the critic's budget tool and the graph's loop condition from disagreeing (D-091 §C).
MAX_ATTEMPTS = 5

# Turns the SDK may spend inside one τ² generate(). Not D-032's `max_turns` for the loop
# agents. Exhausting it raises `ResultError`; adapter.py turns that back into an outcome.
MAX_SDK_TURNS = 2

# Turns one loop agent may spend on one question. D-032 set a single 2 for every role and
# D-085 SS E made that wrong: `output_format` spends a turn, and a tool call spends at least
# one more each way. The split is tools or no tools, which is the only difference that exists
# -- the router and the curator run with `allowed_tools=[]` (D-085 SS D) and answer in one go.
# ponytail: 6 is a guess. Truncating the critic mid-tool-call surfaces as an empty verdict
# rather than an error, so the first live run should read `num_turns` and pin this to it.
AGENT_TURNS = 2
CRITIC_TURNS = 6

# [] — not None, the most misread flag in the Agent SDK (types.py:1807):
#   None → every settings.json and CLAUDE.md on the machine is loaded
#   []   → isolation. An agent reading the developer's CLAUDE.md is not the agent that ships.
# `touchstone doctor` measures this rather than trusting it (D-034). The annotation is the SDK's
# own type, not `list[str]` — an isolation setting a typo can widen is not a setting (D-054).
SETTING_SOURCES: list[SettingSource] = []

# Anthropic via the Claude Code subscription (D-001). Its absence is asserted, not hoped.
API_KEY_ENV = "ANTHROPIC_API_KEY"

# A full id, never the "sonnet" alias, which moves: the model is part of a candidate's
# identity (D-013), and P0 measured two different models answering the same prompt (D-034).
MODEL = "claude-sonnet-5"

# Measurement apparatus, not a participant — frozen the way the benchmark is (D-024), and
# deliberately not MODEL, since one model on both sides shares its own blind spots (D-067).
# τ²'s four retail baselines ran a gpt-4.1 simulator, so they are context, never a reference.
USER_MODEL = "claude-haiku-4-5-20251001"

# All three mining-loop agents: router, curator, critic (D-082). Not MODEL — sonnet-5 is the
# thing under test and must not also be the apparatus. None of the three can gate (docs/05 §5).
LOOP_MODEL = "claude-opus-5"

# τ²'s NL assertion evaluator. It is not dormant: today's tasks.json declares NL_ASSERTION on
# 112 of 114, so it enters the composite (D-069). touchstone gates on reward_breakdown["DB"] and
# reports the composite beside it, unmodified. τ² labels it experimental (evaluator/AGENTS.md).
NL_ASSERTION_MODEL = "claude-opus-5"

# τ²'s reviewer (`--auto-review`). Off by default, not part of reward. Pinned because it is
# the instrument that measures the D-067 simulator risk directly.
REVIEW_MODEL = "claude-opus-5"

# Quota is a rolling five-hour window and overage is rejected, not billed — it kills a run in
# flight. The cheap pins above are that constraint's doing, not a quality judgement (D-067).

# Where extract.py stops rather than running into `rejected`, which loses the attempt in
# flight and cannot be retried until the window resets. Compared against
# RateLimitInfo.utilization, which the SDK reports live (docs/00 §1).
#   read alongside the SDK's own `status`, not instead of it: the vendor decides when
#   `allowed_warning` fires and never says at what fraction, so the stop point has to be ours
#   a budget, not a measurement — calls-per-trace is unmeasured here, and the 15% reserve
#   covers fewer attempts than it looks like, since MAX_ATTEMPTS x (curator + critic) is a
#   floor per trace and the real cost only runs above it
#   read by quota_exhausted() alone, the one-reader rule MAX_ATTEMPTS already gets (D-091 §C)
QUOTA_STOP_UTILIZATION = 0.85

# ── the specimen, asserted rather than assumed ────────────────────────────────────────────
# P1.0. τ² resolves its data directory once at import and warns rather than fails when it is
# missing, and the fallback is broken under a normal install (DEF-051). Measured 2026-08-25
# against commit a2c024725189. These assert reachability, not identity — a task count cannot
# tell `1.0.1` from the pin if their data files agree (DEF-055).
TAU2_RETAIL_TASKS = 114
TAU2_RETAIL_POLICY_BYTES = 6699

# Namespaced, because a bare name is one a neighbour may already own — there is a system-wide
# litellm under systemd on this machine. The rename is docs/09 §env.
# ANTHROPIC_API_KEY and CEREBRAS_API_KEY stay bare on purpose: `doctor` asserts their absence,
# and that only means anything under the name the vendor's SDK reads. test_env_namespace holds it.
OLLAMA_URL = os.environ.get("TOUCHSTONE_OLLAMA_URL", "http://localhost:11434")

# DeepEval phones home by default — PostHog and Confident AI, measured in 4.1.9 (D-076). Set
# here because config is imported first by construction. `setdefault`: default-deny, overridable.
os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "YES")
