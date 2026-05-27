import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import App from "./App";
import type { Profile, ProfileHealthResponse } from "./lib/api";

const mockProxyManagerPage = vi.hoisted(() => vi.fn(({
  profiles,
  onProfilesAssigned,
}: {
  profiles: Profile[];
  onProfilesAssigned?: () => void | Promise<void>;
}) => (
  <section role="region" aria-label="Proxy Manager">
    <h2>Proxy Manager</h2>
    <p>Proxy Manager page</p>
    <p>Proxy profiles: {profiles.map((profile) => profile.name).join(", ")}</p>
    <button type="button" onClick={() => void onProfilesAssigned?.()}>
      Simulate profile assignment refresh
    </button>
  </section>
)));

const mockAutomationTaskLogViewer = vi.hoisted(() => vi.fn(() => (
  <section role="region" aria-label="Automation tasks">
    <h2>Automation tasks</h2>
    <p>Automation task log viewer</p>
  </section>
)));

const mockSystemDiagnosticsPage = vi.hoisted(() => vi.fn(() => (
  <section role="region" aria-label="System diagnostics">
    <h2>System diagnostics</h2>
    <p>System diagnostics page</p>
  </section>
)));

vi.mock("./lib/api", () => ({
  api: {
    authStatus: vi.fn(),
    logout: vi.fn(),
    listProfileTemplates: vi.fn(),
    previewProfileImport: vi.fn(),
    importProfiles: vi.fn(),
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
    onBackToProfiles,
    onDisconnect,
  }: {
    profileId: string;
    automationUrl: string | null;
    clipboardSync: boolean;
    onBackToProfiles?: () => void;
    onDisconnect: () => void;
  }) => (
    <section aria-label="VNC viewer">
      <div>VNC viewer for {profileId}</div>
      <div>Automation URL: {automationUrl ?? "none"}</div>
      <div>Clipboard sync: {clipboardSync ? "enabled" : "disabled"}</div>
      <button type="button" onClick={onBackToProfiles}>All profiles</button>
      <button type="button" onClick={onDisconnect}>Simulate VNC disconnect</button>
    </section>
  ),
}));

vi.mock("./components/ProxyManagerPage", () => ({
  ProxyManagerPage: mockProxyManagerPage,
}));

vi.mock("./components/AutomationTaskLogViewer", () => ({
  AutomationTaskLogViewer: mockAutomationTaskLogViewer,
}));

vi.mock("./components/SystemDiagnosticsPage", () => ({
  SystemDiagnosticsPage: mockSystemDiagnosticsPage,
}));

import { api } from "./lib/api";
import { useProfiles } from "./hooks/useProfiles";

const mockApi = api as {
  authStatus: ReturnType<typeof vi.fn>;
  logout: ReturnType<typeof vi.fn>;
  listProfileTemplates: ReturnType<typeof vi.fn>;
  previewProfileImport: ReturnType<typeof vi.fn>;
  importProfiles: ReturnType<typeof vi.fn>;
};

const mockUseProfiles = useProfiles as ReturnType<typeof vi.fn>;
const mockCreate = vi.fn();
const mockUpdate = vi.fn();
const mockRemove = vi.fn();
const mockLaunch = vi.fn();
const mockStop = vi.fn();
const mockCheckHealth = vi.fn();
const mockRefresh = vi.fn();
const mockLaunchProfiles = vi.fn();
const mockStopProfiles = vi.fn();
const mockAddTagsToProfiles = vi.fn();
const mockDeleteProfiles = vi.fn();
const mockExportProfileConfigs = vi.fn();

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
  mockApi.listProfileTemplates.mockReset();
  mockApi.listProfileTemplates.mockResolvedValue([]);
  mockApi.previewProfileImport.mockReset();
  mockApi.previewProfileImport.mockResolvedValue({
    total: 0,
    valid: 0,
    invalid: 0,
    rows: [],
  });
  mockApi.importProfiles.mockReset();
  mockApi.importProfiles.mockResolvedValue({
    total: 0,
    succeeded: 0,
    failed: 0,
    results: [],
  });
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
  mockCheckHealth.mockResolvedValue({
    requestedCount: 2,
    checkedCount: 2,
    failedCount: 0,
  });
  mockRefresh.mockReset();
  mockRefresh.mockResolvedValue(undefined);
  mockProxyManagerPage.mockClear();
  mockAutomationTaskLogViewer.mockClear();
  mockSystemDiagnosticsPage.mockClear();
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
  mockExportProfileConfigs.mockReset();
  mockExportProfileConfigs.mockResolvedValue({
    schema_version: 1,
    total: 2,
    exported: 2,
    failed: 0,
    results: [],
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
    refresh: mockRefresh,
    checkHealth: mockCheckHealth,
    launchProfiles: mockLaunchProfiles,
    stopProfiles: mockStopProfiles,
    addTagsToProfiles: mockAddTagsToProfiles,
    deleteProfiles: mockDeleteProfiles,
    exportProfileConfigs: mockExportProfileConfigs,
  });
});

