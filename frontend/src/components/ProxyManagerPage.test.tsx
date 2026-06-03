import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { ProxyManagerPage } from "./ProxyManagerPage";
import { api, type Profile, type ProxyAsset } from "../lib/api";

vi.mock("../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/api")>();
  return {
    ...actual,
    api: {
      listProxies: vi.fn(),
      listProxyProviderPresets: vi.fn(),
      createProxyProviderPreset: vi.fn(),
      updateProxyProviderPreset: vi.fn(),
      deleteProxyProviderPreset: vi.fn(),
      createProxy: vi.fn(),
      bulkCheckProxies: vi.fn(),
      assignProxyToProfiles: vi.fn(),
      assignRandomProxyToProfiles: vi.fn(),
    },
  };
});

const mockListProxies = api.listProxies as ReturnType<typeof vi.fn>;
const mockListProxyProviderPresets = api.listProxyProviderPresets as ReturnType<typeof vi.fn>;
const mockCreateProxyProviderPreset = api.createProxyProviderPreset as ReturnType<typeof vi.fn>;
const mockUpdateProxyProviderPreset = api.updateProxyProviderPreset as ReturnType<typeof vi.fn>;
const mockDeleteProxyProviderPreset = api.deleteProxyProviderPreset as ReturnType<typeof vi.fn>;
const mockCreateProxy = api.createProxy as ReturnType<typeof vi.fn>;
const mockBulkCheckProxies = api.bulkCheckProxies as ReturnType<typeof vi.fn>;
const mockAssignProxyToProfiles = api.assignProxyToProfiles as ReturnType<typeof vi.fn>;
const mockAssignRandomProxyToProfiles = api.assignRandomProxyToProfiles as ReturnType<typeof vi.fn>;

function proxy(overrides: Partial<ProxyAsset>): ProxyAsset {
  return {
    id: "proxy-1",
    name: "US Residential",
    url: "http://proxy.example:8080",
    country_code: "US",
    city: "Los Angeles",
    asn: "AS12345",
    provider: "ProxyCo",
    tags: [{ tag: "stable", color: "#2563eb" }],
    notes: "Primary pool",
    last_check_status: "good",
    last_check_ip: "203.0.113.10",
    last_check_country_code: "US",
    last_check_timezone: "America/Los_Angeles",
    last_check_locale: "en-US",
    last_check_source: "qa",
    last_check_error: null,
    last_check_at: "2026-05-26T04:00:00Z",
    created_at: "2026-05-26T00:00:00Z",
    updated_at: "2026-05-26T04:00:00Z",
    ...overrides,
  };
}

function profile(overrides: Partial<Profile>): Profile {
  return {
    id: "profile-1",
    name: "Alpha Good",
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
    geoip: true,
    last_geoip_ip: null,
    last_geoip_country_code: null,
    last_geoip_timezone: null,
    last_geoip_locale: null,
    last_geoip_source: null,
    last_geoip_resolved_at: null,
    clipboard_sync: true,
    auto_launch: false,
    color_scheme: null,
    launch_args: [],
    notes: null,
    user_data_dir: "/data/profiles/profile-1",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    tags: [],
    status: "stopped",
    vnc_ws_port: null,
    automation_url: null,
    ...overrides,
  };
}

beforeEach(() => {
  mockListProxies.mockReset();
  mockListProxyProviderPresets.mockReset();
  mockListProxyProviderPresets.mockResolvedValue([]);
  mockCreateProxyProviderPreset.mockReset();
  mockUpdateProxyProviderPreset.mockReset();
  mockDeleteProxyProviderPreset.mockReset();
  mockCreateProxy.mockReset();
  mockBulkCheckProxies.mockReset();
  mockAssignProxyToProfiles.mockReset();
  mockAssignRandomProxyToProfiles.mockReset();
});

