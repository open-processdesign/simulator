import { describe, expect, it } from "vitest";
import { formatNumber, parseNumber } from "./format";

describe("numbers", () => {
  it("formats with the locale's decimal separator", () => {
    expect(formatNumber(78.114, "en", 2)).toBe("78.11");
    expect(formatNumber(78.114, "tr", 2)).toBe("78,11");
  });

  it("parses decimal points and commas, rejects text", () => {
    expect(parseNumber("0.05")).toBe(0.05);
    expect(parseNumber("0,05")).toBe(0.05);
    expect(parseNumber("-1e-3")).toBe(-0.001);
    expect(parseNumber("abc")).toBeNull();
    expect(parseNumber("")).toBeNull();
  });
});
