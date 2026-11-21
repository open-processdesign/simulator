"""Pump, compressor, heat exchanger, conversion reactor and shortcut column (T09).

Each test compares engine numbers with an independent calculation: hydraulic power,
ideal-gas isentropic compression, an energy balance, a heat of reaction from tabulated
formation enthalpies, and the closed-form Fenske / Underwood results for a binary.
"""

from __future__ import annotations

import math

import pytest

pytest.importorskip("thermo")

from opd_engine import adapter  # noqa: E402
from opd_engine.adapters.reference import ReferenceAdapter  # noqa: E402

ENGINE = ReferenceAdapter()


def q(v, u):
    return {"value": v, "unit": u}


def st(T, P, F, x, VF=None):
    out = {"pressure": q(P, "Pa"), "molar_flow": q(F, "mol/s"), "mole_fractions": x}
    out.update({"vapor_fraction": q(VF, "1")} if VF is not None else {"temperature": q(T, "K")})
    return out


def one_unit(unit, comps, feeds, outlets, package="PR"):
    """FEED_i → unit → PROD_j. `feeds`: {port: state}; `outlets`: [port]."""
    units, streams = [unit], []
    for k, (port, state) in enumerate(feeds.items()):
        units.append({"id": f"FEED{k}", "type": "feed"})
        streams.append({"id": f"IN{k}", "from": {"unit": f"FEED{k}", "port": "out"},
                        "to": {"unit": unit["id"], "port": port}, "state": state})
    for k, port in enumerate(outlets):
        units.append({"id": f"PROD{k}", "type": "product"})
        streams.append({"id": f"OUT{k}", "from": {"unit": unit["id"], "port": port},
                        "to": {"unit": f"PROD{k}", "port": "in"}})
    return {"format": "opd-flowsheet", "version": "0.1", "name": "t09", "components": comps,
            "thermo": {"package": package}, "units": units, "streams": streams}


def solve(doc):
    result = ENGINE.simulate(doc)
    assert result.converged, [i for i in result.issues if i.severity is adapter.Severity.ERROR]
    return result.document["results"], result


WATER = [{"id": "water", "name": "Water", "cas": "7732-18-5"}]
N2 = [{"id": "n2", "name": "Nitrogen", "cas": "7727-37-9"}]
BT = [{"id": "benzene", "name": "Benzene", "cas": "71-43-2"}, {"id": "toluene", "name": "Toluene", "cas": "108-88-3"}]


def test_pump_power_equals_hydraulic_power_over_efficiency():
    # 1 kg/s of water (55.508 mol/s), ΔP = 10 bar, η = 0.75 → W ≈ ṁ·ΔP/(ρ·η) ≈ 1336 W
    # with ρ(298 K) = 997 kg/m³ (NIST WebBook).
    F = 1000 / 18.01528
    doc = one_unit({"id": "P-1", "type": "pump", "specs": {"pressure_increase": q(1e6, "Pa"), "efficiency": q(0.75, "1")}},
                   WATER, {"in": st(298.15, 101325, F, {"water": 1.0})}, ["out"])
    res, _ = solve(doc)
    power = res["units"]["P-1"]["power"]["value"]
    assert power == pytest.approx(1e6 * 1.0 / 997.0 / 0.75, rel=0.02)
    out = res["streams"]["OUT0"]
    assert out["pressure"]["value"] == pytest.approx(101325 + 1e6)
    assert 298.15 < out["temperature"]["value"] < 298.6  # small heating from pump losses


