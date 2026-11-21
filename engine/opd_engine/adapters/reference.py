"""Reference adapter: a small sequential-modular engine built on MIT-licensed `thermo`.

Purpose (DECISIONS.md D005, D011): tests and local development without DWSIM, the
December demo engine (it runs in the browser through Pyodide, see T03), and the seed of
own modules. All property and phase-equilibrium numbers come from `thermo`
(Caleb Bell et al., https://github.com/CalebBell/thermo, MIT); this module only does
bookkeeping: port conventions, material and energy balances, and the solve order.

Scope (T04): acyclic flowsheets; units feed, product, mixer, splitter, heater, valve,
flash; property packages IDEAL (Raoult), PR and SRK. Recycle loops come in T08.

Port and spec conventions (all values SI, see DECISIONS.md D007 and D013):

=========  =====================  ==========================================================
unit       ports                  specs
=========  =====================  ==========================================================
feed       out                    on the outgoing stream ``state``: pressure, molar_flow,
                                  mole_fractions, and temperature *or* vapor_fraction
product    in                     –
mixer      in*, out               optional pressure (default: lowest inlet pressure);
                                  adiabatic
splitter   in, any outlets        ``split_<port>`` (fraction, unit "1") for every outlet
                                  but one; the remaining outlet takes the rest
heater     in, out                exactly one of temperature, duty, vapor_fraction;
                                  optional pressure *or* pressure_drop (default: none)
valve      in, out                pressure *or* pressure_drop; isenthalpic
flash      in, vapor, liquid      pressure *or* pressure_drop, and exactly one of
                                  temperature, duty, vapor_fraction
=========  =====================  ==========================================================

Duty is heat added to the process stream (W): positive for heating, negative for cooling.
"""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

import thermo
from pydantic import ValidationError
from thermo import (
    CEOSGas,
    CEOSLiquid,
    ChemicalConstantsPackage,
    FlashPureVLS,
    FlashVL,
    GibbsExcessLiquid,
    IdealGas,
    PRMIX,
    SRKMIX,
)
from thermo.interaction_parameters import IPDB

from .. import adapter as _adapter
from ..adapter import Capabilities, Issue, OPDDocument, Severity, SimulationResult, Target
from ..models import Flowsheet, Stream, Unit, check_references, load

UNIT_TYPES = frozenset({"feed", "product", "mixer", "splitter", "heater", "valve", "flash"})
THERMO_PACKAGES = frozenset({"IDEAL", "PR", "SRK"})

# SI unit strings accepted per spec name (v0.1 stores SI only).
_SI = {
    "temperature": {"K"},
    "pressure": {"Pa"},
    "pressure_drop": {"Pa"},
    "duty": {"W"},
    "molar_flow": {"mol/s"},
    "vapor_fraction": {"1", "-", ""},
}
_FRACTION_UNITS = {"1", "-", ""}

# Interaction-parameter tables shipped with `thermo` (ChemSep, public domain data).
_KIJ_TABLE = {"PR": "ChemSep PR"}

# Flow below this is treated as an empty stream (mol/s).
_ZERO_FLOW = 1e-12


class _InputError(Exception):
    """Raised during the solve when an input problem is found; carries the issue."""

    def __init__(self, issue: Issue) -> None:
        super().__init__(issue.code)
        self.issue = issue


@dataclass
class _State:
    """Internal stream state. `zs` and `H` are None for an empty stream."""

    T: float
    P: float
    F: float
    zs: list[float] | None
    H: float | None  # molar enthalpy, J/mol (thermo reference state)
    VF: float | None


def _issue(severity: Severity, code: str, kind: str, id_: str | None, **params: Any) -> Issue:
    return Issue(severity, code, f"issues.{code}", Target(kind, id_), params)


def _error(code: str, kind: str, id_: str | None, **params: Any) -> Issue:
    return _issue(Severity.ERROR, code, kind, id_, **params)


