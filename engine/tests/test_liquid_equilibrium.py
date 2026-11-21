"""Liquid-phase equilibrium reactor (T23).

- Ideal liquid isomerisation A ⇌ B: x_B/x_A = K_a exactly; from formation data
  K_a = K_ig · Psat_A/Psat_B (pure-liquid standard state, ideal vapour).
- MTBE synthesis (isobutene + methanol ⇌ MTBE): K_a from `thermo` formation data against the
  recommended correlation ln K = 4703/T − 10.3 (Izquierdo et al., quoted by Badia et al.,
  J. Chem. Eng. Data 2016) and ΔrH° = −37 ± 10 kJ/mol from the same work.
- Non-ideal liquid (NRTL): the outlet satisfies Π (x_i γ_i)^ν_i = K_a with γ from the model.
"""

from __future__ import annotations

import math

import pytest

pytest.importorskip("thermo")

from opd_engine import adapter  # noqa: E402
from opd_engine.adapters.equilibrium import phase_ln_k  # noqa: E402
from opd_engine.adapters.reference import ReferenceAdapter, _Thermo  # noqa: E402
from opd_engine.models import load  # noqa: E402

ENGINE = ReferenceAdapter()
ISO = [{"id": "chx", "name": "cyclohexane", "cas": "110-82-7"}, {"id": "mcp", "name": "methylcyclopentane", "cas": "96-37-7"}]
ISO_NU = {"chx": -1, "mcp": 1}
MTBE = [{"id": "ib", "name": "isobutene", "cas": "115-11-7"}, {"id": "meoh", "name": "methanol", "cas": "67-56-1"},
        {"id": "mtbe", "name": "MTBE", "cas": "1634-04-4"}]
MTBE_NU = {"ib": -1, "meoh": -1, "mtbe": 1}
IZQUIERDO = {"a": -10.3, "b": 4703.0}


def q(v, u):
    return {"value": v, "unit": u}


def doc(comps, rxns, z, specs, T, P, package="IDEAL", phase="liquid", F=10.0):
    return {
        "format": "opd-flowsheet", "version": "0.1", "name": "liq-eq", "components": comps,
        "thermo": {"package": package},
        "units": [{"id": "FEED", "type": "feed"},
                  {"id": "R-1", "type": "equilibrium_reactor", "specs": specs,
                   "options": {"phase": phase, "reactions": rxns}},
                  {"id": "P", "type": "product"}],
        "streams": [
            {"id": "S1", "from": {"unit": "FEED", "port": "out"}, "to": {"unit": "R-1", "port": "in"},
             "state": {"temperature": q(T, "K"), "pressure": q(P, "Pa"), "molar_flow": q(F, "mol/s"), "mole_fractions": z}},
            {"id": "S2", "from": {"unit": "R-1", "port": "out"}, "to": {"unit": "P", "port": "in"}},
        ],
    }


def solve(d):
    result = ENGINE.simulate(d)
    assert result.converged, [i for i in result.issues if i.severity is adapter.Severity.ERROR]
    return result.document["results"], result


def test_ideal_isomerisation_with_user_k():
    d = doc(ISO, [{"stoichiometry": ISO_NU, "ln_k": {"a": math.log(3.0)}}], {"chx": 1.0, "mcp": 0.0},
            {"temperature": q(300.0, "K")}, 300.0, 101325.0)
    res, _ = solve(d)
    x = res["streams"]["S2"]["mole_fractions"]
    assert x["mcp"] / x["chx"] == pytest.approx(3.0, rel=1e-8)
    assert res["units"]["R-1"]["equilibrium_constant_1"]["value"] == pytest.approx(3.0)


def test_ideal_isomerisation_from_formation_data_uses_pure_liquid_standard_state():
    T = 320.0
    d = doc(ISO, [{"stoichiometry": ISO_NU}], {"chx": 1.0, "mcp": 0.0}, {"temperature": q(T, "K")}, T, 101325.0)
    th = _Thermo(load(d))
    k_gas = math.exp(phase_ln_k(th, [-1, 1], T, 101325.0, "gas", None))
    psat = [p(T) for p in th.props.VaporPressures]
    res, _ = solve(d)
    x = res["streams"]["S2"]["mole_fractions"]
    assert x["mcp"] / x["chx"] == pytest.approx(k_gas * psat[0] / psat[1], rel=1e-6)


