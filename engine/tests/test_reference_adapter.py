"""Tests for the reference adapter (T04).

Numbers under test come from the engine (`thermo`); the tests check them against
independent hand calculations, conservation laws and published physical constants.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

pytest.importorskip("thermo")

from opd_engine import adapter  # noqa: E402
from opd_engine.adapters.reference import ReferenceAdapter  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
FLASH_DRUM = json.loads((ROOT / "examples" / "flash-drum.opd.json").read_text(encoding="utf-8"))

ENGINE = ReferenceAdapter()


def q(value: float, unit: str) -> dict:
    return {"value": value, "unit": unit}


def run(doc: dict):
    result = ENGINE.simulate(doc)
    errors = [i for i in result.issues if i.severity is adapter.Severity.ERROR]
    assert result.converged, errors
    return result.document["results"], result


def stream(res: dict, sid: str) -> dict:
    s = res["streams"][sid]
    return {
        "T": s["temperature"]["value"],
        "P": s["pressure"]["value"],
        "F": s["molar_flow"]["value"],
        "x": s.get("mole_fractions", {}),
        "VF": s.get("vapor_fraction", {}).get("value"),
    }


def component_flows(res: dict, sids: list[str], comp: str) -> float:
    total = 0.0
    for sid in sids:
        s = stream(res, sid)
        total += s["F"] * s["x"].get(comp, 0.0)
    return total


def feed_doc(units: list[dict], streams: list[dict], package: str = "PR",
             components: list[dict] | None = None) -> dict:
    return {
        "format": "opd-flowsheet",
        "version": "0.1",
        "name": "test",
        "components": components or FLASH_DRUM["components"],
        "thermo": {"package": package},
        "units": units,
        "streams": streams,
    }


def bt_feed(sid: str, to_unit: str, T: float = 350.0, P: float = 101325.0, F: float = 100.0,
            zb: float = 0.5, port: str = "in", feed_id: str = "FEED") -> dict:
    return {
        "id": sid,
        "from": {"unit": feed_id, "port": "out"},
        "to": {"unit": to_unit, "port": port},
        "state": {
            "temperature": q(T, "K"),
            "pressure": q(P, "Pa"),
            "molar_flow": q(F, "mol/s"),
            "mole_fractions": {"benzene": zb, "toluene": 1 - zb},
        },
    }


# ---------------------------------------------------------------- registration

def test_registered_and_capabilities():
    assert "reference" in adapter.available()
    caps = ENGINE.capabilities()
    assert {"feed", "product", "mixer", "splitter", "heater", "valve", "flash"} <= caps.unit_types
    assert caps.thermo_packages == {"IDEAL", "PR", "SRK"}
    assert caps.supports_recycle
    assert "thermo" in ENGINE.version()


# ---------------------------------------------------------------- flash drum example

def test_flash_drum_example_solves_with_closed_balances():
    res, result = run(copy.deepcopy(FLASH_DRUM))
    assert res["engine"] == "reference" and res["converged"] is True
    vap, liq = stream(res, "S2"), stream(res, "S3")
    # Two phases at the spec T and P; vapour richer in the lighter component (benzene).
    assert vap["T"] == pytest.approx(368.15) and liq["P"] == pytest.approx(101325)
    assert 0 < vap["F"] < 100 and 0 < liq["F"] < 100
    assert vap["x"]["benzene"] > 0.5 > liq["x"]["benzene"]
    assert vap["VF"] == 1.0 and liq["VF"] == 0.0
    # Material balance per component.
    for comp in ("benzene", "toluene"):
        assert component_flows(res, ["S2", "S3"], comp) == pytest.approx(50.0, rel=1e-9)
    # Heating a subcooled feed into the two-phase region needs heat.
    assert res["units"]["F-101"]["duty"]["value"] > 0
    # No database k_ij for benzene–toluene: k_ij = 0 is used and reported.
    warnings = [i.code for i in result.issues if i.severity is adapter.Severity.WARNING]
    assert warnings == ["missing_binary_parameter"]
    # Input document is not modified; results are attached to a copy.
    assert "results" not in FLASH_DRUM


def test_ideal_flash_matches_raoult_hand_calculation():
    """Raoult's law + Antoine vapour pressures, solved by Rachford–Rice in the test.

    Antoine constants (log10 p/mmHg = A − B/(T/°C + C)) for benzene and toluene from
    R. M. Felder, R. W. Rousseau, *Elementary Principles of Chemical Processes*,
    3rd ed., Wiley (2005), Table B.4. `thermo` uses its own vapour-pressure
    correlations, so agreement is close but not exact.
    """
    antoine = {"benzene": (6.89272, 1203.531, 219.888), "toluene": (6.95805, 1346.773, 219.693)}
    T, P = 368.15, 101325.0

    def psat(A: float, B: float, C: float) -> float:
        return 10 ** (A - B / (T - 273.15 + C)) * 101325 / 760

    K = {c: psat(*abc) / P for c, abc in antoine.items()}
    z = {"benzene": 0.5, "toluene": 0.5}
    lo, hi = 0.0, 1.0
    for _ in range(100):  # bisection on the Rachford–Rice function
        V = (lo + hi) / 2
        f = sum(z[c] * (K[c] - 1) / (1 + V * (K[c] - 1)) for c in z)
        lo, hi = (V, hi) if f > 0 else (lo, V)
    y_benzene = z["benzene"] * K["benzene"] / (1 + V * (K["benzene"] - 1))

    doc = copy.deepcopy(FLASH_DRUM)
    doc["thermo"]["package"] = "IDEAL"
    res, _ = run(doc)
    assert res["units"]["F-101"]["vapor_fraction"]["value"] == pytest.approx(V, abs=0.01)
    assert stream(res, "S2")["x"]["benzene"] == pytest.approx(y_benzene, abs=0.003)


@pytest.mark.parametrize("package", ["PR", "SRK"])
@pytest.mark.parametrize("cas,name,Tb", [
    # Normal boiling points, NIST Chemistry WebBook (SRD 69): benzene 353.2 K, toluene 383.8 K.
    ("71-43-2", "Benzene", 353.2),
    ("108-88-3", "Toluene", 383.8),
])
def test_pure_component_boiling_point(package, cas, name, Tb):
    comp = [{"id": "c", "name": name, "cas": cas}]
    doc = feed_doc(
        units=[{"id": "FEED", "type": "feed"}, {"id": "P", "type": "product"}],
        streams=[{
            "id": "S1", "from": {"unit": "FEED", "port": "out"}, "to": {"unit": "P", "port": "in"},
            "state": {"vapor_fraction": q(0.5, "1"), "pressure": q(101325, "Pa"),
                      "molar_flow": q(1.0, "mol/s"), "mole_fractions": {"c": 1.0}},
        }],
        package=package, components=comp,
    )
    res, _ = run(doc)
    assert stream(res, "S1")["T"] == pytest.approx(Tb, abs=1.5)


def test_ideal_and_pr_agree_for_near_ideal_mixture():
    """Benzene–toluene at 1 atm is close to ideal; the packages should agree closely."""
    vf = {}
    for package in ("IDEAL", "PR"):
        doc = copy.deepcopy(FLASH_DRUM)
        doc["thermo"]["package"] = package
        res, _ = run(doc)
        vf[package] = res["units"]["F-101"]["vapor_fraction"]["value"]
    assert vf["PR"] == pytest.approx(vf["IDEAL"], abs=0.03)


# ---------------------------------------------------------------- units

def heater_doc(spec: dict, T_feed: float = 300.0) -> dict:
    return feed_doc(
        units=[{"id": "FEED", "type": "feed"}, {"id": "H-1", "type": "heater", "specs": spec},
               {"id": "P", "type": "product"}],
        streams=[bt_feed("S1", "H-1", T=T_feed),
                 {"id": "S2", "from": {"unit": "H-1", "port": "out"}, "to": {"unit": "P", "port": "in"}}],
    )


def test_heater_temperature_and_duty_specs_are_consistent():
    res_t, _ = run(heater_doc({"temperature": q(340.0, "K")}))
    duty = res_t["units"]["H-1"]["duty"]["value"]
    assert duty > 0
    assert stream(res_t, "S2")["T"] == pytest.approx(340.0)
    # Feeding back the computed duty must reproduce the temperature (energy balance).
    res_q, _ = run(heater_doc({"duty": q(duty, "W")}))
    assert stream(res_q, "S2")["T"] == pytest.approx(340.0, abs=1e-3)
    # Cooling gives a negative duty.
    res_c, _ = run(heater_doc({"temperature": q(290.0, "K")}))
    assert res_c["units"]["H-1"]["duty"]["value"] < 0


def test_heater_vapor_fraction_and_pressure_drop():
    res, _ = run(heater_doc({"vapor_fraction": q(1.0, "1"), "pressure_drop": q(5000, "Pa")}))
    out = stream(res, "S2")
    assert out["VF"] == pytest.approx(1.0)
    assert out["P"] == pytest.approx(101325 - 5000)
    # Dew point of 50/50 benzene–toluene at ~0.95 bar lies between the two boiling points.
    assert 353 < out["T"] < 384


def test_valve_is_isenthalpic_and_flashes_hot_liquid():
    doc = feed_doc(
        units=[{"id": "FEED", "type": "feed"},
               {"id": "V-1", "type": "valve", "specs": {"pressure": q(101325, "Pa")}},
               {"id": "P", "type": "product"}],
        streams=[bt_feed("S1", "V-1", T=390.0, P=300000.0),
                 {"id": "S2", "from": {"unit": "V-1", "port": "out"}, "to": {"unit": "P", "port": "in"}}],
    )
    res, _ = run(doc)
    out = stream(res, "S2")
    assert stream(res, "S1")["VF"] == 0.0  # subcooled at 3 bar
    assert 0 < out["VF"] < 1  # partially vaporised after letdown
    assert out["T"] < 390.0  # Joule–Thomson + evaporation cooling
    assert res["units"]["V-1"]["pressure_drop"]["value"] == pytest.approx(300000 - 101325)


def test_mixer_splitter_balances():
    doc = feed_doc(
        units=[{"id": "FEED", "type": "feed"}, {"id": "FEED2", "type": "feed"},
               {"id": "M-1", "type": "mixer"},
               {"id": "SP-1", "type": "splitter", "specs": {"split_a": q(0.3, "1")}},
               {"id": "PA", "type": "product"}, {"id": "PB", "type": "product"}],
        streams=[
            bt_feed("S1", "M-1", T=300.0, F=60.0, zb=0.8, port="in1"),
            bt_feed("S2", "M-1", T=340.0, P=150000.0, F=40.0, zb=0.1, port="in2", feed_id="FEED2"),
            {"id": "S3", "from": {"unit": "M-1", "port": "out"}, "to": {"unit": "SP-1", "port": "in"}},
            {"id": "S4", "from": {"unit": "SP-1", "port": "a"}, "to": {"unit": "PA", "port": "in"}},
            {"id": "S5", "from": {"unit": "SP-1", "port": "b"}, "to": {"unit": "PB", "port": "in"}},
        ],
    )
    res, _ = run(doc)
    mix = stream(res, "S3")
    assert mix["F"] == pytest.approx(100.0)
    assert mix["P"] == pytest.approx(101325)  # lowest inlet pressure
    assert mix["x"]["benzene"] == pytest.approx((60 * 0.8 + 40 * 0.1) / 100)
    assert 300.0 < mix["T"] < 340.0  # adiabatic mixing of two liquids
    a, b = stream(res, "S4"), stream(res, "S5")
    assert a["F"] == pytest.approx(30.0) and b["F"] == pytest.approx(70.0)
    assert a["x"] == b["x"] == mix["x"] and a["T"] == b["T"] == mix["T"]
    assert res["units"]["SP-1"]["split_b"]["value"] == pytest.approx(0.7)


def test_flash_pq_adiabatic_letdown_and_single_phase_outlet():
    # Adiabatic flash (duty 0) with a pressure drop: energy is conserved.
    doc = copy.deepcopy(FLASH_DRUM)
    doc["streams"][0]["state"]["temperature"] = q(390.0, "K")
    doc["streams"][0]["state"]["pressure"] = q(300000, "Pa")
    doc["units"][1]["specs"] = {"pressure": q(101325, "Pa"), "duty": q(0.0, "W")}
    res, _ = run(doc)
    assert res["units"]["F-101"]["duty"]["value"] == pytest.approx(0.0, abs=1e-6)
    assert 0 < res["units"]["F-101"]["vapor_fraction"]["value"] < 1
    for comp in ("benzene", "toluene"):
        assert component_flows(res, ["S2", "S3"], comp) == pytest.approx(50.0, rel=1e-9)

    # Well below the bubble point everything leaves as liquid; the vapour outlet is empty.
    doc = copy.deepcopy(FLASH_DRUM)
    doc["units"][1]["specs"]["temperature"] = q(300.0, "K")
    res, _ = run(doc)
    assert stream(res, "S2")["F"] == 0.0 and stream(res, "S2")["x"] == {}
    assert stream(res, "S3")["F"] == pytest.approx(100.0)


def test_user_kij_overrides_database_and_silences_warning():
    doc = copy.deepcopy(FLASH_DRUM)
    doc["thermo"]["binary_parameters"] = [
        {"i": "benzene", "j": "toluene", "name": "kij", "value": 0.02, "source": "user"}]
    res, result = run(doc)
    assert not [i for i in result.issues if i.code == "missing_binary_parameter"]
    base, _ = run(copy.deepcopy(FLASH_DRUM))
    assert (res["units"]["F-101"]["vapor_fraction"]["value"]
            != pytest.approx(base["units"]["F-101"]["vapor_fraction"]["value"], abs=1e-6))


# ---------------------------------------------------------------- input problems

def codes(doc: dict) -> list[str]:
    return [i.code for i in ENGINE.validate(doc) if i.severity is adapter.Severity.ERROR]


def test_missing_flash_spec_is_reported_on_the_unit():
    doc = copy.deepcopy(FLASH_DRUM)
    del doc["units"][1]["specs"]["temperature"]
    issues = [i for i in ENGINE.validate(doc) if i.severity is adapter.Severity.ERROR]
    assert [(i.code, i.target.id, i.params["spec"]) for i in issues] == [
        ("missing_spec", "F-101", "temperature / duty / vapor_fraction")]
    result = ENGINE.simulate(doc)
    assert not result.converged and "results" not in result.document


def test_conflicting_and_non_si_specs():
    doc = copy.deepcopy(FLASH_DRUM)
    doc["units"][1]["specs"]["duty"] = q(0.0, "W")
    assert codes(doc) == ["conflicting_specs"]
    doc = copy.deepcopy(FLASH_DRUM)
    doc["units"][1]["specs"]["temperature"] = q(95.0, "°C")
    assert codes(doc) == ["non_si_unit"]


def test_unconnected_port_and_missing_feed_data():
    doc = copy.deepcopy(FLASH_DRUM)
    doc["streams"] = [s for s in doc["streams"] if s["id"] != "S3"]
    issues = [i for i in ENGINE.validate(doc) if i.severity is adapter.Severity.ERROR]
    assert {(i.code, i.target.id, i.params["port"]) for i in issues} == {
        ("unconnected_port", "F-101", "liquid"), ("unconnected_port", "LIQ", "in")}
    doc = copy.deepcopy(FLASH_DRUM)
    del doc["streams"][0]["state"]["molar_flow"]
    assert codes(doc) == ["missing_spec"]


def test_unsupported_package_and_wrong_ports():
    doc = copy.deepcopy(FLASH_DRUM)
    doc["units"][1]["type"] = "pump"  # a pump has ports in/out, not vapor/liquid
    assert set(codes(doc)) == {"unconnected_port", "unknown_port"}
    doc = copy.deepcopy(FLASH_DRUM)
    doc["thermo"]["package"] = "NRTL"
    assert codes(doc) == ["unsupported_thermo"]


def test_invalid_split_and_bad_document():
    doc = feed_doc(
        units=[{"id": "FEED", "type": "feed"},
               {"id": "SP-1", "type": "splitter", "specs": {"split_a": q(1.2, "1")}},
               {"id": "PA", "type": "product"}, {"id": "PB", "type": "product"}],
        streams=[bt_feed("S1", "SP-1"),
                 {"id": "S2", "from": {"unit": "SP-1", "port": "a"}, "to": {"unit": "PA", "port": "in"}},
                 {"id": "S3", "from": {"unit": "SP-1", "port": "b"}, "to": {"unit": "PB", "port": "in"}}],
    )
    assert codes(doc) == ["invalid_split"]
    assert codes({"format": "opd-flowsheet"}) == ["invalid_document"]


def test_unknown_cas_is_reported_not_raised():
    doc = copy.deepcopy(FLASH_DRUM)
    doc["components"][1]["cas"] = "9999999-99-9"
    result = ENGINE.simulate(doc)
    assert not result.converged
    assert [i.code for i in result.issues] == ["unknown_component_data"]


def test_every_issue_code_has_translations():
    import re

    source = (ROOT / "engine" / "opd_engine" / "adapters" / "reference.py").read_text(encoding="utf-8")
    emitted = set(re.findall(r'_(?:error|issue)\(\s*(?:Severity\.\w+,\s*)?"(\w+)"', source))
    assert {"missing_spec", "recycle_converged", "recycle_not_converged", "calculation_failed"} <= emitted
    for lang in ("en", "tr"):
        issues = json.loads((ROOT / "web" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))["issues"]
        assert emitted <= set(issues), (lang, sorted(emitted - set(issues)))


def test_result_document_is_valid_opd():
    import jsonschema

    from opd_engine.models import load

    _, result = run(copy.deepcopy(FLASH_DRUM))
    schema = json.loads((ROOT / "schema" / "flowsheet.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(result.document, schema)
    assert load(result.document).results.converged is True
