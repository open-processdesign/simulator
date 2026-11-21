"""Gas-phase equilibrium reactor (T18).

For each reaction k, the equilibrium constant follows from standard ideal-gas formation
properties (P° = 1 bar):

    ln K_k(T) = −ΔG°_k(T) / (R·T),
    ΔG°_k(T) = Σ_i ν_ik [ΔHf°_i + ∫₂₉₈ᵀ Cp_i dT] − T Σ_i ν_ik [ΔSf°_i + ∫₂₉₈ᵀ Cp_i/T dT]

and the outlet satisfies Σ_i ν_ik ln(y_i φ_i P / P°) = ln K_k(T) for every reaction, with φ_i
from the gas model of the property package (φ = 1 for Ideal and NRTL). Smith, Van Ness &
Abbott, *Introduction to Chemical Engineering Thermodynamics*, ch. 14.

One reaction is solved by bisection on its extent (always bracketed by the bounds that keep
all flows non-negative); several reactions by `scipy.optimize.least_squares` started from
the one-at-a-time solutions. With a duty instead of a temperature, the outlet temperature is
found by Brent's method on the energy balance.
"""

from __future__ import annotations

import math
from typing import Any, Callable

R_GAS = 8.314462618
P_REF = 1e5
_EPS = 1e-14


class EquilibriumError(Exception):
    def __init__(self, code: str, **params: Any) -> None:
        super().__init__(code)
        self.code = code
        self.params = params


def ln_k(th: Any, nu: list[float], T: float) -> float:
    """ln K(T) from ideal-gas formation enthalpy/entropy and Cp integrals (`thermo` data)."""
    dG = 0.0
    for n, hf, sf, cp in zip(nu, th.constants.Hfgs, th.constants.Sfgs, th.props.HeatCapacityGases):
        if not n:
            continue
        if hf is None or sf is None:
            raise EquilibriumError("missing_formation_data")
        dH = cp.T_dependent_property_integral(298.15, T)
        dS = cp.T_dependent_property_integral_over_T(298.15, T)
        dG += n * ((hf + dH) - T * (sf + dS))
    return -dG / (R_GAS * T)


def _extent_bounds(flows: list[float], nu: list[float]) -> tuple[float, float]:
    lo, hi = -math.inf, math.inf
    for f, n in zip(flows, nu):
        if n > 0:
            lo = max(lo, -f / n)
        elif n < 0:
            hi = min(hi, f / -n)
    return lo, hi


def solve_equilibrium(th: Any, nus: list[list[float]], flows_in: list[float], P: float,
                      T: float) -> list[float]:
    """Extents (mol/s) at temperature T and pressure P."""
    gas = th.flasher.gas
    lnKs = [ln_k(th, nu, T) for nu in nus]

    def flows_of(xi: list[float]) -> list[float]:
        return [f + sum(nu[i] * x for nu, x in zip(nus, xi)) for i, f in enumerate(flows_in)]

    def residuals(xi: list[float]) -> list[float]:
        flows = [max(f, _EPS * max(sum(flows_in), 1.0)) for f in flows_of(xi)]
        F = sum(flows)
        y = [f / F for f in flows]
        lnphi = gas.to(T=T, P=P, zs=y).lnphis()
        lna = [math.log(yi) + lp + math.log(P / P_REF) for yi, lp in zip(y, lnphi)]
        return [sum(n * a for n, a in zip(nu, lna)) - lk for nu, lk in zip(nus, lnKs)]

    def single(k: int, base: list[float]) -> float:
        """Bisection for reaction k with the other extents fixed (residual rises with ξ_k)."""
        start = flows_of(base)
        lo, hi = _extent_bounds(start, nus[k])
        if not (math.isfinite(lo) and math.isfinite(hi)) or hi <= lo:
            raise EquilibriumError("equilibrium_no_reactant", reaction=k + 1)
        span = hi - lo
        a, b = lo + 1e-15 * span, hi - 1e-15 * span
        for _ in range(200):
            mid = 0.5 * (a + b)
            xi = list(base)
            xi[k] = base[k] + mid
            if residuals(xi)[k] > 0:
                b = mid
            else:
                a = mid
            if b - a < 1e-13 * span:
                break
        return base[k] + 0.5 * (a + b)

    xi = [0.0] * len(nus)
    for k in range(len(nus)):
        xi[k] = single(k, xi)
    if len(nus) > 1:
        from scipy.optimize import least_squares

        for _ in range(3):  # a few Gauss–Seidel sweeps give a good start
            for k in range(len(nus)):
                xi[k] = single(k, xi)
        sol = least_squares(residuals, xi, xtol=1e-14, ftol=1e-14, gtol=1e-14)
        xi = [float(v) for v in sol.x]
    if max(abs(r) for r in residuals(xi)) > 1e-8 or min(flows_of(xi)) < -1e-9 * sum(flows_in):
        raise EquilibriumError("equilibrium_not_converged")
    return xi


def solve_adiabatic(energy_residual: Callable[[float], float], T_in: float) -> float:
    """Outlet temperature where the energy balance closes: bracket outward from the inlet
    temperature (the residual rises with T), then Brent's method."""
    from scipy.optimize import brentq

    f0 = energy_residual(T_in)
    if f0 == 0:
        return T_in
    direction = 1.0 if f0 < 0 else -1.0
    a, fa, step = T_in, f0, 25.0
    for _ in range(60):
        b = a + direction * step
        if b < 100.0 or b > 6000.0:
            break
        fb = energy_residual(b)
        if fa * fb <= 0:
            lo, hi = (a, b) if a < b else (b, a)
            return brentq(energy_residual, lo, hi, xtol=1e-9)
        a, fa, step = b, fb, step * 1.5
    raise EquilibriumError("equilibrium_not_converged")
