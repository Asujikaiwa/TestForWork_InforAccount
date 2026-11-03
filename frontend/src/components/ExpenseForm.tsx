"use client";

import { useRef, useState, type FormEvent, type ReactNode } from "react";
import { api } from "@/lib/api";
import { describeAmountProblem } from "@/lib/errors";
import { IdempotencyKeys } from "@/lib/idempotency";
import { parseAmount, satangToApi } from "@/lib/money";
import { splitEqual, summarizeExact, type Share } from "@/lib/split";
import type { GroupDetail, NewExpense } from "@/lib/types";
import { ErrorBanner } from "./ErrorBanner";
import { Money } from "./Money";
import { SplitPreview } from "./SplitPreview";

type SplitType = "equal" | "exact";

const MAX_DESCRIPTION = 200;

/**
 * Expense entry with a live split preview.
 *
 * The parent remounts this component (via `key`) when the user or group
 * changes, so all state below starts fresh for each group.
 */
export function ExpenseForm({
  user,
  group,
  onCreated,
}: {
  user: string;
  group: GroupDetail;
  onCreated: () => void;
}) {
  const members = group.members;
  const [description, setDescription] = useState("");
  const [amountInput, setAmountInput] = useState("");
  const [paidBy, setPaidBy] = useState(
    members.includes(user) ? user : members[0],
  );
  const [splitType, setSplitType] = useState<SplitType>("equal");
  const [selected, setSelected] = useState<string[]>(members);
  const [exactInputs, setExactInputs] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<unknown>(undefined);
  const [showErrors, setShowErrors] = useState(false);
  const keys = useRef(new IdempotencyKeys());

  const amount = parseAmount(amountInput);
  const total = amount.ok ? amount.satang : null;

  // Keep the group's member order, which is the order the backend uses to
  // hand out leftover satang. Ticking boxes in a different order must not
  // change who gets the extra satang.
  const equalMembers = members.filter((m) => selected.includes(m));
  const exact = summarizeExact(total, members, exactInputs);

  const shares: Share[] =
    splitType === "equal"
      ? total === null
        ? []
        : splitEqual(total, equalMembers)
      : exact.shares;

  const descriptionError =
    description.trim() === ""
      ? "Enter a description."
      : description.length > MAX_DESCRIPTION
        ? `At most ${MAX_DESCRIPTION} characters.`
        : null;
  const amountError = amount.ok ? null : describeAmountProblem(amount.problem);

  const splitReady =
    splitType === "equal"
      ? equalMembers.length > 0
      : exact.shares.length > 0 &&
        Object.keys(exact.problems).length === 0 &&
        exact.remaining === 0;

  const isValid = descriptionError === null && amount.ok && splitReady;
  // The brief requires exact splits to stay disabled until the shares equal
  // the total. Other problems keep the button clickable so a click can reveal
  // what is missing (a silently disabled button is confusing).
  const disabled =
    submitting || (splitType === "exact" && exact.remaining !== 0);

  function buildPayload(): NewExpense | null {
    if (total === null) return null;
    return {
      description: description.trim(),
      paid_by: paidBy,
      amount: satangToApi(total),
      split:
        splitType === "equal"
          ? { type: "equal", members: equalMembers }
          : {
              type: "exact",
              shares: Object.fromEntries(
                exact.shares.map((s) => [s.member, satangToApi(s.satang)]),
              ),
            },
    };
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setShowErrors(true);
    const payload = buildPayload();
    if (!isValid || payload === null) return;

    setSubmitting(true);
    setSubmitError(undefined);
    try {
      await api.createExpense(user, group.id, payload, keys.current.keyFor(payload));
      keys.current.reset();
      setDescription("");
      setAmountInput("");
      setExactInputs({});
      setShowErrors(false);
      onCreated();
    } catch (error) {
      // Keep the key: resubmitting the same form must not create a duplicate.
      setSubmitError(error);
    } finally {
      setSubmitting(false);
    }
  }

  function toggleMember(member: string) {
    setSelected((current) =>
      current.includes(member)
        ? current.filter((m) => m !== member)
        : [...current, member],
    );
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-4">
      <h2 className="text-lg font-semibold">Add an expense</h2>

      <Field label="Description" error={showErrors ? descriptionError : null}>
        {(id) => (
          <input
            id={id}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            maxLength={MAX_DESCRIPTION + 1}
            placeholder="Dinner at the night market"
            className={inputClass}
          />
        )}
      </Field>

      <div className="grid grid-cols-2 gap-3">
        <Field
          label="Amount (THB)"
          // Show precision/format problems while typing; "empty" only after submit.
          error={
            amountError && (showErrors || (!amount.ok && amount.problem !== "empty"))
              ? amountError
              : null
          }
        >
          {(id) => (
            <input
              id={id}
              value={amountInput}
              onChange={(e) => setAmountInput(e.target.value)}
              inputMode="decimal"
              autoComplete="off"
              placeholder="1,000.00"
              className={`${inputClass} text-right tabular-nums`}
            />
          )}
        </Field>

        <Field label="Paid by">
          {(id) => (
            <select
              id={id}
              value={paidBy}
              onChange={(e) => setPaidBy(e.target.value)}
              className={inputClass}
            >
              {members.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          )}
        </Field>
      </div>

      <fieldset className="space-y-2">
        <legend className="text-sm font-medium">Split</legend>
        <div className="flex gap-4 text-sm">
          {(["equal", "exact"] as const).map((type) => (
            <label key={type} className="flex items-center gap-1.5">
              <input
                type="radio"
                name="split-type"
                value={type}
                checked={splitType === type}
                onChange={() => setSplitType(type)}
              />
              {type === "equal" ? "Equally" : "Exact amounts"}
            </label>
          ))}
        </div>

        {splitType === "equal" ? (
          <div className="space-y-1">
            {members.map((m) => (
              <label key={m} className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={selected.includes(m)}
                  onChange={() => toggleMember(m)}
                />
                {m}
              </label>
            ))}
            {equalMembers.length === 0 && (
              <p className="text-xs text-red-700">Choose at least one member.</p>
            )}
          </div>
        ) : (
          <>
          <ExactInputs
            members={members}
            inputs={exactInputs}
            problems={exact.problems}
            onChange={(member, value) =>
              setExactInputs((current) => ({ ...current, [member]: value }))
            }
          />
          {showErrors && exact.shares.length === 0 && (
            <p className="text-xs text-red-700">Enter at least one share.</p>
          )}
          </>
        )}
      </fieldset>

      <section className="rounded-md border border-zinc-200 bg-zinc-50 p-3">
        <h3 className="mb-1 text-sm font-medium">Preview</h3>
        <SplitPreview shares={shares} />
        {splitType === "exact" && (
          <Remaining total={total} remaining={exact.remaining} />
        )}
      </section>

      <ErrorBanner error={submitError} />

      <button
        type="submit"
        disabled={disabled}
        className="w-full rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-zinc-300"
      >
        {submitting ? "Saving…" : "Add expense"}
      </button>
    </form>
  );
}

function ExactInputs({
  members,
  inputs,
  problems,
  onChange,
}: {
  members: string[];
  inputs: Record<string, string>;
  problems: Record<string, Parameters<typeof describeAmountProblem>[0]>;
  onChange: (member: string, value: string) => void;
}) {
  return (
    <div className="space-y-2">
      {members.map((m) => {
        const id = `exact-${m}`;
        const problem = problems[m];
        return (
          <div key={m}>
            <div className="flex items-center gap-2">
              <label htmlFor={id} className="w-16 text-sm">
                {m}
              </label>
              <input
                id={id}
                value={inputs[m] ?? ""}
                onChange={(e) => onChange(m, e.target.value)}
                inputMode="decimal"
                autoComplete="off"
                placeholder="0.00"
                aria-invalid={problem !== undefined}
                className={`${inputClass} text-right tabular-nums`}
              />
            </div>
            {problem && (
              <p className="ml-18 text-xs text-red-700">
                {describeAmountProblem(problem)}
              </p>
            )}
          </div>
        );
      })}
      <p className="text-xs text-zinc-500">Leave blank for members who aren&apos;t part of this expense.</p>
    </div>
  );
}

function Remaining({
  total,
  remaining,
}: {
  total: number | null;
  remaining: number | null;
}) {
  if (total === null || remaining === null) return null;
  if (remaining === 0) {
    return (
      <p className="mt-2 text-sm font-medium text-emerald-700">
        ✓ Shares add up to the total.
      </p>
    );
  }
  return (
    <p className="mt-2 text-sm font-medium text-amber-700" aria-live="polite">
      {remaining > 0 ? (
        <>
          Unallocated: <Money satang={remaining} />
        </>
      ) : (
        <>
          Over the total by <Money satang={-remaining} />
        </>
      )}
    </p>
  );
}

function Field({
  label,
  error,
  children,
}: {
  label: string;
  error?: string | null;
  children: (id: string) => ReactNode;
}) {
  const id = `field-${label.toLowerCase().replace(/\W+/g, "-")}`;
  return (
    <div className="space-y-1">
      <label htmlFor={id} className="block text-sm font-medium">
        {label}
      </label>
      {children(id)}
      {error && <p className="text-xs text-red-700">{error}</p>}
    </div>
  );
}

const inputClass =
  "w-full rounded-md border border-zinc-300 px-2.5 py-1.5 text-sm focus:border-zinc-900 focus:outline-none";
