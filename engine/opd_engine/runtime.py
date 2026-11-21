"""JSON-in / JSON-out entry point used by every host of the engine layer.

The browser (Pyodide in a Web Worker, T03) and a future HTTP service call the same
function, so they always return the same shape:

    {"converged": bool, "engine": str, "engine_version": str,
     "document": <OPD document, with `results` when converged>,
     "issues": [{"severity", "code", "message_key", "target": {"kind", "id"} | null, "params"}]}
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from . import adapter


def _load_engine(name: str) -> adapter.EngineAdapter:
    if name == "reference" and name not in adapter.available():
        from .adapters import reference  # noqa: F401  (registers itself on import)
    return adapter.get(name)


def _issue_dict(issue: adapter.Issue) -> dict[str, Any]:
    data = asdict(issue)
    data["severity"] = issue.severity.value
    return data


def simulate(doc: dict[str, Any], engine: str = "reference") -> dict[str, Any]:
    result = _load_engine(engine).simulate(doc)
    return {
        "converged": result.converged,
        "engine": result.engine,
        "engine_version": result.engine_version,
        "document": result.document,
        "issues": [_issue_dict(i) for i in result.issues],
    }


def simulate_json(doc_json: str, engine: str = "reference") -> str:
    """Same as `simulate`, with JSON strings at the boundary (cheap to pass to JS)."""
    return json.dumps(simulate(json.loads(doc_json), engine))
