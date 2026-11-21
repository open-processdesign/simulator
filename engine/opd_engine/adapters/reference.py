"""Reference adapter: a small sequential-modular engine built on MIT-licensed `thermo`.

Purpose (DECISIONS.md D005, D011): tests and local development without DWSIM, the
December demo engine (it runs in the browser through Pyodide, see T03), and the seed of
own modules. All property and phase-equilibrium numbers come from `thermo`
(Caleb Bell et al., https://github.com/CalebBell/thermo, MIT); this module only does
bookkeeping: port conventions, material and energy balances, and the solve order.

Scope: units feed, product, mixer, splitter, heater, valve, flash, pump, compressor,
heat exchanger, conversion reactor, shortcut column (T09); property packages
IDEAL (Raoult), PR, SRK, NRTL (T12) and UNIQUAC (T21); recycle loops through tear streams converged with bounded
Wegstein or successive substitution (see `recycle.py`, T08).

Port and spec conventions (all values SI, see DECISIONS.md D007 and D013):

=========  =====================  ==========================================================
unit       ports                  specs
=========  =====================  ==========================================================
feed       out                    on the outgoing stream ``state``: pressure, molar_flow,
                                  mole_fractions, and temperature *or* vapor_fraction
product    in                     –
mixer      in*, out               optional pressure (default: lowest pressure of the
                                  inlets that carry flow); adiabatic
splitter   in, any outlets        ``split_<port>`` (fraction, unit "1") for every outlet
                                  but one; the remaining outlet takes the rest
heater     in, out                exactly one of temperature, duty, vapor_fraction;
                                  optional pressure *or* pressure_drop (default: none)
valve      in, out                pressure *or* pressure_drop; isenthalpic
flash      in, vapor, liquid      pressure *or* pressure_drop, and exactly one of
                                  temperature, duty, vapor_fraction
pump       in, out                pressure *or* pressure_increase; optional efficiency
                                  (default 0.75)
compressor in, out                pressure *or* pressure_increase; optional isentropic
                                  efficiency (default 0.75)
heat_      hot_in, hot_out,       exactly one of hot_outlet_temperature,
exchanger  cold_in, cold_out      cold_outlet_temperature, duty, ua (W/K) or
                                  u_overall (W/m²K) + area (m²) for rating; optional
                                  hot_pressure_drop, cold_pressure_drop; counter-current
conversion in, out                options.reactions = [{stoichiometry: {component: ν},
_reactor                          key: component, conversion: 0…1}, …] applied in order;
                                  exactly one of temperature, duty; optional pressure
                                  *or* pressure_drop
shortcut_  in, distillate,        options.light_key, options.heavy_key; specs
column     bottoms                lk_recovery (to distillate), hk_recovery (to bottoms),
                                  reflux_ratio_factor (R/Rmin); optional pressure;
                                  total condenser
distill-   in, distillate,        number_of_stages (incl. condenser and reboiler),
ation_     bottoms                feed_stage (counted from the top), reflux_ratio,
column                            distillate_rate; optional pressure; total condenser,
                                  partial reboiler; rigorous MESH (column.py, T15)
cstr, pfr  in, out                volume (m³); exactly one of temperature, duty;
                                  optional pressure *or* pressure_drop; options.phase
                                  ("gas" | "liquid"), options.reactions = [{stoichiometry,
                                  k0, Ea (J/mol), orders: {component: n}}] (kinetics.py)
equilib-   in, out                exactly one of temperature, duty; optional pressure *or*
rium_                             pressure_drop; options.reactions = [{stoichiometry}];
reactor                           gas-phase chemical equilibrium (equilibrium.py, T18)
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
    NRTL,
    UNIQUAC,
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
from .column import ColumnError, solve_column
from . import hx_geometry
from .equilibrium import EquilibriumError, ln_k, phase_ln_k, solve_adiabatic, solve_equilibrium
from .kinetics import KineticsError, parse_rate_laws, solve_cstr, solve_pfr
from .recycle import Accelerator, Block, Edge, solve_plan

UNIT_TYPES = frozenset({"feed", "product", "mixer", "splitter", "heater", "valve", "flash",
                        "pump", "compressor", "heat_exchanger", "conversion_reactor",
                        "shortcut_column", "distillation_column", "cstr", "pfr",
                        "equilibrium_reactor"})
THERMO_PACKAGES = frozenset({"IDEAL", "PR", "SRK", "NRTL", "UNIQUAC"})

# SI unit strings accepted per spec name (v0.1 stores SI only).
_SI = {
    "temperature": {"K"},
    "pressure": {"Pa"},
    "pressure_drop": {"Pa"},
    "duty": {"W"},
    "molar_flow": {"mol/s"},
    "vapor_fraction": {"1", "-", ""},
    "pressure_increase": {"Pa"},
    "efficiency": {"1", "-", ""},
    "hot_outlet_temperature": {"K"},
    "cold_outlet_temperature": {"K"},
    "hot_pressure_drop": {"Pa"},
    "cold_pressure_drop": {"Pa"},
    "lk_recovery": {"1", "-", ""},
    "hk_recovery": {"1", "-", ""},
    "reflux_ratio_factor": {"1", "-", ""},
    "number_of_stages": {"1", "-", ""},
    "feed_stage": {"1", "-", ""},
    "reflux_ratio": {"1", "-", ""},
    "distillate_rate": {"mol/s"},
    "volume": {"m3", "m³"},
    "ua": {"W/K"},
    "u_overall": {"W/m2/K", "W/(m2·K)", "W/m²K"},
    "area": {"m2", "m²"},
}
_FRACTION_UNITS = {"1", "-", ""}

# Interaction-parameter tables shipped with `thermo` (ChemSep, public domain data).
_KIJ_TABLE = {"PR": "ChemSep PR"}

# Key a unit solver may add to its results to return a profile (moved to results.profiles).
_PROFILE = "__profile__"
# Key a unit solver may add with a list of warning issues (the last solve of a unit wins).
_WARNINGS = "__warnings__"

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
        self._fs = fs
        self._pure: dict[int, _Thermo] = {}
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
        elif self.package == "NRTL":
            # Modified Raoult: ideal gas + NRTL liquid, τ_ij = b_ij / T (Renon & Prausnitz,
            # AIChE J. 14 (1968) 135). Parameters: document → ChemSep NRTL table → ideal pair.
            tau_bs, alphas = self._nrtl(fs, n)
            gas = IdealGas(HeatCapacityGases=self.props.HeatCapacityGases)
            model = NRTL(T=298.15, xs=[1.0 / n] * n, tau_bs=tau_bs, alpha_cs=alphas)
            liquid = GibbsExcessLiquid(
                VaporPressures=self.props.VaporPressures,
                HeatCapacityGases=self.props.HeatCapacityGases,
                VolumeLiquids=self.props.VolumeLiquids,
                GibbsExcessModel=model,
                equilibrium_basis="Psat",  # K_i = γ_i Psat_i / P
            )
        elif self.package == "UNIQUAC":
            # Modified Raoult with UNIQUAC (Abrams & Prausnitz, AIChE J. 21 (1975) 116),
            # τ_ij = exp(b_ij / T) in thermo's sign convention (checked against methanol–water
            # VLE); r and q from UNIFAC group contributions.
            rs, qs = self.constants.UNIFAC_Rs, self.constants.UNIFAC_Qs
            if any(v is None for v in list(rs) + list(qs)):
                missing = [cid for cid, r, q in zip(self.ids, rs, qs) if r is None or q is None]
                raise ValueError(f"no UNIQUAC r/q (UNIFAC groups) for {', '.join(missing)}")
            tau_bs = self._activity_b(fs, n)
            gas = IdealGas(HeatCapacityGases=self.props.HeatCapacityGases)
            model = UNIQUAC(T=298.15, xs=[1.0 / n] * n, rs=list(rs), qs=list(qs), tau_bs=tau_bs)
            liquid = GibbsExcessLiquid(
                VaporPressures=self.props.VaporPressures,
                HeatCapacityGases=self.props.HeatCapacityGases,
                VolumeLiquids=self.props.VolumeLiquids,
                GibbsExcessModel=model,
                equilibrium_basis="Psat",
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

    def _nrtl(self, fs: Flowsheet, n: int) -> tuple[list[list[float]], list[list[float]]]:
        """NRTL b_ij (K) and α_ij matrices; a pair without data is treated as ideal (warning)."""
        index = {cid: k for k, cid in enumerate(self.ids)}
        b = [[0.0] * n for _ in range(n)]
        alpha = [[0.0] * n for _ in range(n)]
        missing: set[frozenset[str]] = set()
        for row in binary_parameter_table(fs):
            i, j = index[row["i"]], index[row["j"]]
            if row["name"] == "nrtl_b":
                b[i][j] = row["value"]
            else:
                alpha[i][j] = alpha[j][i] = row["value"]
            if row["source"] == "missing":
                missing.add(frozenset((row["i"], row["j"])))
        for pair in sorted(missing, key=lambda p: sorted(index[x] for x in p)):
            i, j = sorted(pair, key=index.__getitem__)
            self.issues.append(_issue(Severity.WARNING, "missing_binary_parameter", "thermo", None,
                                      i=i, j=j))
        return b, alpha

    def _activity_b(self, fs: Flowsheet, n: int) -> list[list[float]]:
        """b_ij matrix (K) for UNIQUAC; a pair without data gets b = 0 and a warning."""
        index = {cid: k for k, cid in enumerate(self.ids)}
        b = [[0.0] * n for _ in range(n)]
        missing: list[tuple[str, str]] = []
        for row in binary_parameter_table(fs):
            i, j = index[row["i"]], index[row["j"]]
            b[i][j] = row["value"]
            if row["source"] == "missing" and index[row["i"]] < index[row["j"]]:
                missing.append((row["i"], row["j"]))
        for i, j in missing:
            self.issues.append(_issue(Severity.WARNING, "missing_binary_parameter", "thermo", None, i=i, j=j))
        return b

    def Hf(self, zs: list[float]) -> float:
        """Σ z_i ΔHf_i (ideal gas, 298.15 K), J/mol: shifts thermo's H to a reaction basis."""
        return sum(z * hf for z, hf in zip(zs, self.constants.Hfgs))

    def liquid_volume(self, zs: list[float], T: float) -> float:
        """Liquid molar volume, m³/mol, from pure-component correlations (Amagat mixing)."""
        return sum(z * vl.T_dependent_property(T) for z, vl in zip(zs, self.props.VolumeLiquids) if z > 0)

    def entropy(self, zs: list[float], T: float, P: float) -> float:
        return self.flash_raw(zs, T=T, P=P).S()

    def flash_raw(self, zs: list[float], **spec: float) -> Any:
        """Run a `thermo` flash for composition `zs` (pure components need no `zs`).

        A stream with a single non-zero component is flashed with that component's own
        pure flasher: `thermo` 0.6.1's mixture flasher fails (P–H) or returns a wrong
        phase (P–VF with PR) for such two-phase states. Phase compositions are mapped back."""
        if len(zs) > 1:
            nonzero = [k for k, z in enumerate(zs) if z > 0]
            if len(nonzero) == 1:
                return _PureResult(self._pure_thermo(nonzero[0]).flash_raw([1.0], **spec),
                                   nonzero[0], len(zs))
            if self.package == "UNIQUAC" and len(nonzero) < len(zs):
                # thermo's UNIQUAC divides by x_i: absent components get a trace (1e-12).
                zs = [max(z, 1e-12) for z in zs]
                total = sum(zs)
                zs = [z / total for z in zs]
        kwargs = dict(spec) if len(zs) == 1 else dict(spec, zs=zs)
        try:
            return self.flasher.flash(**kwargs)
        except Exception:
            if set(spec) == {"P", "VF"} and 0 < spec["VF"] < 1 and len(zs) > 1:
                return self._flash_PVF_bisect(zs, spec["P"], spec["VF"])
            raise

    def _pure_thermo(self, k: int) -> "_Thermo":
        if k not in self._pure:
            fs = self._fs
            self._pure[k] = _Thermo(fs.model_copy(update={
                "components": [fs.components[k]],
                "thermo": fs.thermo.model_copy(update={"binary_parameters": []}),
            }))
        return self._pure[k]

    def _flash_PVF_bisect(self, zs: list[float], P: float, VF: float) -> Any:
        """P–VF flash by bisection on T between the bubble and dew points (PT flashes).

        Fallback for `thermo` 0.6.1, whose two-phase P–VF solver can fail with activity
        models; vapour fraction rises monotonically with T at fixed P and composition.
        """
        lo = self.flasher.flash(P=P, VF=0.0, zs=zs).T
        hi = self.flasher.flash(P=P, VF=1.0, zs=zs).T
        res = None
        for _ in range(100):
            T = 0.5 * (lo + hi)
            res = self.flasher.flash(T=T, P=P, zs=zs)
            if _vapor_fraction(res) < VF:
                lo = T
            else:
                hi = T
            if hi - lo < 1e-9 * T:
                break
        return res

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


