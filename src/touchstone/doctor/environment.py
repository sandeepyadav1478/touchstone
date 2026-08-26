"""What is true of this machine before a single model call — docs/00 §6.

Everything here is cheap, local and needs neither τ² nor the SDK, which is why it runs
first: a missing CLI or a set API key makes every later check meaningless.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tomllib
from pathlib import Path

import httpx

from .. import config
from .result import Check


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
    """The one check this command exists for."""
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


def _cerebras() -> Check:
    """Report the Cerebras key, with the polarity D-067 requires.

    Absent is the correct state and reads as a pass: under D-067 every role is Anthropic and
    Cerebras is a diagnostic, never a model source. The polarity was inverted before that.

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
