"""One check's verdict, and how it is marked on the terminal.

Separate from the checks so that a module adding one imports the vocabulary and not the
runner — `run()` imports every check, so a check importing `run()`'s module is a cycle.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Status = Literal["pass", "warn", "fail"]

# Glyphs the terminal prints. Not decoration: `MARK` is this command's whole output
# alphabet, so it is a string literal a style sweep must not touch (D-101).
MARK = {"pass": "\u2713", "warn": "\u26a0", "fail": "\u2717"}
COLOUR = {"pass": "green", "warn": "yellow", "fail": "bold red"}


@dataclass
class Check:
    """One probe's verdict — what was checked, what was found, what to do about it."""

    status: Status
    name: str
    detail: str
    note: str = ""
