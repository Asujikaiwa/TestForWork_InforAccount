/**
 * Turn any thrown value into a sentence a user can act on.
 * The mapping is keyed on the API error `code`, never on the server's English
 * message, so wording can change on either side without breaking the other.
 */
import { ApiError } from "./api";
import type { AmountProblem } from "./money";
import { formatSatang, satangFromApi } from "./money";

export function describeError(error: unknown): string {
  if (!(error instanceof ApiError)) {
    return "Something unexpected went wrong. Please try again.";
  }
  const { code, details, status } = error;

  switch (code) {
    case "NETWORK_ERROR":
      return "Can't reach the SplitBill server. Check that the backend is running, then try again.";
    case "MISSING_USER":
    case "UNKNOWN_USER":
      return "That user isn't recognised. Pick a user from the list.";
    case "GROUP_NOT_FOUND":
    case "NOT_GROUP_MEMBER":
      return "Not a member of this group (or the group doesn't exist).";
    case "EXPENSE_NOT_FOUND":
      return "This expense no longer exists. It may already have been deleted.";
    case "NOT_PAYER":
      return "Only the person who paid for this expense can delete it.";
    case "SHARES_MISMATCH":
      return withTotals("The shares do not add up to the total", details);
    case "INVALID_AMOUNT":
      return "Amounts must be greater than 0.";
    case "AMOUNT_PRECISION":
      return "Amounts can have at most 2 decimal places (satang).";
    case "MEMBER_NOT_IN_GROUP": {
      const members = Array.isArray(details.members)
        ? details.members.filter((m): m is string => typeof m === "string")
        : [];
      return members.length > 0
        ? `Not a member of this group: ${members.join(", ")}.`
        : "Everyone in the split, and the payer, must be a member of this group.";
    }
    case "EMPTY_SPLIT":
      return "Choose at least one member to split with.";
    case "IDEMPOTENCY_KEY_REUSED":
      return "This submission clashed with an earlier one. Please submit again.";
    case "VALIDATION_ERROR":
      return "Some fields are missing or invalid. Please check the form.";
    default:
      return status >= 500
        ? "The server had a problem. Please try again in a moment."
        : `The request failed (error ${status}). Please try again.`;
  }
}

function withTotals(base: string, details: Record<string, unknown>): string {
  const { amount, shares_total: sharesTotal } = details;
  if (typeof amount !== "string" || typeof sharesTotal !== "string") {
    return `${base}.`;
  }
  try {
    return `${base}: shares add up to ${formatSatang(satangFromApi(sharesTotal))} but the total is ${formatSatang(satangFromApi(amount))}.`;
  } catch {
    return `${base}.`;
  }
}

/** Inline form messages for client-side amount validation. */
export function describeAmountProblem(problem: AmountProblem): string {
  switch (problem) {
    case "empty":
      return "Enter an amount.";
    case "format":
      return "Use digits only, e.g. 1000 or 1,000.50.";
    case "precision":
      return "At most 2 decimal places.";
    case "zero":
    case "negative":
      return "Must be greater than 0.";
    case "too_large":
      return "Too large (max 9,999,999,999.99).";
  }
}
