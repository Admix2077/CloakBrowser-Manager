import { describe, it, expect, vi, beforeEach } from "vitest";
import { api } from "./api";

// Mock fetch globally
const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

function jsonResponse(data: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? "OK" : "Error",
    json: () => Promise.resolve(data),
  };
}

beforeEach(() => {
  mockFetch.mockReset();
});

// ── listProfiles ────────────────────────────────────────────────────────────

describe("api.listProfiles", () => {
  it("returns profile array on success", async () => {
    const profiles = [{ id: "1", name: "Test" }];
    mockFetch.mockResolvedValueOnce(jsonResponse(profiles));
    const result = await api.listProfiles();
    expect(result).toEqual(profiles);
    expect(mockFetch).toHaveBeenCalledWith("/api/profiles", {
      headers: { "Content-Type": "application/json" },
    });
  });
});

// ── createProfile ───────────────────────────────────────────────────────────

describe("api.createProfile", () => {
  it("sends POST with JSON body", async () => {
    const profile = { id: "2", name: "New" };
    mockFetch.mockResolvedValueOnce(jsonResponse(profile));
    await api.createProfile({ name: "New" });
    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toBe("/api/profiles");
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body)).toEqual({ name: "New" });
  });
});

describe("api.previewProfileImport", () => {
  it("sends pasted CSV text to the profile import preview endpoint", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({
      total: 1,
      valid: 1,
      invalid: 0,
      rows: [],
    }));

    await api.previewProfileImport("name,platform\nImported,linux");

    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toBe("/api/profiles/import/preview");
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body)).toEqual({
      csv_text: "name,platform\nImported,linux",
    });
  });
});

describe("api.importProfiles", () => {
  it("sends pasted CSV text with explicit confirmation to the profile import endpoint", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({
      total: 1,
      succeeded: 1,
      failed: 0,
      results: [],
    }));

    await api.importProfiles("name,platform\nImported,linux");

    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toBe("/api/profiles/import");
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body)).toEqual({
      csv_text: "name,platform\nImported,linux",
      confirm_import: true,
    });
  });
});

describe("api.exportProfiles", () => {
  it("sends selected profile ids to the profile config export endpoint", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({
      schema_version: 1,
      total: 2,
      exported: 1,
      failed: 1,
      results: [],
    }));

    await api.exportProfiles(["profile-1", "missing"]);

    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toBe("/api/profiles/export");
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body)).toEqual({
      profile_ids: ["profile-1", "missing"],
    });
  });

  it("sends independent confirmation when sensitive proxy export is requested", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({
      schema_version: 1,
      total: 1,
      exported: 1,
      failed: 0,
      results: [],
    }));

    await api.exportProfiles(["profile-1"], { includeSensitive: true });

    const [, options] = mockFetch.mock.calls[0];
    expect(JSON.parse(options.body)).toEqual({
      profile_ids: ["profile-1"],
      include_sensitive: true,
      confirm_sensitive_export: true,
    });
  });
});

describe("api.importProfileCookies", () => {
  it("sends cookie JSON v1 to the profile cookie import endpoint", async () => {
    const document = {
      format: "cloakbrowser.cookie-json.v1",
      schema_version: 1,
      cookies: [{
        name: "session",
        value: "secret-cookie-value",
        domain: "example.com",
        path: "/",
        secure: true,
        httpOnly: true,
        sameSite: "Lax",
      }],
    };
    mockFetch.mockResolvedValueOnce(jsonResponse({
      profile_id: "profile-1",
      imported: 1,
      summary: { cookie_count: 1 },
    }));

    await api.importProfileCookies("profile-1", document);

    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toBe("/api/profiles/profile-1/cookies/import");
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body)).toEqual({
      ...document,
      confirm_import: true,
    });
  });
});

describe("api.exportProfileCookies", () => {
  it("requires explicit confirmation when requesting cookie export", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({
      profile_id: "profile-1",
      exported: 1,
      summary: { cookie_count: 1 },
      document: {
        format: "cloakbrowser.cookie-json.v1",
        schema_version: 1,
        cookies: [],
      },
    }));

    await api.exportProfileCookies("profile-1");

    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toBe("/api/profiles/profile-1/cookies/export");
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body)).toEqual({ confirm_export: true });
  });
});

