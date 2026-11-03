import { formatSatang, type Satang } from "@/lib/money";

/** Renders satang as Thai-formatted baht, e.g. ฿1,000.00. */
export function Money({
  satang,
  signed = false,
  className = "",
}: {
  satang: Satang;
  signed?: boolean;
  className?: string;
}) {
  return (
    <span className={`tabular-nums ${className}`}>
      ฿{formatSatang(satang, { signed })}
    </span>
  );
}