function tableProfileNames(): string[] {
  return within(screen.getByRole("table"))
    .getAllByRole("row")
    .slice(1)
    .map((row) => within(row).getAllByRole("cell")[1]?.textContent ?? "");
}

describe("App operations console", () => {
  it("renders a structured loading skeleton while auth status is pending", () => {
    mockApi.authStatus.mockReturnValue(new Promise(() => undefined));

    render(<App />);

    const status = screen.getByRole("status", { name: "Loading operations console" });
    expect(status).toBeTruthy();
    expect(status.className).toContain("animate-app-skeleton");
    expect(screen.getAllByLabelText("Loading skeleton row").length).toBeGreaterThanOrEqual(3);
  });

  it("renders a structured loading skeleton while profiles are loading", async () => {
    mockUseProfiles.mockReturnValue({
      profiles: [],
      healthByProfileId: {},
      loading: true,
      error: null,
      create: mockCreate,
      update: mockUpdate,
      remove: mockRemove,
      launch: mockLaunch,
      stop: mockStop,
      refresh: mockRefresh,
      checkHealth: mockCheckHealth,
      launchProfiles: mockLaunchProfiles,
      stopProfiles: mockStopProfiles,
      addTagsToProfiles: mockAddTagsToProfiles,
      deleteProfiles: mockDeleteProfiles,
    });

    render(<App />);

    expect(await screen.findByRole("status", { name: "Loading operations console" })).toBeTruthy();
    expect(screen.getAllByLabelText("Loading skeleton row").length).toBeGreaterThanOrEqual(3);
  });

  it("switches between profile operations and the Proxy Manager section", async () => {
    render(<App />);

    await waitFor(() => expect(screen.getByRole("table")).toBeTruthy());
    expect(screen.getByRole("button", { name: "Profiles" }).className).toContain("active:translate-y-px");
    expect(screen.getByRole("button", { name: "Proxy Manager" }).className).toContain("transition-[background-color,color,box-shadow,transform]");
    expect(screen.getByRole("table").closest("[data-console-section]")?.className).toContain("animate-console-section-in");

    fireEvent.click(screen.getByRole("button", { name: "Proxy Manager" }));

    expect(screen.getByRole("region", { name: "Proxy Manager" })).toBeTruthy();
    expect(screen.getByText("Proxy inventory · redacted URLs · assignment controls")).toBeTruthy();
    expect(screen.getByRole("region", { name: "Proxy Manager" }).closest("[data-console-section]")?.className).toContain("animate-console-section-in");
    expect(screen.queryByRole("table")).toBeNull();
    expect(screen.queryByRole("button", { name: "New Profile" })).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Profiles" }));

    expect(await screen.findByRole("table")).toBeTruthy();
    expect(screen.getAllByRole("button", { name: "New Profile" }).length).toBeGreaterThan(0);
  });

  it("switches to the read-only Automation task log section", async () => {
    render(<App />);

    await waitFor(() => expect(screen.getByRole("table")).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: "Automation" }));

    expect(screen.getByRole("region", { name: "Automation tasks" })).toBeTruthy();
    expect(screen.getByText("Queued scripts · redacted task payloads")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "New Profile" })).toBeNull();
    expect(screen.queryByRole("table")).toBeNull();
    expect(mockAutomationTaskLogViewer).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole("button", { name: "Profiles" }));

    expect(await screen.findByRole("table")).toBeTruthy();
  });

  it("switches to the read-only System diagnostics section", async () => {
    render(<App />);

    await waitFor(() => expect(screen.getByRole("table")).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: "System" }));

    expect(screen.getByRole("region", { name: "System diagnostics" })).toBeTruthy();
    expect(screen.getByText("Runtime counts · worker settings · storage checks")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "New Profile" })).toBeNull();
    expect(screen.queryByRole("table")).toBeNull();
    expect(mockSystemDiagnosticsPage).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole("button", { name: "Profiles" }));

    expect(await screen.findByRole("table")).toBeTruthy();
  });

  it("passes profiles and refresh into the Proxy Manager section for assignment workflows", async () => {
    render(<App />);

    await waitFor(() => expect(screen.getByRole("table")).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: "Proxy Manager" }));

    expect(screen.getByText("Proxy profiles: Beta Broken, Alpha Good")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Simulate profile assignment refresh" }));

    expect(mockRefresh).toHaveBeenCalledTimes(1);
  });

  it("keeps profile creation reachable from the operations console", async () => {
    render(<App />);

    await waitFor(() => expect(screen.getByRole("table")).toBeTruthy());
    fireEvent.click(screen.getAllByRole("button", { name: "New Profile" })[0]);

    expect(await screen.findByRole("heading", { name: "New Profile" })).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Profile Name"), { target: { value: "Created From Console" } });
    fireEvent.click(screen.getByRole("tab", { name: "Network" }));
    fireEvent.change(screen.getByLabelText("Proxy"), { target: { value: "http://proxy.example:8080" } });
    fireEvent.change(screen.getByLabelText("Timezone"), { target: { value: "America/New_York" } });
    fireEvent.change(screen.getByLabelText("Locale"), { target: { value: "en-US" } });
    fireEvent.click(screen.getByRole("tab", { name: "Advanced" }));
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
    fireEvent.click(screen.getByRole("tab", { name: "Network" }));
    fireEvent.change(screen.getByLabelText("Timezone"), { target: { value: "America/Los_Angeles" } });
    fireEvent.click(screen.getByRole("tab", { name: "Advanced" }));
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
    expect(screen.queryByRole("region", { name: "Profiles list" })).toBeNull();
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

    const tableRegion = await screen.findByRole("region", { name: "Profile operations table" });
    const emptyState = within(tableRegion).getByRole("status", { name: "No profiles yet" });
    expect(emptyState).toBeTruthy();
    expect(within(screen.getByRole("region", { name: "Profiles list" })).getByRole("status", { name: "No profiles yet" })).toBeTruthy();
    fireEvent.click(within(emptyState).getByRole("button", { name: "Create profile" }));
    expect(await screen.findByRole("heading", { name: "New Profile" })).toBeTruthy();
  });

  it("shows a filtered-empty state and clears filters back to the table", async () => {
    render(<App />);

    await waitFor(() => expect(screen.getByRole("table")).toBeTruthy());
    fireEvent.change(screen.getByLabelText("Search profiles"), { target: { value: "does-not-exist" } });

    const tableRegion = screen.getByRole("region", { name: "Profile operations table" });
    const emptyState = within(tableRegion).getByRole("status", { name: "No profiles match these filters" });
    expect(emptyState).toBeTruthy();
    expect(within(screen.getByRole("region", { name: "Profiles list" })).getByRole("status", { name: "No matching profile shortcuts" })).toBeTruthy();
    fireEvent.click(within(emptyState).getByRole("button", { name: "Clear filters" }));

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
    expect((await screen.findByRole("status", { name: "Profile operation feedback" })).textContent).toBe("Health checked for 2 profiles.");
    expect((screen.getByRole("button", { name: "Stop selected" }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("shows inline warning feedback when a bulk health check partially fails", async () => {
    mockCheckHealth.mockResolvedValue({
      requestedCount: 2,
      checkedCount: 1,
      failedCount: 1,
    });

    render(<App />);

    await waitFor(() => expect(screen.getByRole("table")).toBeTruthy());
    fireEvent.click(screen.getByLabelText("Select Beta Broken"));
    fireEvent.click(screen.getByLabelText("Select Alpha Good"));
    fireEvent.click(screen.getByRole("button", { name: "Check health" }));

    expect((await screen.findByRole("alert", { name: "Profile operation feedback" })).textContent).toBe("Health check finished: 1 checked, 1 failed.");
  });

  it("keeps high-risk bulk actions disabled while leaving health check available", async () => {
    render(<App />);

    await waitFor(() => expect(screen.getByRole("table")).toBeTruthy());
    fireEvent.click(screen.getByLabelText("Select Beta Broken"));
    fireEvent.click(screen.getByLabelText("Select Alpha Good"));

    expect((screen.getByRole("button", { name: "Check health" }) as HTMLButtonElement).disabled).toBe(false);
    expect((screen.getByRole("button", { name: "Export config" }) as HTMLButtonElement).disabled).toBe(false);
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

  it("exports selected profile configs as a JSON download and shows partial feedback", async () => {
    const exportResponse = {
      schema_version: 1,
      total: 2,
      exported: 1,
      failed: 1,
      results: [
        {
          profile_id: "beta",
          ok: true,
          error: null,
          config: {
            name: "Beta Broken",
            fingerprint_seed: 12345,
            proxy: "http://user:hiddenpass@proxy.example:8080",
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
            clipboard_sync: true,
            auto_launch: false,
            color_scheme: null,
            launch_args: [],
            notes: null,
            tags: [],
          },
        },
        {
          profile_id: "alpha",
          ok: false,
          error: "Profile not found",
          config: null,
        },
      ],
    };
    mockExportProfileConfigs.mockResolvedValue(exportResponse);
    const createObjectURLDescriptor = Object.getOwnPropertyDescriptor(URL, "createObjectURL");
    const revokeObjectURLDescriptor = Object.getOwnPropertyDescriptor(URL, "revokeObjectURL");
    const createObjectURL = vi.fn(() => "blob:profile-export");
    const revokeObjectURL = vi.fn();
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: createObjectURL,
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      value: revokeObjectURL,
    });
    const anchorClick = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => undefined);

    try {
      render(<App />);

      await waitFor(() => expect(screen.getByRole("table")).toBeTruthy());
      fireEvent.click(screen.getByLabelText("Select Beta Broken"));
      fireEvent.click(screen.getByLabelText("Select Alpha Good"));
      fireEvent.click(screen.getByRole("button", { name: "Export config" }));

      await waitFor(() => expect(mockExportProfileConfigs).toHaveBeenCalledWith(["beta", "alpha"]));
      expect(createObjectURL).toHaveBeenCalledTimes(1);
      const downloadedBlob = createObjectURL.mock.calls[0][0] as Blob;
      await expect(downloadedBlob.text()).resolves.toBe(JSON.stringify(exportResponse, null, 2));
      expect(anchorClick).toHaveBeenCalledTimes(1);
      expect(revokeObjectURL).toHaveBeenCalledWith("blob:profile-export");
      expect((await screen.findByRole("alert", { name: "Profile operation feedback" })).textContent).toBe("Export finished: 1 exported, 1 failed.");
      expect(document.body.innerHTML).not.toContain("hiddenpass");
    } finally {
      anchorClick.mockRestore();
      if (createObjectURLDescriptor) {
        Object.defineProperty(URL, "createObjectURL", createObjectURLDescriptor);
      } else {
        delete (URL as typeof URL & { createObjectURL?: unknown }).createObjectURL;
      }
      if (revokeObjectURLDescriptor) {
        Object.defineProperty(URL, "revokeObjectURL", revokeObjectURLDescriptor);
      } else {
        delete (URL as typeof URL & { revokeObjectURL?: unknown }).revokeObjectURL;
      }
    }
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

  it("returns to the all profiles table when selecting the sidebar All profiles quick view from profile editing", async () => {
    render(<App />);

    await waitFor(() => expect(screen.getByRole("table")).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: "Open Alpha Good" }));

    expect(await screen.findByText("Edit Profile")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "All profiles" }));

    expect(screen.getByRole("table")).toBeTruthy();
    expect(tableProfileNames()).toHaveLength(2);
    expect(tableProfileNames().join(" ")).toContain("Alpha Good");
    expect(tableProfileNames().join(" ")).toContain("Beta Broken");
    expect(screen.queryByRole("heading", { name: "Edit Profile" })).toBeNull();
    expect((screen.getByLabelText("Health status") as HTMLSelectElement).value).toBe("all");
  });

  it("applies a profile template when creating a profile", async () => {
    mockApi.listProfileTemplates.mockResolvedValue([
      {
        id: "template-mac",
        name: "Mac warmup",
        platform: "macos",
        screen_width: 1440,
        screen_height: 900,
        gpu_vendor: "Apple",
        gpu_renderer: "Apple M2",
        hardware_concurrency: 8,
        color_scheme: "light",
        humanize: true,
        human_preset: "careful",
        launch_args: ["--private-window"],
        geoip: false,
        created_at: "2026-05-26T00:00:00Z",
        updated_at: "2026-05-26T00:00:00Z",
      },
    ]);

    render(<App />);

    await waitFor(() => expect(screen.getByRole("table")).toBeTruthy());
    fireEvent.click(screen.getAllByRole("button", { name: "New Profile" }).at(-1)!);

    const templateSelect = await screen.findByLabelText("Profile template");
    fireEvent.change(templateSelect, { target: { value: "template-mac" } });
    fireEvent.change(screen.getByLabelText("Profile Name"), { target: { value: "Templated profile" } });
    fireEvent.click(screen.getByRole("button", { name: "Create" }));

    await waitFor(() => expect(mockCreate).toHaveBeenCalledWith(expect.objectContaining({
      name: "Templated profile",
      template_id: "template-mac",
      platform: "macos",
      screen_width: 1440,
      screen_height: 900,
      gpu_vendor: "Apple",
      gpu_renderer: "Apple M2",
      hardware_concurrency: 8,
      color_scheme: "light",
      humanize: true,
      human_preset: "careful",
      launch_args: ["--private-window"],
      geoip: false,
    })));
  });

  it("previews profile CSV import without creating profiles or leaking proxy credentials", async () => {
    mockApi.previewProfileImport.mockResolvedValue({
      total: 2,
      valid: 1,
      invalid: 1,
      rows: [
        {
          line_number: 2,
          ok: true,
          errors: [],
          source: {
            name: "Imported JP",
            proxy: "http://jp.proxy.example:8080",
            template: "Mac warmup",
          },
          profile: {
            name: "Imported JP",
            template_id: "template-mac",
            proxy: "http://jp.proxy.example:8080",
            timezone: "Asia/Tokyo",
            locale: "ja-JP",
            platform: "macos",
            screen_width: 1440,
            screen_height: 900,
            gpu_vendor: "Apple",
            gpu_renderer: "Apple M2",
            hardware_concurrency: 8,
            color_scheme: "light",
            humanize: true,
            human_preset: "careful",
            launch_args: ["--private-window"],
            geoip: false,
            notes: "Warmup row",
            tags: [
              { tag: "asia", color: null },
              { tag: "warmup", color: null },
            ],
          },
        },
        {
          line_number: 3,
          ok: false,
          errors: ["name is required", "platform must be one of: windows, macos, linux"],
          source: {
            proxy: "http://bad.proxy.example:8080",
            platform: "ios",
          },
          profile: null,
        },
      ],
    });

    render(<App />);

    await waitFor(() => expect(screen.getByRole("table")).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: "Import CSV" }));

    const dialog = await screen.findByRole("dialog", { name: "Import profile CSV preview" });
    fireEvent.change(within(dialog).getByLabelText("Profile CSV content"), {
      target: {
        value: [
          "name,proxy,tags,notes,template,platform,locale,timezone",
          "Imported JP,http://user:hiddenpass@jp.proxy.example:8080,asia|warmup,Warmup row,Mac warmup,macos,ja-JP,Asia/Tokyo",
          ",http://user:hiddenpass@bad.proxy.example:8080,bad,,Missing,ios,en-US,America/Chicago",
        ].join("\n"),
      },
    });
    fireEvent.click(within(dialog).getByRole("button", { name: "Preview CSV" }));

    await waitFor(() => expect(mockApi.previewProfileImport).toHaveBeenCalledWith(
      expect.stringContaining("Imported JP"),
    ));
    expect(mockCreate).not.toHaveBeenCalled();
    expect(within(dialog).getByText("1 ready")).toBeTruthy();
    expect(within(dialog).getByText("1 blocked")).toBeTruthy();
    expect(within(dialog).getByText("Imported JP")).toBeTruthy();
    expect(within(dialog).getByText("macos")).toBeTruthy();
    expect(within(dialog).getByText("ja-JP")).toBeTruthy();
    expect(within(dialog).getByText("asia")).toBeTruthy();
    expect(within(dialog).getByText("name is required")).toBeTruthy();

    const renderedEvidence = [
      dialog.textContent,
      ...Array.from(dialog.querySelectorAll("[title]")).map((element) => element.getAttribute("title") ?? ""),
    ].join(" ");
    expect(renderedEvidence).not.toContain("hiddenpass");
    expect(renderedEvidence).not.toContain("user:");
  });

  it("imports valid profile CSV rows through the batch API and refreshes profiles", async () => {
    const csvText = [
      "name,proxy,tags,notes,template,platform,locale,timezone",
      "Imported JP,http://user:hiddenpass@jp.proxy.example:8080,asia|warmup,Warmup row,Mac warmup,macos,ja-JP,Asia/Tokyo",
      ",http://user:hiddenpass@bad.proxy.example:8080,bad,,Missing,ios,en-US,America/Chicago",
    ].join("\n");
    mockApi.previewProfileImport.mockResolvedValue({
      total: 2,
      valid: 1,
      invalid: 1,
      rows: [
        {
          line_number: 2,
          ok: true,
          errors: [],
          source: { name: "Imported JP", proxy: "http://jp.proxy.example:8080" },
          profile: {
            name: "Imported JP",
            template_id: null,
            proxy: "http://jp.proxy.example:8080",
            timezone: "Asia/Tokyo",
            locale: "ja-JP",
            platform: "macos",
            screen_width: 1440,
            screen_height: 900,
            gpu_vendor: null,
            gpu_renderer: null,
            hardware_concurrency: null,
            color_scheme: "light",
            humanize: true,
            human_preset: "careful",
            launch_args: [],
            geoip: false,
            notes: "Warmup row",
            tags: [{ tag: "asia", color: null }],
          },
        },
        {
          line_number: 3,
          ok: false,
          errors: ["name is required"],
          source: { proxy: "http://bad.proxy.example:8080" },
          profile: null,
        },
      ],
    });
    mockApi.importProfiles.mockResolvedValue({
      total: 2,
      succeeded: 1,
      failed: 1,
      results: [
        {
          line_number: 2,
          ok: true,
          errors: [],
          source: { name: "Imported JP", proxy: "http://jp.proxy.example:8080" },
          profile: profile({
            id: "imported-jp",
            name: "Imported JP",
            proxy: "http://user:hiddenpass@jp.proxy.example:8080",
            timezone: "Asia/Tokyo",
            locale: "ja-JP",
            platform: "macos",
            tags: [{ tag: "asia", color: null }],
          }),
        },
        {
          line_number: 3,
          ok: false,
          errors: ["name is required"],
          source: { proxy: "http://bad.proxy.example:8080" },
          profile: null,
        },
      ],
    });

    render(<App />);

    await waitFor(() => expect(screen.getByRole("table")).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: "Import CSV" }));

    const dialog = await screen.findByRole("dialog", { name: "Import profile CSV preview" });
    fireEvent.change(within(dialog).getByLabelText("Profile CSV content"), {
      target: { value: csvText },
    });
    fireEvent.click(within(dialog).getByRole("button", { name: "Preview CSV" }));

    await waitFor(() => expect(mockApi.previewProfileImport).toHaveBeenCalledWith(csvText));
    fireEvent.click(await within(dialog).findByRole("button", { name: "Create valid profiles" }));

    await waitFor(() => expect(mockApi.importProfiles).toHaveBeenCalledWith(csvText));
    expect(mockCreate).not.toHaveBeenCalled();
    await waitFor(() => expect(mockRefresh).toHaveBeenCalled());
    expect(await within(dialog).findByText("Imported 1 profile(s), 1 failed")).toBeTruthy();
    expect(within(dialog).getByText("name is required")).toBeTruthy();

    const renderedEvidence = [
      dialog.textContent,
      ...Array.from(dialog.querySelectorAll("[title]")).map((element) => element.getAttribute("title") ?? ""),
    ].join(" ");
    expect(renderedEvidence).not.toContain("hiddenpass");
    expect(renderedEvidence).not.toContain("user:");
  });

  it("returns to the all profiles table when selecting All profiles from the VNC viewer", async () => {
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
    expect(await screen.findByRole("region", { name: "VNC viewer" })).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "All profiles" }));

    expect(await screen.findByRole("table")).toBeTruthy();
    expect(tableProfileNames()).toHaveLength(2);
    expect(tableProfileNames().join(" ")).toContain("Running Profile");
    expect(tableProfileNames().join(" ")).toContain("Stopped Profile");
    expect(screen.queryByRole("region", { name: "VNC viewer" })).toBeNull();
    expect((screen.getByLabelText("Runtime status") as HTMLSelectElement).value).toBe("all");
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
