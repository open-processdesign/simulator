import { useTranslation } from "react-i18next";
import { CATEGORIES, UNITS } from "./catalog";
import { CATEGORY_COLOR, UNIT_ICONS } from "./icons";

export const DRAG_TYPE = "application/opd-unit";

/** Unit palette by category (left column). Drag onto the canvas, or click to add. */
export function Palette({ onAdd }: { onAdd: (unitType: string) => void }) {
  const { t } = useTranslation();
  return (
    <aside aria-label={t("flowsheet.palette")} className="flex w-[var(--opd-palette-w)] shrink-0 flex-col gap-3 overflow-y-auto border-r border-border bg-surface p-3">
      <p className="text-xs text-muted">{t("flowsheet.drag_hint")}</p>
      {CATEGORIES.map((cat) => {
        const units = UNITS.filter((u) => u.category === cat);
        return (
          <section key={cat} className="flex flex-col gap-1">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-subtle">{t(`flowsheet.categories.${cat}`)}</h3>
            {units.map((u) => {
              const Icon = UNIT_ICONS[u.type];
              return (
                <button
                  key={u.type}
                  type="button"
                  disabled={!u.available}
                  draggable={u.available}
                  onDragStart={(e) => {
                    e.dataTransfer.setData(DRAG_TYPE, u.type);
                    e.dataTransfer.effectAllowed = "move";
                  }}
                  onClick={() => onAdd(u.type)}
                  className="flex items-center gap-2 rounded-sm px-2 py-1 text-left text-sm hover:bg-surface-muted disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {Icon && <Icon aria-hidden className="size-4 shrink-0" style={{ color: CATEGORY_COLOR[u.category] }} />}
                  <span className="flex-1">{t(`units.${u.type}`)}</span>
                  {!u.available && <span className="text-[11px] text-subtle">{t("flowsheet.coming_later")}</span>}
                </button>
              );
            })}
          </section>
        );
      })}
    </aside>
  );
}