_NRTL_TABLE = "ChemSep NRTL"
_NRTL_DEFAULT_ALPHA = 0.3


def _nrtl_rows(fs: Flowsheet) -> list[dict[str, Any]]:
    """Per pair a < b: rows nrtl_b (a→b), nrtl_b (b→a) and nrtl_alpha, with sources.

    A pair takes document values first; otherwise the ChemSep NRTL table (b_ij in K,
    τ_ij = b_ij/T); otherwise b = 0 (ideal pair) and α = 0.3, marked "missing".
    """
    given: dict[tuple[str, str, str], tuple[float, str]] = {}
    for p in fs.thermo.binary_parameters:
        name = p.name.lower()
        if name == "nrtl_b":
            given[("nrtl_b", p.i, p.j)] = (p.value, p.source)
        elif name == "nrtl_alpha":
            given[("nrtl_alpha", p.i, p.j)] = given[("nrtl_alpha", p.j, p.i)] = (p.value, p.source)
    rows = []
    comps = fs.components
    for a in range(len(comps)):
        for c in range(a + 1, len(comps)):
            ci, cj = comps[a], comps[c]
            pair = [ci.cas, cj.cas]
            in_db = IPDB.has_ip_specific(_NRTL_TABLE, pair, "bij")
            db_b = IPDB.get_ip_asymmetric_matrix(_NRTL_TABLE, pair, "bij") if in_db else None
            db_alpha = IPDB.get_ip_specific(_NRTL_TABLE, pair, "alphaij") if in_db else None
            for (x, y, k, m) in ((ci, cj, 0, 1), (cj, ci, 1, 0)):
                if ("nrtl_b", x.id, y.id) in given:
                    value, source = given[("nrtl_b", x.id, y.id)]
                elif db_b is not None:
                    value, source = float(db_b[k][m]), "database"
                else:
                    value, source = 0.0, "missing"
                rows.append({"i": x.id, "j": y.id, "name": "nrtl_b", "value": value, "source": source})
            if ("nrtl_alpha", ci.id, cj.id) in given:
                value, source = given[("nrtl_alpha", ci.id, cj.id)]
            elif db_alpha is not None:
                value, source = float(db_alpha), "database"
            else:
                value, source = _NRTL_DEFAULT_ALPHA, "missing"
            rows.append({"i": ci.id, "j": cj.id, "name": "nrtl_alpha", "value": value, "source": source})
    return rows


_UNIQUAC_TABLE = "ChemSep UNIQUAC"


def _uniquac_rows(fs: Flowsheet) -> list[dict[str, Any]]:
    """Per pair a < b: uniquac_b (a→b) and (b→a) in K; document → ChemSep → 0 ("missing")."""
    given = {(p.i, p.j): (p.value, p.source) for p in fs.thermo.binary_parameters
             if p.name.lower() == "uniquac_b"}
    rows = []
    comps = fs.components
    for a in range(len(comps)):
        for c in range(a + 1, len(comps)):
            ci, cj = comps[a], comps[c]
            pair = [ci.cas, cj.cas]
            db = (IPDB.get_ip_asymmetric_matrix(_UNIQUAC_TABLE, pair, "bij")
                  if IPDB.has_ip_specific(_UNIQUAC_TABLE, pair, "bij") else None)
            for x, y, k, m in ((ci, cj, 0, 1), (cj, ci, 1, 0)):
                if (x.id, y.id) in given:
                    value, source = given[(x.id, y.id)]
                elif db is not None:
                    value, source = float(db[k][m]), "database"
                else:
                    value, source = 0.0, "missing"
                rows.append({"i": x.id, "j": y.id, "name": "uniquac_b", "value": value, "source": source})
    return rows


def binary_parameter_table(fs: Flowsheet) -> list[dict[str, Any]]:
    """Binary parameters the engine will use, with where each comes from.

    PR/SRK: one k_ij row per pair; NRTL: b_ij, b_ji and α_ij rows per pair (see `_nrtl_rows`).
    Order of precedence: a value in the document (its own `source`: user, literature, …),
    then the database, else a neutral value with source "missing". Empty for IDEAL.
    """
    if fs.thermo.package == "NRTL":
        return _nrtl_rows(fs)
    if fs.thermo.package == "UNIQUAC":
        return _uniquac_rows(fs)
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


class _PurePhase:
    """A phase of a pure-component flash, with mole fractions over all components."""

    def __init__(self, phase: Any, k: int, n: int) -> None:
        self._phase = phase
        self.zs = [1.0 if j == k else 0.0 for j in range(n)]

    def __getattr__(self, name: str) -> Any:
        return getattr(self._phase, name)


