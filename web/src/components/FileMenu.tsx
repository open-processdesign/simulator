import { useEffect, useRef, useState, type ChangeEvent } from "react";
import { useTranslation } from "react-i18next";
import { ChevronDown } from "lucide-react";
import { EXAMPLES } from "@/examples";
import { emptyFlowsheet, type Flowsheet } from "@/opd/types";
import { useFlowsheet } from "@/state/FlowsheetProvider";
import { downloadDocument, parseDocument } from "@/state/persistence";
import { useSelection } from "@/state/SelectionProvider";
import { cn } from "@/lib/utils";

/** File menu: new, open, save, and the example gallery. Files are OPD JSON (`.opd.json`). */
export function FileMenu() {
  const { t } = useTranslation();
  const { doc, dispatch } = useFlowsheet();
  const { setSelection } = useSelection();
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const root = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent | KeyboardEvent) => {
      if (e instanceof KeyboardEvent ? e.key === "Escape" : !root.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", close);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", close);
    };
  }, [open]);

  const replace = (next: Flowsheet) => {
    const hasWork = doc.components.length > 0 || doc.units.length > 0;
    if (hasWork && !window.confirm(t("file.confirm_replace", { name: doc.name }))) return;
    dispatch({ type: "replace", doc: next });
    setSelection(null);
    setOpen(false);
    setError(null);
  };

  const onFile = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    const parsed = parseDocument(await file.text());
    if (!parsed.ok) {
      setError(t(`file.error_${parsed.reason}`, { file: file.name }));
      setOpen(false);
      return;
    }
    replace(parsed.doc);
    window.location.hash = "#/flowsheet";
  };

  const item = "w-full rounded-sm px-3 py-1.5 text-left text-sm hover:bg-surface-muted";

  return (
    <div ref={root} className="relative">
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1 rounded-sm px-2 py-1 text-sm text-muted hover:bg-surface-muted hover:text-text"
      >
        {t("file.menu")}
        <ChevronDown aria-hidden className="size-3.5" />
      </button>
      {open && (
        <div role="menu" aria-label={t("file.menu")} className="absolute left-0 top-9 z-50 w-72 rounded-md border border-border bg-surface p-1 shadow-[var(--opd-shadow)]">
          <button role="menuitem" type="button" className={item} onClick={() => replace(emptyFlowsheet(t("file.untitled")))}>{t("file.new")}</button>
          <button role="menuitem" type="button" className={item} onClick={() => fileInput.current?.click()}>{t("file.open")}</button>
          <button role="menuitem" type="button" className={item} onClick={() => { downloadDocument(doc); setOpen(false); }}>{t("file.save")}</button>
          <div className="my-1 border-t border-border" />
          <p className="px-3 py-1 text-xs font-semibold uppercase tracking-wide text-subtle">{t("file.examples")}</p>
          {EXAMPLES.map((ex) => (
            <button key={ex.file} role="menuitem" type="button" title={ex.doc.description} className={cn(item, "flex flex-col")}
              onClick={() => { replace(structuredClone(ex.doc)); window.location.hash = "#/flowsheet"; }}>
              <span>{ex.doc.name}</span>
            </button>
          ))}
        </div>
      )}
      <input ref={fileInput} type="file" accept=".json,application/json" className="hidden" aria-label={t("file.open")} onChange={onFile} />
      {error && (
        <p role="alert" className="absolute left-0 top-9 z-50 w-72 rounded-md border border-error bg-surface p-2 text-xs text-error">
          {error}
          <button type="button" className="ml-2 underline" onClick={() => setError(null)}>{t("file.dismiss")}</button>
        </p>
      )}
    </div>
  );
}

/** Process name, editable in place (top bar). */
export function ProcessName() {
  const { t } = useTranslation();
  const { doc, dispatch } = useFlowsheet();
  return (
    <input
      key={doc.name}
      aria-label={t("file.process_name")}
      defaultValue={doc.name}
      onBlur={(e) => dispatch({ type: "set_name", name: e.target.value })}
      onKeyDown={(e) => e.key === "Enter" && (e.target as HTMLInputElement).blur()}
      className="w-44 truncate rounded-sm border border-transparent bg-transparent px-1.5 py-0.5 text-sm text-muted hover:border-border focus:border-border-strong focus:text-text"
    />
  );
}
