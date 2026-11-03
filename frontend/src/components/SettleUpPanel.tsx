"use client";

import { useRef, useState } from "react";
import { api } from "@/lib/api";
import { IdempotencyKeys } from "@/lib/idempotency";
import { satangFromApi } from "@/lib/money";
import type { Settlement } from "@/lib/types";
import { ErrorBanner } from "./ErrorBanner";
import { Money } from "./Money";

/**
 * Suggested payments from the backend (the fewest that settle everyone).
 * The two people involved can mark a suggestion as paid, which records it as
 * a repayment; the server re-checks who may do that.
 */
export function SettleUpPanel({
  user,
  groupId,
  suggestions,
  onRecorded,
}: {
  user: string;
  groupId: number;
  suggestions: Settlement[];
  onRecorded: () => void;
}) {
  const [pending, setPending] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(undefined);
  // Retrying the same suggestion (e.g. after a network error) reuses its key.
  const keys = useRef(new IdempotencyKeys());

  if (suggestions.length === 0) {
    return <p className="text-sm text-zinc-500">Everyone is settled up. 🎉</p>;
  }

  async function markPaid(suggestion: Settlement) {
    const id = `${suggestion.from}->${suggestion.to}`;
    setPending(id);
    setError(undefined);
    try {
      await api.createPayment(user, groupId, suggestion, keys.current.keyFor(suggestion));
      keys.current.reset();
      onRecorded();
    } catch (err) {
      setError(err);
    } finally {
      setPending(null);
    }
  }

  return (
    <div className="space-y-2">
      <ul aria-label="Suggested payments" className="divide-y divide-zinc-100">
        {suggestions.map((s) => {
          const id = `${s.from}->${s.to}`;
          const involved = user === s.from || user === s.to;
          return (
            <li key={id} className="flex items-center justify-between gap-3 py-2 text-sm">
              <span>
                <span className="font-medium">{s.from}</span> pays{" "}
                <span className="font-medium">{s.to}</span>{" "}
                <Money satang={satangFromApi(s.amount)} className="font-semibold" />
              </span>
              {involved && (
                <button
                  type="button"
                  onClick={() => markPaid(s)}
                  disabled={pending !== null}
                  className="rounded-md border border-zinc-300 px-2 py-1 text-xs font-medium hover:bg-zinc-50 disabled:opacity-50"
                >
                  {pending === id ? "Saving…" : "Mark as paid"}
                </button>
              )}
            </li>
          );
        })}
      </ul>
      <ErrorBanner error={error} />
    </div>
  );
}
