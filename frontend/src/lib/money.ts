/**
 * Money helpers.
 *
 * Every amount inside the frontend is an integer number of **satang**
 * (1 THB = 100 satang). We never turn user input into a JavaScript float:
 * strings are parsed digit by digit into an integer, and integers are turned
 * back into strings digit by digit. Integer arithmetic on `number` is exact up
 * to Number.MAX_SAFE_INTEGER (~9.0e15), far above the largest NUMERIC(12,2)
 * value the backend can store (999,999,999,999 satang), so `0.1 + 0.2` is
 * `10 + 20 = 30` satang and displays as "0.30".
 */

export type Satang = number;

/** Largest value of a NUMERIC(12,2) column: 9,999,999,999.99 THB. */
export const MAX_SATANG: Satang = 999_999_999_999;

export type AmountProblem =
  | "empty"
  | "format"
  | "precision"
  | "zero"
  | "negative"
  | "too_large";

export type ParseResult =
  | { ok: true; satang: Satang }
  | { ok: false; problem: AmountProblem };

// Digits, optionally followed by "." and more digits. "10", "10.", "10.5",
// ".5" are all accepted while the user types. Precision is checked separately
// so that "10.005" reports "too many decimals" instead of "not a number".
const AMOUNT_PATTERN = /^(\d*)(?:\.(\d*))?$/;

/**
 * Parse what the user typed into satang.
 * Thousands separators ("1,000.00") and surrounding spaces are tolerated.
 */
export function parseAmount(input: string): ParseResult {
  const cleaned = input.trim().replace(/,/g, "");
  if (cleaned === "") return { ok: false, problem: "empty" };
  if (cleaned.startsWith("-")) return { ok: false, problem: "negative" };

  const match = AMOUNT_PATTERN.exec(cleaned);
  if (!match) return { ok: false, problem: "format" };

  const whole = match[1] ?? "";
  const fraction = match[2] ?? "";
  if (whole === "" && fraction === "") return { ok: false, problem: "format" };
  if (fraction.length > 2) return { ok: false, problem: "precision" };

  const wholeDigits = whole.replace(/^0+/, "");
  // Reject before Number() so a huge string can never lose precision.
  if (wholeDigits.length > 10) return { ok: false, problem: "too_large" };

  const satang =
    Number(wholeDigits || "0") * 100 + Number(fraction.padEnd(2, "0"));
  if (satang > MAX_SATANG) return { ok: false, problem: "too_large" };
  if (satang === 0) return { ok: false, problem: "zero" };
  return { ok: true, satang };
}

/** Parse a money string sent by the API, e.g. "333.33" or "-333.33". */
export function satangFromApi(value: string): Satang {
  const match = /^(-)?(\d+)\.(\d{2})$/.exec(value);
  if (!match) {
    throw new Error(`Unexpected money value from API: ${JSON.stringify(value)}`);
  }
  const [, minus, whole, fraction] = match;
  const satang = Number(whole) * 100 + Number(fraction);
  return minus ? -satang : satang;
}

/** Serialise satang for a request body: 100000 -> "1000.00". */
export function satangToApi(satang: Satang): string {
  assertInteger(satang);
  const sign = satang < 0 ? "-" : "";
  const abs = Math.abs(satang);
  const whole = Math.floor(abs / 100);
  const fraction = String(abs % 100).padStart(2, "0");
  return `${sign}${whole}.${fraction}`;
}

const wholeFormatter = new Intl.NumberFormat("th-TH", {
  maximumFractionDigits: 0,
});

/**
 * Thai display format: 100000 -> "1,000.00", -33333 -> "-333.33".
 * The whole part goes through Intl (grouping separators); the two decimals
 * are appended as text, so no fractional number is ever created.
 */
export function formatSatang(
  satang: Satang,
  options: { signed?: boolean } = {},
): string {
  assertInteger(satang);
  const abs = Math.abs(satang);
  const whole = wholeFormatter.format(Math.floor(abs / 100));
  const fraction = String(abs % 100).padStart(2, "0");
  let sign = "";
  if (satang < 0) sign = "-";
  else if (options.signed && satang > 0) sign = "+";
  return `${sign}${whole}.${fraction}`;
}

function assertInteger(satang: Satang): void {
  if (!Number.isSafeInteger(satang)) {
    throw new Error(`Satang must be a safe integer, got ${satang}`);
  }
}