describe("api.importProfileCookiesNetscape", () => {
  it("sends Netscape cookie text to the profile cookie import endpoint", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({
      profile_id: "profile-1",
      imported: 1,
      summary: { format: "netscape-cookie-file", cookie_count: 1 },
    }));

    await api.importProfileCookiesNetscape("profile-1", "example.com\tFALSE\t/\tFALSE\t0\tsid\tsecret");

    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toBe("/api/profiles/profile-1/cookies/import/netscape");
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body)).toEqual({
      text: "example.com\tFALSE\t/\tFALSE\t0\tsid\tsecret",
      confirm_import: true,
    });
  });
});

describe("api.exportProfileCookiesNetscape", () => {
  it("requires explicit confirmation when requesting Netscape cookie export", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({
      profile_id: "profile-1",
      exported: 1,
      summary: { format: "netscape-cookie-file", cookie_count: 1 },
      text: "# Netscape HTTP Cookie File\nexample.com\tFALSE\t/\tFALSE\t0\tsid\tsecret",
    }));

    await api.exportProfileCookiesNetscape("profile-1");

    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toBe("/api/profiles/profile-1/cookies/export/netscape");
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body)).toEqual({ confirm_export: true });
  });
});

// ── updateProfile ───────────────────────────────────────────────────────────

describe("api.updateProfile", () => {
  it("sends PUT with JSON body", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ id: "1", name: "Updated" }));
    await api.updateProfile("1", { name: "Updated" });
    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toBe("/api/profiles/1");
    expect(options.method).toBe("PUT");
  });
});

// ── deleteProfile ───────────────────────────────────────────────────────────

describe("api.deleteProfile", () => {
  it("sends DELETE request with explicit confirmation", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ ok: true }));
    const result = await api.deleteProfile("1");
    expect(result).toEqual({ ok: true });
    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toBe("/api/profiles/1");
    expect(options.method).toBe("DELETE");
    expect(JSON.parse(options.body)).toEqual({ confirm_delete: true });
  });
});

describe("api.deleteProfileTemplate", () => {
  it("sends DELETE request with explicit confirmation", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ ok: true }));

    const result = await api.deleteProfileTemplate("template-1");

    expect(result).toEqual({ ok: true });
    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toBe("/api/profile-templates/template-1");
    expect(options.method).toBe("DELETE");
    expect(JSON.parse(options.body)).toEqual({ confirm_delete: true });
  });
});

// ── launchProfile ───────────────────────────────────────────────────────────

describe("api.launchProfile", () => {
  it("sends POST to launch endpoint with explicit confirmation", async () => {
    const result = { profile_id: "1", status: "running", vnc_ws_port: 6100, display: ":100" };
    mockFetch.mockResolvedValueOnce(jsonResponse(result));
    const data = await api.launchProfile("1");
    expect(data.vnc_ws_port).toBe(6100);
    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toBe("/api/profiles/1/launch");
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body)).toEqual({ confirm_launch: true });
  });
});

// ── stopProfile ─────────────────────────────────────────────────────────────

describe("api.stopProfile", () => {
  it("sends POST to stop endpoint with explicit confirmation", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ ok: true }));
    await api.stopProfile("1");
    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toBe("/api/profiles/1/stop");
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body)).toEqual({ confirm_stop: true });
  });
});

// ── profile health ─────────────────────────────────────────────────────────

