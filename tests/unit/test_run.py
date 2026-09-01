"""The parts of the runner that are decisions rather than a τ² call.

`run()` itself needs τ², the SDK and a network, so it is covered by a live run and not from
here. What is checkable in 2 seconds is what it decides BEFORE any of that: which tasks, and
under which name — and both are the kind of thing that is silently wrong for a whole run.
"""

import json
from pathlib import Path

import pytest

from touchstone import config
from touchstone.loop.run import PROVENANCE, frozen_task_ids, run_name, same_run


def test_run_and_score_agree_on_one_name() -> None:
    """They resolve the same directory independently, so a typo splits a run from its score."""
    assert run_name("v1") == "touchstone-v1"


def test_the_name_is_namespaced_under_tau2s_own_results_dir() -> None:
    """τ² writes into `data/simulations/` beside its four shipped baselines."""
    assert run_name("v1").startswith("touchstone-"), "a bare label is one someone else may own"


def test_the_task_ids_are_read_from_the_manifest_not_re_derived() -> None:
    """P1.3 recorded the selection AND the hash. Re-deriving it makes the manifest a comment."""
    manifest = json.loads((config.BENCHMARK / "manifest.json").read_text())
    assert frozen_task_ids() == [str(t) for t in manifest["task_ids"]]
    assert len(frozen_task_ids()) == 10


def test_the_ids_are_strings() -> None:
    """τ² task ids are bare integers in the JSON and string keys everywhere they are used."""
    assert all(isinstance(t, str) for t in frozen_task_ids())


def _results(path: Path, *, agent: str, user: str, k: int, tasks: list[str]) -> Path:
    """A τ² results file carrying only the fields `same_run` reads."""
    path.write_text(
        json.dumps(
            {
                "info": {"agent_info": {"llm": agent}, "user_info": {"llm": user}, "num_trials": k},
                "simulations": [{"task_id": t} for t in tasks],
            }
        )
    )
    return path


def test_a_partial_run_of_the_same_configuration_is_resumable(tmp_path: Path) -> None:
    """The case the whole guard exists to ALLOW — two of ten done, the quota still ticking."""
    done = _results(
        tmp_path / "results.json",
        agent=config.MODEL,
        user=config.USER_MODEL,
        k=config.K,
        tasks=frozen_task_ids()[:2],
    )
    assert same_run(done, config.K) is None


def test_a_changed_pin_is_refused_rather_than_merged_into(tmp_path: Path) -> None:
    """τ² warns and continues here, which is how one file holds two configurations (D-111)."""
    assert config.LOOP_MODEL != config.MODEL, "the two pins must differ or this test is a no-op"
    done = _results(
        tmp_path / "results.json",
        agent=config.LOOP_MODEL,
        user=config.USER_MODEL,
        k=config.K,
        tasks=frozen_task_ids(),
    )
    assert (why := same_run(done, config.K)) is not None
    assert "the agent model" in why


def test_a_changed_k_is_refused_because_pass_hat_k_reads_it(tmp_path: Path) -> None:
    """`pass^k` divides by `math.comb(num_trials, k)` — two k values in one file is nonsense."""
    done = _results(
        tmp_path / "results.json",
        agent=config.MODEL,
        user=config.USER_MODEL,
        k=config.K,
        tasks=frozen_task_ids(),
    )
    assert (why := same_run(done, config.K + 1)) is not None
    assert why.startswith("k was")


def test_a_task_the_manifest_no_longer_holds_is_refused(tmp_path: Path) -> None:
    """The manifest can be re-frozen under the same version label. The run on disk cannot."""
    done = _results(
        tmp_path / "results.json",
        agent=config.MODEL,
        user=config.USER_MODEL,
        k=config.K,
        tasks=[*frozen_task_ids()[:2], "9999"],
    )
    assert (why := same_run(done, config.K)) is not None
    assert "9999" in why


def test_a_run_started_under_the_other_auth_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D-112: an api_key half and a subscription half are two runs in one results file.

    Different rate limits and possibly different routing, and `results/<version>.json` names
    only one of them. The sidecar is what makes the disagreement visible at all — τ²'s `info`
    does not record how the call was authenticated.
    """
    monkeypatch.delenv(config.API_KEY_ENV, raising=False)
    done = _results(
        tmp_path / "results.json",
        agent=config.MODEL,
        user=config.USER_MODEL,
        k=config.K,
        tasks=frozen_task_ids(),
    )
    done.with_name(PROVENANCE).write_text(json.dumps({"auth": "api_key"}))
    assert (why := same_run(done, config.K)) is not None
    assert why.startswith("auth was")


def test_a_run_with_no_sidecar_is_not_a_disagreement(tmp_path: Path) -> None:
    """A missing file is not a conflict. Every run made before D-112 has none."""
    done = _results(
        tmp_path / "results.json",
        agent=config.MODEL,
        user=config.USER_MODEL,
        k=config.K,
        tasks=frozen_task_ids(),
    )
    assert not done.with_name(PROVENANCE).exists()
    assert same_run(done, config.K) is None
