"""P1.6 — assemble `results/<version>.json` around what `score()` computed.

The envelope, not the arithmetic. `score()` is pure and returns `aggregate` + `cases`; the rest
of docs/05 §6 is provenance, and every field of it is read from a file something else wrote
rather than restated here:

    benchmark_hash   `suite/benchmark/manifest.json` — P1.3 froze it, and
                     `freeze-benchmark --check` re-verifies it against τ²'s tasks.json
    tau2_commit      the same manifest. Not the results file's `info.git_commit` — see below
    model            the run's own `info.agent_info.llm`, which τ² wrote while running
    auth             read from `touchstone-run.json`, which the RUN wrote. NEVER measured
                     here: `score` is a separate invocation and its environment is not the one
                     that spent the quota (D-112)
    enforced         the same sidecar, same argument. Whether the gate was armed changes what
                     the agent was allowed to do, and τ²'s `info` has no field for it

`info.git_commit` names the wrong repository in any run we drive. τ²'s `get_commit_hash()`
(`utils/utils.py:91`) shells out to `git rev-parse HEAD` in the current working directory, and
ours is `touchstone` — measured 2026-08-26, byte-identical to `touchstone`'s own HEAD
(DEF-074). The pin is the manifest's, which is why P1.3 recorded it.

Keys with no producer are absent, never zero. `cost_per_success_usd`, `tool_calls_mean`,
`p95_latency_s`, `budget_exceeded` and `void_attempts` are span-derived and nothing reads spans
back yet; `diagnostics` and `regression` need phase 2 and phase 3. A key emitted as 0 before
anything can measure it is a published number that nothing computed.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from touchstone import config
from touchstone.loop.schema import Scored
from touchstone.loop.score import score

if TYPE_CHECKING:
    from pathlib import Path


def envelope(
    scored: Scored,
    manifest: dict[str, Any],
    info: dict[str, Any],
    version: str,
    k: int,
    auth: str,
    enforced: bool | None = None,
) -> dict[str, Any]:
    """Wrap `score()`'s two halves in the provenance that makes them comparable — docs/05 §6.

    Takes values, so the shape is checkable without a run, a manifest on disk or a τ² import —
    the same split as `adapter.rebind` and every `doctor` check.

    Args:
        scored: What `score()` returned — `aggregate` and `cases`.
        manifest: `suite/benchmark/manifest.json`, parsed.
        info: The τ² results file's `info` block, written by the run.
        version: The version label this run is published under.
        k: Trials per task — echoed so a reader never has to count `cases`.
        auth: How the run reached Anthropic, measured rather than assumed.
        enforced: Whether the gate was armed on the agent's tool calls. `None` where the run
            recorded nothing, and then the key is ABSENT rather than false — the rule this
            module's header states, and the case it covers is a lost sidecar, where `false`
            would be a claim about a run nothing here can see.

    Returns:
        The published results object, provenance first and arithmetic after it.
    """
    return {
        "version": version,
        "benchmark_hash": manifest["tasks_sha256"],
        "domain": manifest["domain"],
        "tau2_commit": manifest["tau2_commit"],
        "k": k,
        "model": (info.get("agent_info") or {}).get("llm", ""),
        "user_model": (info.get("user_info") or {}).get("llm", ""),
        "provider": "anthropic",
        "auth": auth,
        **({} if enforced is None else {"enforced": enforced}),
        **scored,
    }


def recorded_auth(results_file: Path) -> str:
    """What the run recorded beside itself, or `unknown` when it recorded nothing.

    `unknown` is a real answer and not a default: it says this run predates D-112 or lost its
    sidecar, which is exactly what a reader needs to know before comparing its numbers to a
    run whose auth is stated. Measuring the environment here instead would answer a question
    about the SCORING process and publish it as a fact about the run.
    """
    from touchstone.loop.run import PROVENANCE

    side = results_file.with_name(PROVENANCE)
    return str(json.loads(side.read_text())["auth"]) if side.exists() else "unknown"


def recorded_enforcement(results_file: Path) -> bool | None:
    """Whether the run armed the gate, or None when it recorded nothing.

    `None` rather than False, and the difference is the same one `auth` makes with `unknown`: a
    run with no sidecar did not tell us, and answering False would publish a fact about the gate
    that came from the absence of a file. `envelope` drops the key on None.
    """
    from touchstone.loop.run import PROVENANCE

    side = results_file.with_name(PROVENANCE)
    if not side.exists():
        return None
    recorded = json.loads(side.read_text()).get("enforced")
    return bool(recorded) if recorded is not None else None


def write(results_file: Path, version: str, k: int) -> Path:
    """Score a τ² results file and publish `results/<version>.json`. Returns what it wrote.

    Args:
        results_file: The τ² results file — what `loop.run.run()` returned.
        version: The version label to publish under.
        k: Trials per task, `config.K`.

    Returns:
        The path written, so a caller asserts a file rather than an absence of an error.
    """
    # Imported here, not at module scope: `run` pulls in the adapter and the SDK (0.5 s), and
    # this module is otherwise stdlib-only. `write` is already doing file I/O when it runs.
    from touchstone.loop.run import frozen_task_ids

    raw = json.loads(results_file.read_text())
    manifest = json.loads((config.BENCHMARK / "manifest.json").read_text())
    # `benchmark_hash` is a claim about WHICH tasks produced these numbers, and nothing else in
    # the file can contradict it. Publishing the manifest's hash over a run of different tasks
    # would be undetectable downstream, so it is checked here rather than trusted.
    if (ran := {str(s["task_id"]) for s in raw["simulations"]}) != set(frozen_task_ids()):
        raise ValueError(
            f"{results_file} covers {len(ran)} task(s), not the {len(frozen_task_ids())} the "
            "manifest froze — `benchmark_hash` would name tasks this run did not touch"
        )
    published = envelope(
        score(raw["simulations"], k),
        manifest,
        raw.get("info") or {},
        version,
        k,
        recorded_auth(results_file),
        recorded_enforcement(results_file),
    )

    config.RESULTS.mkdir(parents=True, exist_ok=True)
    out = config.RESULTS / f"{version}.json"
    # `sort_keys=False`: the envelope's order is provenance first, and a reader who opens this
    # file should see what the numbers are ABOUT before seeing the numbers.
    out.write_text(json.dumps(published, indent=2) + "\n")
    return out
