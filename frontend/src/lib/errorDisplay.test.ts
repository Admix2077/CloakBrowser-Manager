import { describe, expect, it } from "vitest";
import { publicErrorText } from "./errorDisplay";

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
});