describe("api.getProfileHealth", () => {
  it("requests the cached health snapshot without a network check", async () => {
    const health = {
      profile_id: "1",
      status: "warning",
      geoip: {
        ip: "203.0.113.20",
        country_code: "JP",
        timezone: "Asia/Tokyo",
        locale: "ja-JP",
        source: "ipwho.is",
        resolved_at: "2026-05-25T00:00:00Z",
      },
      manual_overrides: { timezone: false, locale: false },
      runtime: { status: "stopped", vnc_ws_port: null, automation_url: null },
      warnings: [
        {
          code: "geoip_stale",
          message: "最近一次 GeoIP 检测结果已过期。",
          severity: "warning",
          action: "重新运行健康检测刷新出口 IP 指纹。",
        },
      ],
      checked_at: "2026-05-25T01:00:00Z",
    };
    mockFetch.mockResolvedValueOnce(jsonResponse(health));

    const result = await api.getProfileHealth("1");

    expect(result.status).toBe("warning");
    expect(result.warnings[0].code).toBe("geoip_stale");
    expect(mockFetch).toHaveBeenCalledWith("/api/profiles/1/health", {
      headers: { "Content-Type": "application/json" },
    });
  });
});

describe("api.checkProfileHealth", () => {
  it("sends POST to run an active profile health check", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({
      profile_id: "1",
      status: "good",
      geoip: null,
      manual_overrides: { timezone: false, locale: false },
      runtime: { status: "stopped", vnc_ws_port: null, automation_url: null },
      warnings: [],
      checked_at: "2026-05-25T01:00:00Z",
    }));

    await api.checkProfileHealth("1");

    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toBe("/api/profiles/1/health/check");
    expect(options.method).toBe("POST");
  });
});

// ── proxy assets ───────────────────────────────────────────────────────────

describe("api.listProxies", () => {
  it("requests proxy assets", async () => {
    const proxies = [{ id: "proxy-1", name: "US pool", url: "http://proxy.example:8080" }];
    mockFetch.mockResolvedValueOnce(jsonResponse(proxies));

    const result = await api.listProxies();

    expect(result).toEqual(proxies);
    expect(mockFetch).toHaveBeenCalledWith("/api/proxies", {
      headers: { "Content-Type": "application/json" },
    });
  });
});

describe("api.listProxyProviderPresets", () => {
  it("requests proxy provider presets", async () => {
    const presets = [{
      id: "preset-1",
      name: "Japan mobile default",
      provider: "ProxyJP",
      country_code: "JP",
      tags: [{ tag: "mobile", color: "#0ea5e9" }],
      notes: "Tokyo exits",
      created_at: "2026-05-26T00:00:00Z",
      updated_at: "2026-05-26T00:00:00Z",
    }];
    mockFetch.mockResolvedValueOnce(jsonResponse(presets));

    const result = await api.listProxyProviderPresets();

    expect(result).toEqual(presets);
    expect(mockFetch).toHaveBeenCalledWith("/api/proxy-provider-presets", {
      headers: { "Content-Type": "application/json" },
    });
  });
});

describe("api.createProxyProviderPreset", () => {
  it("sends provider preset metadata without proxy credentials", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ id: "preset-1", name: "US default" }, 201));

    await api.createProxyProviderPreset({
      name: "US default",
      provider: "ProxyCo",
      country_code: "US",
      tags: [{ tag: "residential", color: null }],
      notes: "Provider defaults",
    });

    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toBe("/api/proxy-provider-presets");
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body)).toEqual({
      name: "US default",
      provider: "ProxyCo",
      country_code: "US",
      tags: [{ tag: "residential", color: null }],
      notes: "Provider defaults",
    });
  });
});

describe("api.updateProxyProviderPreset", () => {
  it("sends PUT with partial provider preset metadata", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ id: "preset-1", name: "US updated" }));

    await api.updateProxyProviderPreset("preset-1", {
      name: "US updated",
      tags: [{ tag: "stable", color: null }],
      notes: null,
    });

    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toBe("/api/proxy-provider-presets/preset-1");
    expect(options.method).toBe("PUT");
    expect(JSON.parse(options.body)).toEqual({
      name: "US updated",
      tags: [{ tag: "stable", color: null }],
      notes: null,
    });
  });
});

describe("api.deleteProxyProviderPreset", () => {
  it("sends DELETE with explicit confirmation to a provider preset endpoint", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ ok: true }));

    const result = await api.deleteProxyProviderPreset("preset-1");

    expect(result).toEqual({ ok: true });
    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toBe("/api/proxy-provider-presets/preset-1");
    expect(options.method).toBe("DELETE");
    expect(JSON.parse(options.body)).toEqual({ confirm_delete: true });
  });
});

