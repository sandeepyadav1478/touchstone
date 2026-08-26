"""The one part of the seam that is logic rather than an SDK call.

`rebind` is testable because it takes the module it patches as an argument — the conversions it
sits above are in `test_translate`, and the SDK call itself is covered by the live smoke check.
"""

import sys
import types

from touchstone.adapter import rebind


def test_rebind_reaches_the_modules_that_imported_the_function() -> None:
    """The ten-module trap: patching the home module alone leaves every role on upstream."""

    def upstream() -> str:
        return "upstream"

    def ours() -> str:
        return "ours"

    # setattr, matching `adapter.rebind` — `ModuleType` declares no `generate` (D-100).
    home = types.ModuleType("tau2.utils.llm_utils")
    setattr(home, "generate", upstream)  # noqa: B010
    role = types.ModuleType("tau2.agent.llm_agent")
    setattr(role, "generate", upstream)  # noqa: B010
    bystander = types.ModuleType("tau2.runner.batch")
    setattr(bystander, "generate", lambda: "someone else's generate")  # noqa: B010
    outsider = types.ModuleType("elsewhere.thing")
    setattr(outsider, "generate", upstream)  # noqa: B010

    added = {m.__name__: m for m in (home, role, bystander, outsider)}
    sys.modules.update(added)
    try:
        assert rebind(home, ours) == 2, "the home module and the one role holding a reference"
        assert home.generate is ours and role.generate is ours
        assert bystander.generate() == "someone else's generate", "a different function is left alone"
        assert outsider.generate is upstream, "only tau2.* is patched"
    finally:
        for name in added:
            sys.modules.pop(name, None)
