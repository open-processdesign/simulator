"""Pydantic models for the OPD flowsheet format (v0.1).

These mirror `schema/flowsheet.schema.json` (the source of truth). A test keeps the two
in sync by validating every example with both. All quantities are SI (see DECISIONS.md D007).

Structural rules (types, required fields, enums, id patterns) are enforced on parse and
raise `pydantic.ValidationError`. Cross-reference rules (a stream points to an existing
unit, mole fractions sum to 1, …) are user-facing problems and are reported as `Issue`
objects by `check_references`, so the UI can show and highlight them.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .adapter import Issue, Severity, Target

Id = Annotated[str, Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")]
Fraction = Annotated[float, Field(ge=0.0, le=1.0)]

ThermoPackage = Literal["IDEAL", "PR", "SRK", "NRTL", "UNIQUAC", "UNIFAC"]
UnitType = Literal[
    "feed", "product", "mixer", "splitter", "flash", "heater", "heat_exchanger",
    "pump", "compressor", "valve", "conversion_reactor", "shortcut_column",
    "distillation_column", "cstr", "pfr",
]
ParameterSource = Literal["database", "user", "literature", "regression", "default"]

FRACTION_TOLERANCE = 1e-6


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class Quantity(_Strict):
    value: float
    unit: str


class Component(_Strict):
    id: Id
    name: str
    cas: Annotated[str, Field(pattern=r"^[0-9]{2,7}-[0-9]{2}-[0-9]$")]
    formula: str | None = None


class BinaryParameter(_Strict):
    i: Id
    j: Id
    name: str
    value: float
    source: ParameterSource
    reference: str | None = None


class Thermo(_Strict):
    package: ThermoPackage
    binary_parameters: list[BinaryParameter] = Field(default_factory=list)


class Unit(_Strict):
    id: Id
    type: UnitType
    label: str | None = None
    specs: dict[str, Quantity] = Field(default_factory=dict)
    options: dict[str, Any] = Field(default_factory=dict)


class Port(_Strict):
    unit: Id
    port: str


class StreamState(_Strict):
    temperature: Quantity | None = None
    pressure: Quantity | None = None
    molar_flow: Quantity | None = None
    vapor_fraction: Quantity | None = None
    mole_fractions: dict[str, Fraction] | None = None


class Stream(_Strict):
    id: Id
    label: str | None = None
    from_: Port = Field(alias="from")
    to: Port
    state: StreamState | None = None


class Series(_Strict):
    unit: str
    values: list[float]


class Axis(_Strict):
    name: str
    unit: str
    values: list[float]


class Profile(_Strict):
    """Values along a unit (e.g. per column stage), all series as long as the axis."""

    axis: Axis
    series: dict[str, Series] = Field(default_factory=dict)


class Results(_Strict):
    engine: str | None = None
    engine_version: str | None = None
    converged: bool | None = None
    timestamp: str | None = None
    streams: dict[str, StreamState] = Field(default_factory=dict)
    units: dict[str, dict[str, Quantity]] = Field(default_factory=dict)
    profiles: dict[str, Profile] = Field(default_factory=dict)


class Position(BaseModel):
    model_config = ConfigDict(extra="allow")
    x: float
    y: float


class Flowsheet(_Strict):
    format: Literal["opd-flowsheet"] = "opd-flowsheet"
    version: Literal["0.1"] = "0.1"
    name: Annotated[str, Field(min_length=1)]
    description: str | None = None
    components: list[Component]
    thermo: Thermo
    units: list[Unit]
    streams: list[Stream]
    results: Results | None = None
    layout: dict[str, Position] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to the on-disk JSON shape: aliases, only fields that were set,
        plus `format` and `version`, which every document must carry."""
        body = self.model_dump(by_alias=True, exclude_none=True, exclude_unset=True)
        return {"format": self.format, "version": self.version, **body}

    def unit(self, unit_id: str) -> Unit | None:
        return next((u for u in self.units if u.id == unit_id), None)

    def stream(self, stream_id: str) -> Stream | None:
        return next((s for s in self.streams if s.id == stream_id), None)


def load(source: str | Path | dict[str, Any]) -> Flowsheet:
    """Parse a flowsheet from a dict, a JSON string, or a path to a .opd.json file."""
    if isinstance(source, dict):
        return Flowsheet.model_validate(source)
    if isinstance(source, Path) or (isinstance(source, str) and source.endswith(".json")):
        return Flowsheet.model_validate(json.loads(Path(source).read_text(encoding="utf-8")))
    return Flowsheet.model_validate_json(source)


def _duplicates(ids: list[str]) -> set[str]:
    seen: set[str] = set()
    return {i for i in ids if i in seen or seen.add(i)}


def check_references(doc: Flowsheet) -> list[Issue]:
    """Cross-reference checks that the JSON Schema cannot express.

    Returns user-facing issues; an empty list means the document is consistent.
    Engine-specific checks (missing specs for a unit type) belong to adapters.
    """
    issues: list[Issue] = []

    def err(code: str, kind: str, id_: str | None, **params: Any) -> None:
        issues.append(Issue(Severity.ERROR, code, f"issues.{code}", Target(kind, id_), params))

    for kind, ids in (
        ("component", [c.id for c in doc.components]),
        ("unit", [u.id for u in doc.units]),
        ("stream", [s.id for s in doc.streams]),
    ):
        for dup in sorted(_duplicates(ids)):
            err("duplicate_id", kind, dup, id=dup)

    unit_ids = {u.id for u in doc.units}
    comp_ids = {c.id for c in doc.components}

    for s in doc.streams:
        for end in (s.from_, s.to):
            if end.unit not in unit_ids:
                err("unknown_unit", "stream", s.id, unit=end.unit)
        fractions = s.state.mole_fractions if s.state else None
        if fractions:
            unknown = sorted(set(fractions) - comp_ids)
            if unknown:
                err("unknown_component", "stream", s.id, components=unknown)
            total = sum(fractions.values())
            if abs(total - 1.0) > FRACTION_TOLERANCE:
                err("fractions_not_normalized", "stream", s.id, sum=round(total, 6))

    used_ports: dict[tuple[str, str], str] = {}
    for s in doc.streams:
        for end in (s.from_, s.to):
            key = (end.unit, end.port)
            if key in used_ports and used_ports[key] != s.id:
                err("port_used_twice", "unit", end.unit, port=end.port,
                    streams=[used_ports[key], s.id])
            used_ports.setdefault(key, s.id)

    for p in doc.thermo.binary_parameters:
        for cid in (p.i, p.j):
            if cid not in comp_ids:
                err("unknown_component", "thermo", None, components=[cid])

    for uid in doc.layout:
        if uid not in unit_ids:
            issues.append(Issue(Severity.WARNING, "layout_orphan", "issues.layout_orphan",
                                Target("unit", uid), {"unit": uid}))
    return issues
