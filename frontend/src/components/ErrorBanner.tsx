import { describeError } from "@/lib/errors";

export function ErrorBanner({
  error,
  message,
}: {
  error?: unknown;
  message?: string;
}) {
  const text = message ?? (error !== undefined ? describeError(error) : null);
  if (!text) return null;
  return (
    <p
      role="alert"
      className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
    >
      {text}
    </p>
  );
}
