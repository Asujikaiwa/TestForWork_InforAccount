import { describe, expect, it } from "vitest";
import { IdempotencyKeys } from "./idempotency";

describe("IdempotencyKeys", () => {
  const payload = { description: "Dinner", amount: "1000.00" };

  it("reuses the key when the same payload is resubmitted", () => {
    const keys = new IdempotencyKeys();
    expect(keys.keyFor(payload)).toBe(keys.keyFor({ ...payload }));
  });

  it("issues a new key when the payload changes", () => {
    const keys = new IdempotencyKeys();
    const first = keys.keyFor(payload);
    expect(keys.keyFor({ ...payload, amount: "999.00" })).not.toBe(first);
  });

  it("issues a new key after a successful submit", () => {
    const keys = new IdempotencyKeys();
    const first = keys.keyFor(payload);
    keys.reset();
    expect(keys.keyFor(payload)).not.toBe(first);
  });
});