class _PureResult:
    """Pure-component flash result seen as a result for the full component list."""

    def __init__(self, res: Any, k: int, n: int) -> None:
        self._res = res
        self.zs = [1.0 if j == k else 0.0 for j in range(n)]
        gas = getattr(res, "gas", None)
        liquids = list(getattr(res, "liquids", None) or [])
        self.gas = _PurePhase(gas, k, n) if gas is not None else None
        self.liquids = [_PurePhase(p, k, n) for p in liquids]
        self.liquid0 = self.liquids[0] if self.liquids else None

    def __getattr__(self, name: str) -> Any:
        return getattr(self._res, name)


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
    """Sequential-modular solver on top of `thermo`, with recycle loops (tear streams)."""

    name = "reference"

    def __init__(self, recycle_method: str = "wegstein", max_iterations: int = 200,
                 tolerance: float = 1e-8) -> None:
        if recycle_method not in ("wegstein", "direct"):
            raise ValueError("recycle_method must be 'wegstein' or 'direct'")
        self.recycle_method = recycle_method
        self.max_iterations = max_iterations
        self.tolerance = tolerance  # relative, on tear-stream component flows and pressure

    def version(self) -> str:
        return f"opd-reference 0.1 (thermo {thermo.__version__})"

    def capabilities(self) -> Capabilities:
        return Capabilities(unit_types=UNIT_TYPES, thermo_packages=THERMO_PACKAGES,
                            supports_recycle=True)

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
        comp_ids = [c.id for c in fs.components]
        for u in fs.units:
            issues += _check_unit(u, ins.get(u.id, {}), outs.get(u.id, {}), comp_ids)
        for s in fs.streams:
            src = fs.unit(s.from_.unit)
            if src is not None and src.type == "feed":
                issues += _check_feed_stream(s)
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
        edges = [Edge(st.id, st.from_.unit, st.to.unit) for st in fs.streams]
        blocks = solve_plan([u.id for u in fs.units], edges)
        states: dict[str, _State] = {}
        unit_results: dict[str, dict[str, dict[str, Any]]] = {}
        profiles: dict[str, dict[str, Any]] = {}
        unit_warnings: dict[str, list[Issue]] = {}

        def solve_unit(uid: str) -> Issue | None:
            u = fs.unit(uid)
            assert u is not None
            inlets = {port: states[sid] for port, sid in ins.get(uid, {}).items()}
            try:
                outlets, results = _SOLVERS[u.type](u, inlets, outs.get(uid, {}), th, fs)
            except _InputError as exc:
                return exc.issue
            except Exception as exc:  # thermo did not converge or rejected the input
                return _error("calculation_failed", "unit", u.id, target=u.id,
                              detail=f"{type(exc).__name__}: {exc}")
            for port, state in outlets.items():
                states[outs[uid][port]] = state
            unit_results.pop(uid, None)
            profile = results.pop(_PROFILE, None)
            if profile is not None:
                profiles[uid] = profile
            unit_warnings[uid] = results.pop(_WARNINGS, [])
            if results:
                unit_results[uid] = results
            return None

        for block in blocks:
            if not block.is_loop:
                problem = solve_unit(block.units[0])
            else:
                problem = self._converge(block, fs, th, states, solve_unit, issues)
            if problem is not None:
                issues.append(problem)
                return self._result(doc, False, issues)

        for found in unit_warnings.values():
            issues += found
        out = copy.deepcopy(doc)
        out["results"] = {
            "engine": self.name,
            "engine_version": self.version(),
            "converged": True,
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "streams": {sid: _state_out(st, th.ids) for sid, st in states.items()},
            "units": unit_results,
            **({"profiles": profiles} if profiles else {}),
        }
        return SimulationResult(True, out, issues, self.name, self.version())

    def _converge(self, block: Block, fs: Flowsheet, th: "_Thermo", states: dict[str, _State],
                  solve_unit: Callable[[str], Issue | None], issues: list[Issue]) -> Issue | None:
        """Iterate a recycle loop until its tear streams stop changing (see recycle.py)."""
        n = len(th.ids)
        for sid in block.tears:
            states[sid] = _initial_guess(fs.stream(sid), th)
        acc = Accelerator(method=self.recycle_method)
        residual = math.inf
        for _ in range(self.max_iterations):
            x = {sid: states[sid] for sid in block.tears}
            for uid in block.units:
                problem = solve_unit(uid)
                if problem is not None:
                    return problem
            g = {sid: states[sid] for sid in block.tears}
            residual = max(_residual(x[sid], g[sid], n) for sid in block.tears)
            if residual <= self.tolerance:
                # The last pass started from x ≈ g, so every stream in the loop is consistent.
                issues.append(_issue(Severity.INFO, "recycle_converged", "stream", block.tears[0],
                                     streams=block.tears, iterations=acc.iterations + 1,
                                     method=self.recycle_method))
                return None
            xv = [v for sid in block.tears for v in _to_vector(x[sid], n)]
            gv = [v for sid in block.tears for v in _to_vector(g[sid], n)]
            new = acc.next(xv, gv)
            if new == gv:
                continue  # plain substitution: computed states are reused as they are
            width = n + 2
            for k, sid in enumerate(block.tears):
                states[sid] = _from_vector(new[k * width:(k + 1) * width], g[sid], th)
        return _error("recycle_not_converged", "stream", block.tears[0], target=block.tears[0],
                      streams=block.tears, iterations=self.max_iterations,
                      residual=float(f"{residual:.3g}"))

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


def _initial_guess(stream: Stream | None, th: "_Thermo") -> _State:
    """Tear-stream start value: the stream's own state if fully given, else empty."""
    st = stream.state if stream is not None else None
    if st and st.temperature and st.pressure and st.molar_flow and st.mole_fractions:
        zs = [float(st.mole_fractions.get(cid, 0.0)) for cid in th.ids]
        total = sum(zs)
        if total > 0 and st.molar_flow.value > 0:
            zs = [z / total for z in zs]
            return _scaled(th.flash(zs, T=st.temperature.value, P=st.pressure.value),
                           st.molar_flow.value)
    P = st.pressure.value if st and st.pressure else 101325.0
    T = st.temperature.value if st and st.temperature else 298.15
    return _empty(T, P)


def _to_vector(st: _State, n: int) -> list[float]:
    """Tear variables: component flows (mol/s), enthalpy flow (W), pressure (Pa)."""
    if st.F <= _ZERO_FLOW or st.zs is None:
        return [0.0] * n + [0.0, st.P]
    return [st.F * z for z in st.zs] + [st.F * st.H, st.P]  # type: ignore[operator]


def _from_vector(v: list[float], like: _State, th: "_Thermo") -> _State:
    n = len(th.ids)
    flows = [max(0.0, f) for f in v[:n]]
    F, Hdot, P = sum(flows), v[n], v[n + 1]
    if F <= _ZERO_FLOW:
        return _empty(like.T, P)
    zs = [f / F for f in flows]
    return _scaled(th.flash(zs, P=P, H=Hdot / F), F)


def _residual(x: _State, g: _State, n: int) -> float:
    """Largest relative change of a tear stream: component flows, then pressure."""
    xv, gv = _to_vector(x, n), _to_vector(g, n)
    scale = max(sum(gv[:n]), sum(xv[:n]), _ZERO_FLOW)
    flows = max((abs(a - b) / scale for a, b in zip(xv[:n], gv[:n])), default=0.0)
    pressure = abs(xv[n + 1] - gv[n + 1]) / max(abs(gv[n + 1]), 1.0)
    temperature = 0.0
    if x.F > _ZERO_FLOW and g.F > _ZERO_FLOW:
        temperature = abs(x.T - g.T) / max(g.T, 1.0)
    return max(flows, pressure, temperature)


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


