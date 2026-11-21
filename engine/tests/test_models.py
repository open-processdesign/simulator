import copy
import json
from pathlib import Path

import jsonschema
import pytest
from pydantic import ValidationError

from opd_engine.models import Flowsheet, check_references, load

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "schema" / "flowsheet.schema.json").read_text())
EXAMPLES = sorted((ROOT / "examples").glob("*.opd.json"))
FLASH = ROOT / "examples" / "flash-drum.opd.json"


def flash_dict() -> dict:
    return json.loads(FLASH.read_text())


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.name)
def test_examples_load_and_are_consistent(path):
    doc = load(path)
    assert check_references(doc) == []


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.name)
def test_round_trip_matches_input_and_schema(path):
    raw = json.loads(path.read_text())
    dumped = load(raw).to_dict()
    assert dumped == raw
    jsonschema.validate(dumped, SCHEMA)


def test_load_accepts_json_string():
    assert load(FLASH.read_text()).name == "Benzene-toluene flash drum"


def test_lookup_helpers():
    doc = load(FLASH)
    assert doc.unit("F-101").type == "flash"
    assert doc.stream("S1").from_.unit == "FEED"
    assert doc.unit("nope") is None


# Structural errors: rejected by both the model and the JSON Schema.
@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.pop("thermo"),
        lambda d: d.update(version="0.2"),
        lambda d: d["thermo"].update(package="MAGIC"),
        lambda d: d["units"][1].update(type="reboiler"),
        lambda d: d["units"][1].update(id="1bad"),
        lambda d: d["components"][0].update(cas="71432"),
        lambda d: d.update(unexpected=True),
        lambda d: d["streams"][0]["state"]["mole_fractions"].update(benzene=1.5),
    ],
    ids=["missing-thermo", "wrong-version", "bad-package", "bad-unit-type", "bad-id",
         "bad-cas", "extra-field", "fraction-above-one"],
)
def test_structural_errors_rejected_by_model_and_schema(mutate):
    d = flash_dict()
    mutate(d)
    with pytest.raises(ValidationError):
        Flowsheet.model_validate(d)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(d, SCHEMA)


# Cross-reference errors: valid structure, reported as issues.
def _codes(d: dict) -> list[str]:
    return [i.code for i in check_references(Flowsheet.model_validate(d))]


def test_unknown_unit_in_stream():
    d = flash_dict()
    d["streams"][1]["to"]["unit"] = "GHOST"
    issues = check_references(Flowsheet.model_validate(d))
    assert [i.code for i in issues] == ["unknown_unit"]
    assert issues[0].target.kind == "stream" and issues[0].target.id == "S2"
    assert issues[0].message_key == "issues.unknown_unit"


def test_fractions_not_normalized():
    d = flash_dict()
    d["streams"][0]["state"]["mole_fractions"] = {"benzene": 0.5, "toluene": 0.4}
    assert _codes(d) == ["fractions_not_normalized"]


def test_unknown_component_in_fractions():
    d = flash_dict()
    d["streams"][0]["state"]["mole_fractions"] = {"benzene": 0.5, "xylene": 0.5}
    assert _codes(d) == ["unknown_component"]


def test_duplicate_ids():
    d = flash_dict()
    d["units"].append(copy.deepcopy(d["units"][0]))
    assert "duplicate_id" in _codes(d)


def test_port_used_twice():
    d = flash_dict()
    d["streams"][2]["from"]["port"] = "vapor"
    assert _codes(d) == ["port_used_twice"]


def test_layout_orphan_is_warning():
    d = flash_dict()
    d["layout"]["GHOST"] = {"x": 0, "y": 0}
    issues = check_references(Flowsheet.model_validate(d))
    assert [(i.code, i.severity.value) for i in issues] == [("layout_orphan", "warning")]


def test_built_in_code_document_serializes_with_format_and_version():
    doc = Flowsheet(name="x", components=[], thermo={"package": "IDEAL"}, units=[], streams=[])
    d = doc.to_dict()
    assert d["format"] == "opd-flowsheet" and d["version"] == "0.1"
    jsonschema.validate(d, SCHEMA)
