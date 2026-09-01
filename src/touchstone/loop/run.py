"""P1.6 — drive τ² over the frozen benchmark subset with our adapter behind the seam.

Thin on purpose. Running 114 tasks, driving a simulator and computing `reward_breakdown` is
τ²'s work and it is already done (D-080); what is ours is three things it cannot do for us:

    install     `telemetry.install()` then `adapter.install()`, in that order and BEFORE the
                τ² import that matters, so every model role resolves to the SDK
    restrict    `task_ids` from `suite/benchmark/manifest.json`, never `num_tasks` — the
                frozen ten are a recorded selection (D-098), and a count would re-sample it
    verify      `install()` returns how many references it replaced, and a run that patched
                nothing is stopped here rather than discovered in the results (DEF-052)

Resuming is not a flag, it is the only behaviour -- D-111. τ² writes each simulation as it
completes and skips what is on disk, which is exactly D-015 and is already built; the quota is a
five-hour window that REJECTS rather than bills, so a re-run that discards completed work is the
failure mode. Its `auto_resume=False` branch does not restart a run, it PROMPTS on the console,
and a prompt is a human step in a project that has none. So this module always resumes and owns
the check that upstream downgrades to a warning: `same_run()` below.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from touchstone import adapter, config, telemetry


def run_name(version: str) -> str:
    """The τ² run name for a version — the one place `run` and `score` agree on a path.

    Namespaced, because τ² writes into its own `data/simulations/` beside the four shipped
    baselines: a bare `v4` there is a name someone else's run may already own.
    """
    return f"touchstone-{version}"


def results_path(version: str) -> Path:
    """Where τ² saves a version's run. The one derivation `run` and `score` share.

    Not a constant: τ²'s `DATA_DIR` is resolved from `TAU2_DATA_DIR` at import, so the answer
    depends on the environment. Importing τ² here is why this is a function and not a module
    constant — a module constant would put the 1.71 s import in front of `touchstone doctor`.
    """
    from tau2.utils.utils import DATA_DIR

    # `Path(...)`: τ²'s DATA_DIR is untyped, and an unchecked Any is how a wrong path reaches a
    # caller that annotated itself honestly.
    return Path(DATA_DIR) / "simulations" / run_name(version) / "results.json"


def frozen_task_ids() -> list[str]:
    """The ten ids `suite/benchmark/manifest.json` froze — read, never re-derived.

    P1.3 recorded both the selection rule and the hash it read them at. Re-deriving the
    selection here would make the manifest a description rather than the authority, and the
    two would drift the first time τ²'s split file changed.
    """
    manifest = json.loads((config.BENCHMARK / "manifest.json").read_text())
    return [str(t) for t in manifest["task_ids"]]


def same_run(done: Path, k: int) -> str | None:
    """Why the run on disk is not the run we are about to make, or None when it is.

    The version label is a run's identity, so resuming inside one label is resuming the same
    configuration -- unless someone changed a pin, or `k`, or the manifest, without bumping the
    label. τ² checks exactly this and then downgrades it to a `logger.warning` under
    `auto_resume`, which is how one results file ends up holding two configurations and being
    scored as one. Held here instead, before the quota is spent.

    Task ids are checked as a SUBSET and not for equality: a partial run has only some of the
    frozen ten on disk, and that is the case this function exists to allow. `report.py:106`
    holds the equality, at the point where a complete run is the claim.

    Args:
        done: An existing τ² `results.json` for this version.
        k: Trials per task for the run about to start.

    Returns:
        A sentence naming the first field that differs, or None when every field matches.
    """
    raw = json.loads(done.read_text())
    info = raw.get("info") or {}
    for field, was, now in (
        ("the agent model", (info.get("agent_info") or {}).get("llm"), config.MODEL),
        ("the user model", (info.get("user_info") or {}).get("llm"), config.USER_MODEL),
        ("k", info.get("num_trials"), k),
    ):
        if was != now:
            return f"{field} was {was!r} and is now {now!r}"
    stray = {str(s["task_id"]) for s in raw.get("simulations") or []} - set(frozen_task_ids())
    if stray:
        return f"the manifest no longer contains {sorted(stray)}, which the run on disk holds"
    return None


def run(version: str, k: int) -> Path:
    """Run the frozen subset `k` times each. Returns the τ² results file it wrote.

    Always resumes (D-111). A version whose run on disk was made under a different
    configuration is refused rather than merged into.

    Args:
        version: The version label — names the run directory, and `score` resolves the same one.
        k: Trials per task. `config.K` by default, quoted from there and never as a literal.

    Returns:
        The path τ² saved to, so a caller can assert a file rather than an absence of an error.

    Raises:
        RuntimeError: The adapter patched nothing, or the run on disk is a different run.
    """
    if (done := results_path(version)).exists() and (why := same_run(done, k)):
        raise RuntimeError(
            f"{done} holds a run of {version} made differently — {why}. Resuming would score two "
            f"configurations as one. Use a new version label, or delete {done.parent}"
        )
    telemetry.install()
    if (patched := adapter.install()) < 2:
        raise RuntimeError(
            f"the adapter replaced {patched} reference(s) — τ²'s roles hold their own, so a "
            "run this quiet would measure litellm and report it as ours"
        )

    from tau2.data_model.simulation import TextRunConfig
    from tau2.run import run_domain

    # `llm_agent`/`llm_user` still carry the pins even though the adapter answers every call:
    # τ² records them in `info.agent_info.llm`, and that is what `score` publishes as `model`.
    # A run whose results file names a model it did not use is worse than one with no model.
    cfg: Any = TextRunConfig(
        domain="retail",
        task_ids=frozen_task_ids(),
        num_trials=k,
        agent="llm_agent",
        llm_agent=config.MODEL,
        user="user_simulator",
        llm_user=config.USER_MODEL,
        save_to=run_name(version),
        auto_resume=True,  # D-111: never False — its branch is a console prompt, not a restart
    )
    run_domain(cfg)
    return results_path(version)
