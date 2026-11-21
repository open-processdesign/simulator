"""Rigorous equilibrium-stage distillation column (T15).

Bubble-point (BP) method of Wang and Henke, *Hydrocarbon Processing* 45(8):155 (1966), as
presented in Seader, Henley & Roper, *Separation Process Principles*, 3rd ed., Wiley (2011),
§10.3. Stage 1 is a total condenser, stage N a partial reboiler; one feed; uniform pressure;
specifications: number of stages, feed stage, reflux ratio L₁/D and distillate rate D.

Each iteration:

1. K_ij from the property package at (T_j, P, x_j, y_j): K = φ_L / φ_V (equation of
   state) or γ·Psat/P (activity model), through `thermo` phase objects.
2. Component balances: one tridiagonal system per component (Thomas algorithm) for the
   liquid compositions, with total flows from the current vapour profile.
3. New stage temperatures from bubble points of the normalised x_j; y_j at the same time.
4. Condenser and reboiler duties and a new vapour profile from the stage energy balances.

A θ-method correction (Holland, *Fundamentals and Modeling of Separation Processes*,
Prentice-Hall, 1975) makes the computed distillate match its specification each iteration.
Converged when the stage temperatures and vapour flows stop changing. (Element-wise
Wegstein acceleration was tried and rejected: it diverged on a non-ideal NRTL column; the
θ-method alone brings high-reflux columns from ~350 to ~15 iterations.)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


class ColumnError(Exception):
    """Input that makes the column infeasible or a solver failure; `code` is an issue code."""

    def __init__(self, code: str, **params: Any) -> None:
        super().__init__(code)
        self.code = code
        self.params = params


@dataclass
class ColumnResult:
    T: list[float]  # stage temperatures, K (stage 1 = condenser)
    L: list[float]  # liquid leaving each stage, mol/s (L[0] = reflux, L[-1] = bottoms)
    V: list[float]  # vapour leaving each stage, mol/s (V[0] = 0, total condenser)
    x: list[list[float]]
    y: list[list[float]]
    HL: list[float]  # J/mol
    HV: list[float]
    D: float
    B: float
    Qc: float  # condenser duty, W (negative: heat removed)
    Qr: float  # reboiler duty, W
    iterations: int


def _thomas(a: list[float], b: list[float], c: list[float], d: list[float]) -> list[float]:
    """Solve a tridiagonal system (a: sub-, b: main, c: super-diagonal)."""
    n = len(b)
    cp, dp = [0.0] * n, [0.0] * n
    cp[0], dp[0] = c[0] / b[0], d[0] / b[0]
    for j in range(1, n):
        m = b[j] - a[j] * cp[j - 1]
        cp[j] = c[j] / m if j < n - 1 else 0.0
        dp[j] = (d[j] - a[j] * dp[j - 1]) / m
    out = [0.0] * n
    out[-1] = dp[-1]
    for j in range(n - 2, -1, -1):
        out[j] = dp[j] - cp[j] * out[j + 1]
    return out


def solve_column(th: Any, z: list[float], F: float, H_feed: float, P: float, n_stages: int,
                 feed_stage: int, reflux_ratio: float, D: float, max_iterations: int = 300,
                 tol_T: float = 1e-5, tol_V: float = 1e-7) -> ColumnResult:
    """Solve the column. `th` provides `flasher.liquid`, `flasher.gas` and `flash_raw`."""
    N, f = n_stages, feed_stage - 1  # f: 0-based feed stage
    nc = len(z)
    B = F - D
    if not 0 < D < F:
        raise ColumnError("column_distillate_rate", D=D, F=F)
    liquid, gas = th.flasher.liquid, th.flasher.gas

    # Initial guess: temperatures between the feed's bubble and dew points, constant molal overflow.
    Tb = th.flash_raw(z, P=P, VF=0.0).T
    Td = th.flash_raw(z, P=P, VF=1.0).T
    T = [Tb - 5 + (Td - Tb + 10) * j / (N - 1) for j in range(N)]
    Lr = reflux_ratio * D
    V = [0.0] + [Lr + D] * (N - 1)
    x = [list(z) for _ in range(N)]
    y = [list(z) for _ in range(N)]
    feed = [0.0] * N
    feed[f] = F

    def totals(V: list[float]) -> list[float]:
        """Liquid flows from the vapour profile and the overall balance above each stage."""
        L, cum = [0.0] * N, 0.0
        for j in range(N):
            cum += feed[j] - (D if j == 0 else 0.0)
            L[j] = (V[j + 1] if j + 1 < N else 0.0) + cum - V[0]
        return L

    HL, HV = [0.0] * N, [0.0] * N
    Qc = Qr = 0.0
    for it in range(1, max_iterations + 1):
        L = totals(V)
        if min(L) <= 0 or min(V[1:]) <= 0:
            raise ColumnError("column_not_converged", iterations=it, reason="negative flow")
        # 1. K-values at the current profile.
        K = []
        for j in range(N):
            lp = liquid.to(T=T[j], P=P, zs=x[j])
            gp = gas.to(T=T[j], P=P, zs=y[j])
            K.append([math.exp(a - b) for a, b in zip(lp.lnphis(), gp.lnphis())])
        # 2. Component balances (stage j: L_{j-1} x_{j-1} + V_{j+1} y_{j+1} + F z = (L_j + U_j) x_j + V_j y_j).
        xs_new = [[0.0] * nc for _ in range(N)]
        for i in range(nc):
            a = [L[j - 1] if j > 0 else 0.0 for j in range(N)]
            b = [-((L[j] + (D if j == 0 else 0.0)) + V[j] * K[j][i]) for j in range(N)]
            c = [V[j + 1] * K[j + 1][i] if j + 1 < N else 0.0 for j in range(N)]
            d = [-feed[j] * z[i] for j in range(N)]
            col = _thomas(a, b, c, d)
            for j in range(N):
                xs_new[j][i] = max(col[j], 0.0)
        # θ-method correction (Holland): scale each component's profile so that the computed
        # distillate flows satisfy the distillate-rate specification exactly.
        d_ca = [D * xs_new[0][i] for i in range(nc)]
        b_ca = [L[N - 1] * xs_new[N - 1][i] for i in range(nc)]
        if all(dv > 0 for dv in d_ca):
            ratio = [b_ca[i] / d_ca[i] for i in range(nc)]

            def excess(theta: float) -> float:
                return sum(F * z[i] / (1 + theta * ratio[i]) for i in range(nc)) - D

            lo_t, hi_t = 1e-10, 1e10
            if excess(lo_t) > 0 > excess(hi_t):
                for _ in range(200):  # bisection in log space
                    mid = math.sqrt(lo_t * hi_t)
                    if excess(mid) > 0:
                        lo_t = mid
                    else:
                        hi_t = mid
                theta = math.sqrt(lo_t * hi_t)
                for i in range(nc):
                    factor = (F * z[i] / (1 + theta * ratio[i])) / d_ca[i]
                    for j in range(N):
                        xs_new[j][i] *= factor
        # 3. Bubble points of the normalised compositions → T_j, y_j.
        T_new = []
        for j in range(N):
            s = sum(xs_new[j])
            x[j] = [v / s for v in xs_new[j]]
            res = th.flash_raw(x[j], P=P, VF=0.0)
            T_new.append(res.T)
            y[j] = list(res.gas.zs) if res.gas is not None else list(x[j])
        dT = max(abs(a - b) for a, b in zip(T_new, T))
        T = T_new
        # 4. Enthalpies, duties and the new vapour profile from the energy balances.
        for j in range(N):
            HL[j] = liquid.to(T=T[j], P=P, zs=x[j]).H()
            HV[j] = gas.to(T=T[j], P=P, zs=y[j]).H()
        V_new = [0.0] * N
        V_new[1] = Lr + D
        cum = 0.0  # Σ_{m<j}(F_m − U_m), with U_1 = D
        for j in range(1, N - 1):  # balance of stage j (0-based) gives V_{j+1}
            cum += feed[j - 1] - (D if j - 1 == 0 else 0.0)
            alpha = HL[j - 1] - HV[j]
            beta = HV[j + 1] - HL[j]
            gamma = cum * (HL[j] - HL[j - 1]) + feed[j] * (HL[j] - H_feed)
            V_new[j + 1] = (gamma - alpha * V_new[j]) / beta
        dV = max(abs(a - b) / max(abs(b), 1e-12) for a, b in zip(V_new[1:], V[1:]))
        V = V_new
        if dT < tol_T and dV < tol_V:
            L = totals(V)
            Qc = -V[1] * HV[1] + (L[0] + D) * HL[0]
            Qr = D * HL[0] + B * HL[N - 1] - F * H_feed - Qc
            return ColumnResult(T, L, V, x, y, HL, HV, D, B, Qc, Qr, it)
    raise ColumnError("column_not_converged", iterations=max_iterations, reason="iteration limit")
