import { describe, expect, it } from "vitest";
import { publicErrorText, publicProfileGeoipLabel, publicProfileIdLabel, publicProfileName, publicProfileTagLabel } from "./errorDisplay";

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

  it("removes URL query strings and fragments from visible error text", () => {
    const text = publicErrorText(
      "Automation failed at https://example.test/account/check?session_id=secret-session#private-fragment " +
        "after proxy http://user:hiddenpass@proxy.example:8080/path?opaque=secret#secret",
    );

    expect(text).toBe(
      "Automation failed at https://example.test/account/check " +
        "after proxy http://proxy.example:8080/path",
    );
    expect(text).not.toContain("session_id=secret-session");
    expect(text).not.toContain("private-fragment");
    expect(text).not.toContain("opaque=secret");
    expect(text).not.toContain("hiddenpass");
  });

  it("redacts common API key and session assignment names from visible error text", () => {
    const text = publicErrorText(
      "Provider rejected api_key=key-super-secret access_token=access-super-secret " +
        "refresh_token=refresh-super-secret session_id=session-super-secret " +
        "client_secret=client-super-secret x-api-key: header-super-secret",
    );

    expect(text).toBe(
      "Provider rejected [redacted] [redacted] [redacted] [redacted] [redacted] [redacted]",
    );
    expect(text).not.toContain("key-super-secret");
    expect(text).not.toContain("access-super-secret");
    expect(text).not.toContain("refresh-super-secret");
    expect(text).not.toContain("session-super-secret");
    expect(text).not.toContain("client-super-secret");
    expect(text).not.toContain("header-super-secret");
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

  it("redacts marker-bearing geoip labels without assignment syntax", () => {
    for (const polluted of [
      "api_key-geoip-marker",
      "access_token-geoip-marker",
      "client_secret-geoip-marker",
      "private_key-geoip-marker",
    ]) {
      expect(publicProfileGeoipLabel(polluted)).toBe("unknown");
    }
  });
});

describe("publicProfileName", () => {
  it("redacts marker-bearing profile names while preserving public names", () => {
    expect(publicProfileName("Alpha Good")).toBe("Alpha Good");

    for (const polluted of [
      "api_key-profile-name-marker",
      "access_token-profile-name-marker",
      "client_secret-profile-name-marker",
      "private_key-profile-name-marker",
    ]) {
      expect(publicProfileName(polluted)).toBe("unknown");
    }
  });
});

describe("publicProfileIdLabel", () => {
  it("redacts marker-bearing profile ids while preserving public id labels", () => {
    expect(publicProfileIdLabel("profile-123456")).toBe("profile-");

    for (const polluted of [
      "x-api-key-profile-marker",
      "client_secret-profile-marker",
      "private_key-profile-marker",
    ]) {
      expect(publicProfileIdLabel(polluted)).toBe("unknown");
    }
  });
});

describe("publicProfileTagLabel", () => {
  it("redacts marker-bearing tag labels while preserving public tag labels", () => {
    expect(publicProfileTagLabel("stable-pool")).toBe("stable-pool");

    for (const polluted of [
      "api_key-tag-marker",
      "x-api-key-tag-marker",
      "client_secret-tag-marker",
      "private_key-tag-marker",
    ]) {
      expect(publicProfileTagLabel(polluted)).toBe("unknown");
    }
  });
});
