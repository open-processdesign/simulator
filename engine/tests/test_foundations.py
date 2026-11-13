import json
from pathlib import Path

import jsonschema
import pytest

from opd_engine import adapter
from opd_engine.adapters.dwsim import DwsimAdapter

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "schema" / "flowsheet.schema.json").read_text())


@pytest.mark.parametrize("path", sorted((ROOT / "examples").glob("*.opd.json")), ids=lambda p: p.name)
def test_examples_match_schema(path):
    jsonschema.validate(json.loads(path.read_text()), SCHEMA)


def test_example_references_are_consistent():
    doc = json.loads((ROOT / "examples" / "flash-drum.opd.json").read_text())
    unit_ids = {u["id"] for u in doc["units"]}
    comp_ids = {c["id"] for c in doc["components"]}
    for s in doc["streams"]:
        assert s["from"]["unit"] in unit_ids and s["to"]["unit"] in unit_ids
        fractions = s.get("state", {}).get("mole_fractions")
        if fractions:
            assert set(fractions) <= comp_ids
            assert sum(fractions.values()) == pytest.approx(1.0)


def test_registry_and_placeholder_adapter():
    dw = DwsimAdapter()
    adapter.register(dw)
    assert "dwsim" in adapter.available()
    assert adapter.get("dwsim") is dw
    result = dw.simulate({"name": "x"})
    assert not result.converged
    assert result.issues[0].code == "engine_unavailable"


def test_register_rejects_non_adapter():
    with pytest.raises(TypeError):
        adapter.register(object())  # type: ignore[arg-type]
