import { useId, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { formatNumber } from "@/lib/format";
import type { Flowsheet } from "@/opd/types";
import type { Profile } from "@/state/RunProvider";
import { useUnits } from "@/units/UnitSetProvider";

/**
 * Column stage profiles as two small multiples (one y-axis each, never dual-axis):
 * temperature and liquid mole fractions against stage number, with a crosshair tooltip
 * and a table view. Series colours follow the component order (validated categorical
 * palette, --opd-series-*); text stays in text tokens.
 */
export function ProfileCharts({ unitId, profile, doc }: { unitId: string; profile: Profile; doc: Flowsheet }) {
  const { t, i18n } = useTranslation();
  const units = useUnits();
  const [table, setTable] = useState(false);
  const lang = i18n.resolvedLanguage;
  const isStage = profile.axis.name === "stage";
  const stages = isStage ? profile.axis.values : profile.axis.values.map((v) => units.toDisplay(profile.axis.name, v));
  const axisLabel = isStage ? t("profiles.stage") : `${t(`flowsheet.specs.${profile.axis.name}`, { defaultValue: profile.axis.name })} [${units.unit(profile.axis.name)}]`;
  const temps = profile.series.temperature?.values.map((v) => units.toDisplay("temperature", v)) ?? [];
  const comps = doc.components
    .map((c, k) => ({ id: c.id, name: c.name, color: `var(--opd-series-${(k % 8) + 1})`, values: profile.series[`x_${c.id}`]?.values }))
    .filter((c): c is { id: string; name: string; color: string; values: number[] } => !!c.values)
    .slice(0, 8);

  if (profile.series.hot_temperature && profile.series.cold_temperature) {
    return <HeatCurves unitId={unitId} profile={profile} duties={stages} axisLabel={axisLabel} />;
  }

  return (
    <section aria-label={t("profiles.title", { id: unitId })} className="flex flex-col gap-2 rounded-md border border-border bg-surface p-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold"><span className="num">{unitId}</span> · {t(isStage ? "profiles.title_short" : "profiles.title_length")}</h3>
        <button type="button" className="text-xs text-accent hover:underline" onClick={() => setTable((v) => !v)}>
          {table ? t("profiles.show_chart") : t("profiles.show_table")}
        </button>
      </div>
      {table ? (
        <div className="max-h-80 overflow-auto">
          <table className="w-full text-xs">
            <thead className="sticky top-0 bg-surface-muted text-muted">
              <tr>
                <th className="px-2 py-1 text-left font-medium">{axisLabel}</th>
                <th className="px-2 py-1 text-right font-medium">T [{units.unit("temperature")}]</th>
                {isStage && <th className="px-2 py-1 text-right font-medium">L [{units.unit("molar_flow")}]</th>}
                {isStage && <th className="px-2 py-1 text-right font-medium">V [{units.unit("molar_flow")}]</th>}
                {comps.map((c) => <th key={c.id} className="px-2 py-1 text-right font-medium">x {c.name}</th>)}
              </tr>
            </thead>
            <tbody>
              {stages.map((s, j) => (
                <tr key={s} className="border-t border-border">
                  <td className="num px-2 py-0.5">{isStage ? s : formatNumber(s, lang, 4)}</td>
                  <td className="num px-2 py-0.5 text-right">{formatNumber(temps[j], lang, 2)}</td>
                  {isStage && <td className="num px-2 py-0.5 text-right">{formatNumber(units.toDisplay("molar_flow", profile.series.liquid_flow?.values[j] ?? 0), lang, 3)}</td>}
                  {isStage && <td className="num px-2 py-0.5 text-right">{formatNumber(units.toDisplay("molar_flow", profile.series.vapor_flow?.values[j] ?? 0), lang, 3)}</td>}
                  {comps.map((c) => <td key={c.id} className="num px-2 py-0.5 text-right">{formatNumber(c.values[j], lang, 4)}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
          <LineChart
            title={`${t("flowsheet.specs.temperature")} [${units.unit("temperature")}]`}
            stages={stages}
            series={[{ id: "T", name: t("flowsheet.specs.temperature"), color: "var(--opd-series-1)", values: temps }]}
            digits={2}
            lang={lang}
            stageLabel={axisLabel}
          />
          <LineChart
            title={t(isStage ? "profiles.liquid_composition" : "profiles.composition")}
            stages={stages}
            series={comps}
            digits={4}
            lang={lang}
            stageLabel={axisLabel}
            yMin={0}
            yMax={1}
          />
        </div>
      )}
      {isStage && <p className="text-xs text-subtle">{t("profiles.note")}</p>}
    </section>
  );
}

/** Heat-exchanger T–Q diagram: hot and cold curves against duty from the cold end, one y-axis. */
function HeatCurves({ unitId, profile, duties, axisLabel }: { unitId: string; profile: Profile; duties: number[]; axisLabel: string }) {
  const { t, i18n } = useTranslation();
  const units = useUnits();
  const [table, setTable] = useState(false);
  const lang = i18n.resolvedLanguage;
  const hot = profile.series.hot_temperature.values.map((v) => units.toDisplay("temperature", v));
  const cold = profile.series.cold_temperature.values.map((v) => units.toDisplay("temperature", v));
  const dts = profile.series.hot_temperature.values.map((v, j) => units.toDisplay("lmtd", v - profile.series.cold_temperature.values[j]));
  const tUnit = units.unit("temperature");
  return (
    <section aria-label={t("profiles.title", { id: unitId })} className="flex flex-col gap-2 rounded-md border border-border bg-surface p-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold"><span className="num">{unitId}</span> · {t("profiles.title_heat")}</h3>
        <button type="button" className="text-xs text-accent hover:underline" onClick={() => setTable((v) => !v)}>
          {table ? t("profiles.show_chart") : t("profiles.show_table")}
        </button>
      </div>
      {table ? (
        <div className="max-h-80 overflow-auto">
          <table className="w-full text-xs">
            <thead className="sticky top-0 bg-surface-muted text-muted">
              <tr>
                <th className="px-2 py-1 text-left font-medium">{axisLabel}</th>
                <th className="px-2 py-1 text-right font-medium">{t("flowsheet.specs.hot_temperature")} [{tUnit}]</th>
                <th className="px-2 py-1 text-right font-medium">{t("flowsheet.specs.cold_temperature")} [{tUnit}]</th>
                <th className="px-2 py-1 text-right font-medium">{t("profiles.delta_t")} [{units.unit("lmtd")}]</th>
              </tr>
            </thead>
            <tbody>
              {duties.map((q, j) => (
                <tr key={j} className="border-t border-border">
                  <td className="num px-2 py-0.5">{formatNumber(q, lang, 4)}</td>
                  <td className="num px-2 py-0.5 text-right">{formatNumber(hot[j], lang, 2)}</td>
                  <td className="num px-2 py-0.5 text-right">{formatNumber(cold[j], lang, 2)}</td>
                  <td className="num px-2 py-0.5 text-right">{formatNumber(dts[j], lang, 2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <LineChart
          title={`${t("flowsheet.specs.temperature")} [${tUnit}]`}
          stages={duties}
          series={[
            { id: "hot", name: t("flowsheet.specs.hot_temperature"), color: "var(--opd-series-1)", values: hot },
            { id: "cold", name: t("flowsheet.specs.cold_temperature"), color: "var(--opd-series-2)", values: cold },
          ]}
          digits={2}
          lang={lang}
          stageLabel={axisLabel}
        />
      )}
      <p className="text-xs text-subtle">{t("profiles.heat_note")}</p>
    </section>
  );
}

type Series = { id: string; name: string; color: string; values: number[] };

function niceTicks(min: number, max: number, count = 5): number[] {
  if (max === min) return [min];
  const raw = (max - min) / count;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? raw;
  const out: number[] = [];
  for (let v = Math.ceil(min / step) * step; v <= max + 1e-9 * step; v += step) out.push(Number(v.toPrecision(12)));
  return out;
}

/** Direct labels at line ends, pushed apart so they never overlap (min 12 px). */
function endLabels(labels: { id: string; name: string; y: number }[]): { id: string; name: string; y: number }[] {
  const sorted = [...labels].sort((a, b) => a.y - b.y);
  for (let k = 1; k < sorted.length; k++) sorted[k].y = Math.max(sorted[k].y, sorted[k - 1].y + 12);
  return sorted;
}

function LineChart({ title, stages, series, digits, lang, stageLabel, yMin, yMax }: {
  title: string;
  stages: number[];
  series: Series[];
  digits: number;
  lang: string | undefined;
  stageLabel: string;
  yMin?: number;
  yMax?: number;
}) {
  const clip = useId();
  const [hover, setHover] = useState<number | null>(null);
  const W = 460, H = 220, m = { l: 48, r: series.length > 1 && series.length <= 4 ? 84 : 12, t: 10, b: 30 };
  const all = series.flatMap((s) => s.values);
  const lo = yMin ?? Math.min(...all), hi = yMax ?? Math.max(...all);
  const pad = yMin === undefined ? (hi - lo || 1) * 0.08 : 0;
  const y0 = lo - pad, y1 = hi + pad;
  const sx = (s: number) => m.l + ((s - stages[0]) / (stages[stages.length - 1] - stages[0] || 1)) * (W - m.l - m.r);
  const sy = (v: number) => m.t + (1 - (v - y0) / (y1 - y0 || 1)) * (H - m.t - m.b);
  const yTicks = useMemo(() => niceTicks(y0, y1, 4), [y0, y1]);
  const step = yTicks.length > 1 ? yTicks[1] - yTicks[0] : 1;
  const tickDecimals = (String(Number(step.toPrecision(6))).split(".")[1] ?? "").length;
  const xStep = (stages[stages.length - 1] - stages[0]) / 6 || 1;
  const xDecimals = Math.min(4, Math.max(0, -Math.floor(Math.log10(xStep)) + 1));
  const integerAxis = stages.every((v) => Number.isInteger(v));
  const xTicks = useMemo(() => niceTicks(stages[0], stages[stages.length - 1], 6).filter((v) => !integerAxis || Number.isInteger(v)), [stages, integerAxis]);

  const onMove = (e: React.MouseEvent<SVGRectElement>) => {
    const rect = (e.currentTarget.ownerSVGElement as SVGSVGElement).getBoundingClientRect();
    const px = ((e.clientX - rect.left) / rect.width) * W;
    let best = 0;
    stages.forEach((s, j) => { if (Math.abs(sx(s) - px) < Math.abs(sx(stages[best]) - px)) best = j; });
    setHover(best);
  };

  return (
    <figure className="relative m-0">
      <figcaption className="mb-1 text-xs font-medium text-muted">{title}</figcaption>
      {series.length > 1 && (
        <ul className="mb-1 flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-muted" aria-hidden>
          {series.map((s) => (
            <li key={s.id} className="flex items-center gap-1">
              <span className="inline-block h-0.5 w-3 rounded" style={{ background: s.color }} />
              {s.name}
            </li>
          ))}
        </ul>
      )}
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label={title}>
        <defs>
          <clipPath id={clip}><rect x={m.l} y={m.t} width={W - m.l - m.r} height={H - m.t - m.b} /></clipPath>
        </defs>
        {yTicks.map((v) => (
          <g key={v}>
            <line x1={m.l} x2={W - m.r} y1={sy(v)} y2={sy(v)} stroke="var(--opd-border)" strokeWidth={1} />
            <text x={m.l - 6} y={sy(v)} dy="0.32em" textAnchor="end" fontSize={10} fill="var(--opd-text-muted)" fontFamily="var(--opd-font-num)">
              {formatNumber(v, lang, tickDecimals)}
            </text>
          </g>
        ))}
        {xTicks.map((v) => (
          <text key={v} x={sx(v)} y={H - m.b + 14} textAnchor="middle" fontSize={10} fill="var(--opd-text-muted)" fontFamily="var(--opd-font-num)">{formatNumber(v, lang, integerAxis ? 0 : xDecimals)}</text>
        ))}
        <text x={(m.l + W - m.r) / 2} y={H - 2} textAnchor="middle" fontSize={10} fill="var(--opd-text-muted)">{stageLabel}</text>
        <g clipPath={`url(#${clip})`}>
          {series.map((s) => (
            <polyline key={s.id} fill="none" stroke={s.color} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round"
              points={s.values.map((v, j) => `${sx(stages[j])},${sy(v)}`).join(" ")} />
          ))}
        </g>
        {series.length > 1 && series.length <= 4 && endLabels(series.map((s) => ({ id: s.id, name: s.name, y: sy(s.values[s.values.length - 1]) }))).map((l) => (
          <text key={l.id} x={W - m.r + 6} y={l.y} dy="0.32em" fontSize={10} fill="var(--opd-text-muted)">{l.name}</text>
        ))}
        {hover !== null && (
          <g pointerEvents="none">
            <line x1={sx(stages[hover])} x2={sx(stages[hover])} y1={m.t} y2={H - m.b} stroke="var(--opd-text-subtle)" strokeWidth={1} />
            {series.map((s) => (
              <circle key={s.id} cx={sx(stages[hover])} cy={sy(s.values[hover])} r={4} fill={s.color} stroke="var(--opd-surface)" strokeWidth={2} />
            ))}
          </g>
        )}
        <rect x={m.l} y={m.t} width={W - m.l - m.r} height={H - m.t - m.b} fill="transparent"
          onMouseMove={onMove} onMouseLeave={() => setHover(null)} />
      </svg>
      {hover !== null && (
        <div role="tooltip" style={sx(stages[hover]) > W * 0.55 ? { left: `${(m.l / W) * 100 + 1}%` } : { right: `${(m.r / W) * 100 + 1}%` }}
          className="pointer-events-none absolute top-10 rounded-sm border border-border bg-surface px-2 py-1 text-xs shadow-[var(--opd-shadow)]">
          <div className="text-muted">{stageLabel} <span className="num text-text">{formatNumber(stages[hover], lang, integerAxis ? 0 : 4)}</span></div>
          {series.map((s) => (
            <div key={s.id} className="flex items-center gap-1.5">
              <span className="inline-block size-2 rounded-full" style={{ background: s.color }} />
              <span className="text-muted">{s.name}</span>
              <span className="num ml-auto pl-2 text-text">{formatNumber(s.values[hover], lang, digits)}</span>
            </div>
          ))}
        </div>
      )}
    </figure>
  );
}
