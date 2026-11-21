"""Recycle loops in the reference engine (T08).

Checks: the solve plan (strongly connected components, tear streams), an analytic
mixer–splitter loop, a flash loop with liquid recycle (overall material and energy
balances), Wegstein vs. successive substitution, and the non-convergence report.
"""

from __future__ import annotations

import copy

import pytest

pytest.importorskip("thermo")

from opd_engine import adapter  # noqa: E402
from opd_engine.adapters.recycle import Accelerator, Edge, solve_plan  # noqa: E402
from opd_engine.adapters.reference import ReferenceAdapter  # noqa: E402

BT = [{"id": "benzene", "name": "Benzene", "cas": "71-43-2"},
      {"id": "toluene", "name": "Toluene", "cas": "108-88-3"}]


def q(v, u):
    return {"value": v, "unit": u}


def s(id_, a, ap, b, bp, state=None):
    out = {"id": id_, "from": {"unit": a, "port": ap}, "to": {"unit": b, "port": bp}}
    if state:
        out["state"] = state
    return out


FEED_STATE = {"temperature": q(300.0, "K"), "pressure": q(101325, "Pa"), "molar_flow": q(100.0, "mol/s"),
              "mole_fractions": {"benzene": 0.5, "toluene": 0.5}}


def doc(units, streams, package="PR"):
    return {"format": "opd-flowsheet", "version": "0.1", "name": "recycle", "components": BT,
            "thermo": {"package": package}, "units": units, "streams": streams}


def mixer_splitter_loop(r: float):
    """FEED → M → SP; SP.back (fraction r) → M; SP.out → P. Steady state: R = r·F/(1 − r)."""
    return doc(
        [{"id": "FEED", "type": "feed"}, {"id": "M", "type": "mixer"},
         {"id": "SP", "type": "splitter", "specs": {"split_back": q(r, "1")}}, {"id": "P", "type": "product"}],
        [s("S1", "FEED", "out", "M", "in1", FEED_STATE), s("S2", "M", "out", "SP", "in"),
         s("S3", "SP", "back", "M", "in2"), s("S4", "SP", "out", "P", "in")],
    )


def flash_loop():
    """FEED → M → H (365 K) → F (365 K, 1 atm); vapour → product; liquid → SP:
    40 % recycled to M, rest purged."""
    return doc(
        [{"id": "FEED", "type": "feed"}, {"id": "M", "type": "mixer"},
         {"id": "H", "type": "heater", "specs": {"temperature": q(365.0, "K")}},
         {"id": "F", "type": "flash", "specs": {"pressure": q(101325, "Pa"), "temperature": q(365.0, "K")}},
         {"id": "SP", "type": "splitter", "specs": {"split_rec": q(0.4, "1")}},
         {"id": "VAP", "type": "product"}, {"id": "PURGE", "type": "product"}],
        [s("S1", "FEED", "out", "M", "in1", FEED_STATE), s("S2", "M", "out", "H", "in"),
         s("S3", "H", "out", "F", "in"), s("S4", "F", "vapor", "VAP", "in"), s("S5", "F", "liquid", "SP", "in"),
         s("S6", "SP", "rec", "M", "in2"), s("S7", "SP", "purge", "PURGE", "in")],
    )


def run(d, **kw):
    result = ReferenceAdapter(**kw).simulate(d)
    assert result.converged, [i for i in result.issues if i.severity is adapter.Severity.ERROR]
    return result.document["results"], result


def flow(res, sid, comp=None):
    st = res["streams"][sid]
    F = st["molar_flow"]["value"]
    return F if comp is None else F * st.get("mole_fractions", {}).get(comp, 0.0)


# ---------------------------------------------------------------- plan

def test_solve_plan_finds_loop_and_tear():
    units = ["FEED", "M", "SP", "P"]
    edges = [Edge("S1", "FEED", "M"), Edge("S2", "M", "SP"), Edge("S3", "SP", "M"), Edge("S4", "SP", "P")]
    plan = solve_plan(units, edges)
    assert [(b.units, b.tears) for b in plan] == [(["FEED"], []), (["M", "SP"], ["S3"]), (["P"], [])]


def test_solve_plan_nested_loops_need_every_cycle_torn():
    # A → B → C → A and B → C → B: tearing must break both cycles.
    units = ["X", "A", "B", "C"]
    edges = [Edge("s0", "X", "A"), Edge("s1", "A", "B"), Edge("s2", "B", "C"),
             Edge("s3", "C", "A"), Edge("s4", "C", "B")]
    (_, loop) = solve_plan(units, edges)
    assert set(loop.units) == {"A", "B", "C"}
    assert set(loop.tears) == {"s3", "s4"}
    assert loop.units == ["A", "B", "C"]


