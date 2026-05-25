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
const mockCheckHealth = vi.fn();
const mockLaunchProfiles = vi.fn();
const mockStopProfiles = vi.fn();
const mockAddTagsToProfiles = vi.fn();
const mockDeleteProfiles = vi.fn();

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
  mockCheckHealth.mockReset();
  mockCheckHealth.mockResolvedValue(undefined);
  mockLaunchProfiles.mockReset();
  mockLaunchProfiles.mockResolvedValue(undefined);
  mockStopProfiles.mockReset();
  mockStopProfiles.mockResolvedValue(undefined);
  mockAddTagsToProfiles.mockReset();
  mockAddTagsToProfiles.mockResolvedValue(undefined);
  mockDeleteProfiles.mockReset();
  mockDeleteProfiles.mockResolvedValue({
    requestedCount: 2,
    deletableCount: 2,
    deletedCount: 2,
    skippedRunningCount: 0,
    failedCount: 0,
    deletedIds: ["beta", "alpha"],
  });
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
    checkHealth: mockCheckHealth,
    launchProfiles: mockLaunchProfiles,
    stopProfiles: mockStopProfiles,
    addTagsToProfiles: mockAddTagsToProfiles,
    deleteProfiles: mockDeleteProfiles,
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

  it("starts with the sidebar collapsed on narrow screens while keeping main operations filters available", async () => {
    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      value: 390,
    });

    render(<App />);

    await waitFor(() => expect(screen.getByRole("table")).toBeTruthy());
    expect(screen.getByRole("region", { name: "Profile operations table" }).className).toContain("overflow-auto");
    expect(screen.getByLabelText("Search profiles")).toBeTruthy();
    expect(screen.queryByText("Quick views")).toBeNull();
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

  it("runs a bulk health check for the currently selected profiles", async () => {
    render(<App />);

    await waitFor(() => expect(screen.getByRole("table")).toBeTruthy());
    fireEvent.click(screen.getByLabelText("Select Beta Broken"));
    fireEvent.click(screen.getByLabelText("Select Alpha Good"));

    fireEvent.click(screen.getByRole("button", { name: "Check health" }));

    await waitFor(() => {
      expect(mockCheckHealth).toHaveBeenCalledWith(["beta", "alpha"]);
    });
    expect((screen.getByRole("button", { name: "Stop selected" }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("runs a bulk launch for the currently selected stopped profiles", async () => {
    render(<App />);

    await waitFor(() => expect(screen.getByRole("table")).toBeTruthy());
    fireEvent.click(screen.getByLabelText("Select Beta Broken"));
    fireEvent.click(screen.getByLabelText("Select Alpha Good"));

    fireEvent.click(screen.getByRole("button", { name: "Launch selected" }));

    await waitFor(() => {
      expect(mockLaunchProfiles).toHaveBeenCalledWith(["beta", "alpha"]);
    });
    expect((screen.getByRole("button", { name: "Stop selected" }) as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByRole("button", { name: "Delete selected" }) as HTMLButtonElement).disabled).toBe(false);
  });

  it("requires confirmation and bulk deletes selected stopped profiles", async () => {
    render(<App />);

    await waitFor(() => expect(screen.getByRole("table")).toBeTruthy());
    fireEvent.click(screen.getByLabelText("Select Beta Broken"));
    fireEvent.click(screen.getByLabelText("Select Alpha Good"));

    fireEvent.click(screen.getByRole("button", { name: "Delete selected" }));
    expect(screen.getByText("Browser data will be permanently removed.")).toBeTruthy();
    expect(mockDeleteProfiles).not.toHaveBeenCalled();

    fireEvent.change(screen.getByLabelText("Type DELETE to confirm bulk deletion"), { target: { value: "DELETE" } });
    fireEvent.click(screen.getByRole("button", { name: "Confirm bulk delete" }));

    await waitFor(() => {
      expect(mockDeleteProfiles).toHaveBeenCalledWith(["beta", "alpha"]);
    });
    expect(screen.queryByText("2 selected")).toBeNull();
  });

  it("only passes stopped profiles to confirmed bulk delete and keeps running selected", async () => {
    mockDeleteProfiles.mockResolvedValue({
      requestedCount: 1,
      deletableCount: 1,
      deletedCount: 1,
      skippedRunningCount: 0,
      failedCount: 0,
      deletedIds: ["stopped"],
    });
    mockUseProfiles.mockReturnValue({
      profiles: [
        profile({ id: "running", name: "Running Profile", status: "running" }),
        profile({ id: "stopped", name: "Stopped Profile", status: "stopped" }),
      ],
      healthByProfileId: {
        running: health("running", {
          status: "good",
          runtime: { status: "running", vnc_ws_port: 6100, automation_url: "/api/profiles/running/automation" },
        }),
        stopped: health("stopped", { status: "good" }),
      },
      loading: false,
      error: null,
      create: vi.fn(),
      update: vi.fn(),
      remove: vi.fn(),
      launch: vi.fn(),
      stop: vi.fn(),
      checkHealth: mockCheckHealth,
      launchProfiles: mockLaunchProfiles,
      stopProfiles: mockStopProfiles,
      addTagsToProfiles: mockAddTagsToProfiles,
      deleteProfiles: mockDeleteProfiles,
    });

    render(<App />);

    await waitFor(() => expect(screen.getByRole("table")).toBeTruthy());
    fireEvent.click(screen.getByLabelText("Select Running Profile"));
    fireEvent.click(screen.getByLabelText("Select Stopped Profile"));

    fireEvent.click(screen.getByRole("button", { name: "Delete selected" }));
    expect(screen.getByText("1 running profile will be skipped. Stop it first if it also needs deletion.")).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Type DELETE to confirm bulk deletion"), { target: { value: "DELETE" } });
    fireEvent.click(screen.getByRole("button", { name: "Confirm bulk delete" }));

    await waitFor(() => {
      expect(mockDeleteProfiles).toHaveBeenCalledWith(["stopped"]);
    });
    expect(screen.getByText("1 selected")).toBeTruthy();
  });

  it("runs a bulk stop for the currently selected running profiles", async () => {
    mockUseProfiles.mockReturnValue({
      profiles: [
        profile({ id: "running", name: "Running Profile", status: "running" }),
        profile({ id: "stopped", name: "Stopped Profile", status: "stopped" }),
      ],
      healthByProfileId: {
        running: health("running", {
          status: "good",
          runtime: { status: "running", vnc_ws_port: 6100, automation_url: "/api/profiles/running/automation" },
        }),
        stopped: health("stopped", { status: "good" }),
      },
      loading: false,
      error: null,
      create: vi.fn(),
      update: vi.fn(),
      remove: vi.fn(),
      launch: vi.fn(),
      stop: vi.fn(),
      checkHealth: mockCheckHealth,
      launchProfiles: mockLaunchProfiles,
      stopProfiles: mockStopProfiles,
      addTagsToProfiles: mockAddTagsToProfiles,
      deleteProfiles: mockDeleteProfiles,
    });

    render(<App />);

    await waitFor(() => expect(screen.getByRole("table")).toBeTruthy());
    fireEvent.click(screen.getByLabelText("Select Running Profile"));
    fireEvent.click(screen.getByLabelText("Select Stopped Profile"));

    fireEvent.click(screen.getByRole("button", { name: "Stop selected" }));

    await waitFor(() => {
      expect(mockStopProfiles).toHaveBeenCalledWith(["running"]);
    });
    expect((screen.getByRole("button", { name: "Tag selected" }) as HTMLButtonElement).disabled).toBe(false);
    expect((screen.getByRole("button", { name: "Delete selected" }) as HTMLButtonElement).disabled).toBe(false);
  });

  it("adds a bulk tag to the currently selected profiles", async () => {
    render(<App />);

    await waitFor(() => expect(screen.getByRole("table")).toBeTruthy());
    fireEvent.click(screen.getByLabelText("Select Beta Broken"));
    fireEvent.click(screen.getByLabelText("Select Alpha Good"));

    fireEvent.click(screen.getByRole("button", { name: "Tag selected" }));
    fireEvent.change(screen.getByLabelText("Bulk tag name"), { target: { value: "ops" } });
    fireEvent.click(screen.getByRole("button", { name: "Apply tag" }));

    await waitFor(() => {
      expect(mockAddTagsToProfiles).toHaveBeenCalledWith(
        ["beta", "alpha"],
        [{ tag: "ops", color: "#6366f1" }],
      );
    });
    expect((screen.getByRole("button", { name: "Delete selected" }) as HTMLButtonElement).disabled).toBe(false);
  });

  it("uses sidebar quick views to drive the main operations table", async () => {
    render(<App />);

    await waitFor(() => expect(screen.getByRole("table")).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: "Unavailable profiles" }));

    expect(tableProfileNames()).toHaveLength(1);
    expect(tableProfileNames()[0]).toContain("Beta Broken");
    expect((screen.getByLabelText("Health status") as HTMLSelectElement).value).toBe("error");
  });

  it("previews a profile summary from the operations table without leaving the table", async () => {
    render(<App />);

    await waitFor(() => expect(screen.getByRole("table")).toBeTruthy());
    const summary = screen.getByRole("complementary", { name: "Profile summary" });
    expect(summary).toBeTruthy();
    expect(within(summary).getByText("Beta Broken")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Preview Alpha Good" }));

    const updatedSummary = screen.getByRole("complementary", { name: "Profile summary" });
    expect(screen.getByRole("table")).toBeTruthy();
    expect(within(updatedSummary).getByText("Alpha Good")).toBeTruthy();
    expect(screen.queryByText("Edit Profile")).toBeNull();

    fireEvent.click(within(updatedSummary).getByRole("button", { name: "Open Alpha Good" }));
    expect(await screen.findByText("Edit Profile")).toBeTruthy();
  });
});
