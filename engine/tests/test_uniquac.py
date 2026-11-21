"""UNIQUAC (T21) against experimental VLE at 1 atm (same data as the NRTL test)."""

from __future__ import annotations

import pytest

pytest.importorskip("thermo")

from opd_engine import runtime  # noqa: E402

import sys  # noqa: E402
from pathlib import Path  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
import test_nrtl as base  # noqa: E402


@pytest.mark.parametrize("x,y,t_c", [(0.10, 0.418, 87.7), (0.30, 0.665, 78.0), (0.50, 0.779, 73.1), (0.80, 0.915, 67.6)])
def test_methanol_water_uniquac_matches_experiment(x, y, t_c):
    T, ys, result = base.bubble(base.MW, {"methanol": x, "water": 1 - x}, package="UNIQUAC")
    assert T == pytest.approx(t_c + 273.15, abs=0.7)
    assert ys["methanol"] == pytest.approx(y, abs=0.02)
    assert not [i for i in result.issues if i.code == "missing_binary_parameter"]


def test_ethanol_water_azeotrope_uniquac():
    T, _, _ = base.bubble(base.EW, {"ethanol": 0.894, "water": 0.106}, package="UNIQUAC")
    assert T == pytest.approx(78.15 + 273.15, abs=0.8)


def test_uniquac_parameter_sources():
    rows = runtime.binary_parameters({"components": base.MW, "thermo": {"package": "UNIQUAC"}})
    assert [(r["i"], r["j"], r["name"], r["source"]) for r in rows] == [
        ("methanol", "water", "uniquac_b", "database"), ("water", "methanol", "uniquac_b", "database")]