class _Thermo:
    """Builds a `thermo` flasher for the document's components and property package."""

    def __init__(self, fs: Flowsheet) -> None:
        self.ids = [c.id for c in fs.components]
        self.cas = [c.cas for c in fs.components]
        self.package = fs.thermo.package
        self.issues: list[Issue] = []
        self.constants, self.props = ChemicalConstantsPackage.from_IDs(self.cas)
        n = len(self.cas)

        if self.package == "IDEAL":
            # Raoult's law: ideal gas + ideal liquid with pure-component vapour pressures.
            gas = IdealGas(HeatCapacityGases=self.props.HeatCapacityGases)
            liquid = GibbsExcessLiquid(
                VaporPressures=self.props.VaporPressures,
                HeatCapacityGases=self.props.HeatCapacityGases,
                VolumeLiquids=self.props.VolumeLiquids,
                equilibrium_basis="Psat",  # K_i = Psat_i / P
            )
        else:
            kijs = self._kijs(fs, n)
            eos = PRMIX if self.package == "PR" else SRKMIX
            kwargs = dict(Tcs=self.constants.Tcs, Pcs=self.constants.Pcs,
                          omegas=self.constants.omegas, kijs=kijs)
            gas = CEOSGas(eos, kwargs, HeatCapacityGases=self.props.HeatCapacityGases)
            liquid = CEOSLiquid(eos, kwargs, HeatCapacityGases=self.props.HeatCapacityGases)

        if n == 1:
            self.flasher = FlashPureVLS(self.constants, self.props, gas=gas,
                                        liquids=[liquid], solids=[])
        else:
            self.flasher = FlashVL(self.constants, self.props, liquid=liquid, gas=gas)

    def _kijs(self, fs: Flowsheet, n: int) -> list[list[float]]:
        """k_ij matrix from `binary_parameter_table`; missing pairs get 0 and a warning."""
        index = {cid: k for k, cid in enumerate(self.ids)}
        kij = [[0.0] * n for _ in range(n)]
        for row in binary_parameter_table(fs):
            i, j = index[row["i"]], index[row["j"]]
            kij[i][j] = kij[j][i] = row["value"]
            if row["source"] == "missing":
                self.issues.append(_issue(Severity.WARNING, "missing_binary_parameter",
                                          "thermo", None, i=row["i"], j=row["j"]))
        return kij

    def flash_raw(self, zs: list[float], **spec: float) -> Any:
        """Run a `thermo` flash for composition `zs` (pure components need no `zs`)."""
        kwargs = dict(spec) if len(zs) == 1 else dict(spec, zs=zs)
        return self.flasher.flash(**kwargs)

    def flash(self, zs: list[float], **spec: float) -> _State:
        """Overall state per mole (F = 1); the caller rescales F."""
        res = self.flash_raw(zs, **spec)
        return _State(T=res.T, P=res.P, F=1.0, zs=list(zs), H=res.H(), VF=_vapor_fraction(res))

    @staticmethod
    def split_phases(res: Any) -> tuple[_State | None, _State | None]:
        """(vapour, liquid) states per mole of feed from a flash result; None if absent."""
        vf = _vapor_fraction(res)
        gas = res.gas if vf > 0 else None
        liq = res.liquid0 if vf < 1 else None
        T, P = res.T, res.P
        vap_state = _State(T, P, vf, list(gas.zs), gas.H(), 1.0) if gas is not None else None
        liq_state = _State(T, P, 1 - vf, list(liq.zs), liq.H(), 0.0) if liq is not None else None
        return vap_state, liq_state


def database_kij(package: str, cas_i: str, cas_j: str) -> float | None:
    """k_ij for a pair from the tables shipped with `thermo`, or None if there is none."""
    table = _KIJ_TABLE.get(package)
    pair = [cas_i, cas_j]
    if table and IPDB.has_ip_specific(table, pair, "kij"):
        return float(IPDB.get_ip_specific(table, pair, "kij"))
    return None


def binary_parameter_table(fs: Flowsheet) -> list[dict[str, Any]]:
    """One row per component pair with the k_ij the engine will use and where it comes from.

    Order of precedence: a value in the document (its own `source`: user, literature, …),
    then the database, else 0 with source "missing". Empty for IDEAL (no k_ij in Raoult's law).
    """
    if fs.thermo.package not in ("PR", "SRK"):
        return []
    given = {}
    for p in fs.thermo.binary_parameters:
        if p.name.lower() == "kij":
            given[frozenset((p.i, p.j))] = (p.value, p.source)
    comps = fs.components
    rows = []
    for a in range(len(comps)):
        for b in range(a + 1, len(comps)):
            ci, cj = comps[a], comps[b]
            if frozenset((ci.id, cj.id)) in given:
                value, source = given[frozenset((ci.id, cj.id))]
            else:
                db = database_kij(fs.thermo.package, ci.cas, cj.cas)
                value, source = (db, "database") if db is not None else (0.0, "missing")
            rows.append({"i": ci.id, "j": cj.id, "name": "kij", "value": value, "source": source})
    return rows


