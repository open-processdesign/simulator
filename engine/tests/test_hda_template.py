"""HDA plant template (T27) and the robustness fallbacks it needed.

The template follows the topology and operating conditions of Turton et al., *Analysis,
Synthesis and Design of Chemical Processes*, ch. 1 (two recycles, adiabatic reactor at 75 %
per-pass conversion). Checks: the plant converges, closes the C and H atom balances, and the
reactor converts 75 % of its toluene; the bubble/dew and P–H fallback flashes agree with the
regular `thermo` flashes where those work.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("thermo")

from opd_engine import adapter  # noqa: E402
from opd_engine.adapters.reference import ReferenceAdapter, _Thermo  # noqa: E402
from opd_engine.models import load  # noqa: E402

EXAMPLE = Path(__file__).resolve().parents[2] / "examples" / "hda-benzene-plant-template.opd.json"
ATOMS = {"hydrogen": (0, 2), "methane": (1, 4), "benzene": (6, 6), "toluene": (7, 8)}  # (C, H)


@pytest.fixture(scope="module")
def plant():
    doc = json.loads(EXAMPLE.read_text())
    result = ReferenceAdapter().simulate(doc)
    assert result.converged, [i for i in result.issues if i.severity is adapter.Severity.ERROR]
    return doc, result.document["results"], result


def atoms(stream):
    F = stream["molar_flow"]["value"]
    c = sum(F * x * ATOMS[k][0] for k, x in stream["mole_fractions"].items())
    h = sum(F * x * ATOMS[k][1] for k, x in stream["mole_fractions"].items())
    return c, h


def test_plant_closes_atom_balances(plant):
    _, res, result = plant
    assert "recycle_converged" in [i.code for i in result.issues]
    c_in = [atoms(res["streams"][s]) for s in ("S1", "S3")]
    c_out = [atoms(res["streams"][s]) for s in ("S15", "S16")]
    for k in (0, 1):
        assert sum(x[k] for x in c_out) == pytest.approx(sum(x[k] for x in c_in), rel=1e-5)


def test_reactor_per_pass_conversion(plant):
    _, res, _ = plant
    tol_in = res["streams"]["S6"]["molar_flow"]["value"] * res["streams"]["S6"]["mole_fractions"]["toluene"]
    tol_out = res["streams"]["S9"]["molar_flow"]["value"] * res["streams"]["S9"]["mole_fractions"]["toluene"]
    assert 1 - tol_out / tol_in == pytest.approx(0.75, rel=1e-9)


def test_fallback_flashes_match_regular_flashes(plant):
    doc, _, _ = plant
    th = _Thermo(load(doc))
    zs = [0.0, 0.0, 0.75, 0.25]  # benzene–toluene: regular flashes work here
    for vf in (0.0, 1.0):
        regular = th.flasher.flash(P=2.5e5, VF=vf, zs=zs).T
        assert th._flash_PVF_edge(zs, 2.5e5, vf).T == pytest.approx(regular, abs=1e-4)
    target = th.flasher.flash(T=390.0, P=2.5e5, zs=zs)
    assert th._flash_PH_bisect(zs, 2.5e5, target.H()).T == pytest.approx(target.T, abs=1e-5)
