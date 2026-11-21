import {
  ArrowLeftRight, ArrowRightFromLine, Columns4, ArrowRightToLine, Columns3, Cylinder, Fan, Flame,
  FlaskConical, FlaskRound, Gauge, MoveRight, Merge, Split, Waves, type LucideIcon,
} from "lucide-react";
import type { Category } from "./catalog";

export const UNIT_ICONS: Record<string, LucideIcon> = {
  feed: ArrowRightFromLine,
  product: ArrowRightToLine,
  mixer: Merge,
  splitter: Split,
  flash: Cylinder,
  heater: Flame,
  valve: Gauge,
  heat_exchanger: ArrowLeftRight,
  pump: Waves,
  compressor: Fan,
  conversion_reactor: FlaskConical,
  cstr: FlaskRound,
  pfr: MoveRight,
  shortcut_column: Columns3,
  distillation_column: Columns4,
};

/** Category colours are used for palette and node icons only (DESIGN_SYSTEM.md). */
export const CATEGORY_COLOR: Record<Category, string> = {
  io: "var(--opd-text-muted)",
  mixing: "var(--opd-cat-mixing)",
  separation: "var(--opd-cat-separation)",
  heat: "var(--opd-cat-heat)",
  pressure: "var(--opd-cat-pressure)",
  reaction: "var(--opd-cat-reaction)",
};
