/**
 * Boots the OPD engine layer inside Pyodide (CPython compiled to WebAssembly).
 *
 * Shared by the browser Web Worker (`engine.worker.ts`) and the Node measurement test
 * (`engine.spike.test.ts`), so both measure the same steps. See DECISIONS.md D011, D014.
 */
import type { PyodideAPI } from "pyodide";

/** Packages built into the Pyodide distribution (compiled to WebAssembly). */
export const PYODIDE_PACKAGES = ["micropip", "numpy", "scipy", "pandas", "pydantic"];

/** Pure-Python wheels installed from PyPI with micropip (pinned; MIT licensed). */
export const PYPI_WHEELS = ["fluids==1.3.1", "chemicals==1.5.2", "thermo==0.6.1"];

/** Version of the Pyodide distribution; must match the `pyodide` npm package. */
export const PYODIDE_VERSION = "314.0.8";
export const PYODIDE_CDN = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;

export interface Timing {
  step: string;
  ms: number;
}

export interface BootOptions {
  /** `opd_engine` sources: path relative to the package root (e.g. "adapters/reference.py") → text. */
  sources: Record<string, string>;
  /** What to pass to micropip.install; defaults to PYPI_WHEELS (fetched from PyPI). */
  wheels?: string[];
  onProgress?: (step: string) => void;
  /** Optional flowsheet solved once during boot, so the user's first run is fast
   * (`thermo` loads property data lazily on first use). */
  warmup?: unknown;
}

export interface BinaryParameterRow {
  i: string;
  j: string;
  name: "kij" | "nrtl_b" | "nrtl_alpha";
  value: number;
  source: "database" | "missing" | "user" | "literature" | "regression" | "default";
}

export interface Engine {
  simulate(doc: unknown): EngineResult;
  /** k_ij per component pair and its source (reads only `components` and `thermo`). */
  binaryParameters(doc: unknown): BinaryParameterRow[];
  /** Input checks only, no calculation. */
  validate(doc: unknown): EngineIssue[];
  timings: Timing[];
  version: string;
}

export interface EngineIssue {
  severity: "error" | "warning" | "info";
  code: string;
  message_key: string;
  target: { kind: string; id: string | null } | null;
  params: Record<string, unknown>;
}

export interface EngineResult {
  converged: boolean;
  engine: string;
  engine_version: string;
  document: Record<string, unknown>;
  issues: EngineIssue[];
}

const PACKAGE_ROOT = "/home/pyodide/opd_engine";

export async function bootEngine(pyodide: PyodideAPI, options: BootOptions): Promise<Engine> {
  const timings: Timing[] = [];
  const step = async <T>(name: string, run: () => Promise<T> | T): Promise<T> => {
    options.onProgress?.(name);
    const start = performance.now();
    const value = await run();
    timings.push({ step: name, ms: Math.round(performance.now() - start) });
    return value;
  };

  await step("load numpy/scipy/pandas/pydantic", () => pyodide.loadPackage(PYODIDE_PACKAGES));
  await step("install thermo/chemicals/fluids", async () => {
    const micropip = pyodide.pyimport("micropip");
    await micropip.install(options.wheels ?? PYPI_WHEELS, { deps: false });
    micropip.destroy();
  });
  await step("write opd_engine sources", () => {
    for (const [path, text] of Object.entries(options.sources)) {
      const full = `${PACKAGE_ROOT}/${path}`;
      pyodide.FS.mkdirTree(full.slice(0, full.lastIndexOf("/")));
      pyodide.FS.writeFile(full, text);
    }
  });
  const api = await step("import engine", () => {
    pyodide.runPython(`import sys\nif "/home/pyodide" not in sys.path: sys.path.insert(0, "/home/pyodide")`);
    const runtime = pyodide.pyimport("opd_engine.runtime");
    pyodide.runPython("import opd_engine.adapters.reference");
    return {
      simulate: runtime.simulate_json as (doc: string) => string,
      binaryParameters: runtime.binary_parameters_json as (doc: string) => string,
      validate: runtime.validate_json as (doc: string) => string,
    };
  });
  if (options.warmup !== undefined) {
    await step("warm-up solve", () => api.simulate(JSON.stringify(options.warmup)));
  }
  const version = pyodide.runPython(
    "import opd_engine.adapter as a; a.get('reference').version()",
  ) as string;

  return {
    timings,
    version,
    simulate(doc: unknown): EngineResult {
      return JSON.parse(api.simulate(JSON.stringify(doc))) as EngineResult;
    },
    validate(doc: unknown): EngineIssue[] {
      return JSON.parse(api.validate(JSON.stringify(doc))) as EngineIssue[];
    },
    binaryParameters(doc: unknown): BinaryParameterRow[] {
      return JSON.parse(api.binaryParameters(JSON.stringify(doc))) as BinaryParameterRow[];
    },
  };
}
