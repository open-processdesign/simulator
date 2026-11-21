"""Kinetic reactors: CSTR and PFR with power-law rate laws (T17).

Rate of reaction k (mol·m⁻³·s⁻¹), Arrhenius form with power-law orders:

    r_k = k0_k · exp(−Ea_k / (R·T)) · Π_i C_i^(n_ik),   C_i = z_i / V_m   (mol/m³)

V_m is the molar volume of the reacting phase (gas or liquid) from the property package.
Component balances (Fogler, *Elements of Chemical Reaction Engineering*, 5th ed., ch. 1–2):

    CSTR:  0 = F_i,in − F_i,out + V · Σ_k ν_ik r_k(out)        (solved with scipy `root`)
    PFR:   dF_i/dV = Σ_k ν_ik r_k                               (integrated with `solve_ivp`)

Energy: isothermal (outlet temperature given) or a given duty (0 = adiabatic), on the same
formation-enthalpy basis as the conversion reactor; in a PFR the duty is spread evenly over
the volume.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable

R_GAS = 8.314462618  # J/(mol·K)


class KineticsError(Exception):
    def __init__(self, code: str, **params: Any) -> None:
        super().__init__(code)
        self.code = code
        self.params = params


@dataclass
class RateLaw:
    stoichiometry: list[float]  # ν_i per component (document order)
    k0: float  # pre-exponential factor, SI (mol/m³/s per (mol/m³)^Σn)
    Ea: float  # activation energy, J/mol
    orders: list[float]  # n_i per component


def parse_rate_laws(reactions: list[dict[str, Any]], ids: list[str]) -> list[RateLaw]:
    index = {cid: k for k, cid in enumerate(ids)}
    laws = []
    for r in reactions:
        nu = [0.0] * len(ids)
        for c, v in r["stoichiometry"].items():
            nu[index[c]] = float(v)
        orders = [0.0] * len(ids)
        for c, v in (r.get("orders") or {}).items():
            orders[index[c]] = float(v)
        laws.append(RateLaw(nu, float(r["k0"]), float(r.get("Ea", 0.0)), orders))
    return laws


def rates(laws: list[RateLaw], T: float, conc: list[float]) -> list[float]:
    out = []
    for law in laws:
        r = law.k0 * math.exp(-law.Ea / (R_GAS * T))
        for c, n in zip(conc, law.orders):
            if n:
                r *= max(c, 0.0) ** n
        out.append(r)
    return out


@dataclass
class ReactorSolution:
    flows: list[float]  # outlet component flows, mol/s
    T: float
    extents: list[float]  # mol/s per reaction (V·r for a CSTR, ∫ r dV for a PFR)
    profile: dict[str, Any] | None = None


def molar_volume(th: Any, phase: str, T: float, P: float, z: list[float]) -> float:
    model = th.flasher.gas if phase == "gas" else th.flasher.liquid
    return model.to(T=T, P=P, zs=z).V()


def solve_cstr(th: Any, laws: list[RateLaw], flows_in: list[float], P: float, volume: float,
               phase: str, temperature_of: Callable[[list[float]], float]) -> ReactorSolution:
    """`temperature_of(flows)` gives the outlet T (fixed, or from the energy balance)."""
    from scipy.optimize import root

    nc, nr = len(flows_in), len(laws)
    scale = max(sum(flows_in), 1e-12)

    def flows_of(xi: list[float]) -> list[float]:
        return [flows_in[i] + sum(laws[k].stoichiometry[i] * xi[k] for k in range(nr)) for i in range(nc)]

    def state(flows: list[float]) -> tuple[float, list[float]]:
        flows = [max(f, 0.0) for f in flows]
        F = sum(flows)
        z = [f / F for f in flows]
        T = temperature_of(flows)
        Vm = molar_volume(th, phase, T, P, z)
        return T, rates(laws, T, [zi / Vm for zi in z])

    # Unknowns: extents ξ_k = V·r_k(outlet), scaled by the feed flow.
    def residual(u: Any) -> list[float]:
        xi = [float(v) * scale for v in u]
        _, r = state(flows_of(xi))
        return [(xi[k] - volume * r[k]) / scale for k in range(nr)]

    sol = None
    for method in ("hybr", "lm"):
        sol = root(residual, [0.0] * nr, method=method)
        if max(abs(v) for v in residual(sol.x)) < 1e-10:
            break
    else:
        raise KineticsError("reactor_not_converged", detail=str(sol.message))
    xi = [float(v) * scale for v in sol.x]
    flows = flows_of(xi)
    if min(flows) < -1e-9 * scale:
        raise KineticsError("reactor_not_converged", detail="negative outlet flow")
    flows = [max(f, 0.0) for f in flows]
    T, _ = state(flows)
    return ReactorSolution(flows, T, xi)


def solve_pfr(th: Any, laws: list[RateLaw], flows_in: list[float], P: float, volume: float,
              phase: str, temperature_of: Callable[[list[float], float], float],
              points: int = 21) -> ReactorSolution:
    """`temperature_of(flows, v)` gives T at reactor volume v (fixed, or from energy)."""
    from scipy.integrate import solve_ivp

    nc, nr = len(flows_in), len(laws)

    def rhs(v: float, y: Any) -> list[float]:
        flows = [max(float(f), 0.0) for f in y[:nc]]
        F = sum(flows)
        z = [f / F for f in flows]
        T = temperature_of(flows, v)
        Vm = molar_volume(th, phase, T, P, z)
        r = rates(laws, T, [zi / Vm for zi in z])
        dF = [sum(laws[k].stoichiometry[i] * r[k] for k in range(nr)) for i in range(nc)]
        return dF + r  # extents integrate the rates

    grid = [volume * j / (points - 1) for j in range(points)]
    sol = solve_ivp(rhs, (0.0, volume), list(flows_in) + [0.0] * nr, method="LSODA",
                    t_eval=grid, rtol=1e-9, atol=1e-12 * max(sum(flows_in), 1.0))
    if not sol.success:
        raise KineticsError("reactor_not_converged", detail=str(sol.message))
    flows = [max(float(f), 0.0) for f in sol.y[:nc, -1]]
    extents = [float(e) for e in sol.y[nc:, -1]]
    temps, zs = [], []
    for j, v in enumerate(sol.t):
        fl = [max(float(f), 0.0) for f in sol.y[:nc, j]]
        temps.append(temperature_of(fl, float(v)))
        zs.append([f / sum(fl) for f in fl])
    profile = {"volume": [float(v) for v in sol.t], "temperature": temps, "z": zs}
    return ReactorSolution(flows, temps[-1], extents, profile)