@pytest.mark.parametrize("T", [323.15, 343.15])
def test_mtbe_k_from_formation_data_vs_literature(T):
    d = doc(MTBE, [{"stoichiometry": MTBE_NU}], {"ib": 0.5, "meoh": 0.5, "mtbe": 0.0},
            {"temperature": q(T, "K")}, T, 2e6)
    th = _Thermo(load(d))
    ln_k = phase_ln_k(th, [-1, -1, 1], T, 2e6, "liquid", None)
    # Formation data in `thermo` give ΔG° to about ±1.2 kJ/mol here: |Δ ln K| ≤ 0.45.
    assert ln_k == pytest.approx(IZQUIERDO["a"] + IZQUIERDO["b"] / T, abs=0.45)


def test_mtbe_reaction_enthalpy_from_van_t_hoff_within_literature_band():
    d = doc(MTBE, [{"stoichiometry": MTBE_NU}], {"ib": 0.5, "meoh": 0.5, "mtbe": 0.0},
            {"temperature": q(330.0, "K")}, 330.0, 2e6)
    th = _Thermo(load(d))
    t1, t2 = 323.15, 343.15
    k1 = phase_ln_k(th, [-1, -1, 1], t1, 2e6, "liquid", None)
    k2 = phase_ln_k(th, [-1, -1, 1], t2, 2e6, "liquid", None)
    dH = -8.314462618 * (k2 - k1) / (1 / t2 - 1 / t1)
    assert dH == pytest.approx(-37e3, abs=10e3)


def test_nrtl_outlet_satisfies_activity_mass_action():
    T, P = 343.15, 2e6
    d = doc(MTBE, [{"stoichiometry": MTBE_NU, "ln_k": IZQUIERDO}], {"ib": 0.5, "meoh": 0.5, "mtbe": 0.0},
            {"temperature": q(T, "K")}, T, P, package="NRTL")
    res, _ = solve(d)
    x = res["streams"]["S2"]["mole_fractions"]
    xs = [x["ib"], x["meoh"], x["mtbe"]]
    th = _Thermo(load(d))
    gammas = th.flasher.liquid.to(T=T, P=P, zs=xs).gammas()
    a = [xi * g for xi, g in zip(xs, gammas)]
    assert a[2] / (a[0] * a[1]) == pytest.approx(math.exp(IZQUIERDO["a"] + IZQUIERDO["b"] / T), rel=1e-6)
    # Methanol–isobutene is strongly non-ideal: more MTBE than the ideal-liquid answer.
    ideal, _ = solve(doc(MTBE, [{"stoichiometry": MTBE_NU, "ln_k": IZQUIERDO}], {"ib": 0.5, "meoh": 0.5, "mtbe": 0.0},
                         {"temperature": q(T, "K")}, T, P))
    assert x["mtbe"] > ideal["streams"]["S2"]["mole_fractions"]["mtbe"]


def test_liquid_reactor_with_vapour_outlet_warns():
    d = doc(MTBE, [{"stoichiometry": MTBE_NU, "ln_k": IZQUIERDO}], {"ib": 0.5, "meoh": 0.5, "mtbe": 0.0},
            {"temperature": q(343.15, "K")}, 343.15, 1e5)
    _, result = solve(d)
    assert "equilibrium_phase_mismatch" in [i.code for i in result.issues]


@pytest.mark.parametrize("options", [{"phase": "solid"}, {"ln_k": {"x": 1.0}}, {"ln_k": "big"}])
def test_invalid_options_are_reported(options):
    rxn = {"stoichiometry": MTBE_NU}
    phase = "liquid"
    if "phase" in options:
        phase = options["phase"]
    else:
        rxn.update(options)
    d = doc(MTBE, [rxn], {"ib": 0.5, "meoh": 0.5, "mtbe": 0.0}, {"temperature": q(343.15, "K")}, 343.15, 2e6,
            phase=phase)
    assert "invalid_option" in [i.code for i in ENGINE.validate(d)]
