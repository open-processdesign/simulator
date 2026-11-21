"""Shell-and-tube geometry, Kern's method (T24, D030).

Hand calculations use water properties at 300 K from the NIST WebBook (ρ = 996.51 kg/m³,
cp = 4180.6 J/(kg·K), μ = 8.5377e-4 Pa·s, k = 0.61032 W/(m·K)); the engine takes its own
property correlations from `thermo` (k is about 2 % lower), hence 3 % on film coefficients.
F factor: R = 1, P = 0.5 gives F = 0.802 (Bowman et al. 1940; read as ≈ 0.80 from the usual
1–2 chart, e.g. Kern Fig. 18), and the reciprocity F(R, P) = F(1/R, P·R).
"""

from __future__ import annotations

import math

import pytest

pytest.importorskip("thermo")

from opd_engine import adapter  # noqa: E402
from opd_engine.adapters.hx_geometry import f_correction  # noqa: E402

from test_units_t09 import ENGINE, WATER, one_unit, q, solve, st  # noqa: E402

RHO, CP, MU, K = 996.51, 4180.6, 8.5377e-4, 0.61032
MW_WATER = 18.01528e-3
GEOM = {"tube_outer_diameter": 0.019, "tube_inner_diameter": 0.0148, "tube_length": 4.88,
        "tube_count": 160, "tube_passes": 2, "pitch": 0.0254, "layout": "triangular",
        "shell_inner_diameter": 0.489, "baffle_spacing": 0.2}
# Cold water 298 → 302 K (mean 300 K) against hot water 344 K, equal flows.
F_COLD = 800.0  # mol/s ≈ 14.4 kg/s


def hx(specs, geometry, hot_T=344.0, P=3e5, F_hot=F_COLD):
    unit = {"id": "E-1", "type": "heat_exchanger", "specs": specs, "options": {"geometry": geometry}}
    feeds = {"hot_in": st(hot_T, P, F_hot, {"water": 1.0}), "cold_in": st(298.0, P, F_COLD, {"water": 1.0})}
    return one_unit(unit, WATER, feeds, ["hot_out", "cold_out"], package="IDEAL")


def test_tube_side_matches_hand_calculation_with_nist_water():
    res, _ = solve(hx({"cold_outlet_temperature": q(302.0, "K")}, {**GEOM, "tube_side": "cold"}))
    e = res["units"]["E-1"]
    m = F_COLD * MW_WATER
    di = GEOM["tube_inner_diameter"]
    area = GEOM["tube_count"] / GEOM["tube_passes"] * math.pi * di ** 2 / 4
    v = m / (RHO * area)
    re = RHO * v * di / MU
    h = 0.023 * re ** 0.8 * (CP * MU / K) ** 0.4 * K / di  # Dittus–Boelter, heating
    f = 0.014 + 1.056 * re ** -0.42
    dp = RHO * v ** 2 / 2 * (f * 2 * GEOM["tube_length"] / di + 1.6 * 2)
    assert e["velocity_tube"]["value"] == pytest.approx(v, rel=0.005)
    assert e["reynolds_tube"]["value"] == pytest.approx(re, rel=0.01)
    assert e["h_tube"]["value"] == pytest.approx(h, rel=0.03)
    assert e["pressure_drop_tube"]["value"] == pytest.approx(dp, rel=0.01)
    # The computed tube-side pressure drop is applied to the cold outlet.
    assert res["streams"]["OUT1"]["pressure"]["value"] == pytest.approx(3e5 - e["pressure_drop_tube"]["value"], rel=1e-4)


def test_shell_side_matches_kern_hand_calculation_with_nist_water():
    res, _ = solve(hx({"cold_outlet_temperature": q(302.0, "K")}, {**GEOM, "tube_side": "hot"}))
    e = res["units"]["E-1"]
    m = F_COLD * MW_WATER
    do, pt, ds, b = GEOM["tube_outer_diameter"], GEOM["pitch"], GEOM["shell_inner_diameter"], GEOM["baffle_spacing"]
    a_s = ds * (pt - do) / pt * b
    de = 4 * (0.43 * pt ** 2 - math.pi * do ** 2 / 8) / (math.pi * do / 2)  # Kern (1950), triangular
    v = m / (RHO * a_s)
    re = RHO * v * de / MU
    h = 0.36 * re ** 0.55 * (CP * MU / K) ** (1 / 3) * K / de
    n_b = round(GEOM["tube_length"] / b) - 1
    dp = 1.728 * re ** -0.188 * ds * (n_b + 1) / de * RHO * v ** 2 / 2
    assert e["baffles"]["value"] == n_b
    assert e["velocity_shell"]["value"] == pytest.approx(v, rel=0.005)
    assert e["reynolds_shell"]["value"] == pytest.approx(re, rel=0.01)
    assert e["h_shell"]["value"] == pytest.approx(h, rel=0.03)
    assert e["pressure_drop_shell"]["value"] == pytest.approx(dp, rel=0.01)