def _check_unit(u: Unit, ins: dict[str, str], outs: dict[str, str],
                comp_ids: list[str] | None = None) -> list[Issue]:
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
    elif t in ("pump", "compressor"):
        need("in", ins)
        need("out", outs)
        no_extra({"in"}, ins)
        no_extra({"out"}, outs)
        issues += _one_of(u, ("pressure", "pressure_increase"), required=True)
        if "pressure_increase" in u.specs and u.specs["pressure_increase"].value < 0:
            issues.append(_error("out_of_range", "unit", u.id, target=u.id,
                                 spec="pressure_increase", min=0, max=None))
    elif t == "heat_exchanger":
        for p in ("hot_in", "cold_in"):
            need(p, ins)
        for p in ("hot_out", "cold_out"):
            need(p, outs)
        no_extra({"hot_in", "cold_in"}, ins)
        no_extra({"hot_out", "cold_out"}, outs)
        given = [n for n in ("hot_outlet_temperature", "cold_outlet_temperature", "duty", "ua")
                 if n in u.specs]
        if "u_overall" in u.specs or "area" in u.specs:
            if not ("u_overall" in u.specs and "area" in u.specs):
                issues.append(_missing("unit", u.id, "area" if "u_overall" in u.specs else "u_overall"))
            given.append("u_overall · area")
        geometry = u.options.get("geometry")
        if geometry is not None:
            for name in hx_geometry.check(geometry):
                issues.append(_error("invalid_option", "unit", u.id, target=u.id, option=f"geometry.{name}"))
            rating = [n for n in given if n in ("ua", "u_overall · area")]
            if rating:
                issues.append(_error("conflicting_specs", "unit", u.id, target=u.id, specs=rating + ["geometry"]))
        if len(given) > 1:
            issues.append(_error("conflicting_specs", "unit", u.id, target=u.id, specs=given))
        elif not given and geometry is None:
            issues.append(_missing("unit", u.id, "hot_outlet_temperature / cold_outlet_temperature / duty / ua"))
        zones = u.options.get("zones", _HX_ZONES)
        if not isinstance(zones, int) or isinstance(zones, bool) or not 1 <= zones <= 100:
            issues.append(_error("out_of_range", "unit", u.id, target=u.id, spec="zones", min=1, max=100))
    elif t == "conversion_reactor":
        need("in", ins)
        need("out", outs)
        no_extra({"in"}, ins)
        no_extra({"out"}, outs)
        issues += _one_of(u, ("pressure", "pressure_drop"), required=False)
        issues += _one_of(u, ("temperature", "duty"), required=True)
        issues += _check_reactions(u, comp_ids or [])
    elif t == "shortcut_column":
        need("in", ins)
        for p in ("distillate", "bottoms"):
            need(p, outs)
        no_extra({"in"}, ins)
        no_extra({"distillate", "bottoms"}, outs)
        for name in ("lk_recovery", "hk_recovery", "reflux_ratio_factor"):
            if name not in u.specs:
                issues.append(_missing("unit", u.id, name))
        for name in ("lk_recovery", "hk_recovery"):
            if name in u.specs and not 0 < u.specs[name].value < 1:
                issues.append(_error("out_of_range", "unit", u.id, target=u.id, spec=name,
                                     min=0, max=1))
        if "reflux_ratio_factor" in u.specs and u.specs["reflux_ratio_factor"].value <= 1:
            issues.append(_error("out_of_range", "unit", u.id, target=u.id,
                                 spec="reflux_ratio_factor", min=1, max=None))
        lk, hk = u.options.get("light_key"), u.options.get("heavy_key")
        for name, key in (("light_key", lk), ("heavy_key", hk)):
            if not key:
                issues.append(_missing("unit", u.id, name))
            elif key not in (comp_ids or []):
                issues.append(_error("unknown_component", "unit", u.id, target=u.id,
                                     components=[key]))
        if lk and hk and lk == hk:
            issues.append(_error("same_keys", "unit", u.id, target=u.id))
    elif t in ("cstr", "pfr"):
        need("in", ins)
        need("out", outs)
        no_extra({"in"}, ins)
        no_extra({"out"}, outs)
        if "volume" not in u.specs:
            issues.append(_missing("unit", u.id, "volume"))
        elif u.specs["volume"].value <= 0:
            issues.append(_error("out_of_range", "unit", u.id, target=u.id, spec="volume", min=0, max=None))
        issues += _one_of(u, ("temperature", "duty"), required=True)
        issues += _one_of(u, ("pressure", "pressure_drop"), required=False)
        if u.options.get("phase", "gas") not in ("gas", "liquid"):
            issues.append(_error("invalid_option", "unit", u.id, target=u.id, option="phase"))
        issues += _check_kinetics(u, comp_ids or [])
    elif t == "equilibrium_reactor":
        need("in", ins)
        need("out", outs)
        no_extra({"in"}, ins)
        no_extra({"out"}, outs)
        issues += _one_of(u, ("temperature", "duty"), required=True)
        issues += _one_of(u, ("pressure", "pressure_drop"), required=False)
        reactions = u.options.get("reactions")
        if not isinstance(reactions, list) or not reactions:
            issues.append(_missing("unit", u.id, "reactions"))
        else:
            for k, r in enumerate(reactions, start=1):
                stoich = r.get("stoichiometry") if isinstance(r, dict) else None
                if not isinstance(stoich, dict) or not stoich:
                    issues.append(_error("invalid_reaction", "unit", u.id, target=u.id, reaction=k))
                    continue
                unknown = sorted(c for c in stoich if c not in (comp_ids or []))
                if unknown:
                    issues.append(_error("unknown_component", "unit", u.id, target=u.id, components=unknown))
                corr = r.get("ln_k")
                if corr is not None and not (
                        isinstance(corr, dict) and corr and set(corr) <= {"a", "b", "c"}
                        and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in corr.values())):
                    issues.append(_error("invalid_option", "unit", u.id, target=u.id, option=f"ln_k {k}"))
        if u.options.get("phase", "gas") not in ("gas", "liquid"):
            issues.append(_error("invalid_option", "unit", u.id, target=u.id, option="phase"))
    elif t == "distillation_column":
        need("in", ins)
        for p in ("distillate", "bottoms"):
            need(p, outs)
        no_extra({"in"}, ins)
        no_extra({"distillate", "bottoms"}, outs)
        for name in ("number_of_stages", "feed_stage", "reflux_ratio", "distillate_rate"):
            if name not in u.specs:
                issues.append(_missing("unit", u.id, name))
        n = u.specs["number_of_stages"].value if "number_of_stages" in u.specs else None
        if n is not None and (n != int(n) or n < 3):
            issues.append(_error("out_of_range", "unit", u.id, target=u.id, spec="number_of_stages",
                                 min=3, max=None))
        if "feed_stage" in u.specs:
            fs_ = u.specs["feed_stage"].value
            if fs_ != int(fs_) or fs_ < 2 or (n is not None and fs_ > n - 1):
                issues.append(_error("out_of_range", "unit", u.id, target=u.id, spec="feed_stage",
                                     min=2, max=(int(n) - 1) if n else None))
        for name in ("reflux_ratio", "distillate_rate"):
            if name in u.specs and u.specs[name].value <= 0:
                issues.append(_error("out_of_range", "unit", u.id, target=u.id, spec=name,
                                     min=0, max=None))
    if "vapor_fraction" in u.specs and not 0 <= u.specs["vapor_fraction"].value <= 1:
        issues.append(_error("out_of_range", "unit", u.id, target=u.id,
                             spec="vapor_fraction", min=0, max=1))
    if "efficiency" in u.specs and not 0 < u.specs["efficiency"].value <= 1:
        issues.append(_error("out_of_range", "unit", u.id, target=u.id, spec="efficiency",
                             min=0, max=1))
    return issues


def _check_kinetics(u: Unit, comp_ids: list[str]) -> list[Issue]:
    reactions = u.options.get("reactions")
    if not isinstance(reactions, list) or not reactions:
        return [_missing("unit", u.id, "reactions")]
    issues: list[Issue] = []
    for k, r in enumerate(reactions, start=1):
        stoich = r.get("stoichiometry") if isinstance(r, dict) else None
        if not isinstance(stoich, dict) or not stoich:
            issues.append(_error("invalid_reaction", "unit", u.id, target=u.id, reaction=k))
            continue
        orders = r.get("orders") or {}
        unknown = sorted(c for c in list(stoich) + list(orders) if c not in comp_ids)
        if unknown:
            issues.append(_error("unknown_component", "unit", u.id, target=u.id, components=unknown))
        k0, Ea = r.get("k0"), r.get("Ea", 0.0)
        if not isinstance(k0, (int, float)) or k0 <= 0:
            issues.append(_error("out_of_range", "unit", u.id, target=u.id, spec=f"k0 {k}", min=0, max=None))
        if not isinstance(Ea, (int, float)) or Ea < 0:
            issues.append(_error("out_of_range", "unit", u.id, target=u.id, spec=f"Ea {k}", min=0, max=None))
        if any(not isinstance(v, (int, float)) or v < 0 for v in orders.values()):
            issues.append(_error("out_of_range", "unit", u.id, target=u.id, spec=f"orders {k}", min=0, max=None))
    return issues


def _check_reactions(u: Unit, comp_ids: list[str]) -> list[Issue]:
    reactions = u.options.get("reactions")
    if not isinstance(reactions, list) or not reactions:
        return [_missing("unit", u.id, "reactions")]
    issues: list[Issue] = []
    for k, r in enumerate(reactions, start=1):
        stoich = r.get("stoichiometry") if isinstance(r, dict) else None
        key, conv = (r.get("key"), r.get("conversion")) if isinstance(r, dict) else (None, None)
        if not isinstance(stoich, dict) or not stoich:
            issues.append(_error("invalid_reaction", "unit", u.id, target=u.id, reaction=k))
            continue
        unknown = sorted(c for c in stoich if c not in comp_ids)
        if unknown:
            issues.append(_error("unknown_component", "unit", u.id, target=u.id, components=unknown))
        if key not in stoich or not isinstance(stoich.get(key), (int, float)) or stoich[key] >= 0:
            issues.append(_error("invalid_reaction_key", "unit", u.id, target=u.id, reaction=k))
        if not isinstance(conv, (int, float)) or not 0 <= conv <= 1:
            issues.append(_error("out_of_range", "unit", u.id, target=u.id,
                                 spec=f"conversion {k}", min=0, max=1))
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
    flowing = [s for s in streams if s.F > _ZERO_FLOW]
    # An empty inlet has no physical pressure, so it does not set the mixer pressure.
    P = (u.specs["pressure"].value if "pressure" in u.specs
         else min(s.P for s in (flowing or streams)))
    _require_positive_pressure(u, P)
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


def _pressure_up(u: Unit, P_in: float) -> float:
    if "pressure" in u.specs:
        return u.specs["pressure"].value
    return P_in + u.specs["pressure_increase"].value


def _solve_pump(u, inlets, outs, th, fs):
    """Shaft power W = F·V_L·ΔP / η, V_L from liquid-volume correlations (incompressible
    liquid; e.g. McCabe, Smith & Harriott, *Unit Operations of Chemical Engineering*,
    7th ed., §8). The outlet follows from the energy balance H_out = H_in + W/F."""
    feed = inlets["in"]
    P = _pressure_up(u, feed.P)
    eta = u.specs["efficiency"].value if "efficiency" in u.specs else 0.75
    if feed.F <= _ZERO_FLOW:
        return {"out": _empty(feed.T, P)}, {"power": _q(0.0, "W")}
    issues = []
    if (feed.VF or 0.0) > 1e-9:
        raise _InputError(_error("pump_vapor_inlet", "unit", u.id, target=u.id,
                                 vapor_fraction=round(feed.VF or 0.0, 4)))
    V = th.liquid_volume(feed.zs, feed.T)  # type: ignore[arg-type]
    power = feed.F * V * (P - feed.P) / eta
    out = _scaled(th.flash(feed.zs, P=P, H=feed.H + power / feed.F), feed.F)  # type: ignore[arg-type, operator]
    del issues
    return {"out": out}, {
        "power": _q(power, "W"),
        "pressure_increase": _q(P - feed.P, "Pa"),
        "temperature": _q(out.T, "K"),
        "efficiency": _q(eta, "1"),
    }


