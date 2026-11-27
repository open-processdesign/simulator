"""Shortcut-column options and phase labelling added for the CHEMCAD HDA case (Q8).

- `condenser_temperature`: a distillate that carries dissolved H2/CH4 has no bubble point at
  low pressure; without the option the engine says so, with it the distillate leaves at the
  given temperature (two-phase) and a flash drum splits it.
- `pressure_drop`: bottoms leave at the top pressure + ΔP (their bubble point at that pressure).
- Components absent from the column feed must not turn the Fenske/Underwood sums into NaN.
- A single phase above its pseudo-critical temperature (Kay's rule) is reported as vapour.
"""

from __future__ import annotations

import math

import pytest

pytest.importorskip("thermo")

from opd_engine.adapters.reference import ReferenceAdapter  # noqa: E402

from test_units_t09 import BT, one_unit, q, solve, st  # noqa: E402

LIGHTS = [{"id": "hydrogen", "name": "Hydrogen", "cas": "1333-74-0"},
          {"id": "methane", "name": "Methane", "cas": "74-82-8"}] + BT
BTX = BT + [{"id": "biphenyl", "name": "Biphenyl", "cas": "92-52-4"}]


def column(specs, comps, x, T=311.15, P=2e5, package="SRK"):
    unit = {"id": "T-1", "type": "shortcut_column",
            "specs": {"lk_recovery": q(0.999, "1"), "hk_recovery": q(0.995, "1"),
                      "reflux_ratio_factor": q(1.3, "1"), "pressure": q(P, "Pa"), **specs},
            "options": {"light_key": "benzene", "heavy_key": "toluene"}}
    return one_unit(unit, comps, {"in": st(T, P, 10.0, x)}, ["distillate", "bottoms"], package)


GASSY = {"hydrogen": 0.002, "methane": 0.02, "benzene": 0.70, "toluene": 0.278}


def test_light_gases_need_a_condenser_temperature():
    x = {"hydrogen": 0.02, "methane": 0.10, "benzene": 0.70, "toluene": 0.18}
    result = ReferenceAdapter().simulate(column({}, LIGHTS, x))
    assert "column_distillate_not_condensable" in [i.code for i in result.issues]


def test_condenser_temperature_gives_a_two_phase_distillate():
    res, _ = solve(column({"condenser_temperature": q(323.15, "K")}, LIGHTS, GASSY))
    d, b = res["streams"]["OUT0"], res["streams"]["OUT1"]
    assert d["temperature"]["value"] == pytest.approx(323.15)
    assert 0 < d["vapor_fraction"]["value"] < 1  # light gases stay in the vapour
    for c, z in GASSY.items():  # component balances close
        out = sum(s["molar_flow"]["value"] * s["mole_fractions"][c] for s in (d, b))
        assert out == pytest.approx(10.0 * z, rel=1e-9, abs=1e-12)
    assert res["units"]["T-1"]["condenser_duty"]["value"] < 0


def test_pressure_drop_puts_bottoms_at_the_higher_pressure():
    x = {"benzene": 0.5, "toluene": 0.5}
    res0, _ = solve(column({}, BT, x, T=370.0, P=1.0e5))
    res1, _ = solve(column({"pressure_drop": q(0.3e5, "Pa")}, BT, x, T=370.0, P=1.0e5))
    b0, b1 = res0["streams"]["OUT1"], res1["streams"]["OUT1"]
    assert b1["pressure"]["value"] == pytest.approx(1.3e5)
    assert res1["streams"]["OUT0"]["pressure"]["value"] == pytest.approx(1.0e5)
    assert b1["temperature"]["value"] > b0["temperature"]["value"] + 5  # toluene ~ +8 K per 0.3 bar


def test_component_absent_from_the_feed_gives_finite_results():
    unit = {"id": "T-1", "type": "shortcut_column",
            "specs": {"lk_recovery": q(0.999999, "1"), "hk_recovery": q(0.99, "1"),
                      "reflux_ratio_factor": q(1.3, "1"), "pressure": q(2e5, "Pa")},
            "options": {"light_key": "toluene", "heavy_key": "biphenyl"}}
    comps = [{"id": "hydrogen", "name": "Hydrogen", "cas": "1333-74-0"}] + BTX
    x = {"hydrogen": 0.0, "benzene": 0.001, "toluene": 0.966, "biphenyl": 0.033}
    res, _ = solve(one_unit(unit, comps, {"in": st(413.0, 2.1e5, 3.0, x)}, ["distillate", "bottoms"], "SRK"))
    for name in ("stages", "reflux_ratio", "condenser_duty", "reboiler_duty"):
        assert math.isfinite(res["units"]["T-1"][name]["value"]), name
    assert res["streams"]["OUT0"]["mole_fractions"]["hydrogen"] == 0


def test_compressed_hydrogen_is_reported_as_vapour():
    comps = [{"id": "hydrogen", "name": "Hydrogen", "cas": "1333-74-0"},
             {"id": "methane", "name": "Methane", "cas": "74-82-8"}]
    x = {"hydrogen": 0.95, "methane": 0.05}
    unit = {"id": "F-1", "type": "flash", "specs": {"temperature": q(900.0, "K"), "pressure": q(32e5, "Pa")}}
    res, _ = solve(one_unit(unit, comps, {"in": st(300.0, 32e5, 1.0, x)}, ["vapor", "liquid"]))
    assert res["streams"]["OUT0"]["molar_flow"]["value"] == pytest.approx(1.0)
    assert res["streams"]["OUT1"]["molar_flow"]["value"] == pytest.approx(0.0, abs=1e-12)
    assert res["units"]["F-1"]["vapor_fraction"]["value"] == 1.0
