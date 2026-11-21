"""Rigorous distillation column (bubble-point method, T15).

The converged stage profile is checked against the MESH equations directly (material
balance, equilibrium, summation, enthalpy balance on every stage); the column is compared
with the shortcut (FUG) design it should roughly reproduce.
"""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path

import pytest

pytest.importorskip("thermo")

from opd_engine import adapter  # noqa: E402
from opd_engine.adapters.column import solve_column  # noqa: E402
from opd_engine.adapters.reference import ReferenceAdapter, _Thermo  # noqa: E402
from opd_engine.models import load  # noqa: E402

ENGINE = ReferenceAdapter()
ROOT = Path(__file__).resolve().parents[2]
BT = [{"id": "benzene", "name": "benzene", "cas": "71-43-2"}, {"id": "toluene", "name": "toluene", "cas": "108-88-3"}]


def q(v, u):
    return {"value": v, "unit": u}


def column_doc(N=20, feed_stage=10, R=2.4, D=40.0, package="PR", comps=BT, z=None, P=150000.0, unit_type="distillation_column", specs=None, options=None):
    z = z or {"benzene": 0.4, "toluene": 0.6}
    return {
        "format": "opd-flowsheet", "version": "0.1", "name": "column", "components": comps,
        "thermo": {"package": package},
        "units": [{"id": "FEED", "type": "feed"},
                  {"id": "T-1", "type": unit_type, "specs": specs or {
                      "number_of_stages": q(N, "1"), "feed_stage": q(feed_stage, "1"),
                      "reflux_ratio": q(R, "1"), "distillate_rate": q(D, "mol/s"), "pressure": q(P, "Pa")},
                   **({"options": options} if options else {})},
                  {"id": "TOP", "type": "product"}, {"id": "BOT", "type": "product"}],
        "streams": [
            {"id": "S1", "from": {"unit": "FEED", "port": "out"}, "to": {"unit": "T-1", "port": "in"},
             "state": {"vapor_fraction": q(0.0, "1"), "pressure": q(P, "Pa"), "molar_flow": q(100.0, "mol/s"), "mole_fractions": z}},
            {"id": "S2", "from": {"unit": "T-1", "port": "distillate"}, "to": {"unit": "TOP", "port": "in"}},
            {"id": "S3", "from": {"unit": "T-1", "port": "bottoms"}, "to": {"unit": "BOT", "port": "in"}},
        ],
    }


def solve(doc):
    result = ENGINE.simulate(doc)
    assert result.converged, [i for i in result.issues if i.severity is adapter.Severity.ERROR]
    return result.document["results"]


def test_profile_satisfies_mesh_equations():
    doc = column_doc()
    th = _Thermo(load(doc))
    z = [0.4, 0.6]
    feed = th.flash(z, P=150000.0, VF=0.0)
    F, N, f = 100.0, 20, 9
    r = solve_column(th, z, F, feed.H, 150000.0, N, f + 1, 2.4, 40.0)
    D, B = r.D, r.B
    for j in range(N):
        # M: component balances, stage j (U_1 = D is the liquid distillate draw).
        for i in range(2):
            inflow = (r.L[j - 1] * r.x[j - 1][i] if j > 0 else 0.0) + (r.V[j + 1] * r.y[j + 1][i] if j + 1 < N else 0.0) \
                + (F * z[i] if j == f else 0.0)
            out = (r.L[j] + (D if j == 0 else 0.0)) * r.x[j][i] + r.V[j] * r.y[j][i]
            assert inflow == pytest.approx(out, abs=1e-6 * F)
        # E: equilibrium y = K x with K recomputed from the property package; S: Σy = Σx = 1.
        lp = th.flasher.liquid.to(T=r.T[j], P=150000.0, zs=r.x[j])
        gp = th.flasher.gas.to(T=r.T[j], P=150000.0, zs=r.y[j])
        K = [math.exp(a - b) for a, b in zip(lp.lnphis(), gp.lnphis())]
        for i in range(2):
            assert r.y[j][i] == pytest.approx(K[i] * r.x[j][i], rel=1e-5, abs=1e-9)
        assert sum(r.x[j]) == pytest.approx(1.0) and sum(r.y[j]) == pytest.approx(1.0, abs=1e-6)
        # H: enthalpy balance on the inner stages.
        if 0 < j < N - 1:
            hin = r.L[j - 1] * r.HL[j - 1] + r.V[j + 1] * r.HV[j + 1] + (F * feed.H if j == f else 0.0)
            hout = r.L[j] * r.HL[j] + r.V[j] * r.HV[j]
            assert hin == pytest.approx(hout, abs=1e-4 * abs(r.Qc))
    # Overall balances.
    assert r.L[N - 1] == pytest.approx(B) and D + B == pytest.approx(F)
    assert F * feed.H + r.Qc + r.Qr == pytest.approx(D * r.HL[0] + B * r.HL[N - 1], rel=1e-9, abs=1e-3)
    assert r.T[0] < r.T[-1]  # cold top, hot bottom
    assert all(r.T[j] <= r.T[j + 1] + 1e-9 for j in range(N - 1))


