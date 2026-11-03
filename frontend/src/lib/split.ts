/**
 * Split calculations used by the live preview.
 *
 * These mirror the backend rules exactly so that what the user sees before
 * submitting is what the server stores:
 *   - equal split: everyone gets floor(total / n) satang, and the leftover
 *     satang are handed out one at a time to members in the order listed.
 *   - exact split: the shares must add up to the total to the satang.
 */
import { parseAmount, type AmountProblem, type Satang } from "./money";

export type Share = { member: string; satang: Satang };

export function splitEqual(total: Satang, members: readonly string[]): Share[] {
  if (members.length === 0) return [];
  const count = members.length;
  const base = Math.floor(total / count);
  const remainder = total - base * count; // always < count
  return members.map((member, index) => ({
    member,
    satang: base + (index < remainder ? 1 : 0),
  }));
}

export type ExactSummary = {
  /** Valid, non-zero shares in member order (what will be sent). */
  shares: Share[];
  /** Members whose input could not be parsed, with the reason. */
  problems: Record<string, AmountProblem>;
  allocated: Satang;
  /** total - allocated; negative means the shares exceed the total. */
  remaining: Satang | null;
};

/**
 * Summarise the per-member inputs of an exact split.
 * A blank or zero input means "this member is not part of the split".
 */
export function summarizeExact(
  total: Satang | null,
  members: readonly string[],
  inputs: Readonly<Record<string, string>>,
): ExactSummary {
  const shares: Share[] = [];
  const problems: Record<string, AmountProblem> = {};
  for (const member of members) {
    const parsed = parseAmount(inputs[member] ?? "");
    if (parsed.ok) {
      shares.push({ member, satang: parsed.satang });
    } else if (parsed.problem !== "empty" && parsed.problem !== "zero") {
      problems[member] = parsed.problem;
    }
  }
  const allocated = shares.reduce((sum, share) => sum + share.satang, 0);
  return {
    shares,
    problems,
    allocated,
    remaining: total === null ? null : total - allocated,
  };
}
