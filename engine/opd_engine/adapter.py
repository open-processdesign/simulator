"""Engine adapter interface.

This is the only boundary between the application and a calculation engine.
The UI and API exchange OPD flowsheet documents (see schema/flowsheet.schema.json);
an adapter translates them to an engine, runs it and maps results back.

Rules (see AGENTS.md and docs/ARCHITECTURE.md):
- No engine-specific object may leave an adapter.
- Numbers always come from the engine; adapters never invent values.
- All quantities are SI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable

OPDDocument = dict[str, Any]


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class Target:
    kind: str  # "unit" | "stream" | "thermo" | "component"
    id: str | None = None


@dataclass(frozen=True)
class Issue:
    """User-facing problem. `message_key` is translated via web/locales/*.json."""

    severity: Severity
    code: str
    message_key: str
    target: Target | None = None
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class SimulationResult:
    converged: bool
    document: OPDDocument  # input document with `results` filled in
    issues: list[Issue] = field(default_factory=list)
    engine: str = ""
    engine_version: str = ""


@dataclass(frozen=True)
class Capabilities:
    unit_types: frozenset[str]
    thermo_packages: frozenset[str]
    supports_recycle: bool = False


@runtime_checkable
class EngineAdapter(Protocol):
    """Contract every engine (DWSIM, reference, own modules) must fulfil."""

    name: str

    def version(self) -> str:
        """Engine version string, stored with every result for traceability."""
        ...

    def capabilities(self) -> Capabilities:
        """What this engine can solve; the API uses it to reject unsupported documents early."""
        ...

    def validate(self, doc: OPDDocument) -> list[Issue]:
        """Engine-specific checks (missing specs, unsupported units). Must not run a simulation."""
        ...

    def simulate(self, doc: OPDDocument) -> SimulationResult:
        """Run the flowsheet and return the document with `results` filled in."""
        ...


_REGISTRY: dict[str, EngineAdapter] = {}


def register(adapter: EngineAdapter) -> None:
    if not isinstance(adapter, EngineAdapter):
        raise TypeError(f"{adapter!r} does not implement EngineAdapter")
    _REGISTRY[adapter.name] = adapter


def get(name: str) -> EngineAdapter:
    try:
        return _REGISTRY[name]
    except KeyError:
        raise KeyError(f"Unknown engine '{name}'. Registered: {sorted(_REGISTRY)}") from None


def available() -> list[str]:
    return sorted(_REGISTRY)