def _vapor_fraction(res: Any) -> float:
    vf = res.VF
    if vf is None or (isinstance(vf, float) and math.isnan(vf)):
        return 1.0 if res.gas is not None and res.liquid0 is None else 0.0
    return min(1.0, max(0.0, float(vf)))


def _scaled(state: _State, F: float) -> _State:
    return _State(state.T, state.P, F, state.zs, state.H, state.VF)


def _empty(T: float, P: float) -> _State:
    return _State(T, P, 0.0, None, None, None)


class ReferenceAdapter:
    """Sequential-modular solver for acyclic flowsheets on top of `thermo`."""

    name = "reference"

    def version(self) -> str:
        return f"opd-reference 0.1 (thermo {thermo.__version__})"

    def capabilities(self) -> Capabilities:
        return Capabilities(unit_types=UNIT_TYPES, thermo_packages=THERMO_PACKAGES,
                            supports_recycle=False)

    # ------------------------------------------------------------------ validation

    def validate(self, doc: OPDDocument) -> list[Issue]:
        fs, issues = self._parse(doc)
        if fs is None:
            return issues
        return issues + self._check(fs)

    def _parse(self, doc: OPDDocument) -> tuple[Flowsheet | None, list[Issue]]:
        try:
            fs = load(doc)
        except ValidationError as exc:
            first = exc.errors()[0]
            where = ".".join(str(p) for p in first["loc"])
            return None, [_error("invalid_document", "thermo", None, where=where,
                                 detail=first["msg"])]
        return fs, check_references(fs)

    def _check(self, fs: Flowsheet) -> list[Issue]:
        issues: list[Issue] = []
        if fs.thermo.package not in THERMO_PACKAGES:
            issues.append(_error("unsupported_thermo", "thermo", None,
                                 package=fs.thermo.package, engine=self.name))
        for u in fs.units:
            if u.type not in UNIT_TYPES:
                issues.append(_error("unsupported_unit", "unit", u.id, target=u.id,
                                     type=u.type, engine=self.name))
        issues += _check_si(fs)
        if any(i.severity is Severity.ERROR for i in issues):
            return issues

        ins, outs = _connections(fs)
        for u in fs.units:
            issues += _check_unit(u, ins.get(u.id, {}), outs.get(u.id, {}))
        for s in fs.streams:
            src = fs.unit(s.from_.unit)
            if src is not None and src.type == "feed":
                issues += _check_feed_stream(s)
        if not any(i.severity is Severity.ERROR for i in issues):
            order, cyclic = _topological_order(fs)
            for uid in cyclic:
                issues.append(_error("recycle_not_supported", "unit", uid, target=uid,
                                     engine=self.name))
        return issues

    # ------------------------------------------------------------------ simulation

    def simulate(self, doc: OPDDocument) -> SimulationResult:
        issues = self.validate(doc)
        if any(i.severity is Severity.ERROR for i in issues):
            return self._result(doc, False, issues)
        fs = load(doc)
        try:
            th = _Thermo(fs)
        except ValueError as exc:  # component not in the `chemicals` database
            issues.append(_error("unknown_component_data", "component", None, detail=str(exc)))
            return self._result(doc, False, issues)
        issues += th.issues

        ins, outs = _connections(fs)
        order, _ = _topological_order(fs)
        states: dict[str, _State] = {}
        unit_results: dict[str, dict[str, dict[str, Any]]] = {}

        for uid in order:
            u = fs.unit(uid)
            assert u is not None
            inlets = {port: states[sid] for port, sid in ins.get(uid, {}).items()}
            try:
                outlets, results = _SOLVERS[u.type](u, inlets, outs.get(uid, {}), th, fs)
            except _InputError as exc:
                issues.append(exc.issue)
                return self._result(doc, False, issues)
            except Exception as exc:  # thermo did not converge or rejected the input
                issues.append(_error("calculation_failed", "unit", u.id, target=u.id,
                                     detail=f"{type(exc).__name__}: {exc}"))
                return self._result(doc, False, issues)
            for port, state in outlets.items():
                states[outs[uid][port]] = state
            if results:
                unit_results[uid] = results

        out = copy.deepcopy(doc)
        out["results"] = {
            "engine": self.name,
            "engine_version": self.version(),
            "converged": True,
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "streams": {sid: _state_out(st, th.ids) for sid, st in states.items()},
            "units": unit_results,
        }
        return SimulationResult(True, out, issues, self.name, self.version())

    def _result(self, doc: OPDDocument, converged: bool, issues: list[Issue]) -> SimulationResult:
        return SimulationResult(converged, doc, issues, self.name, self.version())


