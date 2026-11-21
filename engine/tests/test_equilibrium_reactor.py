"""Gas-phase equilibrium reactor (T18).

Water–gas shift CO + H2O ⇌ CO2 + H2: K(T) from `thermo` formation data vs. the Moe (1962)
correlation K = exp(4577.8/T − 4.33) (e.g. quoted in Smith, Van Ness & Abbott and in
Twigg, *Catalyst Handbook*), and K = 1 near 1100 K. Ammonia synthesis: higher pressure gives
more NH3 (Le Chatelier); WGS (Δn = 0) does not depend on pressure.
"""

from __future__ import annotations

import math

import pytest

pytest.importorskip("thermo")

from opd_engine import adapter  # noqa: E402
from opd_engine.adapters.equilibrium import ln_k  # noqa: E402
from opd_engine.adapters.reference import ReferenceAdapter, _Thermo  # noqa: E402
from opd_engine.models import load  # noqa: E402

ENGINE = ReferenceAdapter()
WGS = [{"id": "co", "name": "carbon monoxide", "cas": "630-08-0"}, {"id": "h2o", "name": "water", "cas": "7732-18-5"},
       {"id": "co2", "name": "carbon dioxide", "cas": "124-38-9"}, {"id": "h2", "name": "hydrogen", "cas": "1333-74-0"}]
WGS_RXN = {"stoichiometry": {"co": -1, "h2o": -1, "co2": 1, "h2": 1}}
NH3 = [{"id": "n2", "name": "nitrogen", "cas": "7727-37-9"}, {"id": "h2", "name": "hydrogen", "cas": "1333-74-0"},
       {"id": "nh3", "name": "ammonia", "cas": "7664-41-7"}]
NH3_RXN = {"stoichiometry": {"n2": -1, "h2": -3, "nh3": 2}}


def q(v, u):
    return {"value": v, "unit": u}


def doc(comps, rxns, z, specs, T=600.0, P=1e5, F=10.0, package="IDEAL"):
    return {
        "format": "opd-flowsheet", "version": "0.1", "name": "eq", "components": comps, "thermo": {"package": package},
        "units": [{"id": "FEED", "type": "feed"},
                  {"id": "R-1", "type": "equilibrium_reactor", "specs": specs, "options": {"reactions": rxns}},
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
    return result.document["results"]


@pytest.mark.parametrize("T", [600.0, 700.0, 800.0])
def test_wgs_equilibrium_constant_matches_moe_correlation(T):
    th = _Thermo(load(doc(WGS, [WGS_RXN], {"co": 0.5, "h2o": 0.5}, {"temperature": q(T, "K")})))
    assert math.exp(ln_k(th, [-1, -1, 1, 1], T)) == pytest.approx(math.exp(4577.8 / T - 4.33), rel=0.06)


def test_wgs_equilibrium_crosses_one_near_1100_k():
    th = _Thermo(load(doc(WGS, [WGS_RXN], {"co": 0.5, "h2o": 0.5}, {"temperature": q(1000.0, "K")})))
    assert ln_k(th, [-1, -1, 1, 1], 1050.0) > 0 > ln_k(th, [-1, -1, 1, 1], 1150.0)


def test_outlet_satisfies_the_equilibrium_condition_and_is_pressure_independent_for_wgs():
    z = {"co": 0.4, "h2o": 0.6, "co2": 0.0, "h2": 0.0}
    res1 = solve(doc(WGS, [WGS_RXN], z, {"temperature": q(700.0, "K")}, T=700.0, P=1e5))
    y = res1["streams"]["S2"]["mole_fractions"]
    K = res1["units"]["R-1"]["equilibrium_constant_1"]["value"]
    assert y["co2"] * y["h2"] / (y["co"] * y["h2o"]) == pytest.approx(K, rel=1e-7)
    # Element balance: C, H, O conserved.
    F1 = res1["streams"]["S2"]["molar_flow"]["value"]
    assert F1 * (y["co"] + y["co2"]) == pytest.approx(10 * 0.4, rel=1e-9)
    assert F1 * (2 * y["h2o"] + 2 * y["h2"]) == pytest.approx(10 * 2 * 0.6, rel=1e-9)
    res10 = solve(doc(WGS, [WGS_RXN], z, {"temperature": q(700.0, "K")}, T=700.0, P=1e6))
    assert res10["units"]["R-1"]["extent_1"]["value"] == pytest.approx(res1["units"]["R-1"]["extent_1"]["value"], rel=1e-7)


def test_ammonia_more_pressure_more_product():
    z = {"n2": 0.25, "h2": 0.75, "nh3": 0.0}
    ext = [solve(doc(NH3, [NH3_RXN], z, {"temperature": q(700.0, "K")}, T=700.0, P=P))["units"]["R-1"]["extent_1"]["value"]
           for P in (1e6, 1e7)]
    assert 0 < ext[0] < ext[1] < 2.5


def test_adiabatic_equilibrium_closes_the_energy_balance():
    z = {"co": 0.4, "h2o": 0.6, "co2": 0.0, "h2": 0.0}
    res = solve(doc(WGS, [WGS_RXN], z, {"duty": q(0.0, "W")}, T=600.0))
    T = res["units"]["R-1"]["temperature"]["value"]
    assert T > 600.0  # WGS is exothermic
    assert res["units"]["R-1"]["duty"]["value"] == pytest.approx(0.0, abs=1e-3)
    # The adiabatic outlet is in equilibrium at its own temperature.
    iso = solve(doc(WGS, [WGS_RXN], z, {"temperature": q(T, "K")}, T=600.0))
    assert iso["units"]["R-1"]["extent_1"]["value"] == pytest.approx(res["units"]["R-1"]["extent_1"]["value"], rel=1e-6)


def test_two_simultaneous_reactions():
    comps = WGS + [{"id": "ch4", "name": "methane", "cas": "74-82-8"}]
    smr = {"stoichiometry": {"ch4": -1, "h2o": -1, "co": 1, "h2": 3}}
    z = {"ch4": 0.25, "h2o": 0.75, "co": 0.0, "co2": 0.0, "h2": 0.0}
    res = solve(doc(comps, [smr, WGS_RXN], z, {"temperature": q(1000.0, "K")}, T=1000.0, P=2e5))
    y = res["streams"]["S2"]["mole_fractions"]
    P = 2.0  # bar
    K1 = res["units"]["R-1"]["equilibrium_constant_1"]["value"]
    K2 = res["units"]["R-1"]["equilibrium_constant_2"]["value"]
    assert y["co"] * y["h2"] ** 3 * P ** 2 / (y["ch4"] * y["h2o"]) == pytest.approx(K1, rel=1e-6)
    assert y["co2"] * y["h2"] / (y["co"] * y["h2o"]) == pytest.approx(K2, rel=1e-6)
