import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { TFunction } from "i18next";
import { Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { QuantityField } from "@/components/QuantityField";
import type { EngineIssue } from "@/engine/bootstrap";
import { formatNumber } from "@/lib/format";
import type { Flowsheet, Stream, Unit } from "@/opd/types";
import { useFlowsheet } from "@/state/FlowsheetProvider";
import { specUnit, unitDef, type SpecGroup } from "./catalog";
import { issuesForUnit } from "./useIssues";

export type Selection = { kind: "unit" | "stream"; id: string } | null;

/** Right-hand panel: settings of the selected unit or stream (no pop-up windows). */
export function SidePanel({ selection, issues, onDeleted }: {
  selection: Selection;
  issues: EngineIssue[] | null;
  onDeleted: () => void;
}) {
  const { t } = useTranslation();
  const { doc } = useFlowsheet();
  const unit = selection?.kind === "unit" ? doc.units.find((u) => u.id === selection.id) : undefined;
  const stream = selection?.kind === "stream" ? doc.streams.find((s) => s.id === selection.id) : undefined;

  return (
    <aside
      aria-label={unit ? `${t("flowsheet.unit")} ${unit.id}` : stream ? `${t("flowsheet.stream")} ${stream.id}` : t("flowsheet.unit")}
      className="flex w-[var(--opd-sidepanel-w)] shrink-0 flex-col gap-4 overflow-y-auto border-l border-border bg-surface-muted p-4"
    >
      {unit ? (
        <UnitPanel unit={unit} issues={issues} onDeleted={onDeleted} />
      ) : stream ? (
        <StreamPanel stream={stream} onDeleted={onDeleted} />
      ) : (
        <p className="text-sm text-muted">{t("flowsheet.panel_empty")}</p>
      )}
    </aside>
  );
}

function UnitPanel({ unit, issues, onDeleted }: { unit: Unit; issues: EngineIssue[] | null; onDeleted: () => void }) {
  const { t } = useTranslation();
  const { doc, dispatch } = useFlowsheet();
  const def = unitDef(unit.type);
  const own = issues ? issuesForUnit(unit.id, doc, issues) : null;

  return (
    <>
      <header className="flex items-start justify-between gap-2">
        <div>
          <p className="text-xs text-muted">{t(`units.${unit.type}`)}</p>
          <h2 className="num text-lg font-semibold">{unit.id}</h2>
        </div>
        <Button variant="ghost" size="sm" aria-label={t("flowsheet.delete_unit")} title={t("flowsheet.delete_unit")}
          onClick={() => { dispatch({ type: "remove_unit", id: unit.id }); onDeleted(); }}>
          <Trash2 aria-hidden />
        </Button>
      </header>

      <label className="flex items-center justify-between gap-2 text-sm text-muted">
        {t("flowsheet.label")}
        <input
          key={unit.id}
          defaultValue={unit.label ?? ""}
          onBlur={(e) => dispatch({ type: "set_label", id: unit.id, label: e.target.value })}
          className="h-7 w-[11.5rem] rounded-sm border border-border-strong bg-surface px-2 text-sm text-text"
        />
      </label>

      {def?.groups.map((g) => <SpecGroupEditor key={`${unit.id}-${g.key}`} unit={unit} group={g} />)}
      {unit.type === "splitter" && <SplitterEditor unit={unit} />}
      {unit.type === "feed" && <FeedEditor unit={unit} />}

      {own && (
        <section className="flex flex-col gap-1">
          <h3 className="text-sm font-semibold">{t("flowsheet.issues")}</h3>
          {own.length === 0 ? (
            <p className="text-sm text-ok">{t("flowsheet.no_issues")}</p>
          ) : (
            <ul className="flex flex-col gap-1 text-sm">
              {own.map((i, k) => (
                <li key={k} className={i.severity === "error" ? "text-error" : "text-warn"}>
                  {issueText(t, i)}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </>
  );
}

/** Translate an engine issue; list parameters are joined, spec names translated. */
export function issueText(t: TFunction, issue: EngineIssue): string {
  const params: Record<string, unknown> = { target: issue.target?.id ?? "", ...issue.params };
  for (const [k, v] of Object.entries(params)) if (Array.isArray(v)) params[k] = v.join(", ");
  if (typeof params.spec === "string") {
    params.spec = params.spec
      .split(" / ")
      .map((s) => t(`flowsheet.specs.${s}`, { defaultValue: s }))
      .join(" / ");
  }
  return t(issue.message_key, params as Record<string, string>);
}

function SpecGroupEditor({ unit, group }: { unit: Unit; group: SpecGroup }) {
  const { t } = useTranslation();
  const { dispatch } = useFlowsheet();
  const given = group.options.find((o) => unit.specs?.[o] !== undefined);
  const [choice, setChoice] = useState<string>(given ?? (group.optional ? "" : group.options[0]));
  const active = given ?? choice;
  const single = group.options.length === 1;

  return (
    <fieldset className="flex flex-col gap-2 rounded-md border border-border bg-surface p-3">
      <legend className="px-1 text-sm font-semibold">{t(`flowsheet.groups.${group.key}`)}</legend>
      {!(single && !group.optional) && (
        <div role="radiogroup" className="flex flex-wrap gap-x-3 gap-y-1">
          {group.optional && (
            <label className="flex items-center gap-1 text-sm">
              <input type="radio" checked={active === ""} className="accent-[var(--opd-accent)]"
                onChange={() => { setChoice(""); if (given) dispatch({ type: "set_spec", id: unit.id, name: given, quantity: null }); }} />
              {group.key === "mixer_pressure" ? t("flowsheet.lowest_inlet") : t("flowsheet.none")}
            </label>
          )}
          {group.options.map((o) => (
            <label key={o} className="flex items-center gap-1 text-sm">
              <input type="radio" checked={active === o} className="accent-[var(--opd-accent)]"
                onChange={() => {
                  setChoice(o);
                  if (given && given !== o) dispatch({ type: "set_spec", id: unit.id, name: given, quantity: null });
                }} />
              {t(`flowsheet.specs.${o}`)}
            </label>
          ))}
        </div>
      )}
      {active && (
        <QuantityField
          label={t(`flowsheet.specs.${active}`)}
          unit={specUnit(active)}
          value={unit.specs?.[active]?.value}
          onCommit={(v) =>
            dispatch({
              type: "set_spec", id: unit.id, name: active,
              quantity: v === null ? null : { value: v, unit: specUnit(active) },
              exclusive: group.options.filter((o) => o !== active),
            })
          }
        />
      )}
    </fieldset>
  );
}

function SplitterEditor({ unit }: { unit: Unit }) {
  const { t } = useTranslation();
  const { doc, dispatch } = useFlowsheet();
  const connected = doc.streams.filter((s) => s.from.unit === unit.id).map((s) => s.from.port).sort();
  if (connected.length < 2) return <p className="text-sm text-muted">{t("flowsheet.split_connect")}</p>;
  const rest = connected[connected.length - 1];
  return (
    <fieldset className="flex flex-col gap-2 rounded-md border border-border bg-surface p-3">
      {connected.slice(0, -1).map((port) => (
        <QuantityField
          key={port}
          label={t("flowsheet.split_to", { port: t(`flowsheet.ports.${port}`) })}
          unit="1"
          value={unit.specs?.[`split_${port}`]?.value}
          onCommit={(v) => dispatch({ type: "set_spec", id: unit.id, name: `split_${port}`, quantity: v === null ? null : { value: v, unit: "1" } })}
        />
      ))}
      <p className="text-xs text-muted">{t("flowsheet.split_rest", { port: t(`flowsheet.ports.${rest}`) })}</p>
    </fieldset>
  );
}

function FeedEditor({ unit }: { unit: Unit }) {
  const { t } = useTranslation();
  const { doc } = useFlowsheet();
  const stream = doc.streams.find((s) => s.from.unit === unit.id);
  if (!stream) return <p className="text-sm text-muted">{t("flowsheet.feed_connect_first")}</p>;
  return <FeedStreamEditor stream={stream} doc={doc} />;
}

function FeedStreamEditor({ stream, doc }: { stream: Stream; doc: Flowsheet }) {
  const { t, i18n } = useTranslation();
  const { dispatch } = useFlowsheet();
  const st = stream.state ?? {};
  const [thermal, setThermal] = useState<"temperature" | "vapor_fraction">(st.vapor_fraction ? "vapor_fraction" : "temperature");
  const fractions = st.mole_fractions ?? {};
  const sum = Object.values(fractions).reduce((a, b) => a + b, 0);

  const setField = (field: "temperature" | "pressure" | "molar_flow" | "vapor_fraction", v: number | null, exclusive?: ("temperature" | "vapor_fraction")[]) =>
    dispatch({ type: "set_stream_state", id: stream.id, field, quantity: v === null ? null : { value: v, unit: specUnit(field) }, exclusive });

  return (
    <fieldset className="flex flex-col gap-2 rounded-md border border-border bg-surface p-3">
      <legend className="px-1 text-sm font-semibold">{t("flowsheet.feed_conditions")} <span className="num font-normal text-muted">({stream.id})</span></legend>
      <div role="radiogroup" aria-label={t("flowsheet.thermal_state")} className="flex gap-3">
        {(["temperature", "vapor_fraction"] as const).map((o) => (
          <label key={o} className="flex items-center gap-1 text-sm">
            <input type="radio" checked={thermal === o} className="accent-[var(--opd-accent)]"
              onChange={() => { setThermal(o); const other = o === "temperature" ? "vapor_fraction" : "temperature"; if (st[other]) setField(other, null); }} />
            {t(`flowsheet.specs.${o}`)}
          </label>
        ))}
      </div>
      <QuantityField label={t(`flowsheet.specs.${thermal}`)} unit={specUnit(thermal)} value={st[thermal]?.value}
        onCommit={(v) => setField(thermal, v, [thermal === "temperature" ? "vapor_fraction" : "temperature"])} />
      <QuantityField label={t("flowsheet.specs.pressure")} unit="Pa" value={st.pressure?.value} onCommit={(v) => setField("pressure", v)} />
      <QuantityField label={t("flowsheet.specs.molar_flow")} unit="mol/s" value={st.molar_flow?.value} onCommit={(v) => setField("molar_flow", v)} />

      <h4 className="mt-2 text-sm font-semibold">{t("flowsheet.composition")}</h4>
      {doc.components.length === 0 ? (
        <p className="text-sm text-muted">{t("flowsheet.no_components")}</p>
      ) : (
        <>
          {doc.components.map((c) => (
            <QuantityField key={c.id} label={c.name} unit="1" value={fractions[c.id]}
              onCommit={(v) => {
                const next = { ...fractions };
                if (v === null) delete next[c.id];
                else next[c.id] = v;
                dispatch({ type: "set_composition", id: stream.id, fractions: Object.keys(next).length ? next : null });
              }} />
          ))}
          <div className="flex items-center justify-between">
            <span className={Math.abs(sum - 1) > 1e-6 ? "num text-sm text-warn" : "num text-sm text-muted"}>
              {t("flowsheet.sum", { sum: formatNumber(sum, i18n.resolvedLanguage, 4) })}
            </span>
            <Button variant="secondary" size="sm" disabled={sum <= 0 || Math.abs(sum - 1) < 1e-12}
              onClick={() => dispatch({ type: "set_composition", id: stream.id,
                fractions: Object.fromEntries(Object.entries(fractions).map(([k, x]) => [k, x / sum])) })}>
              {t("flowsheet.normalize")}
            </Button>
          </div>
        </>
      )}
    </fieldset>
  );
}

function StreamPanel({ stream, onDeleted }: { stream: Stream; onDeleted: () => void }) {
  const { t } = useTranslation();
  const { doc, dispatch } = useFlowsheet();
  const source = doc.units.find((u) => u.id === stream.from.unit);
  return (
    <>
      <header className="flex items-start justify-between gap-2">
        <div>
          <p className="text-xs text-muted">{t("flowsheet.stream")}</p>
          <h2 className="num text-lg font-semibold">{stream.id}</h2>
          <p className="num text-xs text-muted">
            {t("flowsheet.from_to", { from: `${stream.from.unit}.${stream.from.port}`, to: `${stream.to.unit}.${stream.to.port}` })}
          </p>
        </div>
        <Button variant="ghost" size="sm" aria-label={t("flowsheet.delete_stream")} title={t("flowsheet.delete_stream")}
          onClick={() => { dispatch({ type: "remove_stream", id: stream.id }); onDeleted(); }}>
          <Trash2 aria-hidden />
        </Button>
      </header>
      {source?.type === "feed" ? <FeedStreamEditor stream={stream} doc={doc} /> : <p className="text-sm text-muted">{t("flowsheet.calculated")}</p>}
    </>
  );
}