# ---------------------------------------------------------------------- helpers

def _q(value: float, unit: str) -> dict[str, Any]:
    return {"value": value, "unit": unit}


def _state_out(st: _State, ids: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "temperature": _q(st.T, "K"),
        "pressure": _q(st.P, "Pa"),
        "molar_flow": _q(st.F, "mol/s"),
    }
    if st.F > _ZERO_FLOW and st.zs is not None:
        out["vapor_fraction"] = _q(st.VF if st.VF is not None else 0.0, "1")
        out["mole_fractions"] = dict(zip(ids, st.zs))
    return out


def _connections(fs: Flowsheet) -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]]]:
    """unit id → {port: stream id}, for inlets and outlets."""
    ins: dict[str, dict[str, str]] = {}
    outs: dict[str, dict[str, str]] = {}
    for s in fs.streams:
        outs.setdefault(s.from_.unit, {})[s.from_.port] = s.id
        ins.setdefault(s.to.unit, {})[s.to.port] = s.id
    return ins, outs


def _topological_order(fs: Flowsheet) -> tuple[list[str], list[str]]:
    """Kahn's algorithm. Returns (order, units on or after a cycle)."""
    indeg = {u.id: 0 for u in fs.units}
    succ: dict[str, list[str]] = {u.id: [] for u in fs.units}
    for s in fs.streams:
        if s.from_.unit in indeg and s.to.unit in indeg:
            succ[s.from_.unit].append(s.to.unit)
            indeg[s.to.unit] += 1
    ready = [u.id for u in fs.units if indeg[u.id] == 0]
    order: list[str] = []
    while ready:
        uid = ready.pop(0)
        order.append(uid)
        for nxt in succ[uid]:
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                ready.append(nxt)
    cyclic = [u.id for u in fs.units if u.id not in order]
    return order, cyclic


def _check_si(fs: Flowsheet) -> list[Issue]:
    issues: list[Issue] = []

    def check(kind: str, id_: str, name: str, unit: str) -> None:
        allowed = _SI.get(name, _FRACTION_UNITS if name.startswith("split_") else None)
        if allowed is not None and unit not in allowed:
            issues.append(_error("non_si_unit", kind, id_, target=id_, spec=name, unit=unit,
                                 expected=sorted(allowed)[0] if allowed else ""))

    for u in fs.units:
        for name, q in u.specs.items():
            check("unit", u.id, name, q.unit)
    for s in fs.streams:
        if s.state is None:
            continue
        for name in ("temperature", "pressure", "molar_flow", "vapor_fraction"):
            q = getattr(s.state, name)
            if q is not None:
                check("stream", s.id, name, q.unit)
    return issues


def _missing(kind: str, id_: str, spec: str) -> Issue:
    return _error("missing_spec", kind, id_, target=id_, spec=spec)


def _one_of(u: Unit, names: tuple[str, ...], required: bool) -> list[Issue]:
    given = [n for n in names if n in u.specs]
    if len(given) > 1:
        return [_error("conflicting_specs", "unit", u.id, target=u.id, specs=given)]
    if required and not given:
        return [_missing("unit", u.id, " / ".join(names))]
    return []


