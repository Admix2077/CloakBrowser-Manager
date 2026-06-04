import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ProfileCookieManager } from "./ProfileCookieManager";
import { api, type CookieExportResponse, type CookieImportResponse, type NetscapeCookieExportResponse, type Profile } from "../lib/api";

vi.mock("../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/api")>();
  return {
    ...actual,
    api: {
      importProfileCookies: vi.fn(),
      exportProfileCookies: vi.fn(),
      importProfileCookiesNetscape: vi.fn(),
      exportProfileCookiesNetscape: vi.fn(),
    },
  };
});

const mockImportProfileCookies = api.importProfileCookies as ReturnType<typeof vi.fn>;
const mockExportProfileCookies = api.exportProfileCookies as ReturnType<typeof vi.fn>;
const mockImportProfileCookiesNetscape = api.importProfileCookiesNetscape as ReturnType<typeof vi.fn>;
const mockExportProfileCookiesNetscape = api.exportProfileCookiesNetscape as ReturnType<typeof vi.fn>;

function profile(overrides: Partial<Profile> = {}): Profile {
  return {
    id: "profile-1",
    name: "Seller US",
    fingerprint_seed: 12345,
    proxy: null,
    timezone: null,
    locale: null,
    platform: "windows",
    user_agent: null,
    screen_width: 1920,
    screen_height: 1080,
    gpu_vendor: null,
    gpu_renderer: null,
    hardware_concurrency: null,
    humanize: false,
    human_preset: "default",
    headless: false,
    geoip: false,
    last_geoip_ip: null,
    last_geoip_country_code: null,
    last_geoip_timezone: null,
    last_geoip_locale: null,
    last_geoip_source: null,
    last_geoip_resolved_at: null,
    clipboard_sync: false,
    auto_launch: false,
    color_scheme: null,
    launch_args: [],
    notes: null,
    user_data_dir: "/data/profiles/profile-1",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    tags: [],
    status: "running",
    vnc_ws_port: 6100,
    automation_url: "/api/profiles/profile-1/automation",
    ...overrides,
  };
}

function importResponse(overrides: Partial<CookieImportResponse> = {}): CookieImportResponse {
  return {
    profile_id: "profile-1",
    imported: 2,
    summary: {
      cookie_count: 2,
      secure_count: 1,
      http_only_count: 1,
      session_cookie_count: 1,
      persistent_cookie_count: 1,
    },
    ...overrides,
  };
}

function exportResponse(overrides: Partial<CookieExportResponse> = {}): CookieExportResponse {
  return {
    profile_id: "profile-1",
    exported: 1,
    summary: {
      cookie_count: 1,
      secure_count: 1,
      http_only_count: 1,
      session_cookie_count: 0,
      persistent_cookie_count: 1,
    },
    document: {
      format: "cloakbrowser.cookie-json.v1",
      schema_version: 1,
      cookies: [{
        name: "export-cookie-name-secret",
        value: "export-secret-value",
        domain: "sensitive.example",
        url: "https://sensitive.example/account?token=export-token#frag",
        path: "/",
        secure: true,
        httpOnly: true,
      }],
    },
    ...overrides,
  };
}

function netscapeExportResponse(overrides: Partial<NetscapeCookieExportResponse> = {}): NetscapeCookieExportResponse {
  return {
    profile_id: "profile-1",
    exported: 2,
    summary: {
      format: "netscape-cookie-file",
      cookie_count: 2,
      secure_count: 1,
      http_only_count: 1,
      session_cookie_count: 1,
      persistent_cookie_count: 1,
    },
    text: [
      "# Netscape HTTP Cookie File",
      ".sensitive.example\tTRUE\t/\tTRUE\t1893456000\tsid\texport-secret-value",
      "#HttpOnly_app.example\tFALSE\t/dashboard\tFALSE\t0\tacctid\tsession-secret",
    ].join("\n"),
    ...overrides,
  };
}