def _solve_compressor(u, inlets, outs, th, fs):
    """Isentropic outlet from S(P_out) = S_in, then W = F·(H_s − H_in)/η_s
    (Smith, Van Ness & Abbott, *Introduction to Chemical Engineering Thermodynamics*, ch. 7)."""
    feed = inlets["in"]
    P = _pressure_up(u, feed.P)
    eta = u.specs["efficiency"].value if "efficiency" in u.specs else 0.75
    if feed.F <= _ZERO_FLOW:
        return {"out": _empty(feed.T, P)}, {"power": _q(0.0, "W")}
    if (feed.VF if feed.VF is not None else 1.0) < 1 - 1e-9:
        raise _InputError(_error("compressor_liquid_inlet", "unit", u.id, target=u.id,
                                 vapor_fraction=round(feed.VF or 0.0, 4)))
    S_in = th.entropy(feed.zs, feed.T, feed.P)  # type: ignore[arg-type]
    iso = th.flash_raw(feed.zs, P=P, S=S_in)  # type: ignore[arg-type]
    dH = (iso.H() - feed.H) / eta  # type: ignore[operator]
    out = _scaled(th.flash(feed.zs, P=P, H=feed.H + dH), feed.F)  # type: ignore[arg-type, operator]
    return {"out": out}, {
        "power": _q(feed.F * dH, "W"),
        "temperature": _q(out.T, "K"),
        "isentropic_temperature": _q(iso.T, "K"),
        "pressure_increase": _q(P - feed.P, "Pa"),
        "efficiency": _q(eta, "1"),
    }


_HX_ZONES = 10  # default number of equal-duty zones (options.zones)
_HX_TABLE = 40  # points of the tabulated heat curves used while rating


def _lmtd(a: float, b: float) -> float:
    return (a - b) / math.log(a / b) if abs(a - b) > 1e-9 * max(a, b) else 0.5 * (a + b)


def _zone_ua(qs: list[float], t_hot: list[float], t_cold: list[float]) -> tuple[float, float, int]:
    """Zoned UA = Σ ΔQ_k / LMTD_k over a counter-current grid (q from the cold end).
    Returns (UA, minimum approach, index of the pinch); UA = inf if the curves touch or cross."""
    dts = [h - c for h, c in zip(t_hot, t_cold)]
    k_min = min(range(len(dts)), key=dts.__getitem__)
    if dts[k_min] <= 0:
        return math.inf, dts[k_min], k_min
    ua = sum((qs[k + 1] - qs[k]) / _lmtd(dts[k], dts[k + 1]) for k in range(len(qs) - 1))
    return ua, dts[k_min], k_min


def _solve_heat_exchanger(u, inlets, outs, th, fs):
    """Two-stream exchanger, energy balance Q = ΔH_hot = −ΔH_cold (see _hx_core).

    With `options.geometry` (T24, D030) the exchanger is a shell-and-tube unit: U from Kern's
    method at the mean temperatures, A from the tubes, F for 1 shell / 2N tube passes. Without
    a thermal specification it is rated (U·A·F = zoned UA); with one, the over-design is
    reported. Pressure drops from the geometry apply where none is specified (re-solved
    until they settle)."""
    hot, cold = inlets["hot_in"], inlets["cold_in"]
    if hot.F <= _ZERO_FLOW or cold.F <= _ZERO_FLOW:
        raise _InputError(_error("hx_empty_side", "unit", u.id, target=u.id))
    given_h = u.specs["hot_pressure_drop"].value if "hot_pressure_drop" in u.specs else None
    given_c = u.specs["cold_pressure_drop"].value if "cold_pressure_drop" in u.specs else None
    if "geometry" not in u.options:
        return _hx_core(u, hot, cold, th, given_h or 0.0, given_c or 0.0, None)
    geom = hx_geometry.parse(u.options["geometry"])
    dp_h, dp_c = given_h or 0.0, given_c or 0.0
    for _ in range(4):
        outlets, results = _hx_core(u, hot, cold, th, dp_h, dp_c, geom)
        tube_hot = geom.tube_side == "hot"
        calc_h = results["pressure_drop_tube" if tube_hot else "pressure_drop_shell"]["value"]
        calc_c = results["pressure_drop_shell" if tube_hot else "pressure_drop_tube"]["value"]
        new_h = given_h if given_h is not None else calc_h
        new_c = given_c if given_c is not None else calc_c
        if abs(new_h - dp_h) <= 1e-3 * max(new_h, 1.0) and abs(new_c - dp_c) <= 1e-3 * max(new_c, 1.0):
            break
        dp_h, dp_c = new_h, new_c
    return outlets, results


def _hx_core(u, hot, cold, th, dp_hot, dp_cold, geom):
    """Counter-current exchanger, energy balance Q = ΔH_hot = −ΔH_cold.

    Zone analysis (D028): the duty is split into `options.zones` equal parts, plus extra
    boundaries at each side's bubble and dew points; each side is flashed at the boundaries
    (pressure linear in duty), so phase changes inside the exchanger show up in the heat
    curves. Reports the minimum internal approach (pinch),
    UA = Σ ΔQ_k/LMTD_k and the T–Q profile. A temperature cross anywhere inside is an
    error. Rating (given UA or U·A) solves zoned UA(Q) = UA; with one zone this is the
    classic end-temperature LMTD method."""
    Ph, Pc = hot.P - dp_hot, cold.P - dp_cold
    _require_positive_pressure(u, min(Ph, Pc))
    zones = int(u.options.get("zones", _HX_ZONES))

    def outlets(Q: float) -> tuple[_State, _State]:
        ho = _scaled(th.flash(hot.zs, P=Ph, H=hot.H - Q / hot.F), hot.F)  # type: ignore[arg-type, operator]
        co = _scaled(th.flash(cold.zs, P=Pc, H=cold.H + Q / cold.F), cold.F)  # type: ignore[arg-type, operator]
        return ho, co

    def phase_boundaries(side: _State, P_out: float) -> list[float]:
        """Molar enthalpies at the bubble and dew points (mean pressure) where they exist."""
        out = []
        for vf in (0.0, 1.0):
            try:
                out.append(th.flash(side.zs, P=0.5 * (side.P + P_out), VF=vf).H)  # type: ignore[arg-type, operator]
            except Exception:  # noqa: BLE001 — no such point (e.g. supercritical): no extra grid point
                pass
        return out

    hot_bounds, cold_bounds = phase_boundaries(hot, Ph), phase_boundaries(cold, Pc)

    def curves(Q: float, ho: _State, co: _State) -> tuple[list[float], list[float], list[float]]:
        """Grid from the cold end (hot outlet / cold inlet, q = 0) to the hot end (q = Q):
        N equal zones plus the bubble and dew points of either side that fall inside."""
        qs = [Q * k / zones for k in range(zones + 1)]
        extra = [hot.F * (h - (hot.H - Q / hot.F)) for h in hot_bounds]  # type: ignore[operator]
        extra += [cold.F * (h - cold.H) for h in cold_bounds]  # type: ignore[operator]
        tol = 1e-6 * Q
        for x in extra:
            if tol < x < Q - tol and all(abs(x - y) > tol for y in qs):
                qs.append(x)
        qs.sort()
        t_hot, t_cold = [ho.T], [cold.T]
        for qk in qs[1:-1]:
            f = qk / Q
            t_hot.append(th.flash(hot.zs, P=Ph + (hot.P - Ph) * f,  # type: ignore[arg-type]
                                  H=hot.H - Q / hot.F + qk / hot.F).T)  # type: ignore[operator]
            t_cold.append(th.flash(cold.zs, P=cold.P - (cold.P - Pc) * f,  # type: ignore[arg-type]
                                   H=cold.H + qk / cold.F).T)  # type: ignore[operator]
        t_hot.append(hot.T)  # type: ignore[arg-type]
        t_cold.append(co.T)  # type: ignore[arg-type]
        return qs, t_hot, t_cold  # type: ignore[return-value]

    if "hot_outlet_temperature" in u.specs:
        h_out = _scaled(th.flash(hot.zs, T=u.specs["hot_outlet_temperature"].value, P=Ph), hot.F)  # type: ignore[arg-type]
        Q = hot.F * (hot.H - h_out.H)  # type: ignore[operator]
        c_out = _scaled(th.flash(cold.zs, P=Pc, H=cold.H + Q / cold.F), cold.F)  # type: ignore[arg-type, operator]
    elif "cold_outlet_temperature" in u.specs:
        c_out = _scaled(th.flash(cold.zs, T=u.specs["cold_outlet_temperature"].value, P=Pc), cold.F)  # type: ignore[arg-type]
        Q = cold.F * (c_out.H - cold.H)  # type: ignore[operator]
        h_out = _scaled(th.flash(hot.zs, P=Ph, H=hot.H - Q / hot.F), hot.F)  # type: ignore[arg-type, operator]
    elif "duty" in u.specs:
        Q = u.specs["duty"].value
        h_out, c_out = outlets(Q)
    elif geom is None:
        UA = (u.specs["ua"].value if "ua" in u.specs
              else u.specs["u_overall"].value * u.specs["area"].value)
        Q = _rate_heat_exchanger(u, UA, hot, cold, Ph, Pc, th, zones, outlets, curves)
        h_out, c_out = outlets(Q)
    else:
        # Geometry rating: U depends on the mean temperatures and F on the end temperatures.
        h_out, c_out = hot, cold
        UA = math.nan
        for _ in range(40):
            g = _hx_geometry_results(u, geom, hot, cold, h_out, c_out, Ph, Pc, th, final=False)
            UA_new = g["u"] * geom.area
            if abs(UA_new - UA) <= 1e-7 * UA_new:
                break
            UA = UA_new
            Q = _rate_heat_exchanger(u, UA, hot, cold, Ph, Pc, th, zones, outlets, curves,
                                     geom.tube_passes)
            h_out, c_out = outlets(Q)
        else:
            raise _InputError(_error("hx_geometry_not_converged", "unit", u.id, target=u.id))
    dT_hot_end = hot.T - c_out.T  # hot inlet against cold outlet
    dT_cold_end = h_out.T - cold.T  # hot outlet against cold inlet
    if Q < 0 or min(dT_hot_end, dT_cold_end) <= 0:
        raise _InputError(_error("temperature_cross", "unit", u.id, target=u.id,
                                 hot_end=round(dT_hot_end, 2), cold_end=round(dT_cold_end, 2)))
    qs, t_hot, t_cold = curves(Q, h_out, c_out)
    ua, dt_min, k_min = _zone_ua(qs, t_hot, t_cold)
    if dt_min <= 0:
        raise _InputError(_error("internal_temperature_cross", "unit", u.id, target=u.id,
                                 approach=round(dt_min, 2), at=f"{qs[k_min] / Q:.0%}"))
    results: dict[str, Any] = {
        "duty": _q(Q, "W"),
        "hot_outlet_temperature": _q(h_out.T, "K"),
        "cold_outlet_temperature": _q(c_out.T, "K"),
        "approach_hot_end": _q(dT_hot_end, "K"),
        "approach_cold_end": _q(dT_cold_end, "K"),
        "minimum_approach": _q(dt_min, "K"),
        "lmtd": _q(_lmtd(dT_hot_end, dT_cold_end), "K"),
        "mean_temperature_difference": _q(Q / ua, "K"),
        "ua": _q(ua, "W/K"),
        "zones": _q(float(len(qs) - 1), "1"),
        _PROFILE: {
            "axis": {"name": "duty", "unit": "W", "values": qs},
            "series": {
                "hot_temperature": {"unit": "K", "values": t_hot},
                "cold_temperature": {"unit": "K", "values": t_cold},
            },
        },
    }
    if geom is not None:
        g = _hx_geometry_results(u, geom, hot, cold, h_out, c_out, Ph, Pc, th, final=True)
        results.update({
            "area": _q(geom.area, "m2"),
            "u_overall": _q(g["u"], "W/m2/K"),
            "f_correction": _q(g["f"], "1"),
            "overdesign": _q(g["u"] * geom.area * g["f"] / ua - 1, "1"),
            "h_tube": _q(g["tube"]["h"], "W/m2/K"),
            "h_shell": _q(g["shell"]["h"], "W/m2/K"),
            "velocity_tube": _q(g["tube"]["velocity"], "m/s"),
            "velocity_shell": _q(g["shell"]["velocity"], "m/s"),
            "reynolds_tube": _q(g["tube"]["reynolds"], "1"),
            "reynolds_shell": _q(g["shell"]["reynolds"], "1"),
            "pressure_drop_tube": _q(g["tube"]["pressure_drop"], "Pa"),
            "pressure_drop_shell": _q(g["shell"]["pressure_drop"], "Pa"),
            "baffles": _q(float(geom.baffles), "1"),
        })
        if g["warnings"]:
            results[_WARNINGS] = g["warnings"]
    return {"hot_out": h_out, "cold_out": c_out}, results


