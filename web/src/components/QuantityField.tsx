import { useEffect, useId, useState } from "react";
import { useTranslation } from "react-i18next";
import { cn } from "@/lib/utils";
import { parseNumber } from "@/lib/format";
import { useUnits } from "@/units/UnitSetProvider";

/**
 * Number input with a unit suffix (DESIGN_SYSTEM.md → Input with unit suffix).
 * `name` is the OPD spec / state name (e.g. "temperature", "pressure_drop"); the value is SI
 * and is shown and typed in the user's unit set. Accepts a decimal comma; commits on blur or
 * Enter; empty clears the value.
 */
export function QuantityField({ label, name, value, onCommit, compact = false }: {
  label: string;
  name: string;
  value: number | undefined;
  onCommit: (value: number | null) => void;
  compact?: boolean;
}) {
  const { i18n } = useTranslation();
  const units = useUnits();
  const id = useId();
  const unit = units.unit(name);
  const display = value === undefined ? undefined : units.toDisplay(name, value);
  const shown = display === undefined ? ""
    : Number(display.toPrecision(12)).toLocaleString(i18n.resolvedLanguage, { maximumFractionDigits: 10, useGrouping: false });
  const [text, setText] = useState(shown);
  useEffect(() => setText(shown), [shown]);
  const invalid = text.trim() !== "" && parseNumber(text) === null;

  const commit = () => {
    if (text.trim() === "") return value !== undefined && onCommit(null);
    const parsed = parseNumber(text);
    if (parsed === null) return setText(shown);
    if (text.trim() === shown) return;
    onCommit(units.fromDisplay(name, parsed));
  };

  return (
    <div className={cn("flex items-center gap-2", compact ? "" : "justify-between")}>
      <label htmlFor={id} className="text-sm text-muted">{label}</label>
      <div
        className={cn(
          "flex h-7 items-center rounded-sm border bg-surface focus-within:shadow-[var(--opd-focus)]",
          invalid ? "border-error" : "border-border-strong",
        )}
      >
        <input
          id={id}
          inputMode="decimal"
          aria-invalid={invalid}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onBlur={commit}
          onKeyDown={(e) => e.key === "Enter" && (e.target as HTMLInputElement).blur()}
          className="num w-28 bg-transparent px-2 text-right text-sm outline-none focus-visible:shadow-none"
        />
        <span className="num w-12 border-l border-border px-1.5 text-xs text-muted">{unit}</span>
      </div>
    </div>
  );
}
