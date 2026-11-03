import type { Share } from "@/lib/split";
import { Money } from "./Money";

/** Read-only list of who pays what, shown while the user types. */
export function SplitPreview({ shares }: { shares: Share[] }) {
  if (shares.length === 0) {
    return (
      <p className="text-sm text-zinc-500">
        Enter an amount and choose members to see each share.
      </p>
    );
  }
  return (
    <ul aria-label="Split preview" className="divide-y divide-zinc-100 text-sm">
      {shares.map((share) => (
        <li key={share.member} className="flex justify-between py-1">
          <span>{share.member}</span>
          <Money satang={share.satang} />
        </li>
      ))}
    </ul>
  );
}
