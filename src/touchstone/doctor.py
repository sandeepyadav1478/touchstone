"""`touchstone doctor` — the first file in the project.

It stops the two failures that each cost an evening (docs/00 §6).

1. `ANTHROPIC_API_KEY` set     → every run silently bills an API account instead of the
                                 subscription. Nothing else in the project would notice.
2. `setting_sources` not `[]`  → the developer's own CLAUDE.md, skills and MCP servers are
                                 loaded into the agent under test. The scores then describe
                                 this machine, not the agent.

⚠️ Failure 2 is asserted **by measurement, not by reading the constant**: the SDK reports
which memory files it loaded, so `doctor` asks it. A config value that *says* isolation and
a session that *is* isolated are different claims (D-034).
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import httpx

from . import config

Status = Literal["pass", "warn", "fail"]

MARK = {"pass": "✓", "warn": "⚠", "fail": "✗"}
COLOUR = {"pass": "green", "warn": "yellow", "fail": "bold red"}


@dataclass
class Check:
    """One probe's verdict — what was checked, what was found, what to do about it."""

    status: Status
    name: str
    detail: str
    note: str = ""


def _claude_cli() -> Check:
    path = shutil.which("claude")
    if not path:
        return Check(
            "fail", "claude CLI", "not on PATH",
            "the SDK spawns it — nothing runs without it",
        )
    try:
        out = subprocess.run(
            [path, "--version"], capture_output=True, text=True, timeout=20, check=True
        ).stdout.strip()
    except (subprocess.SubprocessError, OSError) as exc:
        return Check("fail", "claude CLI", f"{path} — {type(exc).__name__}")
    return Check("pass", "claude CLI", f"{out.split()[0]}  ({path})")


def _subscription_auth() -> Check:
    creds = Path.home() / ".claude" / ".credentials.json"
    if not creds.exists():
        return Check(
            "fail", "subscription auth", "~/.claude/.credentials.json missing",
            "run `claude` once and log in",
        )
    mode = oct(creds.stat().st_mode & 0o777)[2:]
    return Check("pass", "subscription auth", f"~/.claude/.credentials.json present (mode {mode})")


def _api_key_absent() -> Check:
    """⛔ The one check this command exists for."""
    if os.environ.get(config.API_KEY_ENV):
        return Check(
            "fail",
            config.API_KEY_ENV,
            "SET",
            "runs would bill an API account, not the subscription (D-001). `unset` it",
        )
    return Check("pass", config.API_KEY_ENV, "absent")


def _lockfile() -> Check:
    lock = config.ROOT / "uv.lock"
    pyproject = config.ROOT / "pyproject.toml"
    if not lock.exists():
        return Check(
            "fail", "uv.lock", "missing",
            "a version table nobody can reproduce is anecdote",
        )
    data = tomllib.loads(pyproject.read_text())
    direct = (
        len(data["project"]["dependencies"])
        + sum(len(v) for v in data["project"].get("optional-dependencies", {}).values())
        + sum(len(v) for v in data.get("dependency-groups", {}).values())
    )
    return Check("pass", "uv.lock", f"present, {direct} direct deps")


def specimen_check(tasks: int, policy_bytes: int) -> Check:
    """Compare a resolved specimen against the measured pin — the logic half of P1.0.

    ⚠️ **Split out from `_tau2_data` so it can be tested without importing τ².** That
    import costs **1.71 s** measured here, and phase 1's exit gate is *"`pytest
    tests/unit` green, no network, under 2 seconds"* — one import would spend the whole
    budget. `model_check` above is split for the same reason and it is the same
    convention: the I/O goes in the private wrapper, the decision goes here.

    Args:
        tasks: How many tasks retail's `tasks.json` actually holds.
        policy_bytes: The on-disk size of retail's `policy.md`.

    Returns:
        A pass only when both match `config`'s measured values.
    """
    detail = f"retail: {tasks} tasks, policy {policy_bytes} B"
    if (tasks, policy_bytes) != (config.TAU2_RETAIL_TASKS, config.TAU2_RETAIL_POLICY_BYTES):
        return Check(
            "fail", "tau2 data", detail,
            f"expected {config.TAU2_RETAIL_TASKS} and {config.TAU2_RETAIL_POLICY_BYTES} B — "
            "a different specimen makes every number here about a different corpus",
        )
    return Check("pass", "tau2 data", detail)


