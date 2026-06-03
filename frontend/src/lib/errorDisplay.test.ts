import { describe, expect, it } from "vitest";
import { publicErrorText, publicProfileGeoipLabel } from "./errorDisplay";

describe("publicErrorText", () => {
  it("redacts Windows drive paths without redacting public URL host and port", () => {
    const text = publicErrorText(
      "Proxy failed at http://user:secret@example.test:8080/check " +
        "while reading C:\\Users\\Jeff\\AppData\\Local\\CloakBrowser\\profile-secret " +
        "and D:/profiles/profile-secret/state.json",
    );

    expect(text).toBe(
      "Proxy failed at http://example.test:8080/check " +
        "while reading [redacted-path] and [redacted-path]",
    );
    expect(text).not.toContain("C:\\Users\\Jeff");
    expect(text).not.toContain("D:/profiles");
    expect(text).not.toContain("user:secret");
  });

  it("redacts IP literals from visible error text", () => {
    const text = publicErrorText(
      "Proxy check failed from 203.0.113.45 via 198.51.100.20:8080 " +
        "and ipv6 2001:db8::45 through [2001:db8::46]:443 " +
        "while keeping http://example.test:8080/check readable",
    );

    expect(text).toBe(
      "Proxy check failed from [redacted-ip] via [redacted-ip]:8080 " +
        "and ipv6 [redacted-ip] through [redacted-ip]:443 " +
        "while keeping http://example.test:8080/check readable",
    );
    expect(text).not.toContain("203.0.113.45");
    expect(text).not.toContain("198.51.100.20");
    expect(text).not.toContain("2001:db8::45");
    expect(text).not.toContain("2001:db8::46");
  });
});

describe("publicProfileGeoipLabel", () => {
  it("keeps normal geoip values while redacting polluted evidence", () => {
    expect(publicProfileGeoipLabel("23.144.4.92")).toBe("23.144.4.92");
    expect(publicProfileGeoipLabel("US")).toBe("US");
    expect(publicProfileGeoipLabel("America/Los_Angeles")).toBe("America/Los_Angeles");
    expect(publicProfileGeoipLabel("en-US")).toBe("en-US");

    expect(publicProfileGeoipLabel(
      "US Authorization=Bearer geoip-secret token=geoip-secret /data/geoip 203.0.113.104",
    )).toBe("US [redacted] [redacted] [redacted-path] [redacted-ip]");
  });
});