describe("api.createProxy", () => {
  it("sends POST with proxy asset JSON body", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ id: "proxy-1", name: "US pool" }, 201));

    await api.createProxy({
      name: "US pool",
      url: "http://user:hiddenpass@proxy.example:8080",
      provider: "ProxyCo",
      tags: [{ tag: "us", color: "#2563eb" }],
    });

    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toBe("/api/proxies");
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body)).toEqual({
      name: "US pool",
      url: "http://user:hiddenpass@proxy.example:8080",
      provider: "ProxyCo",
      tags: [{ tag: "us", color: "#2563eb" }],
    });
  });
});

describe("api.getProxy", () => {
  it("requests a single proxy asset", async () => {
    const proxy = { id: "proxy-1", name: "US pool", url: "http://proxy.example:8080" };
    mockFetch.mockResolvedValueOnce(jsonResponse(proxy));

    const result = await api.getProxy("proxy-1");

    expect(result).toEqual(proxy);
    expect(mockFetch).toHaveBeenCalledWith("/api/proxies/proxy-1", {
      headers: { "Content-Type": "application/json" },
    });
  });
});

describe("api.updateProxy", () => {
  it("sends PUT with partial proxy asset JSON body", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ id: "proxy-1", name: "US pool updated" }));

    await api.updateProxy("proxy-1", {
      name: "US pool updated",
      provider: "ProxyCo",
      notes: null,
    });

    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toBe("/api/proxies/proxy-1");
    expect(options.method).toBe("PUT");
    expect(JSON.parse(options.body)).toEqual({
      name: "US pool updated",
      provider: "ProxyCo",
      notes: null,
    });
  });
});

describe("api.deleteProxy", () => {
  it("sends DELETE with explicit confirmation to a proxy asset endpoint", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ ok: true }));

    const result = await api.deleteProxy("proxy-1");

    expect(result).toEqual({ ok: true });
    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toBe("/api/proxies/proxy-1");
    expect(options.method).toBe("DELETE");
    expect(JSON.parse(options.body)).toEqual({ confirm_delete: true });
  });
});

describe("api.checkProxy", () => {
  it("sends POST to a single proxy check endpoint", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({
      id: "proxy-1",
      name: "US pool",
      url: "http://proxy.example:8080",
      last_check_status: "good",
    }));

    await api.checkProxy("proxy-1");

    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toBe("/api/proxies/proxy-1/check");
    expect(options.method).toBe("POST");
  });
});

describe("api.bulkCheckProxies", () => {
  it("sends POST with proxy ids and explicit confirmation to the bulk check endpoint", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({
      total: 2,
      succeeded: 1,
      failed: 1,
      results: [],
    }));

    await api.bulkCheckProxies(["proxy-1", "proxy-2"]);

    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toBe("/api/proxies/bulk/check");
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body)).toEqual({
      proxy_ids: ["proxy-1", "proxy-2"],
      confirm_bulk_check: true,
    });
  });
});

describe("api.assignProxyToProfiles", () => {
  it("sends POST with profile ids and explicit confirmation to the assign endpoint", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({
      proxy_id: "proxy-1",
      proxy: { id: "proxy-1", name: "US pool", url: "http://proxy.example:8080" },
      total: 2,
      succeeded: 1,
      failed: 1,
      results: [
        { profile_id: "profile-1", ok: true, error: null },
        { profile_id: "missing", ok: false, error: "Profile not found" },
      ],
    }));

    await api.assignProxyToProfiles("proxy-1", ["profile-1", "missing"]);

    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toBe("/api/proxies/proxy-1/assign");
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body)).toEqual({
      profile_ids: ["profile-1", "missing"],
      confirm_assign: true,
    });
  });
});

