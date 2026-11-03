"use client";

import { useRef, useState, type FormEvent } from "react";
import { api } from "@/lib/api";
import { describeAmountProblem } from "@/lib/errors";
import { IdempotencyKeys } from "@/lib/idempotency";
import { parseAmount, satangToApi } from "@/lib/money";
import type { GroupDetail, NewPayment } from "@/lib/types";
import { ErrorBanner } from "./ErrorBanner";

/**
 * Record a repayment of any amount. The current user is preselected as the
 * payer; the server only accepts repayments recorded by the payer or receiver.
 */
export function PaymentForm({
  user,
  group,
  onRecorded,
}: {
  user: string;
  group: GroupDetail;
  onRecorded: () => void;
}) {
  const members = group.members;
  const [from, setFrom] = useState(members.includes(user) ? user : members[0]);
  const [to, setTo] = useState(members.find((m) => m !== from) ?? members[0]);
  const [amountInput, setAmountInput] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<unknown>(undefined);
  const keys = useRef(new IdempotencyKeys());

  const amount = parseAmount(amountInput);
  const amountError =
    !amount.ok && amount.problem !== "empty" ? describeAmountProblem(amount.problem) : null;
  const samePerson = from === to;
  const disabled = submitting || !amount.ok || samePerson;

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (disabled || !amount.ok) return;
    const payment: NewPayment = { from, to, amount: satangToApi(amount.satang) };
    setSubmitting(true);
    setSubmitError(undefined);
    try {
      await api.createPayment(user, group.id, payment, keys.current.keyFor(payment));
      keys.current.reset();
      setAmountInput("");
      onRecorded();
    } catch (error) {
      setSubmitError(error); // keep the key so a retry cannot double-record
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-2">
      <div className="flex flex-wrap items-end gap-2 text-sm">
        <label className="space-y-1">
          <span className="block font-medium">From</span>
          <select
            value={from}
            onChange={(e) => setFrom(e.target.value)}
            className={inputClass}
          >
            {members.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </label>
        <label className="space-y-1">
          <span className="block font-medium">To</span>
          <select value={to} onChange={(e) => setTo(e.target.value)} className={inputClass}>
            {members.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </label>
        <label className="space-y-1">
          <span className="block font-medium">Amount (THB)</span>
          <input
            value={amountInput}
            onChange={(e) => setAmountInput(e.target.value)}
            inputMode="decimal"
            autoComplete="off"
            placeholder="0.00"
            className={`${inputClass} w-28 text-right tabular-nums`}
          />
        </label>
        <button
          type="submit"
          disabled={disabled}
          className="rounded-md bg-zinc-900 px-3 py-1.5 font-medium text-white disabled:cursor-not-allowed disabled:bg-zinc-300"
        >
          {submitting ? "Saving…" : "Record repayment"}
        </button>
      </div>
      {samePerson && <p className="text-xs text-red-700">Choose two different people.</p>}
      {amountError && <p className="text-xs text-red-700">{amountError}</p>}
      <ErrorBanner error={submitError} />
    </form>
  );
}

const inputClass =
  "rounded-md border border-zinc-300 px-2.5 py-1.5 text-sm focus:border-zinc-900 focus:outline-none";
