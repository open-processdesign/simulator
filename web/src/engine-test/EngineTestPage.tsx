import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { startEngine, type EngineClient } from "@/engine/client";
import type { EngineResult, Timing } from "@/engine/bootstrap";
import example from "../../../examples/flash-drum.opd.json";

type StreamState = {
  temperature: { value: number };
  pressure: { value: number };
  molar_flow: { value: number };
  mole_fractions?: Record<string, number>;
};

/**
 * Developer page for T03: boots the engine in a Web Worker and solves the flash-drum
 * example. Shows load timings so they can be recorded (DECISIONS.md D014).
 */
export function EngineTestPage() {
  const { t, i18n } = useTranslation();
  const engine = useRef<EngineClient | null>(null);
  const [progress, setProgress] = useState<string>("");
  const [timings, setTimings] = useState<Timing[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [solved, setSolved] = useState<{ result: EngineResult; ms: number } | null>(null);
  const started = useRef(performance.now());

  useEffect(() => {
    const client = startEngine();
    engine.current = client;
    client.onProgress(setProgress);
    client.ready
      .then((info) => setTimings([...info.timings, { step: "total", ms: Math.round(performance.now() - started.current) }]))
      .catch((e: Error) => setError(e.message));
    return () => client.terminate();
  }, []);

  const fmt = (value: number, digits: number) =>
    value.toLocaleString(i18n.resolvedLanguage, { maximumFractionDigits: digits, minimumFractionDigits: digits });

  const streams = (solved?.result.document.results as { streams?: Record<string, StreamState> } | undefined)?.streams;

  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-4 px-6 py-10">
      <h1 className="font-display text-2xl font-medium">{t("engine_test.title")}</h1>
      <p className="text-muted">{t("engine_test.intro")}</p>

      {error ? (
        <p role="alert" className="text-error">{t("engine_test.failed", { error })}</p>
      ) : timings ? (
        <p className="text-ok">{t("engine_test.ready")}</p>
      ) : (
        <p aria-live="polite" className="text-muted">{t("engine_test.loading", { step: progress || "…" })}</p>
      )}

      {timings && (
        <table className="num w-full max-w-md text-sm">
          <thead className="bg-surface-muted text-left text-muted">
            <tr><th className="px-2 py-1 font-medium">{t("engine_test.step")}</th><th className="px-2 py-1 text-right font-medium">{t("engine_test.time")}</th></tr>
          </thead>
          <tbody>
            {timings.map((row) => (
              <tr key={row.step} className="border-t border-border">
                <td className="px-2 py-1 font-sans">{row.step}</td>
                <td className="px-2 py-1 text-right">{fmt(row.ms / 1000, 2)} s</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <div>
        <Button disabled={!timings} onClick={async () => setSolved(await engine.current!.simulate(example))}>
          {t("engine_test.run")}
        </Button>
      </div>

      {solved && streams && (
        <section className="flex flex-col gap-2">
          <p className="text-sm text-muted">{t("engine_test.solve_time", { ms: solved.ms })}</p>
          <table data-testid="stream-table" className="num w-full text-sm">
            <thead className="bg-surface-muted text-right text-muted">
              <tr>
                <th className="px-2 py-1 text-left font-medium">{t("engine_test.stream")}</th>
                <th className="px-2 py-1 font-medium">T [K]</th>
                <th className="px-2 py-1 font-medium">P [Pa]</th>
                <th className="px-2 py-1 font-medium">F [mol/s]</th>
                <th className="px-2 py-1 font-medium">x benzene</th>
                <th className="px-2 py-1 font-medium">x toluene</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(streams).map(([id, s]) => (
                <tr key={id} className="border-t border-border text-right">
                  <td className="px-2 py-1 text-left">{id}</td>
                  <td className="px-2 py-1">{fmt(s.temperature.value, 2)}</td>
                  <td className="px-2 py-1">{fmt(s.pressure.value, 0)}</td>
                  <td className="px-2 py-1">{fmt(s.molar_flow.value, 3)}</td>
                  <td className="px-2 py-1">{s.mole_fractions ? fmt(s.mole_fractions.benzene, 4) : "–"}</td>
                  <td className="px-2 py-1">{s.mole_fractions ? fmt(s.mole_fractions.toluene, 4) : "–"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </main>
  );
}
