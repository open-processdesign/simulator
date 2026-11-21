"""Build the component search index used by the web app (T05).

Lists every component in the `chemicals` database (MIT) that has the data the reference
engine needs for IDEAL/PR/SRK flashes: critical temperature and pressure from a curated
source (IUPAC, Matthews, CRC or PSRK tables), acentric factor, normal boiling point,
ideal-gas heat capacity, vapour pressure and liquid volume correlations.

Run from the repository root after changing the pinned `chemicals`/`thermo` versions:

    python engine/scripts/build_component_index.py

Output: web/src/data/components.json — a list of
{"cas", "name", "formula", "mw" [g/mol], "tb" [K], "synonyms"}.
"""

from __future__ import annotations

import json
import re
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

import chemicals  # noqa: E402
import chemicals.critical as critical  # noqa: E402
import thermo  # noqa: E402
from chemicals import identifiers  # noqa: E402
from chemicals.acentric import omega  # noqa: E402
from chemicals.critical import Pc, Tc  # noqa: E402
from chemicals.phase_change import Tb  # noqa: E402
from thermo import ChemicalConstantsPackage  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "web" / "src" / "data" / "components.json"
_SYNONYM = re.compile(r"^[a-z][a-z0-9 ,'-]{1,29}$")


def synonyms(meta, name: str) -> list[str]:
    seen = {name.lower()}
    out = []
    for s in meta.synonyms or []:
        s = s.strip()
        if _SYNONYM.match(s) and s.lower() not in seen:
            seen.add(s.lower())
            out.append(s)
        if len(out) == 4:
            break
    return out


def main() -> int:
    critical._load_critical_data()
    tables = (critical.critical_data_IUPAC, critical.critical_data_Matthews,
              critical.critical_data_CRC, critical.critical_data_PSRKR4)
    candidates = sorted(set().union(*(set(t.index) for t in tables)))
    rows = []
    for cas in candidates:
        try:
            if not (Tc(cas) and Pc(cas) and omega(cas) is not None and Tb(cas)):
                continue
            constants, props = ChemicalConstantsPackage.from_IDs([cas])
            if not (props.HeatCapacityGases[0].method and props.VaporPressures[0].method
                    and props.VolumeLiquids[0].method):
                continue
            meta = identifiers.search_chemical(cas)
        except Exception:  # missing data for this component: leave it out
            continue
        rows.append({
            "cas": cas,
            "name": meta.common_name,
            "formula": meta.formula,
            "mw": round(meta.MW, 3),
            "tb": round(Tb(cas), 2),
            "synonyms": synonyms(meta, meta.common_name),
        })
    rows.sort(key=lambda r: r["name"].lower())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": f"chemicals {chemicals.__version__}, thermo {thermo.__version__}",
        "components": rows,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"{len(rows)} components → {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
