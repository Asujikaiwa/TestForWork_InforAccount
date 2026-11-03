import { describe, expect, it } from "vitest";
import { formatSatang } from "./money";
import { splitEqual, summarizeExact } from "./split";

const display = (shares: { member: string; satang: number }[]) =>
  shares.map((s) => `${s.member}:${formatSatang(s.satang)}`);

describe("splitEqual", () => {
  it("100.00 among three members gives 33.34, 33.33, 33.33", () => {
    expect(display(splitEqual(10_000, ["alice", "bob", "carol"]))).toEqual([
      "alice:33.34",
      "bob:33.33",
      "carol:33.33",
    ]);
  });

  it("matches the brief: 1,000.00 dinner split three ways", () => {
    expect(display(splitEqual(100_000, ["alice", "bob", "carol"]))).toEqual([
      "alice:333.34",
      "bob:333.33",
      "carol:333.33",
    ]);
  });

  it("hands leftover satang out in the order listed", () => {
    // 0.05 among 3 -> base 1, remainder 2 -> first two get an extra satang
    expect(splitEqual(5, ["carol", "alice", "bob"])).toEqual([
      { member: "carol", satang: 2 },
      { member: "alice", satang: 2 },
      { member: "bob", satang: 1 },
    ]);
  });

  it("always sums to the total", () => {
    for (const total of [1, 2, 99, 100, 101, 10_000, 99_999_999]) {
      for (let n = 1; n <= 7; n++) {
        const members = Array.from({ length: n }, (_, i) => `m${i}`);
        const sum = splitEqual(total, members).reduce((a, s) => a + s.satang, 0);
        expect(sum).toBe(total);
      }
    }
  });

  it("returns nothing when no member is selected", () => {
    expect(splitEqual(10_000, [])).toEqual([]);
  });
});

describe("summarizeExact", () => {
  const members = ["alice", "bob", "carol"];

  it("reports the unallocated amount", () => {
    const s = summarizeExact(100_000, members, { alice: "500", bob: "300" });
    expect(s.allocated).toBe(80_000);
    expect(s.remaining).toBe(20_000);
    expect(s.shares.map((x) => x.member)).toEqual(["alice", "bob"]);
  });

  it("reaches zero when shares equal the total", () => {
    const s = summarizeExact(100_000, members, {
      alice: "500.00",
      bob: "300.00",
      carol: "200.00",
    });
    expect(s.remaining).toBe(0);
    expect(s.problems).toEqual({});
  });

  it("goes negative when shares exceed the total", () => {
    expect(summarizeExact(1_000, members, { alice: "10.01" }).remaining).toBe(-1);
  });

  it("treats blank and zero as not included, flags bad input", () => {
    const s = summarizeExact(1_000, members, {
      alice: "",
      bob: "0",
      carol: "1.005",
    });
    expect(s.shares).toEqual([]);
    expect(s.problems).toEqual({ carol: "precision" });
  });

  it("has no remaining amount while the total is invalid", () => {
    expect(summarizeExact(null, members, { alice: "5" }).remaining).toBeNull();
  });
});