describe("api.assignRandomProxyToProfiles", () => {
  it("sends selected profile ids, proxy filters, and explicit confirmation to the random assign endpoint", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({
      strategy: "random",
      provider_preset_id: null,
      provider: "ProxyJP",
      country_code: "JP",
      tags: ["mobile"],
      candidate_count: 2,
      total: 2,
      succeeded: 2,
      failed: 0,
      results: [
        { profile_id: "alpha", ok: true, error: null, proxy_id: "proxy-jp-1", proxy: null },
        { profile_id: "beta", ok: true, error: null, proxy_id: "proxy-jp-2", proxy: null },
      ],
    }));

    await api.assignRandomProxyToProfiles({
      profile_ids: ["alpha", "beta"],
      country_code: "JP",
      provider: "ProxyJP",
      tags: ["mobile"],
    });

    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toBe("/api/proxies/assign/random");
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body)).toEqual({
      profile_ids: ["alpha", "beta"],
      country_code: "JP",
      provider: "ProxyJP",
      tags: ["mobile"],
      confirm_assign: true,
    });
  });
});

// ── automation tasks ───────────────────────────────────────────────────────

describe("api.listAutomationTasks", () => {
  it("requests automation tasks with pagination", async () => {
    const response = {
      tasks: [
        {
          id: "task-1",
          profile_id: "profile-1",
          status: "queued",
          steps: [{ type: "wait", ms: 1000 }],
          result: null,
          error: null,
          created_at: "2026-05-27T00:00:00Z",
          started_at: null,
          finished_at: null,
        },
      ],
    };
    mockFetch.mockResolvedValueOnce(jsonResponse(response));

    const result = await api.listAutomationTasks({ limit: 20 });

    expect(result).toEqual(response);
    expect(mockFetch).toHaveBeenCalledWith("/api/tasks?limit=20", {
      headers: { "Content-Type": "application/json" },
    });
  });

  it("requests automation tasks for a profile after the profile filter and offset", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ tasks: [] }));

    await api.listAutomationTasks({
      profileId: "profile-1",
      limit: 20,
      offset: 20,
    });

    expect(mockFetch).toHaveBeenCalledWith("/api/tasks?profile_id=profile-1&limit=20&offset=20", {
      headers: { "Content-Type": "application/json" },
    });
  });
});

describe("api.saveProfileProxyAsAsset", () => {
  it("sends proxy asset metadata without a URL to the profile proxy-asset endpoint", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({
      id: "proxy-1",
      name: "Saved from profile",
      url: "http://profile-proxy.example:8080",
    }, 201));

    await api.saveProfileProxyAsAsset("profile-1", {
      name: "Saved from profile",
      provider: "ProfilePool",
      tags: [{ tag: "saved", color: "#2563eb" }],
      notes: "Migrated from profile current proxy",
    });

    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toBe("/api/profiles/profile-1/proxy-asset");
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body)).toEqual({
      name: "Saved from profile",
      provider: "ProfilePool",
      tags: [{ tag: "saved", color: "#2563eb" }],
      notes: "Migrated from profile current proxy",
    });
  });
});

// ── setClipboard ────────────────────────────────────────────────────────────

describe("api.setClipboard", () => {
  it("sends POST with text body", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ ok: true }));
    await api.setClipboard("1", "hello");
    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toBe("/api/profiles/1/clipboard");
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body)).toEqual({ text: "hello" });
  });
});

// ── getClipboard ────────────────────────────────────────────────────────────

describe("api.getClipboard", () => {
  it("returns clipboard text", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ text: "copied" }));
    const result = await api.getClipboard("1");
    expect(result.text).toBe("copied");
  });
});

// ── Error handling ──────────────────────────────────────────────────────────

describe("error handling", () => {
  it("throws ApiError with detail on non-ok response", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      statusText: "Not Found",
      json: () => Promise.resolve({ detail: "Profile not found" }),
    });
    await expect(api.getProfile("bad")).rejects.toThrow("Profile not found");
  });

  it("falls back to statusText when response is not JSON", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
      json: () => Promise.reject(new Error("not json")),
    });
    await expect(api.getStatus()).rejects.toThrow("Internal Server Error");
  });
});
