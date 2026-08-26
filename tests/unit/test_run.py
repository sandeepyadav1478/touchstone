"""The parts of the runner that are decisions rather than a τ² call.

`run()` itself needs τ², the SDK and a network, so it is covered by a live run and not from
here. What is checkable in 2 seconds is what it decides BEFORE any of that: which tasks, and
under which name — and both are the kind of thing that is silently wrong for a whole run.
"""

import json

from touchstone import config
from touchstone.loop.run import frozen_task_ids, run_name


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