def test_compressor_matches_ideal_gas_isentropic_relation():
    # N2, 300 K, 1 → 3 bar, ideal gas, η_s = 1: T2 = T1·(P2/P1)^((γ−1)/γ) with γ ≈ 1.40 → 410.6 K.
    doc = one_unit({"id": "C-1", "type": "compressor", "specs": {"pressure": q(3e5, "Pa"), "efficiency": q(1.0, "1")}},
                   N2, {"in": st(300.0, 1e5, 1.0, {"n2": 1.0})}, ["out"], package="IDEAL")
    res, _ = solve(doc)
    T2 = res["units"]["C-1"]["temperature"]["value"]
    assert T2 == pytest.approx(300 * 3 ** (0.4 / 1.4), abs=2.0)
    # Power = F·Cp·ΔT with Cp ≈ 29.2 J/(mol·K) for N2 near 350 K.
    assert res["units"]["C-1"]["power"]["value"] == pytest.approx(29.2 * (T2 - 300), rel=0.02)
    # η_s < 1 gives a hotter outlet and more power at the same isentropic temperature.
    doc["units"][0]["specs"]["efficiency"] = q(0.75, "1")
    res75, _ = solve(doc)
    u = res75["units"]["C-1"]
    assert u["isentropic_temperature"]["value"] == pytest.approx(T2, abs=1e-6)
    assert u["power"]["value"] == pytest.approx(res["units"]["C-1"]["power"]["value"] / 0.75, rel=1e-6)


def test_heat_exchanger_energy_balance_and_cross_detection():
    feeds = {"hot_in": st(400.0, 2e5, 10.0, {"benzene": 0.0, "toluene": 1.0}),
             "cold_in": st(300.0, 2e5, 20.0, {"benzene": 1.0, "toluene": 0.0})}
    doc = one_unit({"id": "E-1", "type": "heat_exchanger", "specs": {"hot_outlet_temperature": q(330.0, "K")}},
                   BT, feeds, ["hot_out", "cold_out"])
    res, _ = solve(doc)
    e = res["units"]["E-1"]
    Q = e["duty"]["value"]
    assert Q > 0
    # Same duty from the cold side: specify the cold outlet the first run produced.
    doc2 = one_unit({"id": "E-1", "type": "heat_exchanger",
                     "specs": {"cold_outlet_temperature": q(e["cold_outlet_temperature"]["value"], "K")}},
                    BT, feeds, ["hot_out", "cold_out"])
    res2, _ = solve(doc2)
    assert res2["units"]["E-1"]["duty"]["value"] == pytest.approx(Q, rel=1e-6)
    assert res2["units"]["E-1"]["hot_outlet_temperature"]["value"] == pytest.approx(330.0, abs=1e-4)
    # LMTD from the reported end approaches.
    a, b = e["approach_hot_end"]["value"], e["approach_cold_end"]["value"]
    assert e["lmtd"]["value"] == pytest.approx((a - b) / math.log(a / b))
    assert e["ua"]["value"] == pytest.approx(Q / e["lmtd"]["value"])
    # Cooling the hot side below the cold inlet is a temperature cross.
    doc["units"][0]["specs"] = {"hot_outlet_temperature": q(290.0, "K")}
    result = ENGINE.simulate(doc)
    assert not result.converged
    assert [i.code for i in result.issues if i.severity is adapter.Severity.ERROR] == ["temperature_cross"]


HDA = [{"id": "toluene", "name": "Toluene", "cas": "108-88-3"}, {"id": "hydrogen", "name": "Hydrogen", "cas": "1333-74-0"},
       {"id": "benzene", "name": "Benzene", "cas": "71-43-2"}, {"id": "methane", "name": "Methane", "cas": "74-82-8"}]
HDA_REACTION = {"stoichiometry": {"toluene": -1, "hydrogen": -1, "benzene": 1, "methane": 1}, "key": "toluene", "conversion": 0.5}


