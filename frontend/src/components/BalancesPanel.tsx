import { satangFromApi } from "@/lib/money";
import type { Balance } from "@/lib/types";
import { Money } from "./Money";

/**
 * Net balance per member. Positive = the group owes them; negative = they owe.
 * Direction is spelled out in words, not only by colour.
 */
export function BalancesPanel({ balances }: { balances: Balance[] }) {
  return (
    <ul className="divide-y divide-zinc-100">
      {balances.map(({ member, balance }) => {
        const satang = satangFromApi(balance);
        return (
          <li key={member} className="flex items-center justify-between py-2 text-sm">
            <span className="font-medium">{member}</span>
            {satang > 0 ? (
              <span className="text-emerald-700">
                is owed <Money satang={satang} className="font-semibold" />
              </span>
            ) : satang < 0 ? (
              <span className="text-red-700">
                owes <Money satang={-satang} className="font-semibold" />
              </span>
            ) : (
              <span className="text-zinc-500">settled up</span>
            )}
          </li>
        );
      })}
    </ul>
  );
}
