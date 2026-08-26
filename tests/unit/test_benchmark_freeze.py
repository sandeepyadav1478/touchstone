"""The frozen benchmark tier — invariant 7's half that runs without importing τ².

⛔ **No τ² import here.** Resolving the specimen costs 1.71 s and phase 1's exit gate is the
whole unit suite under 2 s, so the live comparison lives in
`scripts/freeze-benchmark.py --check` (CI) and this file asserts the two things that can be
checked from the committed manifest alone: the collation, and that the manifest describes the
selection it claims.
"""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = json.loads((ROOT / "suite" / "benchmark" / "manifest.json").read_text())

_spec = importlib.util.spec_from_file_location(
    "freeze_benchmark", ROOT / "scripts" / "freeze-benchmark.py"
)
freeze = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(freeze)


def test_the_ids_are_ordered_numerically_not_as_strings() -> None:
    # The whole point: a hash over a list is a hash over its order, and these ids are
    # DECIMAL STRINGS. String sort gives 0, 1, 10, 100 — a different ten tasks.
    picked = freeze.select(["9", "10", "5", "100", "12"], n=4)
    assert picked == ["5", "9", "10", "12"]
    assert picked != sorted(["9", "10", "5", "100", "12"])[:4]


def test_the_committed_manifest_is_what_select_produces() -> None:
    # Not a re-run of the generator — the manifest holds the split it was cut from, so this
    # asserts the file agrees with the function that claims to have written it.
    assert freeze.select(MANIFEST["task_ids"], n=len(MANIFEST["task_ids"])) == MANIFEST["task_ids"]


def test_the_frozen_tier_is_a_strict_subset_of_the_specimen() -> None:
    assert len(MANIFEST["task_ids"]) == freeze.N == 10
    assert MANIFEST["split_total"] < MANIFEST["tasks_total"] == 114
    assert len(set(MANIFEST["task_ids"])) == len(MANIFEST["task_ids"])


def test_no_task_bytes_were_vendored() -> None:
    # D-062: ids and a hash, never the corpus. `description`, `user_scenario` and
    # `initial_state` are the task's own fields — none may appear in the manifest at any depth.
    blob = json.dumps(MANIFEST)
    for field in ("description", "user_scenario", "initial_state", "evaluation_criteria"):
        assert field not in blob


def test_the_manifest_carries_the_commit_not_a_version_string() -> None:
    # DEF-055: `1.0.1` names two different trees. The commit IS the identity.
    assert MANIFEST["tau2_commit"] == "a2c024725189"
    assert len(MANIFEST["tasks_sha256"]) == 64


def test_the_gated_component_is_present_on_every_frozen_task() -> None:
    # Invariant 8 / D-069: touchstone gates on reward_breakdown["DB"], so a frozen task that
    # does not declare DB would be ungateable and must never enter the tier silently.
    assert all("DB" in basis for basis in MANIFEST["reward_basis"].values())
