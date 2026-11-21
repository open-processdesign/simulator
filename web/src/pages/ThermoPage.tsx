import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { formatNumber, parseNumber } from "@/lib/format";
import { useEngine } from "@/engine/EngineProvider";
import type { BinaryParameterRow } from "@/engine/bootstrap";
import type { ThermoPackage } from "@/opd/types";
import { useFlowsheet } from "@/state/FlowsheetProvider";

/** Property methods offered in the demo; must match the reference engine's capabilities. */
const PACKAGES: { id: ThermoPackage; available: boolean }[] = [
  { id: "IDEAL", available: true },
  { id: "PR", available: true },
  { id: "SRK", available: true },
  { id: "NRTL", available: false },
];

const SOURCE_STYLE: Record<string, string> = {
  database: "bg-surface-muted text-muted",
  user: "bg-accent-soft text-accent",
  missing: "bg-surface-muted text-warn",
};

/** Step 2: property method and binary interaction parameters. */
export function ThermoPage() {
  const { t } = useTranslation();
  const { doc, dispatch } = useFlowsheet();
  const pkg = doc.thermo.package;

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6 px-6 py-8">
      <h1 className="font-display text-2xl font-medium">{t("pages.thermo.title")}</h1>

      <fieldset className="flex flex-col gap-2">
        <legend className="mb-2 text-sm font-medium">{t("thermo.package_label")}</legend>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {PACKAGES.map(({ id, available }) => (
            <label
              key={id}
              className={cn(
                "flex cursor-pointer gap-3 rounded-md border bg-surface p-3",
                pkg === id ? "border-accent bg-accent-soft" : "border-border",
                !available && "cursor-not-allowed opacity-60",
              )}
            >
              <input
                type="radio"
                name="thermo-package"
                value={id}
                checked={pkg === id}
                disabled={!available}
                onChange={() => dispatch({ type: "set_package", package: id })}
                className="mt-1 accent-[var(--opd-accent)]"
              />
              <span className="flex flex-col gap-0.5">
                <span className="text-sm font-medium">
                  {t(`thermo.packages.${id}.name`)}
                  {!available && <span className="ml-2 text-xs font-normal text-muted">{t("thermo.coming_later")}</span>}
                </span>
                <span className="text-xs text-muted">{t(`thermo.packages.${id}.hint`)}</span>
              </span>
            </label>
          ))}
        </div>
      </fieldset>

      <BinaryParameters />
    </div>
  );
}

function BinaryParameters() {
  const { t, i18n } = useTranslation();
  const { doc, dispatch } = useFlowsheet();
  const { status, client } = useEngine();
  const [rows, setRows] = useState<BinaryParameterRow[] | null>(null);
  const pkg = doc.thermo.package;
  const n = doc.components.length;
  const needsKij = pkg === "PR" || pkg === "SRK";

  useEffect(() => {
    if (!needsKij || n < 2 || status.state !== "ready" || !client) {
      setRows(null);
      return;
    }
    let alive = true;
    client
      .binaryParameters({ components: doc.components, thermo: doc.thermo })
      .then((r) => alive && setRows(r))
      .catch(() => alive && setRows(null));
    return () => {
      alive = false;
    };
  }, [client, status.state, needsKij, n, doc.components, doc.thermo]);

  const name = (id: string) => doc.components.find((c) => c.id === id)?.name ?? id;

  return (
    <section className="flex flex-col gap-2">
      <h2 className="text-base font-semibold">{t("thermo.binary_title")}</h2>
      {!needsKij ? (
        <p className="text-sm text-muted">{t("thermo.binary_not_needed")}</p>
      ) : n < 2 ? (
        <p className="text-sm text-muted">{t("thermo.binary_need_two")}</p>
      ) : !rows ? (
        <p className="text-sm text-muted">{status.state === "failed" ? t("engine.failed") : t("thermo.binary_waiting")}</p>
      ) : (
        <>
          <table className="w-full overflow-hidden rounded-md border border-border bg-surface text-sm">
            <thead className="bg-surface-muted text-left text-muted">
              <tr>
                <th className="px-3 py-1.5 font-medium">{t("thermo.pair")}</th>
                <th className="px-3 py-1.5 text-right font-medium">{t("thermo.kij")}</th>
                <th className="px-3 py-1.5 font-medium">{t("thermo.source")}</th>
                <th className="w-10" />
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <KijRow
                  key={`${row.i}|${row.j}`}
                  row={row}
                  label={`${name(row.i)} – ${name(row.j)}`}
                  lang={i18n.resolvedLanguage}
                  onSet={(value) => dispatch({ type: "set_kij", i: row.i, j: row.j, value })}
                  onReset={() => dispatch({ type: "clear_kij", i: row.i, j: row.j })}
                />
              ))}
            </tbody>
          </table>
          {rows.some((r) => r.source === "missing") && <p className="text-xs text-warn">{t("thermo.missing_note")}</p>}
          <p className="text-xs text-subtle">{t("thermo.database_note")}</p>
        </>
      )}
    </section>
  );
}

function KijRow({ row, label, lang, onSet, onReset }: {
  row: BinaryParameterRow;
  label: string;
  lang: string | undefined;
  onSet: (value: number) => void;
  onReset: () => void;
}) {
  const { t } = useTranslation();
  const shown = formatNumber(row.value, lang, 4);
  const [text, setText] = useState(shown);
  useEffect(() => setText(shown), [shown]);
  const invalid = parseNumber(text) === null;

  const commit = () => {
    const value = parseNumber(text);
    if (value === null) return setText(shown);
    if (formatNumber(value, lang, 4) !== shown) onSet(value);
  };

  return (
    <tr className="border-t border-border">
      <td className="px-3 py-1">{label}</td>
      <td className="px-3 py-1 text-right">
        <input
          aria-label={t("thermo.edit_kij", { i: row.i, j: row.j })}
          aria-invalid={invalid}
          inputMode="decimal"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onBlur={commit}
          onKeyDown={(e) => e.key === "Enter" && (e.target as HTMLInputElement).blur()}
          className={cn(
            "num h-7 w-24 rounded-sm border bg-surface px-2 text-right text-sm",
            invalid ? "border-error" : "border-border-strong",
          )}
        />
      </td>
      <td className="px-3 py-1">
        <span className={cn("rounded-sm px-1.5 py-0.5 text-xs", SOURCE_STYLE[row.source] ?? "bg-surface-muted text-muted")}>
          {t(`thermo.sources.${row.source}`)}
        </span>
      </td>
      <td className="px-1 text-right">
        {row.source === "user" && (
          <Button variant="ghost" size="sm" aria-label={t("thermo.reset")} title={t("thermo.reset")} onClick={onReset}>
            <RotateCcw aria-hidden />
          </Button>
        )}
      </td>
    </tr>
  );
}