def _side_fluid(th, side: _State, T: float, P: float) -> tuple[hx_geometry.Fluid, bool]:
    """Mass flow and transport properties of one side at (T, P); True if two-phase there.
    Liquids: pure-component correlations of `thermo` (Cp, liquid volume, μ by log mixing,
    k); gases: the package's gas phase for ρ and Cp, `thermo` mixing rules for μ and k."""
    zs = side.zs
    mws = th.constants.MWs
    mw = sum(z * m for z, m in zip(zs, mws))  # g/mol
    ws = [z * m / mw for z, m in zip(zs, mws)]
    res = th.flash_raw(zs, T=T, P=P)
    vf = _vapor_fraction(res)
    props = th.props
    if vf >= 0.5:
        gas = res.gas
        rho, cp = gas.rho_mass(), gas.Cp_mass()
        mu = props.ViscosityGasMixture.mixture_property(T, P, zs, ws)
        k = props.ThermalConductivityGasMixture.mixture_property(T, P, zs, ws)
    else:
        rho = mw / 1000 / th.liquid_volume(zs, T)
        cp = props.HeatCapacityLiquidMixture.mixture_property(T, P, zs, ws) / mw * 1000
        mu = props.ViscosityLiquidMixture.mixture_property(T, P, zs, ws)
        k = props.ThermalConductivityLiquidMixture.mixture_property(T, P, zs, ws)
    if not all(isinstance(v, (int, float)) and v > 0 for v in (rho, cp, mu, k)):
        raise ValueError("missing transport properties")
    return hx_geometry.Fluid(m=side.F * mw / 1000, rho=rho, cp=cp, mu=mu, k=k), 0.001 < vf < 0.999


def _hx_geometry_results(u, geom, hot, cold, h_out, c_out, Ph, Pc, th, final: bool) -> dict[str, Any]:
    """Film coefficients, U, F and pressure drops at the mean temperature of each side."""
    try:
        fh, two_h = _side_fluid(th, hot, 0.5 * (hot.T + h_out.T), 0.5 * (hot.P + Ph))
        fc, two_c = _side_fluid(th, cold, 0.5 * (cold.T + c_out.T), 0.5 * (cold.P + Pc))
    except (ValueError, TypeError) as exc:
        raise _InputError(_error("missing_transport_properties", "unit", u.id, target=u.id)) from exc
    tube_hot = geom.tube_side == "hot"
    tube = hx_geometry.tube_side(fh if tube_hot else fc, geom, heating=not tube_hot)
    shell = hx_geometry.shell_side(fc if tube_hot else fh, geom)
    U = hx_geometry.overall_u(geom, tube["h"], shell["h"])
    F: float | None = 1.0
    if final:
        F = hx_geometry.f_correction(hot.T, h_out.T, cold.T, c_out.T, geom.tube_passes)
        if F is None:
            raise _InputError(_error("hx_f_infeasible", "unit", u.id, target=u.id,
                                     passes=geom.tube_passes))
    warnings: list[Issue] = []
    if final:
        for name, two in (("hot", two_h), ("cold", two_c)):
            if two:
                warnings.append(_issue(Severity.WARNING, "geometry_two_phase", "unit", u.id,
                                       target=u.id, side=name))
        if F < 0.75:
            warnings.append(_issue(Severity.WARNING, "low_f_correction", "unit", u.id,
                                   target=u.id, f=round(F, 3)))
    return {"u": U, "f": F, "tube": tube, "shell": shell, "warnings": warnings}


def _rate_heat_exchanger(u, UA, hot, cold, Ph, Pc, th, zones, outlets, curves,
                         passes: int = 1) -> float:
    """Duty for a given UA (for 2N tube passes: zoned UA / F(end temperatures) = UA). Tabulated heat curves (T against duty, _HX_TABLE points each)
    give a cheap zoned UA(Q) for bracketing; a few exact secant steps then make the
    reported zoned UA equal the specification."""
    from scipy.optimize import brentq

    if hot.T <= cold.T:
        raise _InputError(_error("temperature_cross", "unit", u.id, target=u.id,
                                 hot_end=round(hot.T - cold.T, 2), cold_end=round(hot.T - cold.T, 2)))
    # Largest duty without an end cross: neither stream passes the other's inlet T.
    hot_lim = hot.F * (hot.H - th.flash(hot.zs, T=cold.T, P=Ph).H)  # type: ignore[arg-type, operator]
    cold_lim = cold.F * (th.flash(cold.zs, T=hot.T, P=Pc).H - cold.H)  # type: ignore[arg-type, operator]
    hi = min(hot_lim, cold_lim) * (1 - 1e-9)
    # Tabulated curves over [0, hi]: hot by heat released from its inlet, cold by heat absorbed.
    grid = [hi * k / (_HX_TABLE - 1) for k in range(_HX_TABLE)]
    tab_hot = [float(hot.T)] + [th.flash(hot.zs, P=hot.P - (hot.P - Ph) * r / hi,  # type: ignore[arg-type]
                                         H=hot.H - r / hot.F).T for r in grid[1:]]  # type: ignore[operator]
    tab_cold = [float(cold.T)] + [th.flash(cold.zs, P=cold.P - (cold.P - Pc) * a / hi,  # type: ignore[arg-type]
                                           H=cold.H + a / cold.F).T for a in grid[1:]]  # type: ignore[operator]

    def interp(table: list[float], x: float) -> float:
        pos = min(max(x / hi, 0.0), 1.0) * (_HX_TABLE - 1)
        k = min(int(pos), _HX_TABLE - 2)
        return table[k] + (table[k + 1] - table[k]) * (pos - k)

    def required(ua: float, t_hot_out: float, t_cold_out: float) -> float:
        if passes == 1 or not math.isfinite(ua):
            return ua
        F = hx_geometry.f_correction(hot.T, t_hot_out, cold.T, t_cold_out, passes)
        return ua / F if F else math.inf

    def approx(Q: float) -> float:
        qs = [Q * k / zones for k in range(zones + 1)]
        t_hot, t_cold = [interp(tab_hot, Q - q) for q in qs], [interp(tab_cold, q) for q in qs]
        ua, _, _ = _zone_ua(qs, t_hot, t_cold)
        return min(required(ua, t_hot[0], t_cold[-1]), 1e300) - UA

    lo = hi * 1e-9
    Q = brentq(approx, lo, hi, xtol=1e-7 * hi) if approx(hi) > 0 else hi

    def exact(Q: float) -> float:
        ho, co = outlets(Q)
        if ho.T <= cold.T or co.T >= hot.T:
            return math.inf
        return required(_zone_ua(*curves(Q, ho, co))[0], ho.T, co.T) - UA

    # Secant refinement on the exact zoned UA (curve interpolation and pressure profile).
    q0, f0 = Q, exact(Q)
    if not math.isfinite(f0):
        return Q
    q1 = Q * (1 - 1e-4)
    f1 = exact(q1)
    for _ in range(8):
        if abs(f1) <= 1e-9 * UA or not math.isfinite(f1) or f1 == f0:
            break
        q0, f0, q1 = q1, f1, q1 - f1 * (q1 - q0) / (f1 - f0)
        q1 = min(max(q1, lo), hi)
        f1 = exact(q1)
    return q1 if math.isfinite(f1) and abs(f1) <= abs(f0) else q0


