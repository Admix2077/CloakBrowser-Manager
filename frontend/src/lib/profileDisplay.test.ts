import { describe, expect, it } from "vitest";
import { formatTimestamp } from "./profileDisplay";

describe("formatTimestamp", () => {
  it("does not echo non-date timestamp evidence", () => {
    const leakMarker = "timestamp-token-super-secret";
    const value =
      "2026-06-04 Authorization=Bearer " +
      `${leakMarker} token=${leakMarker} /data/timestamp 203.0.113.155`;

    const formatted = formatTimestamp(value);

    expect(formatted).toBe("Invalid timestamp");
    expect(formatted).not.toContain(leakMarker);
    expect(formatted).not.toContain("Authorization");
    expect(formatted).not.toContain("Bearer");
    expect(formatted).not.toContain("token=");
    expect(formatted).not.toContain("/data/timestamp");
    expect(formatted).not.toContain("203.0.113.155");
  });
});
