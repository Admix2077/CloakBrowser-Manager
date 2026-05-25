import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import App from "./App";
import type { Profile, ProfileHealthResponse } from "./lib/api";

vi.mock("./lib/api", () => ({
  api: {
    authStatus: vi.fn(),
    logout: vi.fn(),
  },
  setOnUnauthorized: vi.fn(),
}));

vi.mock("./hooks/useProfiles", () => ({
  useProfiles: vi.fn(),
}));

import { api } from "./lib/api";
import { useProfiles } from "./hooks/useProfiles";

const mockApi = api as {
  authStatus: ReturnType<typeof vi.fn>;
  logout: ReturnType<typeof vi.fn>;
};

const mockUseProfiles = useProfiles as ReturnType<typeof vi.fn>;

function profile(overrides: Partial<Profile>): Profile {
  return {
    id: "profile-1",
    name: "Alpha",
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

function health(profileId: string, overrides: Partial<ProfileHealthResponse>): ProfileHealthResponse {
  return {
    profile_id: profileId,
    status: "unknown",
    geoip: null,
    manual_overrides: { timezone: false, locale: false },
    runtime: { status: "stopped", vnc_ws_port: null, automation_url: null },
    warnings: [],
    checked_at: "2026-05-25T01:00:00Z",
    ...overrides,
  };
}

beforeEach(() => {
  Object.defineProperty(window, "innerWidth", {
    configurable: true,
    value: 1024,
  });
  mockApi.authStatus.mockResolvedValue({ auth_required: false, authenticated: true });
  mockApi.logout.mockResolvedValue({ ok: true });
  mockUseProfiles.mockReturnValue({
    profiles: [
      profile({ id: "beta", name: "Beta Broken" }),
      profile({ id: "alpha", name: "Alpha Good" }),
    ],
    healthByProfileId: {
      beta: health("beta", { status: "error" }),
      alpha: health("alpha", { status: "good" }),
    },
    loading: false,
    error: null,
    create: vi.fn(),
    update: vi.fn(),
    remove: vi.fn(),
    launch: vi.fn(),
    stop: vi.fn(),
  });
});

function tableProfileNames(): string[] {
  return within(screen.getByRole("table"))
    .getAllByRole("row")
    .slice(1)
    .map((row) => within(row).getAllByRole("cell")[1]?.textContent ?? "");
}

describe("App operations console", () => {
  it("shares sidebar filters with the main profile table", async () => {
    render(<App />);

    await waitFor(() => expect(screen.getByRole("table")).toBeTruthy());
    expect(tableProfileNames()[0]).toContain("Beta Broken");

    fireEvent.change(screen.getByLabelText("Sort profiles"), { target: { value: "name" } });
    expect(tableProfileNames()[0]).toContain("Alpha Good");

    fireEvent.change(screen.getByLabelText("Health status"), { target: { value: "good" } });
    expect(tableProfileNames()).toHaveLength(1);
    expect(tableProfileNames()[0]).toContain("Alpha Good");
  });

  it("starts with the sidebar collapsed on narrow screens", async () => {
    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      value: 390,
    });

    render(<App />);

    await waitFor(() => expect(screen.getByRole("table")).toBeTruthy());
    expect(screen.queryByPlaceholderText("Search profiles...")).toBeNull();
    expect(screen.getByTitle("Show sidebar")).toBeTruthy();
  });

  it("tracks selected visible profiles and clears selections hidden by filters", async () => {
    render(<App />);

    await waitFor(() => expect(screen.getByRole("table")).toBeTruthy());
    fireEvent.click(screen.getByLabelText("Select Beta Broken"));

    expect(screen.getByText("1 selected")).toBeTruthy();

    fireEvent.change(screen.getByLabelText("Health status"), { target: { value: "good" } });

    expect(screen.queryByText("1 selected")).toBeNull();
    expect((screen.getByLabelText("Select Alpha Good") as HTMLInputElement).checked).toBe(false);
  });

  it("selects all currently visible profiles from the table header", async () => {
    render(<App />);

    await waitFor(() => expect(screen.getByRole("table")).toBeTruthy());
    fireEvent.change(screen.getByLabelText("Health status"), { target: { value: "good" } });
    fireEvent.click(screen.getByLabelText("Select all visible profiles"));

    expect(screen.getByText("1 selected")).toBeTruthy();
    expect((screen.getByLabelText("Select Alpha Good") as HTMLInputElement).checked).toBe(true);
  });
});