def test_conversion_reactor_heat_of_reaction_from_formation_enthalpies():
    # C7H8 + H2 → C6H6 + CH4 at 298.15 K, ideal gas (dilute in H2, 1 bar).
    # ΔHr° = ΔHf(benzene) + ΔHf(methane) − ΔHf(toluene) = 82.9 − 74.9 − 50.1 kJ/mol ≈ −42 kJ/mol
    # (standard tables, e.g. Smith, Van Ness & Abbott, Table C.4).
    doc = one_unit({"id": "R-1", "type": "conversion_reactor", "specs": {"temperature": q(298.15, "K")},
                    "options": {"reactions": [HDA_REACTION]}},
                   HDA, {"in": st(298.15, 1e5, 100.0, {"toluene": 0.01, "hydrogen": 0.99, "benzene": 0.0, "methane": 0.0})},
                   ["out"], package="IDEAL")
    res, _ = solve(doc)
    r = res["units"]["R-1"]
    assert r["extent_1"]["value"] == pytest.approx(0.5)
    assert r["duty"]["value"] == pytest.approx(0.5 * -42.1e3, rel=0.02)
    out = res["streams"]["OUT0"]["mole_fractions"]
    F = res["streams"]["OUT0"]["molar_flow"]["value"]
    assert F == pytest.approx(100.0)  # equimolar reaction
    assert F * out["benzene"] == pytest.approx(0.5) and F * out["toluene"] == pytest.approx(0.5)

    # Adiabatic: the heat released raises the temperature.
    doc["units"][0]["specs"] = {"duty": q(0.0, "W")}
    res_ad, _ = solve(doc)
    assert res_ad["units"]["R-1"]["temperature"]["value"] > 298.15 + 5


def test_reactor_rejects_unbalanced_or_bad_reactions():
    bad = dict(HDA_REACTION, stoichiometry={"toluene": -1, "benzene": 1})  # loses a CH2
    doc = one_unit({"id": "R-1", "type": "conversion_reactor", "specs": {"temperature": q(900.0, "K")},
                    "options": {"reactions": [bad]}},
                   HDA, {"in": st(900.0, 3e6, 10.0, {"toluene": 0.2, "hydrogen": 0.8, "benzene": 0.0, "methane": 0.0})}, ["out"])
    result = ENGINE.simulate(doc)
    assert [i.code for i in result.issues if i.severity is adapter.Severity.ERROR] == ["unbalanced_reaction"]
    doc["units"][0]["options"] = {"reactions": [dict(HDA_REACTION, key="benzene")]}
    assert [i.code for i in ENGINE.validate(doc)] == ["invalid_reaction_key"]
    doc["units"][0]["options"] = {}
    assert [(i.code, i.params["spec"]) for i in ENGINE.validate(doc)] == [("missing_spec", "reactions")]


def column_doc(lk_rec=0.95, hk_rec=0.95, factor=1.3, z=0.5):
    return one_unit({"id": "T-1", "type": "shortcut_column",
                     "specs": {"lk_recovery": q(lk_rec, "1"), "hk_recovery": q(hk_rec, "1"),
                               "reflux_ratio_factor": q(factor, "1"), "pressure": q(101325, "Pa")},
                     "options": {"light_key": "benzene", "heavy_key": "toluene"}},
                    BT, {"in": st(None, 101325, 100.0, {"benzene": z, "toluene": 1 - z}, VF=0.0)},
                    ["distillate", "bottoms"])


