"""The parts of the runner that are decisions rather than a τ² call.

`run()` itself needs τ², the SDK and a network, so it is covered by a live run and not from
here. What is checkable in 2 seconds is what it decides BEFORE any of that: which tasks, and
under which name — and both are the kind of thing that is silently wrong for a whole run.
"""

import json
import sys
import types
from pathlib import Path

import pytest

from touchstone import config, suite
from touchstone.gate.predicate import Predicate, RequiresPriorTool
from touchstone.loop import run as loop_run
from touchstone.loop.run import PROVENANCE, auth_mode, frozen_task_ids, run_name, same_run


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


def _matching(tmp_path: Path, sidecar: dict[str, object]) -> Path:
    """A run on disk agreeing with the live configuration on every field but enforcement.

    `auth` comes from `auth_mode()` rather than a literal, so the guard under test is the only
    field that can disagree -- a hardcoded `subscription` would make these pass or fail on
    whether the machine running them happens to hold a key.
    """
    done = _results(
        tmp_path / "results.json",
        agent=config.MODEL,
        user=config.USER_MODEL,
        k=config.K,
        tasks=frozen_task_ids(),
    )
    done.with_name(PROVENANCE).write_text(json.dumps({"auth": auth_mode(), **sidecar}))
    return done


def test_an_ungated_run_is_not_resumed_under_the_gate(tmp_path: Path) -> None:
    """The gate changes what the agent may do, so the two halves would be two agents.

    Nothing in τ²'s `info` records it, which is why the sidecar exists at all: without this
    check the merge is silent and the published number covers both.
    """
    done = _matching(tmp_path, {"enforced": False})
    assert (why := same_run(done, config.K, enforced=True)) is not None
    assert why.startswith("enforcement was")


def test_a_gated_run_is_not_resumed_without_the_gate(tmp_path: Path) -> None:
    """The other direction, asserted separately -- a one-sided check passes half the time."""
    done = _matching(tmp_path, {"enforced": True})
    assert (why := same_run(done, config.K, enforced=False)) is not None
    assert why.startswith("enforcement was")


def test_resuming_a_gated_run_under_the_gate_is_allowed(tmp_path: Path) -> None:
    """The case the check exists to allow, and the one an over-strict guard would break."""
    done = _matching(tmp_path, {"enforced": True})
    assert same_run(done, config.K, enforced=True) is None


def test_a_sidecar_that_predates_the_gate_reads_as_ungated(tmp_path: Path) -> None:
    """False here is a measurement, not a default: the run could not have armed a gate.

    Distinguished from `auth`, whose fallback is the LIVE value -- absent evidence there means
    no disagreement, and absent evidence here means the field did not exist yet.
    """
    done = _matching(tmp_path, {})
    assert same_run(done, config.K, enforced=False) is None
    assert (why := same_run(done, config.K, enforced=True)) is not None
    assert "False" in why


AUTH = Predicate(
    rule="orders are read only after the user is identified",
    source="policy.md:3",
    check=RequiresPriorTool(tool="get_order_details", prior=("get_user_details",)),
)


def test_an_empty_suite_is_refused_rather_than_armed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tier 1 is silent on retail (D-105), so a gate with no predicate refuses nothing.

    The label would still say enforced, which is the phase-3 exit gate's own wording: wired
    but never seen to fire reads exactly like working.
    """
    # Patched on the module rather than on `loop_run`: `run.py` imports the module and calls
    # `suite.predicates()` through it, so one setattr reaches the caller and nothing is shadowed.
    monkeypatch.setattr(suite, "predicates", tuple)
    with pytest.raises(RuntimeError, match="empty regression suite"):
        loop_run.admitted()


def test_a_suite_with_a_case_in_it_is_what_the_gate_gets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(suite, "predicates", lambda: (AUTH,))
    assert loop_run.admitted() == (AUTH,)


def test_the_gate_arms_what_the_orchestrator_builds_and_returns_it_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`install_gate` against a stand-in τ², the same trick `test_adapter` uses on the seam.

    Two claims. The wrapper hands back upstream's own object, because the orchestrator holds
    that instance and a copy would gate an environment nobody runs against. And every
    environment it hands back is armed -- which is the list `run()` checks after the run, so an
    empty one there means the rebind landed on a function upstream stopped calling.
    """
    # The parameter names are `enforce.arm`'s to keep, not this file's: `gated` binds over the
    # method and calls upstream through the signature it found there.
    class Env:
        def make_tool_call(self, tool_name: str, requestor: str = "assistant", **kw: object) -> str:
            return f"{requestor} called {tool_name}{sorted(kw)}"

    built: list[Env] = []

    def build_environment(domain: str) -> Env:
        assert domain == "retail", "the stand-in was built for the specimen and nothing else"
        built.append(env := Env())
        return env

    tau2 = types.ModuleType("tau2")
    runner = types.ModuleType("tau2.runner")
    build = types.ModuleType("tau2.runner.build")
    setattr(build, "build_environment", build_environment)  # noqa: B010
    setattr(tau2, "runner", runner)  # noqa: B010
    setattr(runner, "build", build)  # noqa: B010
    for name, module in (("tau2", tau2), ("tau2.runner", runner), ("tau2.runner.build", build)):
        monkeypatch.setitem(sys.modules, name, module)

    states = loop_run.install_gate([AUTH])
    assert states == [], "nothing is armed until something is built"

    environment = build.build_environment("retail")
    assert environment is built[0], "the wrapper returned something upstream did not build"
    assert len(states) == 1
    with pytest.raises(ValueError, match=r"policy\.md:3"):
        environment.make_tool_call("get_order_details", order_id="#1")
