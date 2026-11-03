/**
 * Idempotency keys for "create expense".
 *
 * One key per *intended* expense: if the user presses submit again with the
 * exact same form contents (double click, retry after a network error), the
 * same key is sent and the backend returns the original expense instead of
 * creating a duplicate. Changing any field means a different expense, so a
 * new key is generated.
 */
export class IdempotencyKeys {
  private current: { payload: string; key: string } | null = null;

  keyFor(payload: unknown): string {
    const serialised = JSON.stringify(payload);
    if (this.current?.payload !== serialised) {
      this.current = { payload: serialised, key: newKey() };
    }
    return this.current.key;
  }

  /** Call after the expense was stored, so the next one gets a fresh key. */
  reset(): void {
    this.current = null;
  }
}

function newKey(): string {
  // randomUUID needs a secure context (https or localhost).
  if (typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}