def test_shortcut_column_binary_matches_closed_form_fenske_and_underwood():
    res, _ = solve(column_doc())
    c = res["units"]["T-1"]
    alpha = c["relative_volatility"]["value"]
    assert 2.2 < alpha < 2.7  # benzene/toluene near 1 atm
    # Fenske, binary: N_min = ln[(0.95/0.05)(0.95/0.05)] / ln α.
    assert c["minimum_stages"]["value"] == pytest.approx(math.log(19 * 19) / math.log(alpha), rel=1e-9)
    # Underwood for a binary, saturated-liquid feed (q = 1):
    # R_min = [x_D/z − α (1 − x_D)/(1 − z)] / (α − 1).
    D = res["streams"]["OUT0"]["molar_flow"]["value"]
    xD = res["streams"]["OUT0"]["mole_fractions"]["benzene"]
    assert D == pytest.approx(0.95 * 50 + 0.05 * 50)
    assert xD == pytest.approx(47.5 / 50)
    rmin = (xD / 0.5 - alpha * (1 - xD) / 0.5) / (alpha - 1)
    assert c["minimum_reflux_ratio"]["value"] == pytest.approx(rmin, rel=1e-4)
    assert c["reflux_ratio"]["value"] == pytest.approx(1.3 * rmin, rel=1e-4)
    # Gilliland at R = 1.3 Rmin typically gives N ≈ 2–2.5 N_min.
    assert 1.6 < c["stages"]["value"] / c["minimum_stages"]["value"] < 2.8
    assert 0 < c["feed_stage"]["value"] < c["stages"]["value"]
    # Material balance and saturated products.
    B = res["streams"]["OUT1"]["molar_flow"]["value"]
    assert D + B == pytest.approx(100.0)
    assert res["streams"]["OUT0"]["vapor_fraction"]["value"] == pytest.approx(0.0, abs=1e-9)
    # Energy: condenser removes heat, reboiler adds it; for a saturated-liquid feed they nearly balance.
    qc, qr = c["condenser_duty"]["value"], c["reboiler_duty"]["value"]
    assert qc < 0 < qr
    assert qr == pytest.approx(-qc, rel=0.15)


def test_shortcut_column_more_reflux_fewer_stages():
    n13 = solve(column_doc(factor=1.3))[0]["units"]["T-1"]["stages"]["value"]
    n20 = solve(column_doc(factor=2.0))[0]["units"]["T-1"]["stages"]["value"]
    assert n20 < n13


def test_column_spec_problems():
    doc = column_doc()
    doc["units"][0]["options"]["heavy_key"] = "benzene"
    doc["units"][0]["specs"]["reflux_ratio_factor"] = q(0.9, "1")
    assert set(i.code for i in ENGINE.validate(doc)) == {"same_keys", "out_of_range"}


def test_all_examples_solve():
    import json
    from pathlib import Path

    for path in sorted((Path(__file__).resolve().parents[2] / "examples").glob("*.opd.json")):
        result = ENGINE.simulate(json.loads(path.read_text(encoding="utf-8")))
        assert result.converged, (path.name, [i for i in result.issues if i.severity is adapter.Severity.ERROR])


def test_heat_exchanger_rating_with_ua_reproduces_design():
    feeds = {"hot_in": st(400.0, 2e5, 10.0, {"benzene": 0.0, "toluene": 1.0}),
             "cold_in": st(300.0, 2e5, 20.0, {"benzene": 1.0, "toluene": 0.0})}
    design = solve(one_unit({"id": "E-1", "type": "heat_exchanger", "specs": {"hot_outlet_temperature": q(330.0, "K")}},
                            BT, feeds, ["hot_out", "cold_out"]))[0]["units"]["E-1"]
    UA = design["ua"]["value"]
    rated = solve(one_unit({"id": "E-1", "type": "heat_exchanger", "specs": {"ua": q(UA, "W/K")}},
                           BT, feeds, ["hot_out", "cold_out"]))[0]["units"]["E-1"]
    assert rated["hot_outlet_temperature"]["value"] == pytest.approx(330.0, abs=1e-3)
    assert rated["duty"]["value"] == pytest.approx(design["duty"]["value"], rel=1e-6)
    # Same with U and area; a bigger exchanger transfers more heat.
    rated2 = solve(one_unit({"id": "E-1", "type": "heat_exchanger",
                             "specs": {"u_overall": q(500.0, "W/m2/K"), "area": q(UA / 500.0 * 2, "m2")}},
                            BT, feeds, ["hot_out", "cold_out"]))[0]["units"]["E-1"]
    assert rated2["duty"]["value"] > rated["duty"]["value"]
    assert rated2["ua"]["value"] == pytest.approx(2 * UA, rel=1e-6)
