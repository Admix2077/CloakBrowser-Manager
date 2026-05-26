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

vi.mock("./components/ProfileViewer", () => ({
  ProfileViewer: ({
    profileId,
    automationUrl,
    clipboardSync,
    onDisconnect,
  }: {
    profileId: string;
    automationUrl: string | null;
    clipboardSync: boolean;
    onDisconnect: () => void;
  }) => (
    <section aria-label="VNC viewer">
      <div>VNC viewer for {profileId}</div>
      <div>Automation URL: {automationUrl ?? "none"}</div>
      <div>Clipboard sync: {clipboardSync ? "enabled" : "disabled"}</div>
      <button type="button" onClick={onDisconnect}>Simulate VNC disconnect</button>
    </section>
  ),
}));

import { api } from "./lib/api";
import { useProfiles } from "./hooks/useProfiles";

const mockApi = api as {
  authStatus: ReturnType<typeof vi.fn>;
  logout: ReturnType<typeof vi.fn>;
};

const mockUseProfiles = useProfiles as ReturnType<typeof vi.fn>;
const mockCreate = vi.fn();
const mockUpdate = vi.fn();
const mockRemove = vi.fn();
const mockLaunch = vi.fn();
const mockStop = vi.fn();
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
  mockCreate.mockReset();
  mockCreate.mockResolvedValue(profile({ id: "created", name: "Created Profile" }));
  mockUpdate.mockReset();
  mockUpdate.mockResolvedValue(undefined);
  mockRemove.mockReset();
  mockRemove.mockResolvedValue(undefined);
  mockLaunch.mockReset();
  mockLaunch.mockResolvedValue(undefined);
  mockStop.mockReset();
  mockStop.mockResolvedValue(undefined);
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
    create: mockCreate,
    update: mockUpdate,
    remove: mockRemove,
    launch: mockLaunch,
    stop: mockStop,
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
  it("keeps profile creation reachable from the operations console", async () => {
    render(<App />);

    await waitFor(() => expect(screen.getByRole("table")).toBeTruthy());
    fireEvent.click(screen.getAllByRole("button", { name: "New Profile" })[0]);

    expect(await screen.findByRole("heading", { name: "New Profile" })).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Profile Name"), { target: { value: "Created From Console" } });
    fireEvent.change(screen.getByLabelText("Proxy"), { target: { value: "http://proxy.example:8080" } });
    fireEvent.change(screen.getByLabelText("Timezone"), { target: { value: "America/New_York" } });
    fireEvent.change(screen.getByLabelText("Locale"), { target: { value: "en-US" } });
    fireEvent.change(screen.getByPlaceholderText("Optional notes about this profile..."), {
      target: { value: "Created from operations console" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create" }));

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith(expect.objectContaining({
        name: "Created From Console",
        proxy: "http://proxy.example:8080",
        timezone: "America/New_York",
        locale: "en-US",
        notes: "Created from operations console",
      }));
    });
  });

  it("keeps stopped profile editing reachable from the operations table", async () => {
    render(<App />);

    await waitFor(() => expect(screen.getByRole("table")).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: "Open Alpha Good" }));

    expect(await screen.findByRole("heading", { name: "Edit Profile" })).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Profile Name"), { target: { value: "Alpha Edited" } });
    fireEvent.change(screen.getByLabelText("Timezone"), { target: { value: "America/Los_Angeles" } });
    fireEvent.change(screen.getByPlaceholderText("Optional notes about this profile..."), {
      target: { value: "Edited from operations console" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(mockUpdate).toHaveBeenCalledWith("alpha", expect.objectContaining({
        name: "Alpha Edited",
        timezone: "America/Los_Angeles",
        notes: "Edited from operations console",
      }));
    });
  });

  it("keeps the VNC viewer reachable when opening a running profile from the operations table", async () => {
    mockUseProfiles.mockReturnValue({
      profiles: [
        profile({
          id: "running",
          name: "Running Profile",
          status: "running",
          automation_url: "/api/profiles/running/automation",
          clipboard_sync: true,
          vnc_ws_port: 6100,
        }),
        profile({ id: "stopped", name: "Stopped Profile", status: "stopped" }),
      ],
      healthByProfileId: {
        running: health("running", {
          status: "good",
          runtime: { status: "running", vnc_ws_port: 6100, automation_url: "/api/profiles/running/automation" },
        }),
        stopped: health("stopped", { status: "unknown" }),
      },
      loading: false,
      error: null,
      create: mockCreate,
      update: mockUpdate,
      remove: mockRemove,
      launch: mockLaunch,
      stop: mockStop,
      checkHealth: mockCheckHealth,
      launchProfiles: mockLaunchProfiles,
      stopProfiles: mockStopProfiles,
      addTagsToProfiles: mockAddTagsToProfiles,
      deleteProfiles: mockDeleteProfiles,
    });

    render(<App />);

    await waitFor(() => expect(screen.getByRole("table")).toBeTruthy());
    fireEvent.click(within(screen.getByRole("table")).getByRole("button", { name: "Open Running Profile" }));

    const viewer = await screen.findByRole("region", { name: "VNC viewer" });
    expect(within(viewer).getByText("VNC viewer for running")).toBeTruthy();
    expect(within(viewer).getByText("Automation URL: /api/profiles/running/automation")).toBeTruthy();
    expect(within(viewer).getByText("Clipboard sync: enabled")).toBeTruthy();
    expect(screen.queryByRole("table")).toBeNull();
  });

  it("returns from the VNC viewer to profile editing when the viewer disconnects", async () => {
    mockUseProfiles.mockReturnValue({
      profiles: [
        profile({
          id: "running",
          name: "Running Profile",
          status: "running",
          automation_url: "/api/profiles/running/automation",
          clipboard_sync: false,
          vnc_ws_port: 6100,
        }),
      ],
      healthByProfileId: {
        running: health("running", {
          status: "good",
          runtime: { status: "running", vnc_ws_port: 6100, automation_url: "/api/profiles/running/automation" },
        }),
      },
      loading: false,
      error: null,
      create: mockCreate,
      update: mockUpdate,
      remove: mockRemove,
      launch: mockLaunch,
      stop: mockStop,
      checkHealth: mockCheckHealth,
      launchProfiles: mockLaunchProfiles,
      stopProfiles: mockStopProfiles,
      addTagsToProfiles: mockAddTagsToProfiles,
      deleteProfiles: mockDeleteProfiles,
    });

    render(<App />);

    await waitFor(() => expect(screen.getByRole("table")).toBeTruthy());
    fireEvent.click(within(screen.getByRole("table")).getByRole("button", { name: "Open Running Profile" }));
    expect(await screen.findByRole("region", { name: "VNC viewer" })).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Simulate VNC disconnect" }));

    expect(await screen.findByRole("heading", { name: "Edit Profile" })).toBeTruthy();
    expect(screen.getByDisplayValue("Running Profile")).toBeTruthy();
    expect(screen.queryByRole("region", { name: "VNC viewer" })).toBeNull();
  });

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

  it("shows a no-profile empty state that keeps creation one click away", async () => {
    mockUseProfiles.mockReturnValue({
      profiles: [],
      healthByProfileId: {},
      loading: false,
      error: null,
      create: mockCreate,
      update: mockUpdate,
      remove: mockRemove,
      launch: mockLaunch,
      stop: mockStop,
      checkHealth: mockCheckHealth,
      launchProfiles: mockLaunchProfiles,
      stopProfiles: mockStopProfiles,
      addTagsToProfiles: mockAddTagsToProfiles,
      deleteProfiles: mockDeleteProfiles,
    });

    render(<App />);

    expect(await screen.findByRole("status", { name: "No profiles yet" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Create profile" }));
    expect(await screen.findByRole("heading", { name: "New Profile" })).toBeTruthy();
  });

  it("shows a filtered-empty state and clears filters back to the table", async () => {
    render(<App />);

    await waitFor(() => expect(screen.getByRole("table")).toBeTruthy());
    fireEvent.change(screen.getByLabelText("Search profiles"), { target: { value: "does-not-exist" } });

    expect(screen.getByRole("status", { name: "No profiles match these filters" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Clear filters" }));

    expect(tableProfileNames()).toHaveLength(2);
    expect((screen.getByLabelText("Search profiles") as HTMLInputElement).value).toBe("");
  });

  it("surfaces an all-unknown health state without blocking table operations", async () => {
    mockUseProfiles.mockReturnValue({
      profiles: [
        profile({ id: "unknown-a", name: "Unknown A" }),
        profile({ id: "unknown-b", name: "Unknown B" }),
      ],
      healthByProfileId: {},
      loading: false,
      error: null,
      create: mockCreate,
      update: mockUpdate,
      remove: mockRemove,
      launch: mockLaunch,
      stop: mockStop,
      checkHealth: mockCheckHealth,
      launchProfiles: mockLaunchProfiles,
      stopProfiles: mockStopProfiles,
      addTagsToProfiles: mockAddTagsToProfiles,
      deleteProfiles: mockDeleteProfiles,
    });

    render(<App />);

    expect(await screen.findByRole("status", { name: "Health not checked yet" })).toBeTruthy();
    expect(screen.getByText("2 visible profiles do not have health results yet. Select them and run Check health when ready.")).toBeTruthy();
    fireEvent.click(within(screen.getByRole("table")).getByRole("button", { name: "Open Unknown A" }));
    expect(await screen.findByRole("heading", { name: "Edit Profile" })).toBeTruthy();
  });

  it("starts with the sidebar collapsed on narrow screens while using profile cards", async () => {
    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      value: 390,
    });

    render(<App />);

    const cards = await screen.findByRole("list", { name: "Profile cards" });
    expect(screen.queryByRole("table")).toBeNull();
    expect(screen.getByRole("region", { name: "Profile operations table" }).className).toContain("overflow-auto");
    expect(screen.getByLabelText("Search profiles")).toBeTruthy();
    expect(screen.queryByText("Quick views")).toBeNull();
    expect(screen.getByTitle("Show sidebar")).toBeTruthy();

    fireEvent.click(within(cards).getByRole("button", { name: "Open Alpha Good" }));
    expect(await screen.findByRole("heading", { name: "Edit Profile" })).toBeTruthy();
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

  it("keeps high-risk bulk actions disabled while leaving health check available", async () => {
    render(<App />);

    await waitFor(() => expect(screen.getByRole("table")).toBeTruthy());
    fireEvent.click(screen.getByLabelText("Select Beta Broken"));
    fireEvent.click(screen.getByLabelText("Select Alpha Good"));

    expect((screen.getByRole("button", { name: "Check health" }) as HTMLButtonElement).disabled).toBe(false);
    expect((screen.getByRole("button", { name: "Launch selected" }) as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByRole("button", { name: "Stop selected" }) as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByRole("button", { name: "Tag selected" }) as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByRole("button", { name: "Delete selected" }) as HTMLButtonElement).disabled).toBe(true);

    fireEvent.click(screen.getByRole("button", { name: "Launch selected" }));
    fireEvent.click(screen.getByRole("button", { name: "Delete selected" }));
    fireEvent.click(screen.getByRole("button", { name: "Stop selected" }));
    fireEvent.click(screen.getByRole("button", { name: "Tag selected" }));
    expect(mockLaunchProfiles).not.toHaveBeenCalled();
    expect(mockStopProfiles).not.toHaveBeenCalled();
    expect(mockAddTagsToProfiles).not.toHaveBeenCalled();
    expect(mockDeleteProfiles).not.toHaveBeenCalled();
    expect(screen.queryByLabelText("Bulk tag name")).toBeNull();
    expect(screen.queryByRole("dialog", { name: "Confirm bulk profile deletion" })).toBeNull();
  });

  it("keeps high-risk bulk actions disabled for mixed running and stopped selections", async () => {
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

    expect((screen.getByRole("button", { name: "Launch selected" }) as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByRole("button", { name: "Stop selected" }) as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByRole("button", { name: "Tag selected" }) as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByRole("button", { name: "Delete selected" }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Launch selected" }));
    fireEvent.click(screen.getByRole("button", { name: "Stop selected" }));
    fireEvent.click(screen.getByRole("button", { name: "Tag selected" }));
    fireEvent.click(screen.getByRole("button", { name: "Delete selected" }));
    expect(mockLaunchProfiles).not.toHaveBeenCalled();
    expect(mockStopProfiles).not.toHaveBeenCalled();
    expect(mockAddTagsToProfiles).not.toHaveBeenCalled();
    expect(mockDeleteProfiles).not.toHaveBeenCalled();
    expect(screen.queryByRole("dialog", { name: "Confirm bulk profile deletion" })).toBeNull();
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
