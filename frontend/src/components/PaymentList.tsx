import { satangFromApi } from "@/lib/money";
import type { Payment } from "@/lib/types";
import { Money } from "./Money";

const dateFormat = new Intl.DateTimeFormat("en-GB", {
  dateStyle: "medium",
  timeStyle: "short",
});

export function PaymentList({ payments }: { payments: Payment[] }) {
  if (payments.length === 0) {
    return <p className="text-sm text-zinc-500">No repayments yet.</p>;
  }
  return (
    <ul aria-label="Repayments" className="divide-y divide-zinc-100 text-sm">
      {payments.map((p) => (
        <li key={p.id} className="flex items-center justify-between gap-3 py-2">
          <span>
            <span className="font-medium">{p.from}</span> paid{" "}
            <span className="font-medium">{p.to}</span>
            <span className="block text-xs text-zinc-500">
              {dateFormat.format(new Date(p.created_at))} · recorded by {p.created_by}
            </span>
          </span>
          <Money satang={satangFromApi(p.amount)} className="font-semibold" />
        </li>
      ))}
    </ul>
  );
}
