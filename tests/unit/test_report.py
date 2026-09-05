"""The envelope around `score()` — provenance, and the fields that make a run comparable.

No τ² import, no run, no network: `envelope()` takes values, so every field it publishes is
checkable inside phase 1's two-second gate.
"""

import json
from pathlib import Path

import pytest

from touchstone import config
from touchstone.loop.report import envelope, recorded_auth, recorded_enforcement, write
from touchstone.loop.run import PROVENANCE
from touchstone.loop.schema import TERMINATION_REASONS, Scored

MANIFEST = {
    "domain": "retail",
    "tau2_commit": "a2c024725189",
    "tasks_sha256": "8e03ebce7901",
}
INFO = {"agent_info": {"llm": "claude-sonnet-5"}, "user_info": {"llm": "claude-haiku-4-5"}}
# Written out in full rather than cast: `Scored` and `Aggregate` are total, so a fixture that
# type-checks is a fixture that names every published key. A `cast` here would let this test keep
# passing after a key was added to the schema and never to the envelope.
SCORED: Scored = {
    "aggregate": {
        "k": 3, "trials": 30, "tasks": 10,
        "reward_mean": 0.4, "pass_hat_1": 0.4, "pass_hat_k": 0.6,
        "reward_breakdown_zeroed": {"DB": 4},
        "infra_error_convention": "counted_as_failed",
        "infra_errors": 1,
        "undersampled_tasks": [],
        "termination_reasons": dict.fromkeys(TERMINATION_REASONS, 0),  # type: ignore[typeddict-item]
    },
    "cases": [{"id": "5", "trials": 3, "success_k": 1, "db_passed": 2, "db_scored": 3}],
}


def test_provenance_comes_from_the_manifest_not_the_results_file() -> None:
    """τ²'s `info.git_commit` runs `git rev-parse` in the CWD — ours, not τ²'s (DEF-074)."""
    out = envelope(SCORED, MANIFEST, {**INFO, "git_commit": "deadbeef"}, "v1", 3, "subscription")
    assert out["tau2_commit"] == "a2c024725189"
    assert "deadbeef" not in json.dumps(out), "the results file's commit names the wrong repo"


def test_the_model_comes_from_the_run_not_from_config() -> None:
    """A results file naming a model it did not use is worse than one naming none."""
    out = envelope(SCORED, MANIFEST, {"agent_info": {"llm": "gpt-4.1"}}, "v1", 3, "subscription")
    assert out["model"] == "gpt-4.1" != config.MODEL


def test_keys_with_no_producer_are_absent_rather_than_zero() -> None:
    """A key emitted as 0 before anything can measure it is a number nothing computed.

    The first version of this asserted `absent.isdisjoint(json.dumps(...))`, which iterates
    the JSON string CHARACTER by character and can therefore never fail. It passed on the real
    envelope and on an envelope containing every forbidden key.
    """
    out = envelope(SCORED, MANIFEST, INFO, "v1", 3, "subscription")
    absent = {"cost_per_success_usd", "tool_calls_mean", "p95_latency_s", "budget_exceeded",
              "void_attempts", "diagnostics", "regression"}
    assert absent.isdisjoint(out)
    assert absent.isdisjoint(out["aggregate"])


def test_the_scored_halves_pass_through_untouched() -> None:
    out = envelope(SCORED, MANIFEST, INFO, "v1", 3, "subscription")
    assert out["aggregate"] == SCORED["aggregate"]
    assert out["cases"] == SCORED["cases"]


def test_auth_is_read_from_the_run_and_never_measured_here(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """D-112: `score` is a separate invocation, so its environment is not the run's.

    The key is set here, which is the state that used to produce `api_key`. The published
    value is whatever the RUN wrote, and the environment of this process changes nothing.
    """
    monkeypatch.setenv(config.API_KEY_ENV, "sk-whatever")
    results = tmp_path / "results.json"
    results.with_name(PROVENANCE).write_text(json.dumps({"auth": "subscription"}))
    assert recorded_auth(results) == "subscription"


def test_a_run_that_recorded_nothing_publishes_unknown(tmp_path: Path) -> None:
    """`unknown` is an answer, not a default — it says the run predates its own sidecar."""
    assert recorded_auth(tmp_path / "results.json") == "unknown"


def test_enforcement_is_published_both_ways_and_absent_when_unrecorded(tmp_path: Path) -> None:
    """Three states, not two. `False` is a claim about the run and `absent` is a claim about us.

    A lost sidecar publishing `false` would say the gate was off, which is a fact this process
    has no access to — the same reason `auth` answers `unknown` rather than guessing.
    """
    results = tmp_path / "results.json"
    assert recorded_enforcement(results) is None

    results.with_name(PROVENANCE).write_text(json.dumps({"auth": "subscription"}))
    assert recorded_enforcement(results) is None, "a sidecar older than the field recorded nothing"

    results.with_name(PROVENANCE).write_text(json.dumps({"auth": "subscription", "enforced": True}))
    assert recorded_enforcement(results) is True

    assert envelope(SCORED, MANIFEST, INFO, "v1", 3, "subscription", True)["enforced"] is True
    assert envelope(SCORED, MANIFEST, INFO, "v1", 3, "subscription", False)["enforced"] is False
    assert "enforced" not in envelope(SCORED, MANIFEST, INFO, "v1", 3, "subscription")


def test_a_results_file_of_other_tasks_is_refused(tmp_path: Path) -> None:
    """`benchmark_hash` is a claim about which tasks ran, and nothing downstream can check it.

    τ²'s four shipped retail baselines cover 114 tasks and sit one directory from ours. Scored
    without this guard they would publish under the frozen ten's hash, and the file would read
    as ours at ten tasks while holding someone else's at 114.
    """
    f = tmp_path / "results.json"
    f.write_text(json.dumps({"simulations": [{"task_id": "9999"}], "info": INFO}))
    with pytest.raises(ValueError, match="manifest froze"):
        write(f, "v1", 3)
