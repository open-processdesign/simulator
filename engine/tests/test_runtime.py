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


def test_binary_parameter_sources():
    doc = {
        "components": [
            {"id": "methane", "name": "Methane", "cas": "74-82-8"},
            {"id": "co2", "name": "Carbon dioxide", "cas": "124-38-9"},
            {"id": "benzene", "name": "Benzene", "cas": "71-43-2"},
        ],
        "thermo": {"package": "PR", "binary_parameters": [
            {"i": "co2", "j": "benzene", "name": "kij", "value": 0.07, "source": "user"}]},
    }
    rows = {(r["i"], r["j"]): r for r in runtime.binary_parameters(doc)}
    assert rows[("methane", "co2")]["source"] == "database"
    assert rows[("methane", "co2")]["value"] == pytest.approx(0.0978)  # ChemSep PR table
    assert rows[("co2", "benzene")] == {"i": "co2", "j": "benzene", "name": "kij",
                                        "value": 0.07, "source": "user"}
    assert rows[("methane", "benzene")]["source"] in ("database", "missing")
    assert runtime.binary_parameters({**doc, "thermo": {"package": "IDEAL"}}) == []


def test_component_index_entries_load_in_the_engine():
    """Spot-check the web component index: entries must be usable by the engine."""
    import random

    from thermo import ChemicalConstantsPackage

    index = json.loads((Path(__file__).resolve().parents[2] / "web" / "src" / "data"
                        / "components.json").read_text(encoding="utf-8"))["components"]
    assert len(index) > 1000
    cas = {c["cas"] for c in index}
    assert {"71-43-2", "108-88-3", "7732-18-5", "1333-74-0", "74-82-8"} <= cas
    for entry in random.Random(4).sample(index, 15):
        constants, _ = ChemicalConstantsPackage.from_IDs([entry["cas"]])
        assert constants.Tcs[0] > 0 and constants.Pcs[0] > 0


def test_validate_reports_without_solving():
    doc = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    assert runtime.validate(doc) == []
    del doc["streams"][0]["state"]["pressure"]
    issues = runtime.validate(doc)
    assert [(i["code"], i["target"]["id"]) for i in issues] == [("missing_spec", "S1")]