def test_self_loop_is_a_loop():
    plan = solve_plan(["A"], [Edge("s", "A", "A")])
    assert plan[0].tears == ["s"]


def test_wegstein_beats_substitution_on_a_slow_linear_map():
    # g(x) = 0.9 x + 10, fixed point x* = 100. Substitution shrinks the error by 0.9 per
    # step; bounded Wegstein (q = −5 here, since the unbounded q = −9) by 0.4.
    errors = {}
    for method in ("wegstein", "direct"):
        acc, x = Accelerator(method), [0.0]
        for _ in range(20):
            x = acc.next(x, [0.9 * x[0] + 10])
        errors[method] = abs(x[0] - 100.0)
    assert errors["direct"] == pytest.approx(100 * 0.9 ** 20, rel=1e-9)
    assert errors["wegstein"] < 1e-5 < errors["direct"]

    # With wider bounds the method is exact on a linear map after one accelerated step.
    acc, x = Accelerator("wegstein", q_min=-20.0), [0.0]
    for _ in range(4):
        x = acc.next(x, [0.9 * x[0] + 10])
    assert x[0] == pytest.approx(100.0, rel=1e-12)


# ---------------------------------------------------------------- engine

@pytest.mark.parametrize("r", [0.5, 0.9])
def test_mixer_splitter_loop_matches_analytic_recycle(r):
    res, result = run(mixer_splitter_loop(r))
    assert flow(res, "S3") == pytest.approx(r * 100.0 / (1 - r), rel=1e-6)
    assert flow(res, "S4") == pytest.approx(100.0, rel=1e-6)
    info = [i for i in result.issues if i.code == "recycle_converged"]
    assert len(info) == 1 and info[0].params["streams"] == ["S3"]
    assert info[0].severity is adapter.Severity.INFO and info[0].target.id == "S3"


def test_wegstein_needs_far_fewer_iterations_than_substitution():
    _, weg = run(mixer_splitter_loop(0.9), recycle_method="wegstein")
    _, direct = run(mixer_splitter_loop(0.9), recycle_method="direct", max_iterations=1000)
    it_w = next(i.params["iterations"] for i in weg.issues if i.code == "recycle_converged")
    it_d = next(i.params["iterations"] for i in direct.issues if i.code == "recycle_converged")
    assert it_w * 3 <= it_d  # e.g. 20 vs. 160 for r = 0.9


def test_flash_loop_closes_material_and_energy_balances():
    res, result = run(flash_loop())
    for comp in ("benzene", "toluene"):
        out = flow(res, "S4", comp) + flow(res, "S7", comp)
        assert out == pytest.approx(50.0, rel=1e-6)
    # Split is exact on the converged liquid.
    assert flow(res, "S6") == pytest.approx(0.4 * flow(res, "S5"), rel=1e-9)
    # Mixer outlet = feed + recycle, per component.
    for comp in ("benzene", "toluene"):
        assert flow(res, "S2", comp) == pytest.approx(flow(res, "S1", comp) + flow(res, "S6", comp), rel=1e-6)
    # Opening the loop at the converged recycle must give the same heater and flash duties
    # (energy balance of the loop is consistent with the once-through calculation).
    s6 = res["streams"]["S6"]
    opened = flash_loop()
    opened["units"] += [{"id": "REC", "type": "feed"}, {"id": "REC_OUT", "type": "product"}]
    for st in opened["streams"]:
        if st["id"] == "S6":
            st["to"] = {"unit": "REC_OUT", "port": "in"}
    opened["streams"].append(s("S8", "REC", "out", "M", "in2",
                               {k: s6[k] for k in ("temperature", "pressure", "molar_flow", "mole_fractions")}))
    opened_res, _ = run(opened)
    for unit in ("H", "F"):
        assert opened_res["units"][unit]["duty"]["value"] == pytest.approx(res["units"][unit]["duty"]["value"], rel=1e-6)


def test_initial_guess_from_tear_stream_state_is_used():
    d = mixer_splitter_loop(0.5)
    d["streams"][2]["state"] = {"temperature": q(300.0, "K"), "pressure": q(101325, "Pa"),
                                "molar_flow": q(100.0, "mol/s"), "mole_fractions": {"benzene": 0.5, "toluene": 0.5}}
    _, result = run(d)
    iterations = next(i.params["iterations"] for i in result.issues if i.code == "recycle_converged")
    assert iterations <= 2  # started at the answer


def test_non_convergence_is_reported_on_the_tear_stream():
    result = ReferenceAdapter(recycle_method="direct", max_iterations=3).simulate(mixer_splitter_loop(0.9))
    assert not result.converged
    err = [i for i in result.issues if i.severity is adapter.Severity.ERROR]
    assert [(i.code, i.target.id) for i in err] == [("recycle_not_converged", "S3")]
    assert err[0].params["iterations"] == 3 and err[0].params["residual"] > 0
