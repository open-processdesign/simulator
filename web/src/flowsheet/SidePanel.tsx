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

import type { Selection } from "@/state/SelectionProvider";

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
      {unit.type === "conversion_reactor" && <ReactionsEditor unit={unit} />}
      {unit.type === "shortcut_column" && <KeysEditor unit={unit} />}
      {(unit.type === "cstr" || unit.type === "pfr") && <KineticsEditor unit={unit} />}
      {unit.type === "equilibrium_reactor" && <EquilibriumEditor unit={unit} />}
      {unit.type === "heat_exchanger" && <GeometryEditor unit={unit} />}
      {unit.type === "heat_exchanger" && <ZonesEditor unit={unit} />}

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
              {t(`flowsheet.none_label.${group.key}`, { defaultValue: t("flowsheet.none") })}
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
          name={active}
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
          name="fraction"
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
      <QuantityField label={t(`flowsheet.specs.${thermal}`)} name={thermal} value={st[thermal]?.value}
        onCommit={(v) => setField(thermal, v, [thermal === "temperature" ? "vapor_fraction" : "temperature"])} />
      <QuantityField label={t("flowsheet.specs.pressure")} name="pressure" value={st.pressure?.value} onCommit={(v) => setField("pressure", v)} />
      <QuantityField label={t("flowsheet.specs.molar_flow")} name="molar_flow" value={st.molar_flow?.value} onCommit={(v) => setField("molar_flow", v)} />

      <h4 className="mt-2 text-sm font-semibold">{t("flowsheet.composition")}</h4>
      {doc.components.length === 0 ? (
        <p className="text-sm text-muted">{t("flowsheet.no_components")}</p>
      ) : (
        <>
          {doc.components.map((c) => (
            <QuantityField key={c.id} label={c.name} name="fraction" value={fractions[c.id]}
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

type Reaction = { stoichiometry: Record<string, number>; key: string; conversion: number };

function ReactionsEditor({ unit }: { unit: Unit }) {
  const { t } = useTranslation();
  const { doc, dispatch } = useFlowsheet();
  const reactions = (unit.options?.reactions as Reaction[] | undefined) ?? [];
  const save = (next: Reaction[]) => dispatch({ type: "set_options", id: unit.id, options: { reactions: next } });
  const update = (k: number, patch: Partial<Reaction>) => save(reactions.map((r, i) => (i === k ? { ...r, ...patch } : r)));

  if (doc.components.length === 0) return <p className="text-sm text-muted">{t("flowsheet.no_components")}</p>;
  return (
    <fieldset className="flex flex-col gap-3 rounded-md border border-border bg-surface p-3">
      <legend className="px-1 text-sm font-semibold">{t("flowsheet.specs.reactions")}</legend>
      {reactions.map((r, k) => (
        <div key={k} className="flex flex-col gap-1.5 border-b border-border pb-3 last:border-0 last:pb-0">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">{t("flowsheet.reaction_n", { n: k + 1 })}</span>
            <Button variant="ghost" size="sm" aria-label={t("flowsheet.remove_reaction", { n: k + 1 })}
              onClick={() => save(reactions.filter((_, i) => i !== k))}>
              <Trash2 aria-hidden />
            </Button>
          </div>
          <p className="text-xs text-muted">{t("flowsheet.stoich_hint")}</p>
          {doc.components.map((c) => (
            <QuantityField key={c.id} label={`ν ${c.name}`} name="number" value={r.stoichiometry[c.id]}
              onCommit={(v) => {
                const stoich = { ...r.stoichiometry };
                if (v === null || v === 0) delete stoich[c.id];
                else stoich[c.id] = v;
                update(k, { stoichiometry: stoich });
              }} />
          ))}
          <label className="flex items-center justify-between gap-2 text-sm text-muted">
            {t("flowsheet.key_component")}
            <select value={r.key} onChange={(e) => update(k, { key: e.target.value })}
              className="h-7 w-[11.5rem] rounded-sm border border-border-strong bg-surface px-2 text-sm text-text">
              <option value="">–</option>
              {doc.components.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </label>
          <QuantityField label={t("flowsheet.conversion")} name="fraction" value={r.conversion}
            onCommit={(v) => update(k, { conversion: v ?? 0 })} />
        </div>
      ))}
      <Button variant="secondary" size="sm" onClick={() => save([...reactions, { stoichiometry: {}, key: "", conversion: 0.5 }])}>
        {t("flowsheet.add_reaction")}
      </Button>
    </fieldset>
  );
}

function KeysEditor({ unit }: { unit: Unit }) {
  const { t } = useTranslation();
  const { doc, dispatch } = useFlowsheet();
  if (doc.components.length === 0) return <p className="text-sm text-muted">{t("flowsheet.no_components")}</p>;
  return (
    <fieldset className="flex flex-col gap-2 rounded-md border border-border bg-surface p-3">
      <legend className="px-1 text-sm font-semibold">{t("flowsheet.keys")}</legend>
      {(["light_key", "heavy_key"] as const).map((key) => (
        <label key={key} className="flex items-center justify-between gap-2 text-sm text-muted">
          {t(`flowsheet.specs.${key}`)}
          <select value={(unit.options?.[key] as string | undefined) ?? ""}
            onChange={(e) => dispatch({ type: "set_options", id: unit.id, options: { [key]: e.target.value || undefined } })}
            className="h-7 w-[11.5rem] rounded-sm border border-border-strong bg-surface px-2 text-sm text-text">
            <option value="">–</option>
            {doc.components.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </label>
      ))}
      <p className="text-xs text-muted">{t("flowsheet.column_note")}</p>
    </fieldset>
  );
}

type RateLaw = { stoichiometry: Record<string, number>; k0: number; Ea: number; orders: Record<string, number> };

function KineticsEditor({ unit }: { unit: Unit }) {
  const { t } = useTranslation();
  const { doc, dispatch } = useFlowsheet();
  const reactions = (unit.options?.reactions as RateLaw[] | undefined) ?? [];
  const phase = (unit.options?.phase as string | undefined) ?? "gas";
  const save = (next: RateLaw[]) => dispatch({ type: "set_options", id: unit.id, options: { reactions: next } });
  const update = (k: number, patch: Partial<RateLaw>) => save(reactions.map((r, i) => (i === k ? { ...r, ...patch } : r)));
  const setMap = (k: number, key: "stoichiometry" | "orders", cid: string, v: number | null) => {
    const map = { ...reactions[k][key] };
    if (v === null || v === 0) delete map[cid];
    else map[cid] = v;
    update(k, { [key]: map } as Partial<RateLaw>);
  };

  if (doc.components.length === 0) return <p className="text-sm text-muted">{t("flowsheet.no_components")}</p>;
  return (
    <fieldset className="flex flex-col gap-3 rounded-md border border-border bg-surface p-3">
      <legend className="px-1 text-sm font-semibold">{t("flowsheet.kinetics")}</legend>
      <label className="flex items-center justify-between gap-2 text-sm text-muted">
        {t("flowsheet.phase")}
        <select value={phase} onChange={(e) => dispatch({ type: "set_options", id: unit.id, options: { phase: e.target.value } })}
          className="h-7 w-[11.5rem] rounded-sm border border-border-strong bg-surface px-2 text-sm text-text">
          <option value="gas">{t("flowsheet.phase_gas")}</option>
          <option value="liquid">{t("flowsheet.phase_liquid")}</option>
        </select>
      </label>
      <p className="text-xs text-muted">{t("flowsheet.rate_hint")}</p>
      {reactions.map((r, k) => (
        <div key={k} className="flex flex-col gap-1.5 border-t border-border pt-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">{t("flowsheet.reaction_n", { n: k + 1 })}</span>
            <Button variant="ghost" size="sm" aria-label={t("flowsheet.remove_reaction", { n: k + 1 })}
              onClick={() => save(reactions.filter((_, i) => i !== k))}>
              <Trash2 aria-hidden />
            </Button>
          </div>
          {doc.components.map((c) => (
            <QuantityField key={`nu-${c.id}`} label={`ν ${c.name}`} name="number" value={r.stoichiometry[c.id]}
              onCommit={(v) => setMap(k, "stoichiometry", c.id, v)} />
          ))}
          <QuantityField label={t("flowsheet.k0")} name="rate_constant" value={r.k0} onCommit={(v) => update(k, { k0: v ?? 0 })} />
          <QuantityField label={t("flowsheet.Ea")} name="activation_energy" value={r.Ea} onCommit={(v) => update(k, { Ea: v ?? 0 })} />
          {doc.components.map((c) => (
            <QuantityField key={`n-${c.id}`} label={t("flowsheet.order_of", { name: c.name })} name="order" value={r.orders[c.id]}
              onCommit={(v) => setMap(k, "orders", c.id, v)} />
          ))}
        </div>
      ))}
      <Button variant="secondary" size="sm" onClick={() => save([...reactions, { stoichiometry: {}, k0: 1, Ea: 0, orders: {} }])}>
        {t("flowsheet.add_reaction")}
      </Button>
    </fieldset>
  );
}

type EqReaction = { stoichiometry: Record<string, number>; ln_k?: { a?: number; b?: number; c?: number } };

function EquilibriumEditor({ unit }: { unit: Unit }) {
  const { t } = useTranslation();
  const { doc, dispatch } = useFlowsheet();
  const reactions = (unit.options?.reactions as EqReaction[] | undefined) ?? [];
  const phase = (unit.options?.phase as string | undefined) ?? "gas";
  const save = (next: EqReaction[]) => dispatch({ type: "set_options", id: unit.id, options: { reactions: next } });
  const update = (k: number, r: EqReaction) => save(reactions.map((x, i) => (i === k ? r : x)));
  if (doc.components.length === 0) return <p className="text-sm text-muted">{t("flowsheet.no_components")}</p>;
  return (
    <fieldset className="flex flex-col gap-3 rounded-md border border-border bg-surface p-3">
      <legend className="px-1 text-sm font-semibold">{t("flowsheet.specs.reactions")}</legend>
      <label className="flex items-center justify-between gap-2 text-sm text-muted">
        {t("flowsheet.phase")}
        <select value={phase} onChange={(e) => dispatch({ type: "set_options", id: unit.id, options: { phase: e.target.value } })}
          className="h-7 w-[11.5rem] rounded-sm border border-border-strong bg-surface px-2 text-sm text-text">
          <option value="gas">{t("flowsheet.phase_gas")}</option>
          <option value="liquid">{t("flowsheet.phase_liquid")}</option>
        </select>
      </label>
      <p className="text-xs text-muted">{t(phase === "liquid" ? "flowsheet.equilibrium_hint_liquid" : "flowsheet.equilibrium_hint")}</p>
      {reactions.map((r, k) => (
        <div key={k} className="flex flex-col gap-1.5 border-t border-border pt-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">{t("flowsheet.reaction_n", { n: k + 1 })}</span>
            <Button variant="ghost" size="sm" aria-label={t("flowsheet.remove_reaction", { n: k + 1 })}
              onClick={() => save(reactions.filter((_, i) => i !== k))}>
              <Trash2 aria-hidden />
            </Button>
          </div>
          {doc.components.map((c) => (
            <QuantityField key={c.id} label={`ν ${c.name}`} name="number" value={r.stoichiometry[c.id]}
              onCommit={(v) => {
                const st = { ...r.stoichiometry };
                if (v === null || v === 0) delete st[c.id];
                else st[c.id] = v;
                update(k, { ...r, stoichiometry: st });
              }} />
          ))}
          <label className="flex items-center justify-between gap-2 text-sm text-muted">
            {t("flowsheet.k_source")}
            <select value={r.ln_k ? "correlation" : "formation"}
              onChange={(e) => {
                const next: EqReaction = { stoichiometry: r.stoichiometry };
                if (e.target.value === "correlation") next.ln_k = { a: 0 };
                update(k, next);
              }}
              className="h-7 w-[11.5rem] rounded-sm border border-border-strong bg-surface px-2 text-sm text-text">
              <option value="formation">{t("flowsheet.k_formation")}</option>
              <option value="correlation">{t("flowsheet.k_correlation")}</option>
            </select>
          </label>
          {r.ln_k && (
            <>
              <p className="text-xs text-muted">{t("flowsheet.k_correlation_hint")}</p>
              {(["a", "b", "c"] as const).map((name) => (
                <QuantityField key={name} label={t(`flowsheet.k_coef_${name}`)} name="number" value={r.ln_k?.[name]}
                  onCommit={(v) => {
                    const lnk = { ...r.ln_k };
                    if (v === null || v === 0) delete lnk[name];
                    else lnk[name] = v;
                    update(k, { ...r, ln_k: Object.keys(lnk).length ? lnk : { a: 0 } });
                  }} />
              ))}
            </>
          )}
        </div>
      ))}
      <Button variant="secondary" size="sm" onClick={() => save([...reactions, { stoichiometry: {} }])}>
        {t("flowsheet.add_reaction")}
      </Button>
    </fieldset>
  );
}

/** Number of equal-duty zones of a heat exchanger (engine default 10; phase changes add zones). */
function ZonesEditor({ unit }: { unit: Unit }) {
  const { t } = useTranslation();
  const { dispatch } = useFlowsheet();
  const zones = unit.options?.zones as number | undefined;
  return (
    <fieldset className="flex flex-col gap-2 rounded-md border border-border bg-surface p-3">
      <legend className="px-1 text-sm font-semibold">{t("flowsheet.zone_analysis")}</legend>
      <label className="flex items-center justify-between gap-2 text-sm text-muted">
        {t("flowsheet.specs.zones")}
        <input type="number" min={1} max={100} step={1} inputMode="numeric" placeholder="10"
          value={zones ?? ""}
          onChange={(e) => {
            const v = e.target.value === "" ? undefined : Math.round(Number(e.target.value));
            dispatch({ type: "set_options", id: unit.id, options: { zones: v !== undefined && Number.isFinite(v) ? v : undefined } });
          }}
          className="num h-7 w-[11.5rem] rounded-sm border border-border-strong bg-surface px-2 text-right text-sm text-text" />
      </label>
      <p className="text-xs text-muted">{t("flowsheet.zones_hint")}</p>
    </fieldset>
  );
}

/** Starting geometry when the user switches shell-and-tube on (SI; 19 mm tubes, 2 passes). */
const DEFAULT_GEOMETRY = {
  tube_outer_diameter: 0.019, tube_inner_diameter: 0.0148, tube_length: 4.88, tube_count: 160, tube_passes: 2,
  pitch: 0.0254, layout: "triangular", shell_inner_diameter: 0.489, baffle_spacing: 0.2, tube_side: "cold",
};
const GEOMETRY_FIELDS = ["tube_outer_diameter", "tube_inner_diameter", "tube_length", "tube_count", "pitch",
  "shell_inner_diameter", "baffle_spacing", "wall_conductivity", "fouling_tube", "fouling_shell"] as const;

/** Optional shell-and-tube geometry (Kern's method in the engine). */
function GeometryEditor({ unit }: { unit: Unit }) {
  const { t } = useTranslation();
  const { dispatch } = useFlowsheet();
  const geometry = unit.options?.geometry as Record<string, number | string> | undefined;
  const set = (next: Record<string, number | string> | undefined) =>
    dispatch({ type: "set_options", id: unit.id, options: { geometry: next } });
  const select = "h-7 w-[11.5rem] rounded-sm border border-border-strong bg-surface px-2 text-sm text-text";
  return (
    <fieldset className="flex flex-col gap-2 rounded-md border border-border bg-surface p-3">
      <legend className="px-1 text-sm font-semibold">{t("flowsheet.geometry")}</legend>
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" checked={!!geometry} onChange={(e) => set(e.target.checked ? { ...DEFAULT_GEOMETRY } : undefined)} />
        {t("flowsheet.geometry_enable")}
      </label>
      <p className="text-xs text-muted">{t("flowsheet.geometry_hint")}</p>
      {geometry && (
        <>
          <label className="flex items-center justify-between gap-2 text-sm text-muted">
            {t("flowsheet.geometry_fields.tube_side")}
            <select value={(geometry.tube_side as string) ?? "cold"} className={select}
              onChange={(e) => set({ ...geometry, tube_side: e.target.value })}>
              <option value="cold">{t("flowsheet.geometry_fields.side_cold")}</option>
              <option value="hot">{t("flowsheet.geometry_fields.side_hot")}</option>
            </select>
          </label>
          <label className="flex items-center justify-between gap-2 text-sm text-muted">
            {t("flowsheet.geometry_fields.tube_passes")}
            <select value={String(geometry.tube_passes ?? 1)} className={select}
              onChange={(e) => set({ ...geometry, tube_passes: Number(e.target.value) })}>
              {[1, 2, 4, 6, 8].map((n) => <option key={n} value={n}>{n}</option>)}
            </select>
          </label>
          <label className="flex items-center justify-between gap-2 text-sm text-muted">
            {t("flowsheet.geometry_fields.layout")}
            <select value={(geometry.layout as string) ?? "triangular"} className={select}
              onChange={(e) => set({ ...geometry, layout: e.target.value })}>
              <option value="triangular">{t("flowsheet.geometry_fields.triangular")}</option>
              <option value="square">{t("flowsheet.geometry_fields.square")}</option>
            </select>
          </label>
          {GEOMETRY_FIELDS.map((name) => (
            <QuantityField key={name} label={t(`flowsheet.geometry_fields.${name}`)} name={name}
              value={geometry[name] as number | undefined}
              onCommit={(v) => {
                const next = { ...geometry };
                if (v === null) delete next[name];
                else next[name] = name === "tube_count" ? Math.round(v) : v;
                set(next);
              }} />
          ))}
        </>
      )}
    </fieldset>
  );
}
