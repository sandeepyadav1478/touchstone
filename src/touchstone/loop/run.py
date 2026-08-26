"""P1.6 — drive τ² over the frozen benchmark subset with our adapter behind the seam.

Thin on purpose. Running 114 tasks, driving a simulator and computing `reward_breakdown` is
τ²'s work and it is already done (D-080); what is ours is three things it cannot do for us:

    install     `telemetry.install()` then `adapter.install()`, in that order and BEFORE the
                τ² import that matters, so every model role resolves to the SDK
    restrict    `task_ids` from `suite/benchmark/manifest.json`, never `num_tasks` — the
                frozen ten are a recorded selection (D-098), and a count would re-sample it
    verify      `install()` returns how many references it replaced, and a run that patched
                nothing is stopped here rather than discovered in the results (DEF-052)

`--resume` is τ²'s own `auto_resume`: it writes each simulation as it completes and skips what
is already on disk, which is exactly D-015 and is already built. The quota is a five-hour window
that REJECTS rather than bills, so a re-run that discards completed work is the failure mode.
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


def run(version: str, k: int, *, resume: bool = False) -> Path:
    """Run the frozen subset `k` times each. Returns the τ² results file it wrote.

    Args:
        version: The version label — names the run directory, and `score` resolves the same one.
        k: Trials per task. `config.K` by default, quoted from there and never as a literal.
        resume: Skip simulations already on disk (τ²'s `auto_resume`).

    Returns:
        The path τ² saved to, so a caller can assert a file rather than an absence of an error.
    """
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
        auto_resume=resume,
    )
    run_domain(cfg)
    return results_path(version)