describe("ProxyManagerPage", () => {
  it("renders a proxy asset table with redacted endpoint labels", async () => {
    mockListProxies.mockResolvedValue([
      proxy({
        id: "proxy-1",
        name: "Credential Pool",
        url: "http://user:hiddenpass@proxy.example:8080",
        last_check_status: "good",
      }),
      proxy({
        id: "proxy-2",
        name: "Broken JP Pool",
        url: "socks5://secret:topsecret@jp.proxy.example:1080",
        country_code: "JP",
        city: "Tokyo",
        provider: "ProxyJP",
        tags: [{ tag: "needs-review", color: "#ef4444" }],
        last_check_status: "error",
        last_check_error: "Connection timeout",
        last_check_at: "2026-05-26T05:00:00Z",
      }),
    ]);

    render(<ProxyManagerPage />);

    const page = await screen.findByRole("region", { name: "Proxy Manager" });
    expect(within(page).getByRole("heading", { name: "Proxy Manager" })).toBeTruthy();
    expect(within(page).getByText("Proxy inventory with credential-redacted checks and profile assignment controls.")).toBeTruthy();
    expect(within(page).getByText("URL credentials are hidden in the UI. Bulk check, profile assignment, provider presets, and CSV import are active; proxy asset add, edit, and delete remain disabled.")).toBeTruthy();
    expect(page.textContent).not.toContain("credential-safe");
    expect(within(page).getByText("2 proxies")).toBeTruthy();
    expect(within(page).getByText("1 good")).toBeTruthy();
    expect(within(page).getByText("1 needs review")).toBeTruthy();

    const table = within(page).getByRole("table", { name: "Proxy assets" });
    expect(within(table).getByText("Credential Pool")).toBeTruthy();
    expect(within(table).getByText("Broken JP Pool")).toBeTruthy();
    expect(within(table).getByText("http://proxy.example:8080")).toBeTruthy();
    expect(within(table).getByText("socks5://jp.proxy.example:1080")).toBeTruthy();
    expect(within(table).getByText("Connection timeout")).toBeTruthy();

    expect(page.textContent).not.toContain("hiddenpass");
    expect(page.textContent).not.toContain("topsecret");
    expect(page.textContent).not.toContain("user:");
    expect(page.textContent).not.toContain("secret:");
    expect(within(page).queryByRole("button", { name: /delete/i })).toBeNull();
  });

  it("shows a non-destructive empty state when no proxy assets exist", async () => {
    mockListProxies.mockResolvedValue([]);

    render(<ProxyManagerPage />);

    expect(await screen.findByRole("status", { name: "No proxy assets yet" })).toBeTruthy();
    expect(screen.getByText("Proxy assets created through the API will appear here.")).toBeTruthy();
    expect(screen.queryByRole("button", { name: /delete/i })).toBeNull();
    expect((screen.getByRole("button", { name: "Assign to profiles" }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("keeps the table scroll isolated for dense proxy lists", async () => {
    mockListProxies.mockResolvedValue([
      proxy({ id: "proxy-1", name: "US Pool" }),
      proxy({ id: "proxy-2", name: "DE Pool", country_code: "DE", city: "Berlin" }),
    ]);

    render(<ProxyManagerPage />);

    const region = await screen.findByRole("region", { name: "Proxy assets table" });
    expect(region.className).toContain("overflow-auto");
    expect(within(region).getByRole("table", { name: "Proxy assets" }).className).toContain("min-w-[980px]");
  });

  it("filters proxy assets locally by search without leaking credentials", async () => {
    const leakMarker = "proxy-last-check-token-super-secret";
    mockListProxies.mockResolvedValue([
      proxy({
        id: "proxy-1",
        name: "Credential Pool",
        url: "http://user:hiddenpass@proxy.example:8080",
        provider: "ProxyCo",
        tags: [{ tag: "stable", color: "#2563eb" }],
      }),
      proxy({
        id: "proxy-2",
        name: "Broken JP Pool",
        url: "socks5://secret:topsecret@jp.proxy.example:1080",
        country_code: "JP",
        city: "Tokyo",
        provider: "ProxyJP",
        tags: [{ tag: "needs-review", color: "#ef4444" }],
        notes:
          "Failed through socks5://note:topsecret@notes.proxy.example:1080 " +
          `Authorization=Bearer ${leakMarker} /data/proxy-secret`,
        last_check_status: "error",
        last_check_error:
          "Failed socks5://secret:topsecret@jp.proxy.example:1080 " +
          `token=${leakMarker} from 203.0.113.45 via [2001:db8::45]:443`,
      }),
      proxy({
        id: "proxy-3",
        name: "DE Backup",
        url: "http://de.proxy.example:8080",
        country_code: "DE",
        city: "Berlin",
        provider: "ProxyDE",
        tags: [{ tag: "backup", color: "#64748b" }],
      }),
    ]);

    render(<ProxyManagerPage />);

    const page = await screen.findByRole("region", { name: "Proxy Manager" });
    const table = within(page).getByRole("table", { name: "Proxy assets" });
    const search = within(page).getByLabelText("Search proxy assets");

    fireEvent.change(search, { target: { value: "jp.proxy.example" } });
    expect(within(page).getByText("1 of 3 visible")).toBeTruthy();
    expect(within(table).getByText("Broken JP Pool")).toBeTruthy();
    expect(within(table).queryByText("Credential Pool")).toBeNull();
    expect(within(table).queryByText("DE Backup")).toBeNull();

    fireEvent.change(search, { target: { value: "proxyco" } });
    expect(within(table).getByText("Credential Pool")).toBeTruthy();
    expect(within(table).queryByText("Broken JP Pool")).toBeNull();

    fireEvent.change(search, { target: { value: "needs-review" } });
    expect(within(table).getByText("Broken JP Pool")).toBeTruthy();
    expect(within(table).queryByText("Credential Pool")).toBeNull();

    expect(page.textContent).not.toContain("hiddenpass");
    expect(page.textContent).not.toContain("topsecret");
    expect(page.textContent).not.toContain("user:");
    expect(page.textContent).not.toContain("secret:");
    expect(page.textContent).not.toContain(leakMarker);
    expect(page.textContent).not.toContain("Authorization");
    expect(page.textContent).not.toContain("Bearer");
    expect(page.textContent).not.toContain("token=");
    expect(page.textContent).not.toContain("/data/proxy-secret");
    expect(page.textContent).not.toContain("203.0.113.45");
    expect(page.textContent).not.toContain("2001:db8::45");
    const titleText = Array.from(page.querySelectorAll("[title]"))
      .map((element) => element.getAttribute("title") ?? "")
      .join(" ");
    expect(titleText).not.toContain("hiddenpass");
    expect(titleText).not.toContain("topsecret");
    expect(titleText).not.toContain("user:");
    expect(titleText).not.toContain("secret:");
    expect(titleText).not.toContain(leakMarker);
    expect(titleText).not.toContain("Authorization");
    expect(titleText).not.toContain("Bearer");
    expect(titleText).not.toContain("token=");
    expect(titleText).not.toContain("/data/proxy-secret");
    expect(titleText).not.toContain("203.0.113.45");
    expect(titleText).not.toContain("2001:db8::45");
    expect(mockListProxies).toHaveBeenCalledTimes(1);
  });

  it("redacts persisted proxy asset names from rendered and search evidence", async () => {
    const leakMarker = "proxy-name-token-super-secret";
    mockListProxies.mockResolvedValue([
      proxy({
        id: "proxy-polluted",
        name:
          "JP Pool Authorization=Bearer " +
          `${leakMarker} token=${leakMarker} /data/proxy-name-secret 203.0.113.77`,
        url: "http://proxy.example:8080",
        country_code: "JP",
        city: "Tokyo",
        provider: "ProxyJP",
      }),
    ]);

    render(<ProxyManagerPage />);

    const page = await screen.findByRole("region", { name: "Proxy Manager" });
    const table = within(page).getByRole("table", { name: "Proxy assets" });
    const safeName = "JP Pool [redacted] [redacted] [redacted-path] [redacted-ip]";

    expect(within(table).getByText(safeName)).toBeTruthy();
    expect(within(page).getByLabelText(`Select ${safeName}`)).toBeTruthy();

    const search = within(page).getByLabelText("Search proxy assets");
    fireEvent.change(search, { target: { value: leakMarker } });
    expect(within(page).getByText("0 of 1 visible")).toBeTruthy();
    expect(within(page).getByRole("status", { name: "No proxy assets match filters" })).toBeTruthy();

    fireEvent.change(search, { target: { value: "jp pool" } });
    expect(within(page).getByText("1 of 1 visible")).toBeTruthy();

    const renderedEvidence = [
      page.textContent,
      ...Array.from(page.querySelectorAll("[title]")).map((element) => element.getAttribute("title") ?? ""),
      ...Array.from(page.querySelectorAll("[aria-label]")).map((element) => element.getAttribute("aria-label") ?? ""),
    ].join(" ");

    for (const leaked of [
      leakMarker,
      "Authorization",
      "Bearer",
      "token=",
      "/data/proxy-name-secret",
      "203.0.113.77",
    ]) {
      expect(renderedEvidence).not.toContain(leaked);
    }
  });

  it("filters by country provider and tag with AND semantics from clean option sets", async () => {
    mockListProxies.mockResolvedValue([
      proxy({
        id: "proxy-1",
        name: "US Stable",
        country_code: "US",
        city: "Los Angeles",
        provider: "ProxyCo",
        tags: [{ tag: "stable", color: "#2563eb" }],
      }),
      proxy({
        id: "proxy-2",
        name: "JP Stable",
        country_code: " JP ",
        city: "Tokyo",
        provider: " ProxyJP ",
        tags: [
          { tag: " stable ", color: "#2563eb" },
          { tag: "asia", color: "#0f766e" },
        ],
      }),
      proxy({
        id: "proxy-3",
        name: "JP Backup",
        country_code: "JP",
        city: null,
        provider: null,
        tags: [],
      }),
    ]);

    render(<ProxyManagerPage />);

    const page = await screen.findByRole("region", { name: "Proxy Manager" });
    const table = within(page).getByRole("table", { name: "Proxy assets" });
    const country = within(page).getByLabelText("Country filter");
    const provider = within(page).getByLabelText("Provider filter");
    const tag = within(page).getByLabelText("Tag filter");

    expect(Array.from(country.querySelectorAll("option")).map((option) => option.value)).toEqual([
      "__all_proxy_filter__",
      "JP",
      "US",
    ]);
    expect(Array.from(provider.querySelectorAll("option")).map((option) => option.value)).toEqual([
      "__all_proxy_filter__",
      "ProxyCo",
      "ProxyJP",
    ]);
    expect(Array.from(tag.querySelectorAll("option")).map((option) => option.value)).toEqual([
      "__all_proxy_filter__",
      "asia",
      "stable",
    ]);

    fireEvent.change(country, { target: { value: "JP" } });
    expect(within(table).getByText("JP Stable")).toBeTruthy();
    expect(within(table).getByText("JP Backup")).toBeTruthy();
    expect(within(table).queryByText("US Stable")).toBeNull();

    fireEvent.change(provider, { target: { value: "ProxyJP" } });
    fireEvent.change(tag, { target: { value: "stable" } });
    expect(within(page).getByText("1 of 3 visible")).toBeTruthy();
    expect(within(table).getByText("JP Stable")).toBeTruthy();
    expect(within(table).queryByText("JP Backup")).toBeNull();
    expect(within(table).queryByText("US Stable")).toBeNull();
    expect(mockListProxies).toHaveBeenCalledTimes(1);
  });

  it("shows a filter empty state with a clear action without masking the true empty inventory state", async () => {
    mockListProxies.mockResolvedValue([
      proxy({ id: "proxy-1", name: "US Stable", provider: "ProxyCo" }),
      proxy({ id: "proxy-2", name: "JP Backup", country_code: "JP", provider: "ProxyJP" }),
    ]);

    render(<ProxyManagerPage />);

    const page = await screen.findByRole("region", { name: "Proxy Manager" });
    fireEvent.change(within(page).getByLabelText("Search proxy assets"), {
      target: { value: "does-not-exist" },
    });

    expect(await within(page).findByRole("status", { name: "No proxy assets match filters" })).toBeTruthy();
    expect(within(page).getByText("0 of 2 visible")).toBeTruthy();
    fireEvent.click(within(page).getByRole("button", { name: "Clear proxy filters" }));

    expect(within(page).getByText("2 of 2 visible")).toBeTruthy();
    expect(within(page).getByRole("table", { name: "Proxy assets" })).toBeTruthy();
    expect(within(page).queryByRole("status", { name: "No proxy assets match filters" })).toBeNull();
    expect(mockListProxies).toHaveBeenCalledTimes(1);
  });

  it("bulk checks selected proxy assets and updates row health without leaking credentials", async () => {
    mockListProxies.mockResolvedValue([
      proxy({
        id: "proxy-1",
        name: "Credential Pool",
        url: "http://user:hiddenpass@proxy.example:8080",
        last_check_status: null,
      }),
      proxy({
        id: "proxy-2",
        name: "Broken JP Pool",
        url: "socks5://secret:topsecret@jp.proxy.example:1080",
        country_code: "JP",
        provider: "ProxyJP",
        tags: [{ tag: "needs-review", color: "#ef4444" }],
        last_check_status: null,
      }),
    ]);
    mockBulkCheckProxies.mockResolvedValue({
      total: 2,
      succeeded: 1,
      failed: 1,
      results: [
        {
          proxy_id: "proxy-1",
          ok: true,
          error: null,
          proxy: proxy({
            id: "proxy-1",
            name: "Credential Pool",
            url: "http://user:hiddenpass@proxy.example:8080",
            last_check_status: "good",
            last_check_ip: "203.0.113.11",
            last_check_country_code: "US",
            last_check_error: null,
            last_check_at: "2026-05-26T06:00:00Z",
          }),
        },
        {
          proxy_id: "proxy-2",
          ok: false,
          error: "cannot connect via socks5://secret:topsecret@jp.proxy.example:1080",
          proxy: proxy({
            id: "proxy-2",
            name: "Broken JP Pool",
            url: "socks5://secret:topsecret@jp.proxy.example:1080",
            country_code: "JP",
            provider: "ProxyJP",
            tags: [{ tag: "needs-review", color: "#ef4444" }],
            last_check_status: "error",
            last_check_error: "cannot connect via socks5://secret:topsecret@jp.proxy.example:1080",
            last_check_at: "2026-05-26T06:01:00Z",
          }),
        },
      ],
    });

    render(<ProxyManagerPage />);

    const page = await screen.findByRole("region", { name: "Proxy Manager" });
    fireEvent.click(within(page).getByLabelText("Select Credential Pool"));
    fireEvent.click(within(page).getByLabelText("Select Broken JP Pool"));
    expect(within(page).getByText("2 selected")).toBeTruthy();

    fireEvent.click(within(page).getByRole("button", { name: "Check selected proxies" }));

    await waitFor(() => expect(mockBulkCheckProxies).toHaveBeenCalledWith(["proxy-1", "proxy-2"]));
    expect(await within(page).findByText("Bulk check complete: 1 succeeded, 1 failed")).toBeTruthy();
    expect(within(page).getByText("good")).toBeTruthy();
    expect(within(page).getByText("error")).toBeTruthy();
    expect(within(page).getByText("cannot connect via socks5://jp.proxy.example:1080")).toBeTruthy();
    expect(within(page).getByText("1 good")).toBeTruthy();
    expect(within(page).getByText("1 needs review")).toBeTruthy();

    const titleText = Array.from(page.querySelectorAll("[title]"))
      .map((element) => element.getAttribute("title") ?? "")
      .join(" ");
    expect(`${page.textContent} ${titleText}`).not.toContain("hiddenpass");
    expect(`${page.textContent} ${titleText}`).not.toContain("topsecret");
    expect(`${page.textContent} ${titleText}`).not.toContain("user:");
    expect(`${page.textContent} ${titleText}`).not.toContain("secret:");
    expect(within(page).queryByRole("button", { name: /delete/i })).toBeNull();
  });

  it("selects all visible filtered proxy assets for bulk checking", async () => {
    mockListProxies.mockResolvedValue([
      proxy({ id: "proxy-1", name: "US Stable", country_code: "US", provider: "ProxyCo" }),
      proxy({ id: "proxy-2", name: "JP Stable", country_code: "JP", provider: "ProxyJP" }),
      proxy({ id: "proxy-3", name: "JP Backup", country_code: "JP", provider: "ProxyJP" }),
    ]);
    mockBulkCheckProxies.mockResolvedValue({
      total: 2,
      succeeded: 2,
      failed: 0,
      results: [
        { proxy_id: "proxy-2", ok: true, error: null, proxy: null },
        { proxy_id: "proxy-3", ok: true, error: null, proxy: null },
      ],
    });

    render(<ProxyManagerPage />);

    const page = await screen.findByRole("region", { name: "Proxy Manager" });
    fireEvent.change(within(page).getByLabelText("Country filter"), { target: { value: "JP" } });
    fireEvent.click(within(page).getByLabelText("Select all visible proxy assets"));

    expect(within(page).getByText("2 selected")).toBeTruthy();
    fireEvent.click(within(page).getByRole("button", { name: "Check selected proxies" }));

    await waitFor(() => expect(mockBulkCheckProxies).toHaveBeenCalledWith(["proxy-2", "proxy-3"]));
    expect(await within(page).findByText("Bulk check complete: 2 succeeded, 0 failed")).toBeTruthy();
  });

  it("shows a redacted error when bulk proxy checking fails", async () => {
    const leakMarker = "bulk-check-token-super-secret";
    mockListProxies.mockResolvedValue([
      proxy({
        id: "proxy-1",
        name: "Credential Pool",
        url: "http://user:hiddenpass@proxy.example:8080",
      }),
    ]);
    mockBulkCheckProxies.mockRejectedValueOnce(
      new Error(
        `cannot check http://user:hiddenpass@proxy.example:8080 Authorization=Bearer ${leakMarker} token=${leakMarker} /data/proxies.db`,
      ),
    );

    render(<ProxyManagerPage />);

    const page = await screen.findByRole("region", { name: "Proxy Manager" });
    fireEvent.click(within(page).getByLabelText("Select Credential Pool"));
    fireEvent.click(within(page).getByRole("button", { name: "Check selected proxies" }));

    expect((await within(page).findByRole("alert")).textContent).toContain(
      "Bulk check failed: cannot check http://proxy.example:8080",
    );
    expect(page.textContent).not.toContain("hiddenpass");
    expect(page.textContent).not.toContain(leakMarker);
    expect(page.textContent).not.toContain("Authorization");
    expect(page.textContent).not.toContain("Bearer");
    expect(page.textContent).not.toContain("token=");
    expect(page.textContent).not.toContain("/data/proxies.db");
    expect(mockBulkCheckProxies).toHaveBeenCalledTimes(1);
    expect(mockListProxies).toHaveBeenCalledTimes(1);
  });

  it("enables proxy assignment only when one proxy asset is selected", async () => {
    mockListProxies.mockResolvedValue([
      proxy({ id: "proxy-1", name: "US Stable" }),
      proxy({ id: "proxy-2", name: "JP Backup", country_code: "JP" }),
    ]);

    render(<ProxyManagerPage profiles={[
      profile({ id: "alpha", name: "Alpha Good" }),
    ]} />);

    const page = await screen.findByRole("region", { name: "Proxy Manager" });
    const assignButton = within(page).getByRole("button", { name: "Assign to profiles" }) as HTMLButtonElement;
    expect(assignButton.disabled).toBe(true);

    fireEvent.click(within(page).getByLabelText("Select US Stable"));
    expect(assignButton.disabled).toBe(false);

    fireEvent.click(within(page).getByLabelText("Select JP Backup"));
    expect(assignButton.disabled).toBe(true);
  });

  it("assigns the selected proxy to checked profiles and refreshes profile data", async () => {
    const onProfilesAssigned = vi.fn().mockResolvedValue(undefined);
    mockListProxies.mockResolvedValue([
      proxy({
        id: "proxy-1",
        name: "Credential Pool",
        url: "http://user:hiddenpass@proxy.example:8080",
      }),
    ]);
    mockAssignProxyToProfiles.mockResolvedValue({
      proxy_id: "proxy-1",
      proxy: proxy({
        id: "proxy-1",
        name: "Credential Pool",
        url: "http://user:hiddenpass@proxy.example:8080",
      }),
      total: 2,
      succeeded: 2,
      failed: 0,
      results: [
        { profile_id: "alpha", ok: true, error: null },
        { profile_id: "beta", ok: true, error: null },
      ],
    });

    render(<ProxyManagerPage
      profiles={[
        profile({ id: "alpha", name: "Alpha Good", proxy: "http://old-user:oldpass@old.proxy.example:8080" }),
        profile({ id: "beta", name: "Beta Broken", status: "running" }),
      ]}
      onProfilesAssigned={onProfilesAssigned}
    />);

    const page = await screen.findByRole("region", { name: "Proxy Manager" });
    fireEvent.click(within(page).getByLabelText("Select Credential Pool"));
    fireEvent.click(within(page).getByRole("button", { name: "Assign to profiles" }));

    const dialog = await screen.findByRole("dialog", { name: "Assign proxy to profiles" });
    expect(within(dialog).getByText("Credential Pool")).toBeTruthy();
    expect(within(dialog).getByText("http://proxy.example:8080")).toBeTruthy();
    expect(within(dialog).getByText("http://old.proxy.example:8080")).toBeTruthy();

    fireEvent.click(within(dialog).getByLabelText("Assign Alpha Good"));
    fireEvent.click(within(dialog).getByLabelText("Assign Beta Broken"));
    expect(within(dialog).getByText("2 profiles selected")).toBeTruthy();
    fireEvent.click(within(dialog).getByRole("button", { name: "Assign proxy" }));

    await waitFor(() => expect(mockAssignProxyToProfiles).toHaveBeenCalledWith("proxy-1", ["alpha", "beta"]));
    expect(onProfilesAssigned).toHaveBeenCalledTimes(1);
    expect(await within(page).findByText("Assigned proxy to 2 profile(s), 0 failed")).toBeTruthy();
    expect(screen.queryByRole("dialog", { name: "Assign proxy to profiles" })).toBeNull();

    const titleText = Array.from(page.querySelectorAll("[title]"))
      .map((element) => element.getAttribute("title") ?? "")
      .join(" ");
    expect(`${page.textContent} ${titleText}`).not.toContain("hiddenpass");
    expect(`${page.textContent} ${titleText}`).not.toContain("oldpass");
    expect(`${page.textContent} ${titleText}`).not.toContain("user:");
    expect(`${page.textContent} ${titleText}`).not.toContain("old-user:");
  });

  it("redacts legacy current proxy credentials in the assignment dialog", async () => {
    mockListProxies.mockResolvedValue([
      proxy({ id: "proxy-1", name: "Credential Pool" }),
    ]);

    render(<ProxyManagerPage
      profiles={[
        profile({
          id: "legacy-profile",
          name: "Legacy Proxy Profile",
          proxy: "legacy.proxy.example:8080:legacy-user:legacypass",
        }),
      ]}
    />);

    const page = await screen.findByRole("region", { name: "Proxy Manager" });
    fireEvent.click(within(page).getByLabelText("Select Credential Pool"));
    fireEvent.click(within(page).getByRole("button", { name: "Assign to profiles" }));

    const dialog = await screen.findByRole("dialog", { name: "Assign proxy to profiles" });
    expect(within(dialog).getByText("legacy.proxy.example:8080")).toBeTruthy();

    const titleText = Array.from(dialog.querySelectorAll("[title]"))
      .map((element) => element.getAttribute("title") ?? "")
      .join(" ");
    expect(`${dialog.textContent} ${titleText}`).not.toContain("legacypass");
    expect(`${dialog.textContent} ${titleText}`).not.toContain("legacy-user");
  });

  it("folds non-public assignment profile runtime statuses before rendering", async () => {
    const leakMarker = "assignment-status-secret";
    mockListProxies.mockResolvedValue([
      proxy({ id: "proxy-1", name: "Credential Pool" }),
    ]);

    render(<ProxyManagerPage
      profiles={[
        profile({
          id: "polluted-status",
          name: "Polluted Status",
          status: `running Authorization=Bearer ${leakMarker} token=${leakMarker}` as Profile["status"],
        }),
      ]}
    />);

    const page = await screen.findByRole("region", { name: "Proxy Manager" });
    fireEvent.click(within(page).getByLabelText("Select Credential Pool"));
    fireEvent.click(within(page).getByRole("button", { name: "Assign to profiles" }));

    const dialog = await screen.findByRole("dialog", { name: "Assign proxy to profiles" });
    expect(within(dialog).getByText("unknown")).toBeTruthy();
    expect(dialog.textContent).not.toContain("Authorization");
    expect(dialog.textContent).not.toContain("Bearer");
    expect(dialog.textContent).not.toContain("token=");
    expect(dialog.innerHTML).not.toContain(leakMarker);

    fireEvent.change(within(dialog).getByLabelText("Search profiles for assignment"), {
      target: { value: leakMarker },
    });
    expect(within(dialog).queryByText("Polluted Status")).toBeNull();

    fireEvent.change(within(dialog).getByLabelText("Search profiles for assignment"), {
      target: { value: "unknown" },
    });
    expect(within(dialog).getByText("Polluted Status")).toBeTruthy();
  });

  it("does not turn a successful assignment into an assign failure when refresh fails", async () => {
    const onProfilesAssigned = vi.fn().mockRejectedValue(new Error("refresh failed"));
    mockListProxies.mockResolvedValue([
      proxy({ id: "proxy-1", name: "Credential Pool" }),
    ]);
    mockAssignProxyToProfiles.mockResolvedValue({
      proxy_id: "proxy-1",
      proxy: proxy({ id: "proxy-1", name: "Credential Pool" }),
      total: 1,
      succeeded: 1,
      failed: 0,
      results: [{ profile_id: "alpha", ok: true, error: null }],
    });

    render(<ProxyManagerPage
      profiles={[
        profile({ id: "alpha", name: "Alpha Good" }),
      ]}
      onProfilesAssigned={onProfilesAssigned}
    />);

    const page = await screen.findByRole("region", { name: "Proxy Manager" });
    fireEvent.click(within(page).getByLabelText("Select Credential Pool"));
    fireEvent.click(within(page).getByRole("button", { name: "Assign to profiles" }));

    const dialog = await screen.findByRole("dialog", { name: "Assign proxy to profiles" });
    fireEvent.click(within(dialog).getByLabelText("Assign Alpha Good"));
    fireEvent.click(within(dialog).getByRole("button", { name: "Assign proxy" }));

    await waitFor(() => expect(mockAssignProxyToProfiles).toHaveBeenCalledWith("proxy-1", ["alpha"]));
    expect(onProfilesAssigned).toHaveBeenCalledTimes(1);
    expect(await within(page).findByText("Assigned proxy to 1 profile(s), 0 failed. Refresh failed: refresh failed")).toBeTruthy();
    expect(screen.queryByRole("dialog", { name: "Assign proxy to profiles" })).toBeNull();
    expect(page.textContent).not.toContain("Assign failed");
  });

  it("selects all visible assignment profiles after search", async () => {
    mockListProxies.mockResolvedValue([
      proxy({ id: "proxy-1", name: "US Stable" }),
    ]);
    mockAssignProxyToProfiles.mockResolvedValue({
      proxy_id: "proxy-1",
      proxy: proxy({ id: "proxy-1", name: "US Stable" }),
      total: 1,
      succeeded: 1,
      failed: 0,
      results: [{ profile_id: "beta", ok: true, error: null }],
    });

    render(<ProxyManagerPage profiles={[
      profile({ id: "alpha", name: "Alpha Good" }),
      profile({ id: "beta", name: "Beta Broken" }),
    ]} />);

    const page = await screen.findByRole("region", { name: "Proxy Manager" });
    fireEvent.click(within(page).getByLabelText("Select US Stable"));
    fireEvent.click(within(page).getByRole("button", { name: "Assign to profiles" }));

    const dialog = await screen.findByRole("dialog", { name: "Assign proxy to profiles" });
    fireEvent.change(within(dialog).getByLabelText("Search profiles for assignment"), {
      target: { value: "beta" },
    });
    expect(within(dialog).queryByText("Alpha Good")).toBeNull();
    expect(within(dialog).getByText("Beta Broken")).toBeTruthy();

    fireEvent.click(within(dialog).getByLabelText("Select all visible assignment profiles"));
    fireEvent.click(within(dialog).getByRole("button", { name: "Assign proxy" }));

    await waitFor(() => expect(mockAssignProxyToProfiles).toHaveBeenCalledWith("proxy-1", ["beta"]));
  });

  it("shows a redacted assign error when proxy assignment fails", async () => {
    mockListProxies.mockResolvedValue([
      proxy({
        id: "proxy-1",
        name: "Credential Pool",
        url: "http://user:hiddenpass@proxy.example:8080",
      }),
    ]);
    mockAssignProxyToProfiles.mockRejectedValueOnce(
      new Error("cannot assign http://user:hiddenpass@proxy.example:8080"),
    );

    render(<ProxyManagerPage profiles={[
      profile({ id: "alpha", name: "Alpha Good" }),
    ]} />);

    const page = await screen.findByRole("region", { name: "Proxy Manager" });
    fireEvent.click(within(page).getByLabelText("Select Credential Pool"));
    fireEvent.click(within(page).getByRole("button", { name: "Assign to profiles" }));

    const dialog = await screen.findByRole("dialog", { name: "Assign proxy to profiles" });
    fireEvent.click(within(dialog).getByLabelText("Assign Alpha Good"));
    fireEvent.click(within(dialog).getByRole("button", { name: "Assign proxy" }));

    expect((await within(dialog).findByRole("alert")).textContent).toContain(
      "Assign failed: cannot assign http://proxy.example:8080",
    );
    expect(`${document.body.textContent}`).not.toContain("hiddenpass");
    expect(mockAssignProxyToProfiles).toHaveBeenCalledTimes(1);
  });

  it("randomly assigns proxies from the current country provider and tag filters to checked profiles", async () => {
    const onProfilesAssigned = vi.fn().mockResolvedValue(undefined);
    mockListProxies.mockResolvedValue([
      proxy({
        id: "proxy-jp-1",
        name: "JP Mobile A",
        url: "http://user:hiddenpass@jp-a.proxy.example:8080",
        country_code: "JP",
        city: "Tokyo",
        provider: "ProxyJP",
        tags: [{ tag: "mobile", color: "#0ea5e9" }],
      }),
      proxy({
        id: "proxy-us-1",
        name: "US Stable",
        country_code: "US",
        provider: "ProxyUS",
        tags: [{ tag: "stable", color: "#2563eb" }],
      }),
    ]);
    mockAssignRandomProxyToProfiles.mockResolvedValue({
      strategy: "random",
      provider_preset_id: null,
      provider: "ProxyJP",
      country_code: "JP",
      tags: ["mobile"],
      candidate_count: 1,
      total: 2,
      succeeded: 2,
      failed: 0,
      results: [
        { profile_id: "alpha", ok: true, error: null, proxy_id: "proxy-jp-1", proxy: null },
        { profile_id: "beta", ok: true, error: null, proxy_id: "proxy-jp-1", proxy: null },
      ],
    });

    render(<ProxyManagerPage
      profiles={[
        profile({ id: "alpha", name: "Alpha Good" }),
        profile({ id: "beta", name: "Beta Broken", status: "running" }),
      ]}
      onProfilesAssigned={onProfilesAssigned}
    />);

    const page = await screen.findByRole("region", { name: "Proxy Manager" });
    fireEvent.change(within(page).getByLabelText("Country filter"), { target: { value: "JP" } });
    fireEvent.change(within(page).getByLabelText("Provider filter"), { target: { value: "ProxyJP" } });
    fireEvent.change(within(page).getByLabelText("Tag filter"), { target: { value: "mobile" } });

    expect(within(page).getByText("1 of 2 visible")).toBeTruthy();
    fireEvent.click(within(page).getByRole("button", { name: "Random assign" }));

    const dialog = await screen.findByRole("dialog", { name: "Random proxy assignment" });
    expect(within(dialog).getByText("1 candidate proxy")).toBeTruthy();
    expect(within(dialog).getByText("JP")).toBeTruthy();
    expect(within(dialog).getByText("ProxyJP")).toBeTruthy();
    expect(within(dialog).getByText("mobile")).toBeTruthy();

    fireEvent.click(within(dialog).getByLabelText("Assign Alpha Good"));
    fireEvent.click(within(dialog).getByLabelText("Assign Beta Broken"));
    expect(within(dialog).getByText("2 profiles selected")).toBeTruthy();
    fireEvent.click(within(dialog).getByRole("button", { name: "Assign random proxy" }));

    await waitFor(() => expect(mockAssignRandomProxyToProfiles).toHaveBeenCalledWith({
      profile_ids: ["alpha", "beta"],
      country_code: "JP",
      provider: "ProxyJP",
      tags: ["mobile"],
    }));
    expect(onProfilesAssigned).toHaveBeenCalledTimes(1);
    expect(await within(page).findByText("Random assigned proxy to 2 profile(s), 0 failed")).toBeTruthy();
    expect(screen.queryByRole("dialog", { name: "Random proxy assignment" })).toBeNull();

    const renderedEvidence = [
      page.textContent,
      ...Array.from(document.body.querySelectorAll("[title]")).map((element) => element.getAttribute("title") ?? ""),
    ].join(" ");
    expect(renderedEvidence).not.toContain("hiddenpass");
    expect(renderedEvidence).not.toContain("user:");
  });

  it("creates proxy provider presets from the manager dialog without sensitive provider fields", async () => {
    const createdPreset = {
      id: "preset-new",
      name: "Japan mobile default",
      provider: "ProxyJP",
      country_code: "JP",
      tags: [
        { tag: "mobile", color: null },
        { tag: "warmup", color: null },
      ],
      notes: "Tokyo exits",
      created_at: "2026-05-26T00:00:00Z",
      updated_at: "2026-05-26T00:00:00Z",
    };
    mockListProxies.mockResolvedValue([]);
    mockCreateProxyProviderPreset.mockResolvedValue(createdPreset);

    render(<ProxyManagerPage />);

    const page = await screen.findByRole("region", { name: "Proxy Manager" });
    fireEvent.click(within(page).getByRole("button", { name: "Manage presets" }));

    const dialog = await screen.findByRole("dialog", { name: "Manage provider presets" });
    expect(dialog.textContent).not.toMatch(/api key|password|billing|account/i);

    fireEvent.change(within(dialog).getByLabelText("Preset name"), {
      target: { value: "Japan mobile default" },
    });
    fireEvent.change(within(dialog).getByLabelText("Preset provider"), {
      target: { value: "ProxyJP" },
    });
    fireEvent.change(within(dialog).getByLabelText("Preset country"), {
      target: { value: "jp" },
    });
    fireEvent.change(within(dialog).getByLabelText("Preset tags"), {
      target: { value: "mobile, warmup" },
    });
    fireEvent.change(within(dialog).getByLabelText("Preset notes"), {
      target: { value: "Tokyo exits" },
    });
    fireEvent.click(within(dialog).getByRole("button", { name: "Save preset" }));

    await waitFor(() => expect(mockCreateProxyProviderPreset).toHaveBeenCalledWith({
      name: "Japan mobile default",
      provider: "ProxyJP",
      country_code: "JP",
      tags: [
        { tag: "mobile", color: null },
        { tag: "warmup", color: null },
      ],
      notes: "Tokyo exits",
    }));
    expect(await within(dialog).findByText("Saved provider preset Japan mobile default")).toBeTruthy();
    expect(within(dialog).getByText("Japan mobile default")).toBeTruthy();
    expect(within(dialog).getByText("ProxyJP")).toBeTruthy();
    expect(within(dialog).getByText("mobile")).toBeTruthy();
  });

  it("redacts persisted provider preset name and notes from rendered evidence", async () => {
    const leakMarker = "preset-card-token-super-secret";
    mockListProxies.mockResolvedValue([]);
    mockListProxyProviderPresets.mockResolvedValue([
      {
        id: "preset-polluted",
        name:
          "Japan default Authorization=Bearer " +
          `${leakMarker} token=${leakMarker} /data/provider-secret 203.0.113.55`,
        provider: "ProxyJP",
        country_code: "JP",
        tags: [{ tag: "mobile", color: "#0ea5e9" }],
        notes:
          "Notes Bearer " +
          `${leakMarker} token=${leakMarker} /home/provider-secret 2001:db8::55`,
        created_at: "2026-05-26T00:00:00Z",
        updated_at: "2026-05-26T00:00:00Z",
      },
    ]);

    render(<ProxyManagerPage />);

    const page = await screen.findByRole("region", { name: "Proxy Manager" });
    fireEvent.click(within(page).getByRole("button", { name: "Manage presets" }));

    const dialog = await screen.findByRole("dialog", { name: "Manage provider presets" });
    expect(within(dialog).getByText("Japan default [redacted] [redacted] [redacted-path] [redacted-ip]")).toBeTruthy();
    expect(within(dialog).getByText("Notes [redacted] [redacted] [redacted-path] [redacted-ip]")).toBeTruthy();

    const renderedEvidence = [
      dialog.textContent,
      ...Array.from(dialog.querySelectorAll("[title]")).map((element) => element.getAttribute("title") ?? ""),
      ...Array.from(dialog.querySelectorAll("[aria-label]")).map((element) => element.getAttribute("aria-label") ?? ""),
    ].join(" ");

    for (const leaked of [
      leakMarker,
      "Authorization",
      "Bearer",
      "token=",
      "/data/provider-secret",
      "/home/provider-secret",
      "203.0.113.55",
      "2001:db8::55",
    ]) {
      expect(renderedEvidence).not.toContain(leaked);
    }
  });

  it("updates and deletes proxy provider presets from the manager dialog", async () => {
    mockListProxies.mockResolvedValue([]);
    mockListProxyProviderPresets.mockResolvedValue([
      {
        id: "preset-jp",
        name: "Japan mobile default",
        provider: "ProxyJP",
        country_code: "JP",
        tags: [{ tag: "mobile", color: "#0ea5e9" }],
        notes: "Tokyo exits",
        created_at: "2026-05-26T00:00:00Z",
        updated_at: "2026-05-26T00:00:00Z",
      },
    ]);
    mockUpdateProxyProviderPreset.mockResolvedValue({
      id: "preset-jp",
      name: "Japan warmup default",
      provider: "ProxyJP",
      country_code: "JP",
      tags: [{ tag: "warmup", color: null }],
      notes: "Updated exits",
      created_at: "2026-05-26T00:00:00Z",
      updated_at: "2026-05-26T00:10:00Z",
    });
    mockDeleteProxyProviderPreset.mockResolvedValue({ ok: true });

    render(<ProxyManagerPage />);

    const page = await screen.findByRole("region", { name: "Proxy Manager" });
    await waitFor(() => expect(mockListProxyProviderPresets).toHaveBeenCalledTimes(1));
    fireEvent.click(within(page).getByRole("button", { name: "Manage presets" }));

    const dialog = await screen.findByRole("dialog", { name: "Manage provider presets" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Edit Japan mobile default" }));
    fireEvent.change(within(dialog).getByLabelText("Preset name"), {
      target: { value: "Japan warmup default" },
    });
    fireEvent.change(within(dialog).getByLabelText("Preset tags"), {
      target: { value: "warmup" },
    });
    fireEvent.change(within(dialog).getByLabelText("Preset notes"), {
      target: { value: "Updated exits" },
    });
    fireEvent.click(within(dialog).getByRole("button", { name: "Save changes" }));

    await waitFor(() => expect(mockUpdateProxyProviderPreset).toHaveBeenCalledWith("preset-jp", {
      name: "Japan warmup default",
      provider: "ProxyJP",
      country_code: "JP",
      tags: [{ tag: "warmup", color: null }],
      notes: "Updated exits",
    }));
    expect(await within(dialog).findByText("Saved provider preset Japan warmup default")).toBeTruthy();

    fireEvent.click(within(dialog).getByRole("button", { name: "Delete Japan warmup default" }));

    await waitFor(() => expect(mockDeleteProxyProviderPreset).toHaveBeenCalledWith("preset-jp"));
    expect(await within(dialog).findByText("Deleted provider preset Japan warmup default")).toBeTruthy();
    expect(within(dialog).queryByText("Japan warmup default")).toBeNull();
  });

  it("imports valid pasted CSV rows through createProxy and skips invalid rows", async () => {
    const existingProxy = proxy({ id: "proxy-existing", name: "Existing Pool" });
    const importedProxy = proxy({
      id: "proxy-imported",
      name: "Imported JP",
      url: "http://jp.proxy.example:8080",
      country_code: "JP",
      city: "Tokyo",
      asn: "AS64512",
      provider: "ProxyJP",
      tags: [
        { tag: "asia", color: null },
        { tag: "stable", color: null },
      ],
      notes: "Primary imported pool",
    });
    mockListProxies
      .mockResolvedValueOnce([existingProxy])
      .mockResolvedValueOnce([existingProxy, importedProxy]);
    mockCreateProxy.mockResolvedValue(importedProxy);

    render(<ProxyManagerPage />);

    const page = await screen.findByRole("region", { name: "Proxy Manager" });
    fireEvent.click(within(page).getByRole("button", { name: "Import CSV" }));

    const dialog = await screen.findByRole("dialog", { name: "Import proxy CSV" });
    fireEvent.change(within(dialog).getByLabelText("Proxy CSV content"), {
      target: {
        value: [
          "name,url,country_code,city,asn,provider,tags,notes",
          "Imported JP,http://user:hiddenpass@jp.proxy.example:8080,JP,Tokyo,AS64512,ProxyJP,asia|stable,Primary imported pool",
          "Missing Url,,US,New York,AS64513,ProxyUS,broken,Missing endpoint",
        ].join("\n"),
      },
    });

    expect(within(dialog).getByText("1 ready")).toBeTruthy();
    expect(within(dialog).getByText("1 blocked")).toBeTruthy();
    expect(within(dialog).getByText("Missing url")).toBeTruthy();

    fireEvent.click(within(dialog).getByRole("button", { name: "Import valid rows" }));

    await waitFor(() => expect(mockCreateProxy).toHaveBeenCalledTimes(1));
    expect(mockCreateProxy).toHaveBeenCalledWith({
      name: "Imported JP",
      url: "http://user:hiddenpass@jp.proxy.example:8080",
      country_code: "JP",
      city: "Tokyo",
      asn: "AS64512",
      provider: "ProxyJP",
      tags: [
        { tag: "asia", color: null },
        { tag: "stable", color: null },
      ],
      notes: "Primary imported pool",
    });
    await waitFor(() => expect(mockListProxies).toHaveBeenCalledTimes(2));
    expect(await within(dialog).findByText("Imported 1 proxy asset(s), 1 failed")).toBeTruthy();
    expect(within(within(page).getByRole("table", { name: "Proxy assets" })).getByText("Imported JP")).toBeTruthy();

    const renderedEvidence = [
      within(page).getByRole("table", { name: "Proxy assets" }).textContent,
      within(dialog).getByRole("table", { name: "Proxy CSV preview" }).textContent,
      within(dialog).getByText("Row 3: Missing url").textContent,
      ...Array.from(page.querySelectorAll("[title]")).map((element) => element.getAttribute("title") ?? ""),
    ].join(" ");
    expect(renderedEvidence).not.toContain("hiddenpass");
    expect(renderedEvidence).not.toContain("user:");
  });

  it("applies proxy provider preset defaults to CSV import rows", async () => {
    const existingProxy = proxy({ id: "proxy-existing", name: "Existing Pool" });
    const importedProxy = proxy({
      id: "proxy-imported",
      name: "Imported Preset JP",
      url: "http://jp.proxy.example:8080",
      country_code: "JP",
      provider: "ProxyJP",
      tags: [
        { tag: "mobile", color: "#0ea5e9" },
        { tag: "bulk", color: null },
      ],
    });
    mockListProxies
      .mockResolvedValueOnce([existingProxy])
      .mockResolvedValueOnce([existingProxy, importedProxy]);
    mockListProxyProviderPresets.mockResolvedValue([
      {
        id: "preset-jp",
        name: "Japan mobile default",
        provider: "ProxyJP",
        country_code: "JP",
        tags: [{ tag: "mobile", color: "#0ea5e9" }],
        notes: "Tokyo exits",
        created_at: "2026-05-26T00:00:00Z",
        updated_at: "2026-05-26T00:00:00Z",
      },
    ]);
    mockCreateProxy.mockResolvedValue(importedProxy);

    render(<ProxyManagerPage />);

    const page = await screen.findByRole("region", { name: "Proxy Manager" });
    await waitFor(() => expect(mockListProxyProviderPresets).toHaveBeenCalledTimes(1));
    fireEvent.click(within(page).getByRole("button", { name: "Import CSV" }));

    const dialog = await screen.findByRole("dialog", { name: "Import proxy CSV" });
    fireEvent.change(within(dialog).getByLabelText("Provider preset"), {
      target: { value: "preset-jp" },
    });
    fireEvent.change(within(dialog).getByLabelText("Proxy CSV content"), {
      target: {
        value: [
          "name,url,tags",
          "Imported Preset JP,http://user:hiddenpass@jp.proxy.example:8080,bulk",
        ].join("\n"),
      },
    });

    expect(within(dialog).getByText("Japan mobile default")).toBeTruthy();
    expect(within(dialog).getByText("ProxyJP")).toBeTruthy();
    expect(within(dialog).getByText("mobile, bulk")).toBeTruthy();

    fireEvent.click(within(dialog).getByRole("button", { name: "Import valid rows" }));

    await waitFor(() => expect(mockCreateProxy).toHaveBeenCalledWith({
      name: "Imported Preset JP",
      url: "http://user:hiddenpass@jp.proxy.example:8080",
      country_code: "JP",
      provider: "ProxyJP",
      tags: [
        { tag: "mobile", color: "#0ea5e9" },
        { tag: "bulk", color: null },
      ],
      notes: "Tokyo exits",
    }));
    expect(`${document.body.textContent}`).not.toContain("hiddenpass");
  });

  it("keeps CSV import failures visible and redacted after partial success", async () => {
    const leakMarker = "proxy-import-token-super-secret";
    const existingProxy = proxy({ id: "proxy-existing", name: "Existing Pool" });
    const importedProxy = proxy({ id: "proxy-imported", name: "Imported Good" });
    mockListProxies
      .mockResolvedValueOnce([existingProxy])
      .mockResolvedValueOnce([existingProxy, importedProxy]);
    mockCreateProxy
      .mockResolvedValueOnce(importedProxy)
      .mockRejectedValueOnce(
        new Error(
          `cannot save http://user:hiddenpass@bad.proxy.example:8080 Authorization=Bearer ${leakMarker} token=${leakMarker} /data/proxies.db`,
        ),
      );

    render(<ProxyManagerPage />);

    const page = await screen.findByRole("region", { name: "Proxy Manager" });
    fireEvent.click(within(page).getByRole("button", { name: "Import CSV" }));

    const dialog = await screen.findByRole("dialog", { name: "Import proxy CSV" });
    fireEvent.change(within(dialog).getByLabelText("Proxy CSV content"), {
      target: {
        value: [
          "name,url,provider,tags",
          "Imported Good,http://good.proxy.example:8080,ProxyCo,stable",
          "Imported Bad,http://user:hiddenpass@bad.proxy.example:8080,ProxyCo,bad",
        ].join("\n"),
      },
    });
    fireEvent.click(within(dialog).getByRole("button", { name: "Import valid rows" }));

    await waitFor(() => expect(mockCreateProxy).toHaveBeenCalledTimes(2));
    expect(await within(dialog).findByText("Imported 1 proxy asset(s), 1 failed")).toBeTruthy();
    const importFailureAlert = within(dialog).getByRole("alert");
    expect(importFailureAlert.textContent).toContain("Row 3: cannot save http://bad.proxy.example:8080");
    const renderedEvidence = [
      within(dialog).getByRole("table", { name: "Proxy CSV preview" }).textContent,
      importFailureAlert.textContent,
      ...Array.from(dialog.querySelectorAll("[title]")).map((element) => element.getAttribute("title") ?? ""),
    ].join(" ");
    expect(renderedEvidence).not.toContain("hiddenpass");
    expect(renderedEvidence).not.toContain("user:");
    expect(renderedEvidence).not.toContain(leakMarker);
    expect(renderedEvidence).not.toContain("Authorization");
    expect(renderedEvidence).not.toContain("Bearer");
    expect(renderedEvidence).not.toContain("token=");
    expect(renderedEvidence).not.toContain("/data/proxies.db");
    expect(await within(within(page).getByRole("table", { name: "Proxy assets" })).findByText("Imported Good")).toBeTruthy();
  });

  it("surfaces a retry action when proxy assets fail to load", async () => {
    mockListProxies
      .mockRejectedValueOnce(new Error("Proxy API unavailable"))
      .mockResolvedValueOnce([proxy({ id: "proxy-1", name: "Recovered Pool" })]);

    render(<ProxyManagerPage />);

    expect((await screen.findByRole("alert")).textContent).toContain("Proxy API unavailable");
    screen.getByRole("button", { name: "Retry loading proxy assets" }).click();

    await waitFor(() => expect(mockListProxies).toHaveBeenCalledTimes(2));
    expect(await screen.findByText("Recovered Pool")).toBeTruthy();
  });

  it("redacts sensitive proxy load errors before rendering retry state", async () => {
    const leakMarker = "proxy-load-token-super-secret";
    mockListProxies.mockRejectedValueOnce(
      new Error(
        `Proxy API failed Authorization=Bearer ${leakMarker} token=${leakMarker} /data/proxies.db`,
      ),
    );

    render(<ProxyManagerPage />);

    const alert = await screen.findByRole("alert");
    const text = alert.textContent ?? "";
    expect(text).toContain("Proxy API failed");
    expect(text).not.toContain(leakMarker);
    expect(text).not.toContain("Authorization");
    expect(text).not.toContain("Bearer");
    expect(text).not.toContain("token=");
    expect(text).not.toContain("/data/proxies.db");
    expect(screen.getByRole("button", { name: "Retry loading proxy assets" })).toBeTruthy();
  });
});