def _tau2_data() -> Check:
    """Assert the specimen a run would actually load — P1.0.

    ⛔ **τ² resolves its data directory ONCE, at import, and warns rather than fails.**
    `tau2/utils/utils.py:30-35` logs three `logger.warning` lines and continues
    (DEF-051), and `tau2/domains/retail/utils.py:3-6` freezes every `RETAIL_*` path
    off that resolution at module level. A warning in someone else's logger is not a
    check, and by the time a run notices, the paths have been wrong for the whole
    process.

    ⚠️ **It reads τ²'s own constants rather than re-deriving the path.** Re-deriving
    would give a check that can pass while the run fails; the only value worth
    asserting on is the one the run will use. That is also why the import is here and
    not at module scope — importing τ² runs its resolution, and `doctor` should be
    able to report that the import itself failed.

    🔴 **The failing case is the DEFAULT one.** With `TAU2_DATA_DIR` unset, τ² falls
    back to `Path(__file__).parents[3] / "data"`, which under a venv install resolves
    inside the venv rather than the checkout. Measured here 2026-08-25:
    `.venv/lib/python3.12/data`, which has never existed.

    Returns:
        A pass only when both retail files are on disk AND match the measured pin.
    """
    try:
        from tau2.domains.retail.utils import RETAIL_POLICY_PATH, RETAIL_TASK_SET_PATH
    except ImportError as exc:
        return Check(
            "fail", "tau2 data", f"tau2 not importable — {exc}",
            "the specimen is pinned in pyproject's [tool.uv.sources]",
        )

    if missing := [p for p in (RETAIL_TASK_SET_PATH, RETAIL_POLICY_PATH) if not p.exists()]:
        return Check(
            "fail", "tau2 data", f"{len(missing)} of 2 files missing under {RETAIL_POLICY_PATH.parent}",
            "set TAU2_DATA_DIR to the checkout's data/ directory — τ² only warns",
        )

    return specimen_check(
        len(json.loads(RETAIL_TASK_SET_PATH.read_text())),
        RETAIL_POLICY_PATH.stat().st_size,
    )


def _cerebras() -> Check:
    """Report the Cerebras key, with the polarity D-067 requires.

    ⛔ **Absent is the CORRECT state and must read as a pass.** This check was written
    the other way round: absent warned with *"path B unavailable, the judge has no
    fallback"*, and present passed with *"path B available"*. That was the pre-D-067
    design, where Cerebras judged and stood in when the Claude quota ran out. Under
    D-067 every role is Anthropic and Cerebras is a `doctor` diagnostic, never a model
    source — so the old wording made the correct environment emit a warning, and a
    warning on the correct state is how a whole column of warnings stops being read.

    Returns:
        A pass when the key is absent, a warning when it is set.
    """
    if os.environ.get("CEREBRAS_API_KEY"):
        return Check(
            "warn", "CEREBRAS_API_KEY", "set",
            "nothing here reads it — D-067 allows no non-Anthropic model source",
        )
    return Check("pass", "CEREBRAS_API_KEY", "absent — correct, no fallback provider is used")


def _http(url: str, name: str, hint: str) -> Check:
    try:
        httpx.get(url, timeout=2.0)
    except httpx.HTTPError:
        return Check("warn", name, f"{url} unreachable", hint)
    return Check("pass", name, url)


def model_check(usage_by_model: dict[str, Any], total_cost_usd: float) -> Check:
    """Which model actually answered — matched by name, never by position.

    ⛔ The id is a KEY of `model_usage`; there is no `canonicalModel` field in the Python SDK
    (D-033). And there can be **more than one key**: in isolation mode the CLI makes its own
    housekeeping call on haiku, and that key sorts *first*. `next(iter(...))` therefore reads a
    model the agent never used — which is how this check failed on its first run against a
    correctly pinned model (D-035).
    """
    others = [m for m in usage_by_model if m != config.MODEL]
    if config.MODEL not in usage_by_model:
        return Check(
            "fail",
            "model",
            f"asked {config.MODEL}, answered {', '.join(usage_by_model) or 'nothing'}",
            "the pin did not take — every version-table row would be unattributable (D-013)",
        )
    return Check(
        "pass",
        "model",
        f"{config.MODEL}  (pinned, answered by a live call, ${total_cost_usd:.4f} total)",
        f"+ {', '.join(others)} — the CLI's own housekeeping, not the agent" if others else "",
    )


