#!/usr/bin/env python3
"""Check every relative markdown link in the *tracked* files, against git rather than disk.

The distinction is the whole point. A link audit that asks the filesystem passes on a
target that is gitignored, because the file is right there — and then 404s for every
reader of the public repo, who never receives it. `DECISIONS.md`, `DEFECTS.md` and
`ROADMAP.md` are exactly that: present locally, deliberately excluded from the push.

That failure was introduced and caught on 2026-08-16 in one sitting. Three links to
`../DECISIONS.md` and `../DEFECTS.md` were written into `docs/05-scoring.md`, an ad-hoc
`Path.exists()` audit reported *0 broken links*, and the convention every other tracked
doc already followed — cite those three as plain backticked text, never as a link — is
what showed the audit was answering a different question.

Two phases:

  1. Every `](relative/path)` in a tracked .md resolves to another *tracked* file.
  2. No tracked .md links to a file git is ignoring, which is phase 1's failure mode
     stated in the direction that explains it.

    python3 scripts/check-links.py             # check, print a summary
    python3 scripts/check-links.py --verbose   # also print every resolved link
"""

from __future__ import annotations

import argparse
import logging
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINK = re.compile(r"\]\(([^)]+)\)")


def git(*args: str) -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True
    )
    return out.stdout.split()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)

    tracked = {(ROOT / p).resolve() for p in git("ls-files")}
    docs = sorted(p for p in tracked if p.suffix == ".md")
    logging.info("── milestone 1/2 · %d tracked markdown files", len(docs))

    broken: list[str] = []
    ignored: list[str] = []
    checked = 0

    for doc in docs:
        rel = doc.relative_to(ROOT)
        for lineno, line in enumerate(doc.read_text(encoding="utf-8").splitlines(), 1):
            for m in LINK.finditer(line):
                target = m.group(1).split("#")[0].strip()
                if not target or target.startswith(("http://", "https://", "mailto:")):
                    continue
                resolved = (doc.parent / target).resolve()
                checked += 1
                where = f"{rel}:{lineno} -> {target}"
                if resolved in tracked:
                    if args.verbose:
                        logging.info("  ok  %s", where)
                    continue
                # Split the two failures apart: a link to a file that is present but
                # ignored reads as fine locally and is the one worth naming.
                if resolved.exists():
                    ignored.append(where)
                else:
                    broken.append(where)

    logging.info("── milestone 2/2 · %d relative links checked", checked)

    for w in ignored:
        logging.error("  IGNORED BY GIT — 404s for every public reader: %s", w)
    for w in broken:
        logging.error("  MISSING: %s", w)

    if ignored or broken:
        logging.error(
            "\nFAIL — %d link(s) to gitignored files, %d to missing files",
            len(ignored),
            len(broken),
        )
        logging.error(
            "Cite DECISIONS.md, DEFECTS.md and ROADMAP.md as plain `backticks`, "
            "never as a link — they are local-only by design (README §working files)."
        )
        return 1

    logging.info("\nPASS — %d links, all resolve to tracked files", checked)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