def _check_unit(u: Unit, ins: dict[str, str], outs: dict[str, str]) -> list[Issue]:
    issues: list[Issue] = []

    def need(port: str, ports: dict[str, str]) -> None:
        if port not in ports:
            issues.append(_error("unconnected_port", "unit", u.id, target=u.id, port=port))

    def no_extra(allowed: set[str], ports: dict[str, str]) -> None:
        for port in sorted(set(ports) - allowed):
            issues.append(_error("unknown_port", "unit", u.id, target=u.id, port=port,
                                 type=u.type))

    t = u.type
    if t == "feed":
        need("out", outs)
        no_extra({"out"}, outs)
        no_extra(set(), ins)
    elif t == "product":
        need("in", ins)
        no_extra({"in"}, ins)
        no_extra(set(), outs)
    elif t == "mixer":
        if not any(p.startswith("in") for p in ins):
            need("in", ins)
        no_extra({p for p in ins if p.startswith("in")}, ins)
        need("out", outs)
        no_extra({"out"}, outs)
    elif t == "splitter":
        need("in", ins)
        no_extra({"in"}, ins)
        if len(outs) < 2:
            issues.append(_error("too_few_outlets", "unit", u.id, target=u.id, minimum=2))
        open_ports = [p for p in outs if f"split_{p}" not in u.specs]
        for name in u.specs:
            if not name.startswith("split_") or name[6:] not in outs:
                issues.append(_error("unknown_spec", "unit", u.id, target=u.id, spec=name))
        if outs and len(open_ports) != 1:
            issues.append(_error("split_needs_one_open_outlet", "unit", u.id, target=u.id))
        total = sum(q.value for n, q in u.specs.items() if n.startswith("split_"))
        if any(q.value < 0 for n, q in u.specs.items() if n.startswith("split_")) or total > 1 + 1e-9:
            issues.append(_error("invalid_split", "unit", u.id, target=u.id, sum=round(total, 6)))
    elif t in ("heater", "valve", "flash"):
        need("in", ins)
        outlets = {"vapor", "liquid"} if t == "flash" else {"out"}
        for p in sorted(outlets):
            need(p, outs)
        no_extra({"in"}, ins)
        no_extra(outlets, outs)
        issues += _one_of(u, ("pressure", "pressure_drop"), required=t != "heater")
        if t in ("heater", "flash"):
            issues += _one_of(u, ("temperature", "duty", "vapor_fraction"), required=True)
        if "vapor_fraction" in u.specs and not 0 <= u.specs["vapor_fraction"].value <= 1:
            issues.append(_error("out_of_range", "unit", u.id, target=u.id,
                                 spec="vapor_fraction", min=0, max=1))
    return issues


def _check_feed_stream(s: Stream) -> list[Issue]:
    st = s.state
    issues: list[Issue] = []
    for name in ("pressure", "molar_flow", "mole_fractions"):
        if st is None or getattr(st, name) is None:
            issues.append(_missing("stream", s.id, name))
    has_T = st is not None and st.temperature is not None
    has_VF = st is not None and st.vapor_fraction is not None
    if not has_T and not has_VF:
        issues.append(_missing("stream", s.id, "temperature / vapor_fraction"))
    if has_T and has_VF:
        issues.append(_error("conflicting_specs", "stream", s.id, target=s.id,
                             specs=["temperature", "vapor_fraction"]))
    if st is not None and st.molar_flow is not None and st.molar_flow.value < 0:
        issues.append(_error("out_of_range", "stream", s.id, target=s.id, spec="molar_flow",
                             min=0, max=None))
    return issues


def _outlet_pressure(u: Unit, P_in: float) -> float:
    if "pressure" in u.specs:
        return u.specs["pressure"].value
    if "pressure_drop" in u.specs:
        return P_in - u.specs["pressure_drop"].value
    return P_in


def _require_positive_pressure(u: Unit, P: float) -> None:
    if P <= 0:
        raise _InputError(_error("out_of_range", "unit", u.id, target=u.id, spec="pressure",
                                 min=0, max=None))


# ---------------------------------------------------------------------- unit solvers
# Each solver: (unit, inlet states by port, outlet stream ids by port, thermo, flowsheet)
#   → ({outlet port: state}, {result name: quantity})

Solver = Callable[[Unit, dict[str, _State], dict[str, str], _Thermo, Flowsheet],
                  tuple[dict[str, _State], dict[str, dict[str, Any]]]]


def _solve_feed(u, inlets, outs, th, fs):
    s = fs.stream(outs["out"])
    assert s is not None and s.state is not None
    st = s.state
    zs = [float((st.mole_fractions or {}).get(cid, 0.0)) for cid in th.ids]
    total = sum(zs)
    zs = [z / total for z in zs]  # check_references already enforced |Σz − 1| ≤ 1e-6
    P = st.pressure.value  # type: ignore[union-attr]
    F = st.molar_flow.value  # type: ignore[union-attr]
    if st.temperature is not None:
        state = th.flash(zs, T=st.temperature.value, P=P)
    else:
        state = th.flash(zs, P=P, VF=st.vapor_fraction.value)  # type: ignore[union-attr]
    return {"out": _scaled(state, F)}, {}


def _solve_product(u, inlets, outs, th, fs):
    return {}, {}


