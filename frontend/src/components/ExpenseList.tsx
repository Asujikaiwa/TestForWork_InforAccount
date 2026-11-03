"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { satangFromApi } from "@/lib/money";
import type { Expense } from "@/lib/types";
import { ErrorBanner } from "./ErrorBanner";
import { Money } from "./Money";

const dateFormat = new Intl.DateTimeFormat("en-GB", {
  dateStyle: "medium",
  timeStyle: "short",
});

export function ExpenseList({
  user,
  groupId,
  expenses,
  onDeleted,
}: {
  user: string;
  groupId: number;
  expenses: Expense[];
  onDeleted: () => void;
}) {
  if (expenses.length === 0) {
    return <p className="text-sm text-zinc-500">No expenses yet.</p>;
  }
  return (
    <ul className="space-y-3">
      {expenses.map((expense) => (
        <ExpenseItem
          key={expense.id}
          user={user}
          groupId={groupId}
          expense={expense}
          onDeleted={onDeleted}
        />
      ))}
    </ul>
  );
}

function ExpenseItem({
  user,
  groupId,
  expense,
  onDeleted,
}: {
  user: string;
  groupId: number;
  expense: Expense;
  onDeleted: () => void;
}) {
  const [confirming, setConfirming] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<unknown>(undefined);

  // The server enforces "payer only"; hiding the button just avoids offering
  // an action that is guaranteed to fail.
  const canDelete = expense.paid_by === user;

  async function handleDelete() {
    setDeleting(true);
    setError(undefined);
    try {
      await api.deleteExpense(user, groupId, expense.id);
      onDeleted();
    } catch (err) {
      setError(err);
      setDeleting(false);
      setConfirming(false);
    }
  }

  return (
    <li className="rounded-md border border-zinc-200 p-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-medium">{expense.description}</p>
          <p className="text-xs text-zinc-500">
            Paid by {expense.paid_by} · {dateFormat.format(new Date(expense.created_at))}
            {" · "}
            {expense.split_type === "equal" ? "split equally" : "exact amounts"}
          </p>
        </div>
        <Money satang={satangFromApi(expense.amount)} className="font-semibold" />
      </div>

      <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-zinc-600">
        {expense.shares.map((share) => (
          <li key={share.member}>
            {share.member}: <Money satang={satangFromApi(share.amount)} />
          </li>
        ))}
      </ul>

      {canDelete && (
        <div className="mt-2 flex gap-2 text-xs">
          {confirming ? (
            <>
              <span className="text-zinc-600">Delete this expense?</span>
              <button
                type="button"
                onClick={handleDelete}
                disabled={deleting}
                className="font-medium text-red-700 hover:underline disabled:opacity-50"
              >
                {deleting ? "Deleting…" : "Yes, delete"}
              </button>
              <button
                type="button"
                onClick={() => setConfirming(false)}
                disabled={deleting}
                className="text-zinc-600 hover:underline"
              >
                Cancel
              </button>
            </>
          ) : (
            <button
              type="button"
              onClick={() => setConfirming(true)}
              className="text-zinc-600 hover:text-red-700 hover:underline"
            >
              Delete
            </button>
          )}
        </div>
      )}
      {error !== undefined && (
        <div className="mt-2">
          <ErrorBanner error={error} />
        </div>
      )}
    </li>
  );
}
