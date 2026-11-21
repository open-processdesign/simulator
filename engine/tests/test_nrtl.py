"""NRTL in the reference engine (T12), checked against experimental VLE at 101.325 kPa.

Methanol–water (x, y, T) points: Perry's Chemical Engineers' Handbook, VLE data for
methanol–water at 1 atm (also reprinted in McCabe, Smith & Harriott, *Unit Operations of
Chemical Engineering*). Ethanol–water azeotrope: x = 0.894 at 78.15 °C (CRC Handbook of
Chemistry and Physics, azeotrope table).
"""

from __future__ import annotations

import pytest

pytest.importorskip("thermo")

from opd_engine import adapter, runtime  # noqa: E402
from opd_engine.adapters.reference import ReferenceAdapter  # noqa: E402

ENGINE = ReferenceAdapter()
MW = [{"id": "methanol", "name": "methanol", "cas": "67-56-1"}, {"id": "water", "name": "water", "cas": "7732-18-5"}]
EW = [{"id": "ethanol", "name": "ethanol", "cas": "64-17-5"}, {"id": "water", "name": "water", "cas": "7732-18-5"}]


def q(v, u):
    return {"value": v, "unit": u}


def bubble(comps, x: dict, package="NRTL", P=101325.0, params=None):
    """Bubble point via a flash at a small vapour fraction (0.001): returns (T, y)."""
    doc = {
        "format": "opd-flowsheet", "version": "0.1", "name": "vle", "components": comps,
        "thermo": {"package": package, "binary_parameters": params or []},
        "units": [{"id": "F", "type": "feed"},
                  {"id": "D", "type": "flash", "specs": {"pressure": q(P, "Pa"), "vapor_fraction": q(1e-3, "1")}},
                  {"id": "V", "type": "product"}, {"id": "L", "type": "product"}],
        "streams": [
            {"id": "S1", "from": {"unit": "F", "port": "out"}, "to": {"unit": "D", "port": "in"},
             "state": {"temperature": q(300.0, "K"), "pressure": q(P, "Pa"), "molar_flow": q(1.0, "mol/s"), "mole_fractions": x}},
            {"id": "S2", "from": {"unit": "D", "port": "vapor"}, "to": {"unit": "V", "port": "in"}},
            {"id": "S3", "from": {"unit": "D", "port": "liquid"}, "to": {"unit": "L", "port": "in"}},
        ],
    }
    result = ENGINE.simulate(doc)
    assert result.converged, [i for i in result.issues if i.severity is adapter.Severity.ERROR]
    vap = result.document["results"]["streams"]["S2"]
    return vap["temperature"]["value"], vap.get("mole_fractions"), result  # none if no vapour


@pytest.mark.parametrize("x,y,t_c", [(0.10, 0.418, 87.7), (0.30, 0.665, 78.0), (0.50, 0.779, 73.1), (0.80, 0.915, 67.6)])
def test_methanol_water_matches_experiment(x, y, t_c):
    T, ys, result = bubble(MW, {"methanol": x, "water": 1 - x})
    assert T == pytest.approx(t_c + 273.15, abs=0.7)
    assert ys["methanol"] == pytest.approx(y, abs=0.02)
    assert not [i for i in result.issues if i.code == "missing_binary_parameter"]


def test_nrtl_is_clearly_better_than_raoult_for_methanol_water():
    t_nrtl, y_nrtl, _ = bubble(MW, {"methanol": 0.1, "water": 0.9})
    t_ideal, y_ideal, _ = bubble(MW, {"methanol": 0.1, "water": 0.9}, package="IDEAL")
    assert abs(y_nrtl["methanol"] - 0.418) < 0.02 < abs(y_ideal["methanol"] - 0.418)
    assert abs(t_nrtl - 360.85) < 0.7 < abs(t_ideal - 360.85)


def test_ethanol_water_minimum_boiling_azeotrope():
    T, _, _ = bubble(EW, {"ethanol": 0.894, "water": 0.106})
    assert T == pytest.approx(78.15 + 273.15, abs=0.6)
    _, below, _ = bubble(EW, {"ethanol": 0.80, "water": 0.20})
    _, above, _ = bubble(EW, {"ethanol": 0.96, "water": 0.04})
    assert below["ethanol"] > 0.80  # left of the azeotrope ethanol is enriched in the vapour
    assert above["ethanol"] < 0.96  # right of it, the vapour is leaner: y < x


def test_parameter_sources_and_user_override():
    rows = runtime.binary_parameters({"components": MW, "thermo": {"package": "NRTL"}})
    assert [(r["i"], r["j"], r["name"], r["source"]) for r in rows] == [
        ("methanol", "water", "nrtl_b", "database"),
        ("water", "methanol", "nrtl_b", "database"),
        ("methanol", "water", "nrtl_alpha", "database"),
    ]
    user = [{"i": "methanol", "j": "water", "name": "nrtl_b", "value": 0.0, "source": "user"},
            {"i": "water", "j": "methanol", "name": "nrtl_b", "value": 0.0, "source": "user"}]
    rows = runtime.binary_parameters({"components": MW, "thermo": {"package": "NRTL", "binary_parameters": user}})
    assert [r["source"] for r in rows] == ["user", "user", "database"]
    # τ = 0 makes NRTL ideal: the bubble point equals Raoult's law.
    T_user, _, _ = bubble(MW, {"methanol": 0.3, "water": 0.7}, params=user)
    T_ideal, _, _ = bubble(MW, {"methanol": 0.3, "water": 0.7}, package="IDEAL")
    assert T_user == pytest.approx(T_ideal, abs=1e-3)


def test_missing_pair_is_ideal_with_a_warning():
    comps = [{"id": "benzene", "name": "benzene", "cas": "71-43-2"}, {"id": "hexane", "name": "hexane", "cas": "110-54-3"},
             {"id": "nitrogen", "name": "nitrogen", "cas": "7727-37-9"}]
    rows = runtime.binary_parameters({"components": comps, "thermo": {"package": "NRTL"}})
    missing = {(r["i"], r["j"]) for r in rows if r["source"] == "missing" and r["name"] == "nrtl_alpha"}
    assert ("benzene", "nitrogen") in missing
    _, _, result = bubble(comps, {"benzene": 0.5, "hexane": 0.49, "nitrogen": 0.01})
    warned = {(i.params["i"], i.params["j"]) for i in result.issues if i.code == "missing_binary_parameter"}
    assert ("benzene", "nitrogen") in warned
