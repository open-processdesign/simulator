"""Literature validation cases (T25, T26) — published CHEMCAD stream tables.

Cumene, Unit 800: R. Turton (WVU), "Cumene Production – Change in Reactor Conditions",
Appendix 1, Table 1 (current operating conditions) and the equipment summary (E-801
12,800 MJ/h, H-801 6,334 MJ/h, R-801 heat removal 9,840 MJ/h, E-802 16,257 MJ/h).
https://richardturton.faculty.wvu.edu/files/d/3bcf319c-2670-4fae-926f-04045aa5f217/cumene2.pdf

Dimethyl ether, Unit 200: R. Turton (WVU), "Production of Dimethyl Ether", stream tables
(K-values NRTL, enthalpy SRK in the original simulation).
https://richardturton.faculty.wvu.edu/files/d/7cd9840b-ef1f-4995-9ebe-7d654abf91ea/dimethyl_ether.pdf

Tolerances are recorded in docs/VALIDATION.md with the deviations found.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("thermo")

from opd_engine import adapter  # noqa: E402
from opd_engine.adapters.reference import ReferenceAdapter  # noqa: E402

ENGINE = ReferenceAdapter()
EXAMPLES = Path(__file__).resolve().parents[2] / "examples"
MJ_PER_H = 1 / 3.6e-3  # W per MJ/h


def run(name, package=None):
    doc = json.loads((EXAMPLES / name).read_text())
    if package:
        doc["thermo"]["package"] = package
    result = ENGINE.simulate(doc)
    assert result.converged, [i for i in result.issues if i.severity is adapter.Severity.ERROR]
    return result.document["results"]


def kmol_h(stream):
    F = stream["molar_flow"]["value"] * 3.6
    return F, {k: v * F for k, v in stream["mole_fractions"].items()}


@pytest.fixture(scope="module")
def cumene():
    return run("cumene-unit-800-validation.opd.json")


@pytest.mark.parametrize("unit,published", [("E-801", 12_800), ("H-801", 6_334), ("R-801", -9_840), ("E-802", -16_257)])
def test_cumene_duties(cumene, unit, published):
    assert cumene["units"][unit]["duty"]["value"] == pytest.approx(published * MJ_PER_H, rel=0.04)


def test_cumene_flash_split(cumene):
    F9, x9 = kmol_h(cumene["streams"]["S9"])
    F10, x10 = kmol_h(cumene["streams"]["S10"])
    assert F9 == pytest.approx(19.89, rel=0.03)
    assert F10 == pytest.approx(203.17, rel=0.01)
    for comp, published in {"propylene": 5.97, "propane": 5.27, "benzene": 7.88, "cumene": 0.77}.items():
        assert x9[comp] == pytest.approx(published, abs=0.1)
    for comp, published in {"benzene": 101.08, "cumene": 93.62, "pdipb": 2.79}.items():
        assert x10[comp] == pytest.approx(published, rel=0.005)


def test_cumene_reactor_effluent_matches_stream_8(cumene):
    _, x8 = kmol_h(cumene["streams"]["S8"])
    for comp, published in {"propylene": 8.86, "propane": 8.06, "benzene": 108.96, "cumene": 94.39, "pdipb": 2.79}.items():
        # The published table closes the benzene balance to ±0.07 kmol/h (rounding).
        assert x8[comp] == pytest.approx(published, abs=0.1)


def test_dme_adiabatic_reactor_outlet_temperature():
    # SRK/PR enthalpies as in the original; the activity package (ideal-gas vapour) is ~10 K hotter.
    res = run("dme-unit-200-validation.opd.json", package="PR")
    assert res["streams"]["S6"]["temperature"]["value"] == pytest.approx(365.65 + 273.15, abs=3.0)


def test_dme_letdown_of_methanol_water_bottoms():
    res = run("dme-unit-200-validation.opd.json")
    s11, s14 = res["streams"]["S11"], res["streams"]["S14"]
    assert s11["temperature"]["value"] == pytest.approx(138.82 + 273.15, abs=0.3)
    assert s11["vapor_fraction"]["value"] == pytest.approx(0.0459, abs=0.03)
    assert s14["temperature"]["value"] == pytest.approx(80.93 + 273.15, abs=0.5)
    assert s14["vapor_fraction"]["value"] == pytest.approx(0.14, abs=0.05)