async def _probe() -> list[Check]:
    """One live call. It settles the model id AND whether the session is isolated.

    ⚠️ `max_turns` is not a count of model calls — with `output_format` the structured-output
    step spends one of its own (D-032). Nothing here uses output_format, so 2 is ample.
    """
    from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, ResultMessage

    options = ClaudeAgentOptions(
        setting_sources=config.SETTING_SOURCES,  # ⛔ [] — see config.py
        model=config.MODEL,  # ⛔ pinned; the probe exists to prove it resolves
        allowed_tools=[],
        max_turns=2,
        max_budget_usd=0.10,
    )

    result: ResultMessage | None = None
    async with ClaudeSDKClient(options=options) as client:
        await client.query("Reply with the single word: ok")
        async for message in client.receive_response():
            if isinstance(message, ResultMessage):
                result = message
        usage = await client.get_context_usage()

    if result is None or result.is_error:
        return [
            Check(
                "fail", "model", "no result from a live probe",
                str(result and result.errors),
            )
        ]

    checks = [model_check(result.model_usage or {}, result.total_cost_usd or 0.0)]

    memory = usage.get("memoryFiles") or []
    agents = usage.get("agents") or []
    mcp = [t for t in (usage.get("mcpTools") or []) if t.get("isLoaded")]
    contamination = len(memory) + len(agents) + len(mcp)
    if contamination:
        names = ", ".join(Path(m.get("path", "?")).name for m in memory) or "—"
        checks.append(
            Check(
                "fail",
                "setting_sources",
                f"{len(memory)} memory file(s), {len(agents)} agent(s), "
                f"{len(mcp)} MCP tool(s) loaded",
                f"the agent under test is reading this machine: {names}. Must be []",
            )
        )
    else:
        checks.append(
            Check(
                "pass",
                "setting_sources",
                f"[] — 0 memory files, 0 agents, 0 MCP tools "
                f"({usage.get('totalTokens', '?')} ctx tokens)",
            )
        )
    return checks


def run(probe: bool = True) -> int:
    """Print the report, return the process exit code."""
    from rich.console import Console

    console = Console()
    checks = [_claude_cli(), _subscription_auth(), _api_key_absent()]
    if probe:
        checks += asyncio.run(_probe())
    else:
        checks.append(Check(
            "warn", "model", "not probed",
            "--no-probe was passed; D-001 needs a live id",
        ))
    checks += [
        _cerebras(),
        # ⛔ Unreachable is fine: D-067 makes ollama a diagnostic, never a model source.
        _http(f"{config.OLLAMA_URL}/api/tags", "ollama", "a diagnostic — never a model source"),
        # D-077: no trace-server check. MLflow autologs LangGraph in-process and
        # writes to `mlruns/` on disk, so there is no service to be up or down.
        # A tracking-store check belongs in the P1.0 doctor pass, designed, not
        # bolted on here.
        _tau2_data(),
        _lockfile(),
    ]

    width = max(len(c.name) for c in checks)
    console.print("touchstone doctor")
    for c in checks:
        line = f"  [{COLOUR[c.status]}]{MARK[c.status]}[/] {c.name:<{width}}  {c.detail}"
        if c.note:
            line += f"   [dim]— {c.note}[/dim]"
        console.print(line)

    failed = [c for c in checks if c.status == "fail"]
    if failed:
        console.print(f"\n[bold red]✗ {len(failed)} blocking[/] — fix before running anything.")
        return 1
    if probe:
        console.print(
            "\n[green]✓ green.[/] Paste this output verbatim into your "
            "decision record (D-001)."
        )
    else:
        console.print("\n[green]✓ green[/], but unprobed — D-001 needs a run with the live call.")
    return 0
