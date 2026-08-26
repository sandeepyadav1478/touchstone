"""P1.2 — where a span goes after `adapter.py` opens it.

**There is no provider and no exporter here, and that is the whole finding.** D-074 made MLflow
the spine and deleted the OTel SDK, the OTLP exporter and the Phoenix container with it, so the
row this file was scheduled against — *"provider + exporter"* — describes a stack that no longer
exists. What is left is three lines of configuration and one flush, because `mlflow.start_span()`
already owns the tracer, the processor and the writer.

⚠️ **Three things were assumed about that store and all three are wrong on the installed version.
Measured 2026-08-26 against `mlflow-skinny` 3.15.1, not read from documentation:**

1. 🔴 **`mlruns/` on disk RAISES by default.** `MlflowException: The filesystem tracking backend
   is in maintenance mode` — it is refused unless `MLFLOW_ALLOW_FILE_STORE=true` is in the
   environment. D-074's *"writes to `mlruns/` on disk, so there is no service to be up or down"*
   is true about the *architecture* and false about the *call*, and `doctor.py:307` repeats it.
2. 🔴 **`sqlite:///` — the backend MLflow's own error message tells you to migrate to — is not
   registered in `mlflow-skinny` at all.** Supported schemes are
   `['', 'file', 'databricks', 'databricks-uc', 'uc', 'http', 'https']`; the SQLAlchemy store
   ships in full `mlflow`. So the advertised escape hatch costs a second, heavier dependency,
   and the flag costs nothing. ⛔ **Do not "fix" the maintenance-mode warning by switching to
   sqlite without adding `mlflow` proper — it fails at `set_experiment`, not at first write.**
3. 🔴 **Export is ASYNCHRONOUS, so a span is not readable when the `with` block closes.**
   Measured: `search_traces()` immediately after a closed span returned **0**, then **1** after
   `flush()`. The queue does drain at interpreter exit — which is exactly the shape that makes
   this invisible in a script and wrong in a test.

⛔ **Nothing here is a fallback.** If the store cannot be reached the run has no evidence, and a
version table whose rows have no traces behind them is a table of anecdotes — so `doctor` asserts
a **round trip** (write, flush, read back, compare) rather than an import, per DEF-052.
"""

from __future__ import annotations

import os

import mlflow

from touchstone import config


def install() -> str:
    """Point MLflow at the on-disk store. Returns the URI it actually resolved to.

    ⛔ **Returns a value rather than nothing** — DEF-052. Three emitters in this project were
    assumed live for days because installing them raised nothing; a caller that cannot compare
    the result against what it asked for has not checked anything.
    """
    # `setdefault`, not assignment: an operator who has set it to something else has made a
    # decision, and silently overriding it is how a run stops writing where its logs say it does.
    os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")
    mlflow.set_tracking_uri(config.TRACKING_URI)
    mlflow.set_experiment(config.EXPERIMENT)
    return mlflow.get_tracking_uri()


def flush() -> None:
    """Drain the async export queue so a span written in this process can be read in it.

    ⚠️ `terminate` stays False. Draining is needed after every unit of work that something reads
    back; shutting the threads down is needed once, at exit, and doing both here would make the
    second call in a run a silent no-op.
    """
    mlflow.flush_trace_async_logging()
