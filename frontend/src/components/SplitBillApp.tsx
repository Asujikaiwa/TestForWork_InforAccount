"use client";

import { useCallback, useState } from "react";
import { api } from "@/lib/api";
import { KNOWN_USERS } from "@/lib/config";
import { useApi } from "@/lib/use-api";
import { BalancesPanel } from "./BalancesPanel";
import { ErrorBanner } from "./ErrorBanner";
import { ExpenseForm } from "./ExpenseForm";
import { ExpenseList } from "./ExpenseList";

export function SplitBillApp() {
  const [user, setUser] = useState<string>(KNOWN_USERS[0]);
  const [chosenGroupId, setChosenGroupId] = useState<number | null>(null);
  // Bumped after every create/delete to refetch expenses and balances.
  const [version, setVersion] = useState(0);
  const refresh = useCallback(() => setVersion((v) => v + 1), []);

  const groups = useApi(
    user,
    0,
    useCallback((signal: AbortSignal) => api.listGroups(user, signal), [user]),
  );

  // Derived instead of synced with an effect: keep the chosen group if this
  // user is a member of it, otherwise fall back to their first group.
  const groupId =
    groups.data?.find((g) => g.id === chosenGroupId)?.id ??
    groups.data?.[0]?.id ??
    null;
  const scope = groupId === null ? null : `${user}|${groupId}`;

  const group = useApi(
    scope,
    0,
    useCallback(
      (signal: AbortSignal) => api.getGroup(user, groupId!, signal),
      [user, groupId],
    ),
  );
  const expenses = useApi(
    scope,
    version,
    useCallback(
      (signal: AbortSignal) => api.listExpenses(user, groupId!, signal),
      [user, groupId],
    ),
  );
  const balances = useApi(
    scope,
    version,
    useCallback(
      (signal: AbortSignal) => api.getBalances(user, groupId!, signal),
      [user, groupId],
    ),
  );

  return (
    <div className="mx-auto w-full max-w-5xl space-y-6 px-4 py-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">SplitBill</h1>
          <p className="text-sm text-zinc-500">Shared expenses, accurate to the satang.</p>
        </div>
        <div className="flex flex-wrap gap-3">
          <label className="text-sm">
            <span className="block font-medium">You are</span>
            <select
              value={user}
              onChange={(e) => setUser(e.target.value)}
              className="mt-1 rounded-md border border-zinc-300 px-2.5 py-1.5"
            >
              {KNOWN_USERS.map((u) => (
                <option key={u} value={u}>
                  {u}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            <span className="block font-medium">Group</span>
            <select
              value={groupId ?? ""}
              onChange={(e) => setChosenGroupId(Number(e.target.value))}
              disabled={!groups.data?.length}
              className="mt-1 min-w-48 rounded-md border border-zinc-300 px-2.5 py-1.5"
            >
              {groups.data?.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.name}
                </option>
              ))}
            </select>
          </label>
        </div>
      </header>

      <ErrorBanner error={groups.error} />
      {groups.loading && !groups.data && <p className="text-sm text-zinc-500">Loading groups…</p>}
      {groups.data?.length === 0 && (
        <p className="text-sm text-zinc-500">{user} isn&apos;t in any group yet.</p>
      )}

      {groupId !== null && (
        <div className="grid gap-6 md:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)]">
          <section className="rounded-lg border border-zinc-200 bg-white p-4">
            <ErrorBanner error={group.error} />
            {group.data ? (
              <ExpenseForm
                key={`${user}|${group.data.id}`}
                user={user}
                group={group.data}
                onCreated={refresh}
              />
            ) : (
              !group.error && <p className="text-sm text-zinc-500">Loading group…</p>
            )}
          </section>

          <div className="space-y-6">
            <section className="rounded-lg border border-zinc-200 bg-white p-4">
              <h2 className="mb-2 text-lg font-semibold">Balances</h2>
              <ErrorBanner error={balances.error} />
              {balances.data ? (
                <BalancesPanel balances={balances.data.balances} />
              ) : (
                !balances.error && <p className="text-sm text-zinc-500">Loading balances…</p>
              )}
            </section>

            <section className="rounded-lg border border-zinc-200 bg-white p-4">
              <h2 className="mb-2 text-lg font-semibold">Expenses</h2>
              <ErrorBanner error={expenses.error} />
              {expenses.data ? (
                <ExpenseList
                  user={user}
                  groupId={groupId}
                  expenses={expenses.data}
                  onDeleted={refresh}
                />
              ) : (
                !expenses.error && <p className="text-sm text-zinc-500">Loading expenses…</p>
              )}
            </section>
          </div>
        </div>
      )}
    </div>
  );
}
