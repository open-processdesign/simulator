"""Zone analysis of the heat exchanger (T22, D028).

Checks: an isothermal condensing side reproduces the classic LMTD result; a desuperheat–
condense–subcool side gives a zoned UA that is grid-independent and well above Q/LMTD of
the end temperatures; the internal pinch at the dew point matches a hand energy balance
with ideal-gas heat capacities from the NIST WebBook (Shomate); an internal cross with
fine end approaches is reported; rating reproduces a phase-change design.
"""

from __future__ import annotations

import pytest

pytest.importorskip("thermo")

from opd_engine import adapter  # noqa: E402

from test_units_t09 import ENGINE, N2, WATER, one_unit, q, solve, st  # noqa: E402

COMPS = WATER + N2
P_ATM = 101325.0
STEAM = st(450.0, P_ATM, 1.0, {"water": 1.0, "n2": 0.0})  # superheated steam, 1 mol/s
T_SAT = 373.12  # water, 1 atm (NIST WebBook)
CP_STEAM = 34.2  # J/(mol·K), ideal gas 373–450 K (NIST Shomate, mean)
CP_N2 = 29.13  # J/(mol·K), ideal gas 300–360 K (NIST Shomate, mean)


def hx(specs, hot, cold, zones=None):
    unit = {"id": "E-1", "type": "heat_exchanger", "specs": specs}
    if zones is not None:
        unit["options"] = {"zones": zones}
    return one_unit(unit, COMPS, {"hot_in": hot, "cold_in": cold}, ["hot_out", "cold_out"], package="IDEAL")


def test_isothermal_condensing_side_matches_lmtd():
    saturated = st(None, P_ATM, 1.0, {"water": 1.0, "n2": 0.0}, VF=1.0)
    cold = st(300.0, P_ATM, 5.0, {"water": 1.0, "n2": 0.0})
    res, _ = solve(hx({"cold_outlet_temperature": q(340.0, "K")}, saturated, cold))
    e = res["units"]["E-1"]
    assert e["hot_outlet_temperature"]["value"] == pytest.approx(T_SAT, abs=0.05)
    # Constant hot temperature: the end-temperature LMTD is exact up to the cold-side cp variation.
    assert e["ua"]["value"] == pytest.approx(e["duty"]["value"] / e["lmtd"]["value"], rel=0.005)


def test_phase_change_zoned_ua_is_grid_independent_and_differs_from_end_lmtd():
    cold = st(290.0, P_ATM, 30.0, {"water": 1.0, "n2": 0.0})
    spec = {"hot_outlet_temperature": q(330.0, "K")}
    coarse = solve(hx(spec, STEAM, cold, zones=1))[0]["units"]["E-1"]
    fine = solve(hx(spec, STEAM, cold, zones=100))[0]["units"]["E-1"]
    # Splitting at the dew and bubble points already gives the three-zone answer.
    assert coarse["zones"]["value"] == 3
    assert coarse["ua"]["value"] == pytest.approx(fine["ua"]["value"], rel=0.002)
    end_lmtd_ua = fine["duty"]["value"] / fine["lmtd"]["value"]
    assert fine["ua"]["value"] > 1.08 * end_lmtd_ua


def test_internal_pinch_at_dew_point_matches_hand_balance():
    cold = st(300.0, P_ATM, 25.4, {"water": 0.0, "n2": 1.0})
    res, _ = solve(hx({"hot_outlet_temperature": q(330.0, "K")}, STEAM, cold))
    e = res["units"]["E-1"]
    Q = e["duty"]["value"]
    q_dew = Q - 1.0 * CP_STEAM * (450.0 - T_SAT)  # heat from the cold end up to the dew point
    t_cold_at_dew = 300.0 + q_dew / (25.4 * CP_N2)
    assert e["minimum_approach"]["value"] == pytest.approx(T_SAT - t_cold_at_dew, abs=0.3)
    assert e["minimum_approach"]["value"] < min(e["approach_hot_end"]["value"], e["approach_cold_end"]["value"])
    profile = res["profiles"]["E-1"]
    assert profile["axis"]["name"] == "duty"
    assert profile["axis"]["values"][-1] == pytest.approx(Q)
    hot_t = profile["series"]["hot_temperature"]["values"]
    cold_t = profile["series"]["cold_temperature"]["values"]
    assert len(hot_t) == len(cold_t) == len(profile["axis"]["values"])
    assert all(b >= a - 1e-9 for a, b in zip(cold_t, cold_t[1:]))


def test_internal_cross_is_reported_although_ends_are_fine():
    cold = st(300.0, P_ATM, 12.0, {"water": 0.0, "n2": 1.0})
    result = ENGINE.simulate(hx({"hot_outlet_temperature": q(330.0, "K")}, STEAM, cold))
    assert not result.converged
    errors = [i for i in result.issues if i.severity is adapter.Severity.ERROR]
    assert [i.code for i in errors] == ["internal_temperature_cross"]
    assert errors[0].params["approach"] < 0


def test_rating_reproduces_phase_change_design():
    cold = st(300.0, P_ATM, 25.4, {"water": 0.0, "n2": 1.0})
    design = solve(hx({"hot_outlet_temperature": q(330.0, "K")}, STEAM, cold))[0]["units"]["E-1"]
    rated = solve(hx({"ua": q(design["ua"]["value"], "W/K")}, STEAM, cold))[0]["units"]["E-1"]
    assert rated["duty"]["value"] == pytest.approx(design["duty"]["value"], rel=1e-6)
    assert rated["hot_outlet_temperature"]["value"] == pytest.approx(330.0, abs=1e-3)


@pytest.mark.parametrize("zones", [0, 101, 2.5])
def test_zone_count_is_checked(zones):
    cold = st(290.0, P_ATM, 30.0, {"water": 1.0, "n2": 0.0})
    result = ENGINE.validate(hx({"hot_outlet_temperature": q(330.0, "K")}, STEAM, cold, zones=zones))
    assert "out_of_range" in [i.code for i in result]
