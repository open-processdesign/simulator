// @vitest-environment node
/**
 * T03 measurement: boot the engine in Pyodide under Node and solve the flash-drum example.
 *
 * Skipped unless PYODIDE_DIST points at an unpacked Pyodide distribution
 * (github.com/pyodide/pyodide/releases, version PYODIDE_VERSION) and WHEEL_DIR holds the
 * thermo / chemicals / fluids wheels (`pip download --no-deps <PYPI_WHEELS> -d $WHEEL_DIR`).
 * Run: PYODIDE_DIST=… WHEEL_DIR=… npm run spike:engine
 */
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { loadPyodide } from "pyodide";
import { bootEngine, PYODIDE_PACKAGES, PYODIDE_VERSION } from "./bootstrap";

const DIST = process.env.PYODIDE_DIST;
const WHEEL_DIR = process.env.WHEEL_DIR;
const ROOT = fileURLToPath(new URL("../../../", import.meta.url));

function pythonSources(dir: string): Record<string, string> {
  const out: Record<string, string> = {};
  const walk = (d: string) => {
    for (const name of readdirSync(d)) {
      const path = join(d, name);
      if (statSync(path).isDirectory()) walk(path);
      else if (name.endsWith(".py")) out[relative(dir, path)] = readFileSync(path, "utf-8");
    }
  };
  walk(dir);
  return out;
}

/** Bytes a browser downloads for the given Pyodide packages, including dependencies. */
function packageBytes(dist: string, names: string[]): number {
  const lock = JSON.parse(readFileSync(join(dist, "pyodide-lock.json"), "utf-8"));
  const seen = new Set<string>();
  const visit = (name: string) => {
    const key = name.toLowerCase().replace(/_/g, "-");
    if (seen.has(key)) return;
    seen.add(key);
    (lock.packages[key]?.depends ?? []).forEach(visit);
  };
  names.forEach(visit);
  return [...seen].reduce((sum, key) => sum + statSync(join(dist, lock.packages[key].file_name)).size, 0);
}

const MB = (bytes: number) => Math.round((bytes / 1e6) * 10) / 10;

describe.skipIf(!DIST || !WHEEL_DIR)("engine in Pyodide (T03 spike)", () => {
  it("boots and solves the flash-drum example", { timeout: 600_000 }, async () => {
    const example = JSON.parse(readFileSync(join(ROOT, "examples", "flash-drum.opd.json"), "utf-8"));
    const start = performance.now();
    const pyodide = await loadPyodide({ indexURL: DIST, packageCacheDir: DIST });
    const runtimeMs = Math.round(performance.now() - start);

    const wheelFiles = readdirSync(WHEEL_DIR!).filter((f) => f.endsWith(".whl"));
    pyodide.FS.mkdirTree("/tmp/wheels");
    for (const f of wheelFiles) pyodide.FS.writeFile(`/tmp/wheels/${f}`, readFileSync(join(WHEEL_DIR!, f)));

    const engine = await bootEngine(pyodide, {
      sources: pythonSources(join(ROOT, "engine", "opd_engine")),
      wheels: wheelFiles.map((f) => `emfs:/tmp/wheels/${f}`),
      warmup: process.env.NO_WARMUP ? undefined : example,
    });

    const t0 = performance.now();
    const first = engine.simulate(example);
    const firstMs = Math.round(performance.now() - t0);
    const t1 = performance.now();
    engine.simulate(example);
    const secondMs = Math.round(performance.now() - t1);

    expect(first.converged).toBe(true);
    const vapor = (first.document.results as any).streams.S2;
    expect(vapor.mole_fractions.benzene).toBeGreaterThan(0.5);

    const core = ["pyodide.asm.wasm", "python_stdlib.zip", "pyodide.asm.mjs", "pyodide-lock.json"]
      .reduce((s, f) => s + statSync(join(DIST!, f)).size, 0);
    const wheels = wheelFiles.reduce((s, f) => s + statSync(join(WHEEL_DIR!, f)).size, 0);
    const report = {
      pyodide: PYODIDE_VERSION,
      engine: engine.version,
      timings_ms: [{ step: "load Python runtime", ms: runtimeMs }, ...engine.timings,
        { step: "first solve", ms: firstMs }, { step: "second solve", ms: secondMs }],
      download_MB: {
        core: MB(core),
        packages: MB(packageBytes(DIST!, PYODIDE_PACKAGES)),
        pypi_wheels: MB(wheels),
      },
      vapor_benzene: vapor.mole_fractions.benzene,
    };
    console.log(JSON.stringify(report, null, 2));
  });
});
