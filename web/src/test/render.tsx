import type { ReactNode } from "react";
import { render } from "@testing-library/react";
import { EngineProvider } from "@/engine/EngineProvider";
import type { EngineClient } from "@/engine/client";
import type { BinaryParameterRow, EngineIssue } from "@/engine/bootstrap";
import type { Flowsheet } from "@/opd/types";
import { FlowsheetProvider } from "@/state/FlowsheetProvider";
import { RunProvider } from "@/state/RunProvider";
import { SelectionProvider } from "@/state/SelectionProvider";

/** k_ij database used by the fake engine: benzene–toluene has no entry (as in ChemSep). */
const FAKE_DB: Record<string, number> = { "74-82-8|124-38-9": 0.0978 };

/** A stand-in for the Web Worker engine with the same contract (no Pyodide in jsdom). */
export function fakeEngine(validate: (doc: Flowsheet) => EngineIssue[] = () => []): EngineClient {
  return {
    validate: async (doc) => validate(doc as Flowsheet),
    ready: Promise.resolve({ version: "fake", timings: [] }),
    onProgress: () => {},
    terminate: () => {},
    simulate: () => Promise.reject(new Error("not used")),
    binaryParameters: async (doc) => {
      const { components, thermo } = doc as Flowsheet;
      if (thermo.package !== "PR" && thermo.package !== "SRK") return [];
      const rows: BinaryParameterRow[] = [];
      for (let a = 0; a < components.length; a++)
        for (let b = a + 1; b < components.length; b++) {
          const [ci, cj] = [components[a], components[b]];
          const user = (thermo.binary_parameters ?? []).find(
            (p) => (p.i === ci.id && p.j === cj.id) || (p.i === cj.id && p.j === ci.id),
          );
          const db = FAKE_DB[`${ci.cas}|${cj.cas}`] ?? FAKE_DB[`${cj.cas}|${ci.cas}`];
          rows.push(
            user ? { i: ci.id, j: cj.id, name: "kij", value: user.value, source: user.source }
            : db !== undefined ? { i: ci.id, j: cj.id, name: "kij", value: db, source: "database" }
            : { i: ci.id, j: cj.id, name: "kij", value: 0, source: "missing" },
          );
        }
      return rows;
    },
  };
}

export function renderWithApp(ui: ReactNode, initial?: Flowsheet, engine: () => EngineClient = fakeEngine) {
  return render(
    <EngineProvider create={engine}>
      <FlowsheetProvider initial={initial}>
        <RunProvider>
          <SelectionProvider>{ui}</SelectionProvider>
        </RunProvider>
      </FlowsheetProvider>
    </EngineProvider>,
  );
}
