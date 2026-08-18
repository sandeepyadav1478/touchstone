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
RUNBOOKS = ROOT / "runbooks"
DIAGRAMS = ROOT / "diagrams"

# The CLI's own checkpointer. ⛔ Not shared with the container's — docs/06 §3.
CHECKPOINTS = ROOT / ".touchstone" / "checkpoints.db"

# Attempts per case. The `--k` flag defaults to this and the docs quote the constant rather
# than restating the number — DEF-003 is what happens otherwise: k lived as prose in five
# files, D-030 lowered it to 3, and two of the five still said 5 alongside a worked example
# printed at 5/5. A number in five files has five chances to go stale.
K = 3

# The supervisor loop's bound: three specialists, each reachable twice (D-039). ⛔ There is
# deliberately NO `--max-hops` flag, and the asymmetry with K above is the point. `k` is a
# parameter of the MEASUREMENT, so it varies per invocation. `max_hops` is a parameter of the
# CANDIDATE (D-013), so changing it produces a different version — and a flag would let a
# candidate's identity move without a commit. Editing this line IS the version bump.
#
# ⚠️ 6 is a hypothesis, not a measurement. No run has happened, so there is no hop distribution
# to fit to; `hops_exhausted` in the results file is what falsifies it (docs/05 §6).
MAX_HOPS = 6

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
MODEL = "claude-sonnet-4-6"

PHOENIX_URL = os.environ.get("PHOENIX_URL", "http://localhost:6006")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