def test_rigorous_column_reproduces_the_shortcut_design():
    fug_doc = column_doc(unit_type="shortcut_column",
                         specs={"lk_recovery": q(0.98, "1"), "hk_recovery": q(0.98, "1"),
                                "reflux_ratio_factor": q(1.3, "1"), "pressure": q(150000.0, "Pa")},
                         options={"light_key": "benzene", "heavy_key": "toluene"})
    fug = solve(fug_doc)
    c = fug["units"]["T-1"]
    D = fug["streams"]["S2"]["molar_flow"]["value"]
    N = math.ceil(c["stages"]["value"]) + 1  # + total condenser
    f = round(c["feed_stage"]["value"]) + 1
    rig = solve(column_doc(N=N, feed_stage=f, R=c["reflux_ratio"]["value"], D=D))
    xD = rig["streams"]["S2"]["mole_fractions"]["benzene"]
    rec = D * xD / 40.0
    # FUG is approximate (constant α, Gilliland correlation); within a few percent.
    assert rec == pytest.approx(0.98, abs=0.03)
    assert xD == pytest.approx(fug["streams"]["S2"]["mole_fractions"]["benzene"], abs=0.02)
    assert rig["units"]["T-1"]["condenser_duty"]["value"] == pytest.approx(c["condenser_duty"]["value"], rel=0.05)


def test_more_reflux_gives_purer_distillate():
    lo = solve(column_doc(R=1.8))["streams"]["S2"]["mole_fractions"]["benzene"]
    hi = solve(column_doc(R=4.0))["streams"]["S2"]["mole_fractions"]["benzene"]
    assert hi > lo


def test_nrtl_methanol_water_column():
    mw = [{"id": "methanol", "name": "methanol", "cas": "67-56-1"}, {"id": "water", "name": "water", "cas": "7732-18-5"}]
    res = solve(column_doc(N=15, feed_stage=8, R=1.5, D=29.5, package="NRTL", comps=mw, P=101325.0,
                           z={"methanol": 0.3, "water": 0.7}))
    top, bot = res["streams"]["S2"], res["streams"]["S3"]
    assert top["mole_fractions"]["methanol"] > 0.97 and bot["mole_fractions"]["water"] > 0.98
    # Saturated products: top near methanol's boiling point (64.7 °C); the bottoms boil a few
    # kelvin below water's 100 °C because traces of methanol have a large activity coefficient.
    assert top["temperature"]["value"] == pytest.approx(337.85, abs=1.0)
    assert 365.0 < bot["temperature"]["value"] < 373.15


def test_column_input_errors():
    doc = column_doc(N=10, feed_stage=10)
    assert [(i.code, i.params["spec"]) for i in ENGINE.validate(doc)] == [("out_of_range", "feed_stage")]
    result = ENGINE.simulate(column_doc(D=150.0))  # more distillate than feed
    assert not result.converged
    assert [i.code for i in result.issues if i.severity is adapter.Severity.ERROR] == ["column_distillate_rate"]


def test_stage_profiles_are_stored_in_the_results():
    import jsonschema

    doc = column_doc()
    result = ENGINE.simulate(doc)
    prof = result.document["results"]["profiles"]["T-1"]
    assert prof["axis"]["values"] == [float(j) for j in range(1, 21)]
    s = prof["series"]
    assert set(s) == {"temperature", "liquid_flow", "vapor_flow", "x_benzene", "x_toluene", "y_benzene", "y_toluene"}
    assert all(len(v["values"]) == 20 for v in s.values())
    assert s["temperature"]["values"][0] == pytest.approx(result.document["results"]["units"]["T-1"]["top_temperature"]["value"])
    assert s["vapor_flow"]["values"][0] == 0.0  # total condenser
    schema = json.loads((ROOT / "schema" / "flowsheet.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(result.document, schema)
    assert load(result.document).results.profiles["T-1"].axis.name == "stage"
