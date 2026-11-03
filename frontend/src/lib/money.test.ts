import { describe, expect, it } from "vitest";
import {
  formatSatang,
  MAX_SATANG,
  parseAmount,
  satangFromApi,
  satangToApi,
} from "./money";

describe("parseAmount", () => {
  it.each([
    ["1000.00", 100_000],
    ["1000", 100_000],
    ["1,000.00", 100_000],
    ["  12.5 ", 1_250],
    ["0.01", 1],
    [".5", 50],
    ["10.", 1_000],
    ["9999999999.99", MAX_SATANG],
  ])("parses %j as %i satang", (input, satang) => {
    expect(parseAmount(input)).toEqual({ ok: true, satang });
  });

  it.each([
    ["", "empty"],
    ["   ", "empty"],
    ["10.005", "precision"],
    ["0", "zero"],
    ["0.00", "zero"],
    ["-5", "negative"],
    ["abc", "format"],
    ["1e3", "format"],
    ["1.2.3", "format"],
    [".", "format"],
    ["10000000000.00", "too_large"],
    ["99999999999999999999", "too_large"],
  ])("rejects %j as %s", (input, problem) => {
    expect(parseAmount(input)).toEqual({ ok: false, problem });
  });
});

describe("formatSatang (Thai format)", () => {
  it("formats with thousands separators and 2 decimals", () => {
    expect(formatSatang(100_000)).toBe("1,000.00");
    expect(formatSatang(123_456_789)).toBe("1,234,567.89");
    expect(formatSatang(5)).toBe("0.05");
    expect(formatSatang(0)).toBe("0.00");
  });

  it("formats negatives and optional plus sign", () => {
    expect(formatSatang(-33_333)).toBe("-333.33");
    expect(formatSatang(66_666, { signed: true })).toBe("+666.66");
    expect(formatSatang(0, { signed: true })).toBe("0.00");
  });

  it("is free of floating point error: 0.1 + 0.2 shows 0.30", () => {
    const a = parseAmount("0.1");
    const b = parseAmount("0.2");
    if (!a.ok || !b.ok) throw new Error("parse failed");
    expect(formatSatang(a.satang + b.satang)).toBe("0.30");
  });

  it("refuses non-integer satang", () => {
    expect(() => formatSatang(0.5)).toThrow();
  });
});

describe("API money strings", () => {
  it("round-trips", () => {
    expect(satangToApi(100_000)).toBe("1000.00");
    expect(satangToApi(1)).toBe("0.01");
    expect(satangToApi(-33_333)).toBe("-333.33");
    expect(satangFromApi("333.34")).toBe(33_334);
    expect(satangFromApi("-333.33")).toBe(-33_333);
    expect(satangFromApi("0.00")).toBe(0);
  });

  it("rejects unexpected formats instead of guessing", () => {
    expect(() => satangFromApi("333.3")).toThrow();
    expect(() => satangFromApi("1,000.00")).toThrow();
  });
});