def test_overall_coefficient_and_area():
    res, _ = solve(hx({"cold_outlet_temperature": q(302.0, "K")}, {**GEOM, "fouling_tube": 2e-4}))
    e = res["units"]["E-1"]
    do, di = GEOM["tube_outer_diameter"], GEOM["tube_inner_diameter"]
    u = 1 / (do / (di * e["h_tube"]["value"]) + 2e-4 * do / di + do * math.log(do / di) / (2 * 45.0)
             + 1 / e["h_shell"]["value"])
    assert e["u_overall"]["value"] == pytest.approx(u, rel=1e-9)
    assert e["area"]["value"] == pytest.approx(160 * math.pi * do * 4.88)
    # Over-design: U·A·F against the zoned UA the duty needs.
    assert e["overdesign"]["value"] == pytest.approx(
        e["u_overall"]["value"] * e["area"]["value"] * e["f_correction"]["value"] / e["ua"]["value"] - 1)


def test_f_correction_reference_values():
    # R = 1, P = 0.5
    assert f_correction(400.0, 350.0, 300.0, 350.0, 2) == pytest.approx(0.8023, abs=5e-4)
    # Reciprocity F(R, P) = F(1/R, P R): swap the roles of the two streams.
    R, P = 2.5, 0.3
    t_ci, t_hi = 300.0, 400.0
    t_co = t_ci + P * (t_hi - t_ci)
    t_ho = t_hi - R * (t_co - t_ci)
    a = f_correction(t_hi, t_ho, t_ci, t_co, 2)
    R2, P2 = 1 / R, P * R
    t_co2 = t_ci + P2 * (t_hi - t_ci)
    t_ho2 = t_hi - R2 * (t_co2 - t_ci)
    assert a == pytest.approx(f_correction(t_hi, t_ho2, t_ci, t_co2, 2), rel=1e-9)
    assert f_correction(400.0, 350.0, 300.0, 350.0, 1) == 1.0
    # Unreachable in a 1–2 exchanger (deep temperature cross).
    assert f_correction(400.0, 310.0, 300.0, 390.0, 2) is None


def test_rating_from_geometry_is_consistent_with_design_check():
    rated, result = solve(hx({}, GEOM, hot_T=360.0, F_hot=500.0))
    e = rated["units"]["E-1"]
    assert e["ua"]["value"] / e["f_correction"]["value"] == pytest.approx(
        e["u_overall"]["value"] * e["area"]["value"], rel=1e-5)
    assert e["overdesign"]["value"] == pytest.approx(0.0, abs=1e-5)
    check, _ = solve(hx({"hot_outlet_temperature": q(e["hot_outlet_temperature"]["value"], "K")},
                        GEOM, hot_T=360.0, F_hot=500.0))
    assert check["units"]["E-1"]["overdesign"]["value"] == pytest.approx(0.0, abs=1e-4)
    assert "low_f_correction" in [i.code for i in result.issues]  # F ≈ 0.67 here
    # One tube pass (counter-current) transfers more than the 1–2 arrangement.
    single, _ = solve(hx({}, {**GEOM, "tube_passes": 1}, hot_T=360.0, F_hot=500.0))
    assert single["units"]["E-1"]["duty"]["value"] > e["duty"]["value"]


def test_specified_pressure_drop_overrides_geometry():
    res, _ = solve(hx({"cold_outlet_temperature": q(302.0, "K"), "cold_pressure_drop": q(1000.0, "Pa")}, GEOM))
    assert res["streams"]["OUT1"]["pressure"]["value"] == pytest.approx(3e5 - 1000.0)


@pytest.mark.parametrize("change", [{"tube_inner_diameter": 0.02}, {"tube_passes": 3}, {"pitch": 0.018},
                                    {"layout": "hexagonal"}, {"colour": "red"}, {"tube_count": 0}])
def test_invalid_geometry_is_reported(change):
    codes = [i.code for i in ENGINE.validate(hx({}, {**GEOM, **change}))]
    assert "invalid_option" in codes


def test_ua_and_geometry_conflict():
    issues = ENGINE.validate(hx({"ua": q(1e4, "W/K")}, GEOM))
    assert "conflicting_specs" in [i.code for i in issues if i.severity is adapter.Severity.ERROR]
