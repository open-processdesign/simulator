"""DWSIM adapter (placeholder).

DWSIM runs as a separate service (GPL boundary, crash isolation). This adapter will
call that service, translating OPD documents to DWSIM flowsheets and mapping results back.
Implementation: tasks T08 (headless spike) and T09 (adapter). Do not copy DWSIM source here.
"""

from __future__ import annotations

from ..adapter import Capabilities, Issue, OPDDocument, Severity, SimulationResult, Target


class DwsimAdapter:
    name = "dwsim"

    def __init__(self, service_url: str | None = None) -> None:
        self.service_url = service_url

    def version(self) -> str:
        return "unconfigured"

    def capabilities(self) -> Capabilities:
        return Capabilities(unit_types=frozenset(), thermo_packages=frozenset())

    def validate(self, doc: OPDDocument) -> list[Issue]:
        return [Issue(Severity.ERROR, "engine_unavailable", "issues.engine_unavailable",
                      Target("thermo"), {"engine": self.name})]

    def simulate(self, doc: OPDDocument) -> SimulationResult:
        return SimulationResult(converged=False, document=doc, issues=self.validate(doc),
                                engine=self.name, engine_version=self.version())