def _solve_conversion_reactor(u, inlets, outs, th, fs):
    """Fixed-conversion reactions applied in order: ξ_r = X_r·n_key/(−ν_key). Energy balance
    on a formation-enthalpy basis, H + Σ z_i ΔHf_i (ideal gas, 298.15 K)."""
    feed = inlets["in"]
    P = _outlet_pressure(u, feed.P)
    _require_positive_pressure(u, P)
    if feed.F <= _ZERO_FLOW:
        return {"out": _empty(feed.T, P)}, {"duty": _q(0.0, "W")}
    index = {cid: k for k, cid in enumerate(th.ids)}
    flows = [feed.F * z for z in feed.zs]  # type: ignore[union-attr]
    results: dict[str, dict[str, Any]] = {}
    mws = th.constants.MWs
    for k, r in enumerate(u.options["reactions"], start=1):
        stoich = {c: float(v) for c, v in r["stoichiometry"].items()}
        mass = sum(v * mws[index[c]] for c, v in stoich.items())
        scale = sum(abs(v) * mws[index[c]] for c, v in stoich.items())
        if abs(mass) > 1e-3 * scale:
            raise _InputError(_error("unbalanced_reaction", "unit", u.id, target=u.id, reaction=k,
                                     imbalance=round(mass, 4)))
        key = r["key"]
        extent = float(r["conversion"]) * flows[index[key]] / -stoich[key]
        for c, v in stoich.items():
            flows[index[c]] += v * extent
        if min(flows) < -1e-9 * feed.F:
            raise _InputError(_error("reaction_overconsumes", "unit", u.id, target=u.id, reaction=k))
        flows = [max(0.0, f) for f in flows]
        results[f"extent_{k}"] = _q(extent, "mol/s")
    F = sum(flows)
    zs = [f / F for f in flows]
    H_in = feed.F * (feed.H + th.Hf(feed.zs))  # type: ignore[arg-type, operator]
    if "temperature" in u.specs:
        out = _scaled(th.flash(zs, T=u.specs["temperature"].value, P=P), F)
        duty = F * (out.H + th.Hf(zs)) - H_in  # type: ignore[operator]
    else:
        duty = u.specs["duty"].value
        out = _scaled(th.flash(zs, P=P, H=(H_in + duty) / F - th.Hf(zs)), F)
    results.update({
        "duty": _q(duty, "W"),
        "temperature": _q(out.T, "K"),
        "pressure": _q(P, "Pa"),
        "vapor_fraction": _q(out.VF, "1"),
    })
    return {"out": out}, results


def _solve_shortcut_column(u, inlets, outs, th, fs):
    """Fenske–Underwood–Gilliland shortcut design with a total condenser.

    Constant relative volatilities α_i = K_i/K_HK from a flash of the feed composition at
    column pressure and vapour fraction 0.5; Fenske for N_min and non-key distribution;
    Underwood (one root between the keys) for R_min; Gilliland's correlation in the form of
    Molokanov et al. (1972) for N; Kirkbride (1944) for the feed stage. See Seader, Henley &
    Roper, *Separation Process Principles*, 3rd ed., Wiley (2011), ch. 9.
    """
    feed = inlets["in"]
    P = u.specs["pressure"].value if "pressure" in u.specs else feed.P
    _require_positive_pressure(u, P)
    if feed.F <= _ZERO_FLOW:
        raise _InputError(_error("column_empty_feed", "unit", u.id, target=u.id))
    ids = th.ids
    z = list(feed.zs)  # type: ignore[arg-type]
    lk, hk = ids.index(u.options["light_key"]), ids.index(u.options["heavy_key"])
    r_lk, r_hk = u.specs["lk_recovery"].value, u.specs["hk_recovery"].value
    factor = u.specs["reflux_ratio_factor"].value

    mid = th.flash_raw(z, P=P, VF=0.5)
    if mid.gas is None or mid.liquid0 is None:
        raise _InputError(_error("column_no_two_phase", "unit", u.id, target=u.id))
    K = [y / x if x > 0 else math.inf for y, x in zip(mid.gas.zs, mid.liquid0.zs)]
    alpha = [k / K[hk] for k in K]
    if alpha[lk] <= 1:
        raise _InputError(_error("keys_not_volatile", "unit", u.id, target=u.id))

    # Fenske: minimum stages and distribution of all components at total reflux.
    n_min = math.log((r_lk / (1 - r_lk)) * (r_hk / (1 - r_hk))) / math.log(alpha[lk])
    ratio_hk = (1 - r_hk) / r_hk  # d/b of the heavy key
    f = [feed.F * zi for zi in z]
    d = [fi * (a ** n_min * ratio_hk) / (1 + a ** n_min * ratio_hk) for fi, a in zip(f, alpha)]
    b = [fi - di for fi, di in zip(f, d)]
    D, B = sum(d), sum(b)
    xD, xB = [di / D for di in d], [bi / B for bi in b]

    # Feed thermal condition q (liquid fraction after letdown to column pressure).
    q = 1 - th.flash(z, P=P, H=feed.H).VF  # type: ignore[arg-type, operator]

    # Underwood: Σ α_i z_i / (α_i − θ) = 1 − q with 1 < θ < α_LK (bisection).
    def underwood(theta: float) -> float:
        return sum(a * zi / (a - theta) for a, zi in zip(alpha, z) if zi > 0) - (1 - q)

    lo, hi = 1.0 + 1e-9, alpha[lk] - 1e-9
    for _ in range(200):
        theta = (lo + hi) / 2
        if underwood(theta) > 0:
            hi = theta
        else:
            lo = theta
    r_min = sum(a * x / (a - theta) for a, x in zip(alpha, xD)) - 1
    if r_min <= 0:
        raise _InputError(_error("column_rmin_invalid", "unit", u.id, target=u.id))
    R = factor * r_min

    # Gilliland (Molokanov form).
    X = (R - r_min) / (R + 1)
    Y = 1 - math.exp((1 + 54.4 * X) / (11 + 117.2 * X) * (X - 1) / math.sqrt(X))
    n = (n_min + Y) / (1 - Y)

    # Kirkbride: N_R/N_S = [(z_HK/z_LK)(x_B,LK/x_D,HK)² (B/D)]^0.206.
    ratio = ((z[hk] / z[lk]) * (xB[lk] / xD[hk]) ** 2 * (B / D)) ** 0.206
    feed_stage = n * ratio / (1 + ratio)

    dist = th.flash(xD, P=P, VF=0.0)
    bott = th.flash(xB, P=P, VF=0.0)
    dew = th.flash(xD, P=P, VF=1.0)
    q_cond = -(R + 1) * D * (dew.H - dist.H)  # type: ignore[operator]
    q_reb = D * dist.H + B * bott.H - feed.F * feed.H - q_cond  # type: ignore[operator]

    return {"distillate": _scaled(dist, D), "bottoms": _scaled(bott, B)}, {
        "minimum_stages": _q(n_min, "1"),
        "stages": _q(n, "1"),
        "feed_stage": _q(feed_stage, "1"),
        "minimum_reflux_ratio": _q(r_min, "1"),
        "reflux_ratio": _q(R, "1"),
        "relative_volatility": _q(alpha[lk], "1"),
        "condenser_duty": _q(q_cond, "W"),
        "reboiler_duty": _q(q_reb, "W"),
        "pressure": _q(P, "Pa"),
    }


