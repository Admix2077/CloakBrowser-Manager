import { render, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { ProxyManagerPage } from "./ProxyManagerPage";
import { api, type ProxyAsset } from "../lib/api";

vi.mock("../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/api")>();
  return {
    ...actual,
    api: {
      listProxies: vi.fn(),
    },
  };
});

const mockListProxies = api.listProxies as ReturnType<typeof vi.fn>;

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

beforeEach(() => {
  mockListProxies.mockReset();
});

describe("ProxyManagerPage", () => {
  it("renders a read-only proxy asset table with credential-safe endpoint labels", async () => {
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
    expect(within(page).queryByRole("button", { name: /assign/i })).toBeNull();
  });

  it("shows a non-destructive empty state when no proxy assets exist", async () => {
    mockListProxies.mockResolvedValue([]);

    render(<ProxyManagerPage />);

    expect(await screen.findByRole("status", { name: "No proxy assets yet" })).toBeTruthy();
    expect(screen.getByText("Proxy assets created through the API will appear here.")).toBeTruthy();
    expect(screen.queryByRole("button", { name: /delete/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /assign/i })).toBeNull();
  });

  it("keeps the table scroll isolated for dense proxy lists", async () => {
    mockListProxies.mockResolvedValue([
      proxy({ id: "proxy-1", name: "US Pool" }),
      proxy({ id: "proxy-2", name: "DE Pool", country_code: "DE", city: "Berlin" }),
    ]);

    render(<ProxyManagerPage />);

    const region = await screen.findByRole("region", { name: "Proxy assets table" });
    expect(region.className).toContain("overflow-auto");
    expect(within(region).getByRole("table", { name: "Proxy assets" }).className).toContain("min-w-[920px]");
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
});
