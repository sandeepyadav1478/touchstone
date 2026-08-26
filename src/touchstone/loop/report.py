"""P1.6 — assemble `results/<version>.json` around what `score()` computed.

The envelope, not the arithmetic. `score()` is pure and returns `aggregate` + `cases`; the rest
of docs/05 §6 is provenance, and every field of it is read from a file something else wrote
rather than restated here:

    benchmark_hash   `suite/benchmark/manifest.json` — P1.3 froze it, and
                     `freeze-benchmark --check` re-verifies it against τ²'s tasks.json
    tau2_commit      the same manifest. Not the results file's `info.git_commit` — see below
    model            the run's own `info.agent_info.llm`, which τ² wrote while running
    auth             measured from the environment, the same fact `doctor` reports

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
import os
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
        **scored,
    }


def auth_mode() -> str:
    """`subscription` or `api_key` — measured from the environment, never assumed.

    D-001 runs on the subscription and `doctor` asserts the key's ABSENCE, so the two can
    disagree only if something set it between the check and the run. This reads it at the
    moment the file is written, which is the only moment the answer is about this run.
    """
    return "api_key" if os.environ.get(config.API_KEY_ENV) else "subscription"


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
        score(raw["simulations"], k), manifest, raw.get("info") or {}, version, k, auth_mode()
    )

    config.RESULTS.mkdir(parents=True, exist_ok=True)
    out = config.RESULTS / f"{version}.json"
    # `sort_keys=False`: the envelope's order is provenance first, and a reader who opens this
    # file should see what the numbers are ABOUT before seeing the numbers.
    out.write_text(json.dumps(published, indent=2) + "\n")
    return out