def _solve_mixer(u, inlets, outs, th, fs):
    streams = [s for s in inlets.values()]
    P = u.specs["pressure"].value if "pressure" in u.specs else min(s.P for s in streams)
    _require_positive_pressure(u, P)
    flowing = [s for s in streams if s.F > _ZERO_FLOW]
    if not flowing:
        return {"out": _empty(min(s.T for s in streams), P)}, {}
    F = sum(s.F for s in flowing)
    n = len(th.ids)
    zs = [sum(s.F * s.zs[k] for s in flowing) / F for k in range(n)]  # type: ignore[index]
    H = sum(s.F * s.H for s in flowing) / F  # type: ignore[operator]
    state = th.flash(zs, P=P, H=H)
    return {"out": _scaled(state, F)}, {
        "temperature": _q(state.T, "K"),
        "pressure": _q(P, "Pa"),
    }


def _solve_splitter(u, inlets, outs, th, fs):
    feed = inlets["in"]
    fractions = {p: u.specs[f"split_{p}"].value for p in outs if f"split_{p}" in u.specs}
    rest = [p for p in outs if p not in fractions][0]
    fractions[rest] = max(0.0, 1.0 - sum(fractions.values()))
    return {p: _scaled(feed, feed.F * f) for p, f in fractions.items()}, {
        f"split_{p}": _q(f, "1") for p, f in fractions.items()
    }


def _thermal_spec(u: Unit, feed: _State, P: float) -> dict[str, float]:
    """The flash specification (besides zs) for heater and flash units."""
    if "temperature" in u.specs:
        return {"T": u.specs["temperature"].value, "P": P}
    if "vapor_fraction" in u.specs:
        return {"P": P, "VF": u.specs["vapor_fraction"].value}
    duty = u.specs["duty"].value
    return {"P": P, "H": feed.H + duty / feed.F}  # type: ignore[operator]


def _solve_heater(u, inlets, outs, th, fs):
    feed = inlets["in"]
    P = _outlet_pressure(u, feed.P)
    _require_positive_pressure(u, P)
    if feed.F <= _ZERO_FLOW:
        T = u.specs["temperature"].value if "temperature" in u.specs else feed.T
        return {"out": _empty(T, P)}, {"duty": _q(0.0, "W")}
    out = _scaled(th.flash(feed.zs, **_thermal_spec(u, feed, P)), feed.F)  # type: ignore[arg-type]
    duty = feed.F * (out.H - feed.H)  # type: ignore[operator]
    return {"out": out}, {
        "duty": _q(duty, "W"),
        "temperature": _q(out.T, "K"),
        "pressure": _q(P, "Pa"),
        "vapor_fraction": _q(out.VF, "1"),
    }


def _solve_valve(u, inlets, outs, th, fs):
    feed = inlets["in"]
    P = _outlet_pressure(u, feed.P)
    _require_positive_pressure(u, P)
    if feed.F <= _ZERO_FLOW:
        return {"out": _empty(feed.T, P)}, {}
    out = _scaled(th.flash(feed.zs, P=P, H=feed.H), feed.F)  # type: ignore[arg-type]
    return {"out": out}, {
        "temperature": _q(out.T, "K"),
        "pressure": _q(P, "Pa"),
        "pressure_drop": _q(feed.P - P, "Pa"),
        "vapor_fraction": _q(out.VF, "1"),
    }


def _solve_flash(u, inlets, outs, th, fs):
    feed = inlets["in"]
    P = _outlet_pressure(u, feed.P)
    _require_positive_pressure(u, P)
    if feed.F <= _ZERO_FLOW:
        T = u.specs["temperature"].value if "temperature" in u.specs else feed.T
        return {"vapor": _empty(T, P), "liquid": _empty(T, P)}, {"duty": _q(0.0, "W")}
    res = th.flash_raw(feed.zs, **_thermal_spec(u, feed, P))  # type: ignore[arg-type]
    overall = _State(res.T, res.P, 1.0, feed.zs, res.H(), _vapor_fraction(res))
    vap, liq = th.split_phases(res)
    outlets = {
        "vapor": _scaled(vap, feed.F * vap.F) if vap else _empty(overall.T, P),
        "liquid": _scaled(liq, feed.F * liq.F) if liq else _empty(overall.T, P),
    }
    duty = feed.F * (overall.H - feed.H)  # type: ignore[operator]
    return outlets, {
        "duty": _q(duty, "W"),
        "temperature": _q(overall.T, "K"),
        "pressure": _q(P, "Pa"),
        "vapor_fraction": _q(overall.VF, "1"),
    }


_SOLVERS: dict[str, Solver] = {
    "feed": _solve_feed,
    "product": _solve_product,
    "mixer": _solve_mixer,
    "splitter": _solve_splitter,
    "heater": _solve_heater,
    "valve": _solve_valve,
    "flash": _solve_flash,
}

_adapter.register(ReferenceAdapter())
