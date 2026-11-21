"""Shell-and-tube exchanger geometry: Kern's method (T24).

Single-phase film coefficients and pressure drops for an E-shell with segmental baffles,
plus the LMTD correction factor for one shell pass and an even number of tube passes.

Sources:
- D. Q. Kern, *Process Heat Transfer*, McGraw-Hill (1950), ch. 7 (shell side).
- R. K. Sinnott, *Coulson & Richardson's Chemical Engineering* Vol. 6, 4th ed. (2005),
  §12.8–12.9 (Kern's method, tube-side correlations, return losses).
- Shell-and-tube design model sheet, University of Oklahoma CHE design course (2018):
  f_s = 1.728 Re^-0.188, f_t = 0.014 + 1.056 Re^-0.42, return loss K = 0.9 (one pass) /
  1.6 (several passes).
- Tube side: Dittus–Boelter (Re ≥ 10⁴), Gnielinski with Petukhov's friction factor
  (2300 < Re < 10⁴), Sieder–Tate developing laminar flow (Re ≤ 2300, Nu ≥ 3.66).
- F factor: Bowman, Mueller & Nagle, Trans. ASME 62 (1940) 283, for 1 shell pass /
  2N tube passes.

Wall-viscosity corrections (μ/μ_w)^0.14 are taken as 1. All inputs and outputs in SI.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

LAYOUTS = ("triangular", "square")
FIELDS = ("tube_outer_diameter", "tube_inner_diameter", "tube_length", "tube_count", "tube_passes",
          "pitch", "shell_inner_diameter", "baffle_spacing")
OPTIONAL = {"layout": "triangular", "tube_side": "cold", "wall_conductivity": 45.0,
            "fouling_tube": 0.0, "fouling_shell": 0.0}


@dataclass
class Fluid:
    """Mass flow (kg/s) and properties at the mean temperature of one side."""

    m: float
    rho: float
    cp: float  # J/(kg·K)
    mu: float  # Pa·s
    k: float  # W/(m·K)

    @property
    def pr(self) -> float:
        return self.cp * self.mu / self.k


@dataclass
class Geometry:
    tube_outer_diameter: float
    tube_inner_diameter: float
    tube_length: float
    tube_count: int
    tube_passes: int
    pitch: float
    shell_inner_diameter: float
    baffle_spacing: float
    layout: str = "triangular"
    tube_side: str = "cold"
    wall_conductivity: float = 45.0
    fouling_tube: float = 0.0
    fouling_shell: float = 0.0

    @property
    def area(self) -> float:
        """Outside tube area, m²."""
        return self.tube_count * math.pi * self.tube_outer_diameter * self.tube_length

    @property
    def baffles(self) -> int:
        return max(int(round(self.tube_length / self.baffle_spacing)) - 1, 0)


def check(geom: object) -> list[str]:
    """Names of missing or invalid geometry fields (empty if the geometry is usable)."""
    if not isinstance(geom, dict):
        return ["geometry"]
    bad = []
    for name in FIELDS:
        v = geom.get(name)
        if not isinstance(v, (int, float)) or isinstance(v, bool) or not v > 0:
            bad.append(name)
    for name in ("tube_count", "tube_passes"):
        v = geom.get(name)
        if name not in bad and v != int(v):
            bad.append(name)
    passes = geom.get("tube_passes")
    if "tube_passes" not in bad and passes != 1 and passes % 2:  # type: ignore[operator]
        bad.append("tube_passes")
    if not bad and geom["tube_inner_diameter"] >= geom["tube_outer_diameter"]:
        bad.append("tube_inner_diameter")
    if not bad and geom["pitch"] <= geom["tube_outer_diameter"]:
        bad.append("pitch")
    if not bad and geom["tube_count"] < geom["tube_passes"]:
        bad.append("tube_count")
    if geom.get("layout", "triangular") not in LAYOUTS:
        bad.append("layout")
    if geom.get("tube_side", "cold") not in ("hot", "cold"):
        bad.append("tube_side")
    for name in ("wall_conductivity",):
        v = geom.get(name, OPTIONAL[name])
        if not isinstance(v, (int, float)) or isinstance(v, bool) or not v > 0:
            bad.append(name)
    for name in ("fouling_tube", "fouling_shell"):
        v = geom.get(name, 0.0)
        if not isinstance(v, (int, float)) or isinstance(v, bool) or v < 0:
            bad.append(name)
    unknown = sorted(set(geom) - set(FIELDS) - set(OPTIONAL))
    return bad + unknown


def parse(geom: dict) -> Geometry:
    values = {**OPTIONAL, **geom}
    values["tube_count"] = int(values["tube_count"])
    values["tube_passes"] = int(values["tube_passes"])
    return Geometry(**values)


def tube_side(fl: Fluid, g: Geometry, heating: bool) -> dict[str, float]:
    """Velocity, Re, h (inside, W/m²K) and pressure drop (Pa, incl. return losses)."""
    di = g.tube_inner_diameter
    flow_area = g.tube_count / g.tube_passes * math.pi * di ** 2 / 4
    v = fl.m / (fl.rho * flow_area)
    re = fl.rho * v * di / fl.mu
    pr = fl.pr
    if re >= 1e4:
        nu = 0.023 * re ** 0.8 * pr ** (0.4 if heating else 0.3)
    elif re > 2300:
        f = (0.790 * math.log(re) - 1.64) ** -2
        nu = (f / 8) * (re - 1000) * pr / (1 + 12.7 * math.sqrt(f / 8) * (pr ** (2 / 3) - 1))
    else:
        nu = max(1.86 * (re * pr * di / g.tube_length) ** (1 / 3), 3.66)
    h = nu * fl.k / di
    friction = 64 / re if re <= 2300 else 0.014 + 1.056 * re ** -0.42
    k_return = 0.9 if g.tube_passes == 1 else 1.6
    dp = fl.rho * v ** 2 / 2 * (friction * g.tube_passes * g.tube_length / di + k_return * g.tube_passes)
    return {"velocity": v, "reynolds": re, "h": h, "pressure_drop": dp}


def shell_side(fl: Fluid, g: Geometry) -> dict[str, float]:
    """Kern: cross-flow area at the shell centre line, equivalent diameter, h and ΔP."""
    do, pt = g.tube_outer_diameter, g.pitch
    flow_area = g.shell_inner_diameter * (1 - do / pt) * g.baffle_spacing
    # Kern's equivalent diameter: 4 × free area / wetted perimeter of the unit cell.
    if g.layout == "square":
        de = 4 * (pt ** 2 - math.pi * do ** 2 / 4) / (math.pi * do)
    else:
        de = 4 * (0.5 * pt * 0.86 * pt - 0.5 * math.pi * do ** 2 / 4) / (0.5 * math.pi * do)
    v = fl.m / (fl.rho * flow_area)
    re = fl.rho * v * de / fl.mu
    h = 0.36 * re ** 0.55 * fl.pr ** (1 / 3) * fl.k / de
    friction = 1.728 * re ** -0.188
    dp = friction * g.shell_inner_diameter * (g.baffles + 1) / de * fl.rho * v ** 2 / 2
    return {"velocity": v, "reynolds": re, "h": h, "pressure_drop": dp, "equivalent_diameter": de}


def overall_u(g: Geometry, h_tube: float, h_shell: float) -> float:
    """Overall coefficient on the outside tube area, W/(m²·K)."""
    do, di = g.tube_outer_diameter, g.tube_inner_diameter
    resistance = (do / (di * h_tube) + g.fouling_tube * do / di
                  + do * math.log(do / di) / (2 * g.wall_conductivity) + g.fouling_shell + 1 / h_shell)
    return 1 / resistance


def f_correction(t_hot_in: float, t_hot_out: float, t_cold_in: float, t_cold_out: float,
                 tube_passes: int) -> float | None:
    """LMTD correction for 1 shell pass and 2N tube passes (1.0 for a single, counter-current
    pass); None if the temperatures cannot be reached in a 1–2N exchanger."""
    if tube_passes == 1:
        return 1.0
    if t_hot_in <= t_cold_in:
        return None
    P = (t_cold_out - t_cold_in) / (t_hot_in - t_cold_in)
    if P <= 1e-9 or t_hot_in - t_hot_out <= 1e-9 * t_hot_in:
        return 1.0  # vanishing duty on one side: no correction
    if P >= 1:
        return None
    R = (t_hot_in - t_hot_out) / (t_cold_out - t_cold_in)
    s = math.sqrt(R * R + 1)
    try:
        if abs(R - 1) < 1e-6:
            num = P * math.sqrt(2) / (1 - P)
        else:
            num = s * math.log((1 - P) / (1 - P * R)) / (R - 1)
        den = math.log((2 - P * (R + 1 - s)) / (2 - P * (R + 1 + s)))
    except (ValueError, ZeroDivisionError):
        return None
    F = num / den if den > 0 else None
    return F if F is not None and 0 < F <= 1 + 1e-9 else None
