"""HDA plant vs. the maintainer's CHEMCAD 8.1 case (M3 validation, QUESTIONS Q8).

`examples/hda-chemcad-validation.opd.json` rebuilds the CHEMCAD flowsheet (same stream and
equipment numbers) with SRK; CHEMCAD's two reactors in series (6 and 7) are one reactor with
both reactions, so stream 8 does not exist here. Its specifications are read from the CHEMCAD stream table in
`tests/data/hda_chemcad_case.json`; the engine then has to reproduce the remaining numbers:
recycle flows, phase splits, temperatures after mixing and let-down, and the duties (taken from
CHEMCAD's stream enthalpies, which are on a heat-of-formation basis like the engine's reactor
balance). Tolerances and observed deviations are listed in docs/VALIDATION.md.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("thermo")

from opd_engine import adapter  # noqa: E402
from opd_engine.adapters.reference import ReferenceAdapter  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples" / "hda-chemcad-validation.opd.json"
REF = json.loads((Path(__file__).parent / "data" / "hda_chemcad_case.json").read_text())["streams"]
W_PER_MMBTU_H = 1055.05585262e6 / 3600  # 1 MMBtu/h in W
ATOMS = {"hydrogen": (0, 2), "methane": (1, 4), "benzene": (6, 6), "toluene": (7, 8), "biphenyl": (12, 10)}


@pytest.fixture(scope="module")
def plant():
    result = ReferenceAdapter().simulate(json.loads(EXAMPLE.read_text()))
    assert result.converged, [i for i in result.issues if i.severity is adapter.Severity.ERROR]
    return result


def _stream(plant, sid):
    return plant.document["results"]["streams"][f"S{sid}"]


def _kmol_h(plant, sid):
    return _stream(plant, sid)["molar_flow"]["value"] * 3.6


def _ref_enthalpy_w(sid):
    return REF[sid]["enthalpy_MMBtu_h"] * W_PER_MMBTU_H


def test_recycles_converge_and_atoms_balance(plant):
    assert "recycle_converged" in [i.code for i in plant.issues]
    feeds, products = ("1", "3"), ("14", "18", "20", "22", "25")

    def atoms(sid, k):
        s = _stream(plant, sid)
        return sum(s["molar_flow"]["value"] * x * ATOMS[c][k] for c, x in s["mole_fractions"].items())

    for k in (0, 1):  # C, H
        assert sum(atoms(s, k) for s in products) == pytest.approx(sum(atoms(s, k) for s in feeds), rel=1e-5)


# Process streams: total flow within 0.5 %. The light-ends streams 17/18 and 25 (2 and 0.08
# kmol/h of dissolved H2/CH4) depend on gas solubilities and are checked separately.
@pytest.mark.parametrize("sid", ["6", "9", "10", "11", "12", "13", "14", "15", "16", "19", "20", "21", "22", "23", "24"])
def test_stream_flows(plant, sid):
    assert _kmol_h(plant, sid) == pytest.approx(REF[sid]["molar_flow_kmol_h"], rel=5e-3)


def test_light_ends_flows(plant):
    assert _kmol_h(plant, "17") == pytest.approx(REF["17"]["molar_flow_kmol_h"], rel=0.06)
    assert _kmol_h(plant, "25") == pytest.approx(REF["25"]["molar_flow_kmol_h"], rel=0.08)


# Temperatures the engine computes (mixing, compression, pumping, let-down, bubble points).
@pytest.mark.parametrize("sid, tol", [
    ("2", 2.0), ("4", 0.3), ("5", 0.3), ("6", 0.3), ("15", 0.1), ("16", 0.2),
    ("21", 0.2), ("22", 0.2), ("23", 0.2), ("24", 0.2),
])
def test_stream_temperatures(plant, sid, tol):
    T = _stream(plant, sid)["temperature"]["value"] - 273.15
    assert T == pytest.approx(REF[sid]["temperature_C"], abs=tol)


@pytest.mark.parametrize("sid", ["5", "6", "10", "16"])
def test_vapour_fractions(plant, sid):
    vf = _stream(plant, sid)["vapor_fraction"]["value"]
    assert vf == pytest.approx(REF[sid]["vapor_fraction"], abs=0.003)


# Duties from CHEMCAD's enthalpies: ΔH between the unit's outlet and inlet streams.
@pytest.mark.parametrize("unit, result, inlet, outlet, rel", [
    ("E-5", "duty", "6", "7", 0.01),
    ("R-6", "duty", "7", "9", 0.01),  # CHEMCAD units 6 + 7
    ("E-8", "duty", "9", "10", 0.01),
    ("K-2", "power", "1", "2", 0.01),
    ("P-1", "power", "3", "4", 0.01),
    ("P-17", "power", "23", "24", 0.01),
])
def test_duties(plant, unit, result, inlet, outlet, rel):
    engine = plant.document["results"]["units"][unit][result]["value"]
    chemcad = _ref_enthalpy_w(outlet) - _ref_enthalpy_w(inlet)
    assert engine == pytest.approx(chemcad, rel=rel)


def test_benzene_product(plant):
    s = _stream(plant, "20")
    benzene_kg_h = s["molar_flow"]["value"] * 3.6 * s["mole_fractions"]["benzene"] * 78.11
    assert benzene_kg_h == pytest.approx(REF["20"]["component_flows_kg_h"]["benzene"], rel=5e-3)
    chemcad_purity = (REF["20"]["component_flows_kg_h"]["benzene"] / 78.11) / REF["20"]["molar_flow_kmol_h"]
    assert s["mole_fractions"]["benzene"] == pytest.approx(chemcad_purity, abs=5e-4)


HP = 745.69987  # W


@pytest.mark.parametrize("unit, chemcad_hp", [("K-2", 419.638), ("K-11", 2.59608)])
def test_compressor_powers_from_the_chemcad_dialogs(plant, unit, chemcad_hp):
    # Actual power in CHEMCAD's compressor dialogs (maintainer's screen recording, 2026-11-27).
    # For unit 11 the stream-table enthalpies resolve the power only to about ±7 %.
    engine = plant.document["results"]["units"][unit]["power"]["value"]
    assert engine == pytest.approx(chemcad_hp * HP, rel=0.01)
