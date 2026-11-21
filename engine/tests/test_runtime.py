import json
from pathlib import Path

import pytest

pytest.importorskip("thermo")

from opd_engine import runtime  # noqa: E402

EXAMPLE = Path(__file__).resolve().parents[2] / "examples" / "flash-drum.opd.json"


def test_simulate_json_round_trip():
    out = json.loads(runtime.simulate_json(EXAMPLE.read_text(encoding="utf-8")))
    assert out["converged"] is True
    assert out["engine"] == "reference"
    assert set(out["document"]["results"]["streams"]) == {"S1", "S2", "S3"}
    warning = out["issues"][0]
    assert warning["severity"] == "warning"
    assert warning["message_key"] == "issues.missing_binary_parameter"
    assert warning["target"] == {"kind": "thermo", "id": None}


def test_errors_are_returned_as_issues():
    doc = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    del doc["units"][1]["specs"]["temperature"]
    out = runtime.simulate(doc)
    assert out["converged"] is False
    assert [i["code"] for i in out["issues"]] == ["missing_spec"]
    assert out["issues"][0]["target"] == {"kind": "unit", "id": "F-101"}