def _solve_kinetic_reactor(u, inlets, outs, th, fs):
    """CSTR or PFR with power-law kinetics (see kinetics.py)."""
    feed = inlets["in"]
    P = _outlet_pressure(u, feed.P)
    _require_positive_pressure(u, P)
    if feed.F <= _ZERO_FLOW:
        return {"out": _empty(feed.T, P)}, {"duty": _q(0.0, "W")}
    index = {cid: k for k, cid in enumerate(th.ids)}
    mws = th.constants.MWs
    for k, r in enumerate(u.options["reactions"], start=1):
        mass = sum(float(v) * mws[index[c]] for c, v in r["stoichiometry"].items())
        scale = sum(abs(float(v)) * mws[index[c]] for c, v in r["stoichiometry"].items())
        if abs(mass) > 1e-3 * scale:
            raise _InputError(_error("unbalanced_reaction", "unit", u.id, target=u.id, reaction=k,
                                     imbalance=round(mass, 4)))
    laws = parse_rate_laws(u.options["reactions"], th.ids)
    phase = u.options.get("phase", "gas")
    V = u.specs["volume"].value
    flows_in = [feed.F * z for z in feed.zs]  # type: ignore[union-attr]
    H_in = feed.F * (feed.H + th.Hf(feed.zs))  # type: ignore[arg-type, operator]
    T_fixed = u.specs["temperature"].value if "temperature" in u.specs else None
    Q = u.specs["duty"].value if "duty" in u.specs else 0.0

    def T_energy(flows: list[float], H_total: float) -> float:
        F = sum(flows)
        z = [f / F for f in flows]
        return th.flash(z, P=P, H=H_total / F - th.Hf(z)).T

    try:
        if u.type == "cstr":
            sol = solve_cstr(th, laws, flows_in, P, V, phase,
                             (lambda fl: T_fixed) if T_fixed is not None else (lambda fl: T_energy(fl, H_in + Q)))
        else:
            sol = solve_pfr(th, laws, flows_in, P, V, phase,
                            (lambda fl, v: T_fixed) if T_fixed is not None
                            else (lambda fl, v: T_energy(fl, H_in + Q * v / V)))
    except KineticsError as exc:
        raise _InputError(_error(exc.code, "unit", u.id, target=u.id, **exc.params)) from exc
    F = sum(sol.flows)
    zs = [f / F for f in sol.flows]
    out = _scaled(th.flash(zs, T=sol.T, P=P), F)
    duty = F * (out.H + th.Hf(zs)) - H_in  # type: ignore[operator]
    Vm_in = th.flasher.gas.to(T=feed.T, P=P, zs=feed.zs) if phase == "gas" else th.flasher.liquid.to(T=feed.T, P=P, zs=feed.zs)
    results: dict[str, Any] = {f"extent_{k + 1}": _q(e, "mol/s") for k, e in enumerate(sol.extents)}
    results.update({
        "duty": _q(duty, "W"),
        "temperature": _q(out.T, "K"),
        "pressure": _q(P, "Pa"),
        "space_time": _q(V / (feed.F * Vm_in.V()), "s"),
        "vapor_fraction": _q(out.VF, "1"),
    })
    if sol.profile is not None:
        prof = sol.profile
        results[_PROFILE] = {
            "axis": {"name": "volume", "unit": "m3", "values": prof["volume"]},
            "series": {
                "temperature": {"unit": "K", "values": prof["temperature"]},
                **{f"x_{cid}": {"unit": "1", "values": [z[k] for z in prof["z"]]} for k, cid in enumerate(th.ids)},
            },
        }
    return {"out": out}, results


def _solve_equilibrium_reactor(u, inlets, outs, th, fs):
    """Chemical equilibrium in the gas or liquid phase (see equilibrium.py)."""
    feed = inlets["in"]
    P = _outlet_pressure(u, feed.P)
    _require_positive_pressure(u, P)
    if feed.F <= _ZERO_FLOW:
        return {"out": _empty(feed.T, P)}, {"duty": _q(0.0, "W")}
    index = {cid: k for k, cid in enumerate(th.ids)}
    mws = th.constants.MWs
    nus = []
    for k, r in enumerate(u.options["reactions"], start=1):
        nu = [0.0] * len(th.ids)
        for c, v in r["stoichiometry"].items():
            nu[index[c]] = float(v)
        if abs(sum(n * w for n, w in zip(nu, mws))) > 1e-3 * sum(abs(n) * w for n, w in zip(nu, mws)):
            raise _InputError(_error("unbalanced_reaction", "unit", u.id, target=u.id, reaction=k,
                                     imbalance=round(sum(n * w for n, w in zip(nu, mws)), 4)))
        nus.append(nu)
    flows_in = [feed.F * z for z in feed.zs]  # type: ignore[union-attr]
    H_in = feed.F * (feed.H + th.Hf(feed.zs))  # type: ignore[arg-type, operator]
    phase = u.options.get("phase", "gas")
    correlations = [r.get("ln_k") for r in u.options["reactions"]]

    def outlet(T: float) -> tuple[list[float], _State]:
        xi = solve_equilibrium(th, nus, flows_in, P, T, phase, correlations)
        flows = [max(f + sum(nu[i] * x for nu, x in zip(nus, xi)), 0.0) for i, f in enumerate(flows_in)]
        F = sum(flows)
        zs = [f / F for f in flows]
        return xi, _scaled(th.flash(zs, T=T, P=P), F)

    try:
        if "temperature" in u.specs:
            T = u.specs["temperature"].value
        else:
            Q = u.specs["duty"].value

            def energy(T: float) -> float:
                _, out = outlet(T)
                return out.F * (out.H + th.Hf(out.zs)) - H_in - Q  # type: ignore[operator, arg-type]

            T = solve_adiabatic(energy, feed.T)
        xi, out = outlet(T)
    except EquilibriumError as exc:
        raise _InputError(_error(exc.code, "unit", u.id, target=u.id, **exc.params)) from exc
    duty = out.F * (out.H + th.Hf(out.zs)) - H_in  # type: ignore[operator, arg-type]
    results: dict[str, Any] = {}
    for k, (x, nu) in enumerate(zip(xi, nus), start=1):
        results[f"extent_{k}"] = _q(x, "mol/s")
        results[f"equilibrium_constant_{k}"] = _q(
            math.exp(phase_ln_k(th, nu, T, P, phase, correlations[k - 1])), "1")
    issues: list[Issue] = []
    if (phase == "liquid" and out.VF > 0.01) or (phase == "gas" and out.VF < 0.99):
        issues.append(_issue(Severity.WARNING, "equilibrium_phase_mismatch", "unit", u.id,
                             target=u.id, phase=phase, vapor_fraction=round(out.VF, 3)))
    results.update({
        "duty": _q(duty, "W"),
        "temperature": _q(T, "K"),
        "pressure": _q(P, "Pa"),
        "vapor_fraction": _q(out.VF, "1"),
    })
    if issues:
        results[_WARNINGS] = issues
    return {"out": out}, results


def _solve_distillation_column(u, inlets, outs, th, fs):
    """Rigorous column by the bubble-point method (see column.py)."""
    feed = inlets["in"]
    P = u.specs["pressure"].value if "pressure" in u.specs else feed.P
    _require_positive_pressure(u, P)
    if feed.F <= _ZERO_FLOW:
        raise _InputError(_error("column_empty_feed", "unit", u.id, target=u.id))
    if len(th.ids) < 2:
        raise _InputError(_error("column_needs_two_components", "unit", u.id, target=u.id))
    try:
        r = solve_column(th, list(feed.zs), feed.F, feed.H, P,  # type: ignore[arg-type]
                         int(u.specs["number_of_stages"].value), int(u.specs["feed_stage"].value),
                         u.specs["reflux_ratio"].value, u.specs["distillate_rate"].value)
    except ColumnError as exc:
        raise _InputError(_error(exc.code, "unit", u.id, target=u.id, **exc.params)) from exc
    N = len(r.T)
    dist = _State(r.T[0], P, r.D, r.x[0], r.HL[0], 0.0)
    bott = _State(r.T[N - 1], P, r.B, r.x[N - 1], r.HL[N - 1], 0.0)
    return {"distillate": dist, "bottoms": bott}, {
        "condenser_duty": _q(r.Qc, "W"),
        "reboiler_duty": _q(r.Qr, "W"),
        "top_temperature": _q(r.T[0], "K"),
        "bottom_temperature": _q(r.T[N - 1], "K"),
        "reflux_rate": _q(r.L[0], "mol/s"),
        "boilup_rate": _q(r.V[N - 1], "mol/s"),
        "iterations": _q(float(r.iterations), "1"),
        "pressure": _q(P, "Pa"),
        _PROFILE: {
            "axis": {"name": "stage", "unit": "1", "values": [float(j + 1) for j in range(N)]},
            "series": {
                "temperature": {"unit": "K", "values": list(r.T)},
                "liquid_flow": {"unit": "mol/s", "values": list(r.L)},
                "vapor_flow": {"unit": "mol/s", "values": list(r.V)},
                **{f"x_{cid}": {"unit": "1", "values": [r.x[j][k] for j in range(N)]}
                   for k, cid in enumerate(th.ids)},
                **{f"y_{cid}": {"unit": "1", "values": [r.y[j][k] for j in range(N)]}
                   for k, cid in enumerate(th.ids)},
            },
        },
    }


_SOLVERS: dict[str, Solver] = {
    "distillation_column": _solve_distillation_column,
    "cstr": _solve_kinetic_reactor,
    "equilibrium_reactor": _solve_equilibrium_reactor,
    "pfr": _solve_kinetic_reactor,
    "pump": _solve_pump,
    "compressor": _solve_compressor,
    "heat_exchanger": _solve_heat_exchanger,
    "conversion_reactor": _solve_conversion_reactor,
    "shortcut_column": _solve_shortcut_column,
    "feed": _solve_feed,
    "product": _solve_product,
    "mixer": _solve_mixer,
    "splitter": _solve_splitter,
    "heater": _solve_heater,
    "valve": _solve_valve,
    "flash": _solve_flash,
}

_adapter.register(ReferenceAdapter())
