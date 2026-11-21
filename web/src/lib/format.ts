/** Locale-aware number formatting (decimal comma in Turkish, DESIGN_SYSTEM.md → Language). */
export function formatNumber(value: number, lang: string | undefined, digits = 2): string {
  return value.toLocaleString(lang, { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

/** Parse user input that may use a decimal comma. Returns null if it is not a number. */
export function parseNumber(text: string): number | null {
  const cleaned = text.trim().replace(/\s/g, "").replace(",", ".");
  if (!/^[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?$/.test(cleaned)) return null;
  return Number(cleaned);
}
