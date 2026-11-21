"""CSTR and PFR with power-law kinetics (T17), checked against closed-form solutions.

First-order isomerization n-butane → isobutane in the ideal-gas phase at constant T and P:
the volumetric flow v0 = F·R·T/P is constant (equimolar), so with τ = V/v0
    CSTR: X = kτ / (1 + kτ)        PFR: X = 1 − exp(−kτ)
(Fogler, *Elements of Chemical Reaction Engineering*, ch. 5). Second order in a CSTR gives
kC0τ(1 − X)² = X. Energy: an adiabatic PFR ends at the same temperature as an adiabatic
conversion reactor with the same conversion (same formation-enthalpy balance).
"""

from __future__ import annotations

import math

import pytest

pytest.importorskip("thermo")

from opd_engine import adapter  # noqa: E402
from opd_engine.adapters.reference import ReferenceAdapter  # noqa: E402

ENGINE = ReferenceAdapter()
R = 8.314462618
C4 = [{"id": "nbutane", "name": "n-butane", "cas": "106-97-8"}, {"id": "ibutane", "name": "isobutane", "cas": "75-28-5"}]
ISOM = {"stoichiometry": {"nbutane": -1, "ibutane": 1}, "k0": 0.5, "Ea": 0.0, "orders": {"nbutane": 1}}


def q(v, u):
    return {"value": v, "unit": u}


def reactor_doc(kind, specs, reactions, comps=C4, z=None, T=400.0, P=2e5, F=1.0, package="IDEAL", phase="gas"):
    z = z or {"nbutane": 1.0, "ibutane": 0.0}
    return {
        "format": "opd-flowsheet", "version": "0.1", "name": "kin", "components": comps, "thermo": {"package": package},
        "units": [{"id": "FEED", "type": "feed"},
                  {"id": "R-1", "type": kind, "specs": specs, "options": {"phase": phase, "reactions": reactions}},
                  {"id": "P", "type": "product"}],
        "streams": [
            {"id": "S1", "from": {"unit": "FEED", "port": "out"}, "to": {"unit": "R-1", "port": "in"},
             "state": {"temperature": q(T, "K"), "pressure": q(P, "Pa"), "molar_flow": q(F, "mol/s"), "mole_fractions": z}},
            {"id": "S2", "from": {"unit": "R-1", "port": "out"}, "to": {"unit": "P", "port": "in"}},
        ],
    }


def solve(doc):
    result = ENGINE.simulate(doc)
    assert result.converged, [i for i in result.issues if i.severity is adapter.Severity.ERROR]
    return result.document["results"]


def conversion(res):
    return res["streams"]["S2"]["mole_fractions"]["ibutane"]


@pytest.mark.parametrize("V", [0.01, 0.05, 0.2])
def test_first_order_cstr_and_pfr_match_closed_form(V):
    T, P, F, k = 400.0, 2e5, 1.0, 0.5
    tau = V / (F * R * T / P)
    cstr = solve(reactor_doc("cstr", {"volume": q(V, "m3"), "temperature": q(T, "K")}, [ISOM]))
    pfr = solve(reactor_doc("pfr", {"volume": q(V, "m3"), "temperature": q(T, "K")}, [ISOM]))
    assert conversion(cstr) == pytest.approx(k * tau / (1 + k * tau), rel=1e-6)
    assert conversion(pfr) == pytest.approx(1 - math.exp(-k * tau), rel=1e-6)
    assert cstr["units"]["R-1"]["space_time"]["value"] == pytest.approx(tau, rel=1e-9)
    assert cstr["units"]["R-1"]["extent_1"]["value"] == pytest.approx(F * conversion(cstr), rel=1e-6)
    # A PFR always beats a CSTR of the same volume for a positive-order reaction.
    assert conversion(pfr) > conversion(cstr)


def test_second_order_cstr():
    T, P, F, k, V = 400.0, 2e5, 1.0, 2e-3, 0.05
    law = dict(ISOM, k0=k, orders={"nbutane": 2})
    res = solve(reactor_doc("cstr", {"volume": q(V, "m3"), "temperature": q(T, "K")}, [law]))
    X = conversion(res)
    C0, tau = P / (R * T), V / (F * R * T / P)
    assert k * C0 * tau * (1 - X) ** 2 == pytest.approx(X, rel=1e-6)


def test_arrhenius_temperature_dependence():
    law = dict(ISOM, k0=0.5 * math.exp(50e3 / (R * 400.0)), Ea=50e3)  # k(400 K) = 0.5 s⁻¹
    base = conversion(solve(reactor_doc("pfr", {"volume": q(0.05, "m3"), "temperature": q(400.0, "K")}, [ISOM])))
    same = conversion(solve(reactor_doc("pfr", {"volume": q(0.05, "m3"), "temperature": q(400.0, "K")}, [law])))
    hotter = conversion(solve(reactor_doc("pfr", {"volume": q(0.05, "m3"), "temperature": q(420.0, "K")}, [law])))
    assert same == pytest.approx(base, rel=1e-6)
    assert hotter > same


HDA = [{"id": "toluene", "name": "toluene", "cas": "108-88-3"}, {"id": "hydrogen", "name": "hydrogen", "cas": "1333-74-0"},
       {"id": "benzene", "name": "benzene", "cas": "71-43-2"}, {"id": "methane", "name": "methane", "cas": "74-82-8"}]


def test_adiabatic_pfr_energy_balance_matches_conversion_reactor():
    feed = {"toluene": 0.2, "hydrogen": 0.8, "benzene": 0.0, "methane": 0.0}
    law = {"stoichiometry": {"toluene": -1, "hydrogen": -1, "benzene": 1, "methane": 1}, "k0": 1e-3, "Ea": 0.0,
           "orders": {"toluene": 1, "hydrogen": 0.5}}
    pfr = solve(reactor_doc("pfr", {"volume": q(1.0, "m3"), "duty": q(0.0, "W")}, [law], comps=HDA, z=feed,
                            T=900.0, P=3e6, F=10.0, package="PR"))
    X = pfr["units"]["R-1"]["extent_1"]["value"] / (10.0 * 0.2)
    assert 0.05 < X < 0.99
    conv = solve(reactor_doc("conversion_reactor", {"duty": q(0.0, "W")},
                             [{"stoichiometry": law["stoichiometry"], "key": "toluene", "conversion": X}],
                             comps=HDA, z=feed, T=900.0, P=3e6, F=10.0, package="PR"))
    assert pfr["units"]["R-1"]["temperature"]["value"] == pytest.approx(conv["units"]["R-1"]["temperature"]["value"], abs=1e-3)
    assert pfr["units"]["R-1"]["duty"]["value"] == pytest.approx(0.0, abs=1e-3)
    prof = pfr["profiles"]["R-1"]
    assert prof["axis"]["name"] == "volume" and len(prof["axis"]["values"]) == 21
    temps = prof["series"]["temperature"]["values"]
    assert temps[0] == pytest.approx(900.0, abs=1e-6) and all(b >= a - 1e-9 for a, b in zip(temps, temps[1:]))  # exothermic


def test_kinetics_input_errors():
    doc = reactor_doc("cstr", {"temperature": q(400.0, "K")}, [dict(ISOM, k0=-1)])
    assert sorted((i.code, i.params.get("spec")) for i in ENGINE.validate(doc)) == [
        ("missing_spec", "volume"), ("out_of_range", "k0 1")]
    doc = reactor_doc("pfr", {"volume": q(1.0, "m3"), "temperature": q(400.0, "K")}, [ISOM], phase="plasma")
    assert [i.code for i in ENGINE.validate(doc)] == ["invalid_option"]