beforeEach(() => {
  mockImportProfileCookies.mockReset();
  mockExportProfileCookies.mockReset();
  mockImportProfileCookiesNetscape.mockReset();
  mockExportProfileCookiesNetscape.mockReset();
  Object.defineProperty(window.URL, "createObjectURL", {
    configurable: true,
    value: undefined,
  });
  Object.defineProperty(window.URL, "revokeObjectURL", {
    configurable: true,
    value: vi.fn(),
  });
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("ProfileCookieManager", () => {
  it("imports pasted cookie JSON into a running profile and only renders low-risk summary counts", async () => {
    mockImportProfileCookies.mockResolvedValueOnce(importResponse());
    const cookieJson = JSON.stringify({
      format: "cloakbrowser.cookie-json.v1",
      schema_version: 1,
      cookies: [{
        name: "import-cookie-name-secret",
        value: "import-secret-value",
        domain: "private.example",
        url: "https://private.example/app?token=import-token#fragment",
      }],
    });

    render(<ProfileCookieManager profile={profile()} />);

    const manager = screen.getByRole("region", { name: "Cookie management" });
    fireEvent.change(within(manager).getByLabelText("Cookie JSON v1 document"), {
      target: { value: cookieJson },
    });
    fireEvent.click(within(manager).getByRole("button", { name: "Import cookies" }));

    await waitFor(() => expect(mockImportProfileCookies).toHaveBeenCalledWith(
      "profile-1",
      JSON.parse(cookieJson),
    ));
    expect((await within(manager).findByRole("status")).textContent).toContain("Imported 2 cookie(s)");
    expect(within(manager).getByText("2 total")).toBeTruthy();
    expect(within(manager).getByText("1 secure")).toBeTruthy();

    expect(manager.textContent).not.toContain("import-secret-value");
    expect(manager.textContent).not.toContain("import-cookie-name-secret");
    expect(manager.textContent).not.toContain("private.example");
    expect(manager.textContent).not.toContain("import-token");
    expect(manager.textContent).not.toContain("#fragment");
  });

  it("does not call cookie APIs for stopped profiles", () => {
    render(<ProfileCookieManager profile={profile({ status: "stopped", vnc_ws_port: null, automation_url: null })} />);

    const manager = screen.getByRole("region", { name: "Cookie management" });
    expect(within(manager).getByText("Launch the profile before importing or exporting cookies.")).toBeTruthy();
    expect((within(manager).getByRole("button", { name: "Import cookies" }) as HTMLButtonElement).disabled).toBe(true);
    expect((within(manager).getByRole("button", { name: "Export cookies" }) as HTMLButtonElement).disabled).toBe(true);

    fireEvent.click(within(manager).getByRole("button", { name: "Import cookies" }));
    fireEvent.click(within(manager).getByRole("button", { name: "Export cookies" }));

    expect(mockImportProfileCookies).not.toHaveBeenCalled();
    expect(mockExportProfileCookies).not.toHaveBeenCalled();
    expect(mockImportProfileCookiesNetscape).not.toHaveBeenCalled();
    expect(mockExportProfileCookiesNetscape).not.toHaveBeenCalled();
  });

  it("requires explicit export confirmation and does not render exported cookie document fields", async () => {
    mockExportProfileCookies.mockResolvedValueOnce(exportResponse());

    render(<ProfileCookieManager profile={profile()} />);

    const manager = screen.getByRole("region", { name: "Cookie management" });
    expect((within(manager).getByRole("button", { name: "Export cookies" }) as HTMLButtonElement).disabled).toBe(true);

    fireEvent.click(within(manager).getByLabelText("Confirm cookie export"));
    fireEvent.click(within(manager).getByRole("button", { name: "Export cookies" }));

    await waitFor(() => expect(mockExportProfileCookies).toHaveBeenCalledWith("profile-1"));
    expect((await within(manager).findByRole("status")).textContent).toContain("Exported 1 cookie(s)");
    expect(within(manager).getByText("1 total")).toBeTruthy();

    expect(manager.textContent).not.toContain("export-secret-value");
    expect(manager.textContent).not.toContain("export-cookie-name-secret");
    expect(manager.textContent).not.toContain("sensitive.example");
    expect(manager.textContent).not.toContain("export-token");
    expect(manager.textContent).not.toContain("#frag");
  });

  it("uses a public profile id in cookie export download names", async () => {
    const leakMarker = "cookie-download-token-super-secret";
    const pollutedProfileId =
      "profile Authorization=Bearer " +
      `${leakMarker} token=${leakMarker} /data/cookie-profile 203.0.113.58`;
    mockExportProfileCookies.mockResolvedValueOnce(exportResponse({ profile_id: pollutedProfileId }));
    const createObjectURL = vi.fn(() => "blob:cookie-export");
    const revokeObjectURL = vi.fn();
    let downloadName = "";

    Object.defineProperty(window.URL, "createObjectURL", {
      configurable: true,
      value: createObjectURL,
    });
    Object.defineProperty(window.URL, "revokeObjectURL", {
      configurable: true,
      value: revokeObjectURL,
    });
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
      downloadName = this.download;
    });

    render(<ProfileCookieManager profile={profile({ id: pollutedProfileId })} />);

    const manager = screen.getByRole("region", { name: "Cookie management" });
    fireEvent.click(within(manager).getByLabelText("Confirm cookie export"));
    fireEvent.click(within(manager).getByRole("button", { name: "Export cookies" }));

    await waitFor(() => expect(mockExportProfileCookies).toHaveBeenCalledWith(pollutedProfileId));
    expect(createObjectURL).toHaveBeenCalledTimes(1);
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:cookie-export");
    expect(downloadName).toBe("cloakbrowser-cookies-unknown.json");

    for (const leaked of [
      leakMarker,
      "Authorization",
      "Bearer",
      "token=",
      "/data/cookie-profile",
      "203.0.113.58",
    ]) {
      expect(downloadName).not.toContain(leaked);
    }
  });

  it("does not use sensitive filename-safe profile ids in cookie export download names", async () => {
    const pollutedProfileId = "viewer_token-cookie-secret";
    mockExportProfileCookies.mockResolvedValueOnce(exportResponse({ profile_id: pollutedProfileId }));
    const createObjectURL = vi.fn(() => "blob:cookie-export");
    const revokeObjectURL = vi.fn();
    let downloadName = "";

    Object.defineProperty(window.URL, "createObjectURL", {
      configurable: true,
      value: createObjectURL,
    });
    Object.defineProperty(window.URL, "revokeObjectURL", {
      configurable: true,
      value: revokeObjectURL,
    });
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
      downloadName = this.download;
    });

    render(<ProfileCookieManager profile={profile({ id: pollutedProfileId })} />);

    const manager = screen.getByRole("region", { name: "Cookie management" });
    fireEvent.click(within(manager).getByLabelText("Confirm cookie export"));
    fireEvent.click(within(manager).getByRole("button", { name: "Export cookies" }));

    await waitFor(() => expect(mockExportProfileCookies).toHaveBeenCalledWith(pollutedProfileId));
    expect(createObjectURL).toHaveBeenCalledTimes(1);
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:cookie-export");
    expect(downloadName).toBe("cloakbrowser-cookies-unknown.json");
    expect(downloadName).not.toContain("viewer_token");
    expect(downloadName).not.toContain("cookie-secret");
  });

  it("imports Netscape cookie text and only renders low-risk summary counts", async () => {
    mockImportProfileCookiesNetscape.mockResolvedValueOnce(importResponse({
      summary: {
        format: "netscape-cookie-file",
        cookie_count: 2,
        secure_count: 1,
        http_only_count: 1,
        session_cookie_count: 1,
        persistent_cookie_count: 1,
      },
    }));
    const netscapeText = ".private.example\tTRUE\t/\tTRUE\t1893456000\timport-cookie-name-secret\timport-secret-value";

    render(<ProfileCookieManager profile={profile()} />);

    const manager = screen.getByRole("region", { name: "Cookie management" });
    fireEvent.click(within(manager).getByRole("button", { name: "Netscape" }));
    fireEvent.change(within(manager).getByLabelText("Netscape cookie file text"), {
      target: { value: netscapeText },
    });
    fireEvent.click(within(manager).getByRole("button", { name: "Import cookies" }));

    await waitFor(() => expect(mockImportProfileCookiesNetscape).toHaveBeenCalledWith(
      "profile-1",
      netscapeText,
    ));
    expect(mockImportProfileCookies).not.toHaveBeenCalled();
    expect((await within(manager).findByRole("status")).textContent).toContain("Imported 2 cookie(s)");
    expect(within(manager).getByText("2 total")).toBeTruthy();
    expect(within(manager).getByText("1 secure")).toBeTruthy();

    expect(manager.textContent).not.toContain("import-secret-value");
    expect(manager.textContent).not.toContain("import-cookie-name-secret");
    expect(manager.textContent).not.toContain("private.example");
  });

  it("exports Netscape cookie text for download without rendering the exported text", async () => {
    mockExportProfileCookiesNetscape.mockResolvedValueOnce(netscapeExportResponse());

    render(<ProfileCookieManager profile={profile()} />);

    const manager = screen.getByRole("region", { name: "Cookie management" });
    fireEvent.click(within(manager).getByRole("button", { name: "Netscape" }));
    fireEvent.click(within(manager).getByLabelText("Confirm cookie export"));
    fireEvent.click(within(manager).getByRole("button", { name: "Export cookies" }));

    await waitFor(() => expect(mockExportProfileCookiesNetscape).toHaveBeenCalledWith("profile-1"));
    expect(mockExportProfileCookies).not.toHaveBeenCalled();
    expect((await within(manager).findByRole("status")).textContent).toContain("Exported 2 cookie(s)");
    expect(within(manager).getByText("2 total")).toBeTruthy();

    expect(manager.textContent).not.toContain("export-secret-value");
    expect(manager.textContent).not.toContain("session-secret");
    expect(manager.textContent).not.toContain("sid");
    expect(manager.textContent).not.toContain("acctid");
    expect(manager.textContent).not.toContain("sensitive.example");
  });

  it("shows a fixed invalid JSON error without echoing the pasted cookie document", async () => {
    render(<ProfileCookieManager profile={profile()} />);

    const manager = screen.getByRole("region", { name: "Cookie management" });
    fireEvent.change(within(manager).getByLabelText("Cookie JSON v1 document"), {
      target: { value: '{"name":"session","value":"parse-secret","domain":"private.example"' },
    });
    fireEvent.click(within(manager).getByRole("button", { name: "Import cookies" }));

    expect((await within(manager).findByRole("alert")).textContent).toContain("Invalid Cookie JSON document");
    expect(mockImportProfileCookies).not.toHaveBeenCalled();
    expect(manager.textContent).not.toContain("parse-secret");
    expect(manager.textContent).not.toContain("private.example");
  });
});
