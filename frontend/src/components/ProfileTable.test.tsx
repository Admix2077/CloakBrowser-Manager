import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ProfileTable } from "./ProfileTable";
import type { Profile, ProfileHealthResponse } from "../lib/api";

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

const profiles = [
  profile({
    id: "good",
    name: "Good US",
    proxy: "http://proxy.example:8080",
    status: "running",
    tags: [{ tag: "warm", color: "#22c55e" }],
  }),
  profile({
    id: "error",
    name: "Broken Proxy",
    proxy: "http://:8080",
    status: "stopped",
    tags: [{ tag: "fix", color: "#ef4444" }],
  }),
];

function tableProfile(index: number): Profile {
  return profile({
    id: `table-${index}`,
    name: `Table Profile ${index.toString().padStart(3, "0")}`,
  });
}

const healthByProfileId = {
  good: health("good", {
    status: "good",
    geoip: {
      ip: "23.144.4.92",
      country_code: "US",
      timezone: "America/Los_Angeles",
      locale: "en-US",
      source: "qa",
      resolved_at: "2026-05-25T00:00:00Z",
    },
    checked_at: "2026-05-25T01:00:00Z",
  }),
  error: health("error", {
    status: "error",
    warnings: [{
      code: "proxy_invalid",
      message: "Proxy URL missing hostname: http://:8080",
      severity: "error",
      action: "修正 proxy 格式后重新检测。",
    }],
    checked_at: "2026-05-25T02:00:00Z",
  }),
};

function setViewportWidth(width: number) {
  Object.defineProperty(window, "innerWidth", {
    configurable: true,
    value: width,
  });
  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    value: vi.fn((query: string) => ({
      matches: query.includes("max-width: 767px") ? width <= 767 : width >= 768,
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
  window.dispatchEvent(new Event("resize"));
}

describe("ProfileTable", () => {
  beforeEach(() => {
    setViewportWidth(1024);
  });

  it("renders dense operations columns", () => {
    render(
      <ProfileTable
        profiles={[profiles[1], profiles[0]]}
        healthByProfileId={healthByProfileId}
        onSelect={vi.fn()}
      />,
    );

    expect(screen.getByRole("columnheader", { name: "Select" })).toBeTruthy();
    expect(screen.getByRole("columnheader", { name: "Profile" })).toBeTruthy();
    expect(screen.getByRole("columnheader", { name: "Health" })).toBeTruthy();
    expect(screen.getByRole("columnheader", { name: "Proxy" })).toBeTruthy();
    expect(screen.getByRole("columnheader", { name: "IP" })).toBeTruthy();
    expect(screen.getByRole("columnheader", { name: "Country" })).toBeTruthy();
    expect(screen.getByRole("columnheader", { name: "Timezone" })).toBeTruthy();
    expect(screen.getByRole("columnheader", { name: "Locale" })).toBeTruthy();
    expect(screen.getByRole("columnheader", { name: "Last checked" })).toBeTruthy();

    const rows = screen.getAllByRole("row").slice(1);
    expect(rows[0].textContent).toContain("Broken Proxy");
    expect(rows[0].textContent).toContain("不可用");
    expect(rows[1].textContent).toContain("Good US");
    expect(rows[1].textContent).toContain("可继续");
    expect(screen.getByText("Invalid proxy")).toBeTruthy();
    expect(screen.getByText("http://proxy.example:8080")).toBeTruthy();
    expect(screen.getByText("23.144.4.92")).toBeTruthy();
    expect(screen.getByText("US").getAttribute("data-badge-type")).toBe("country");
    expect(screen.getByText("America/Los_Angeles")).toBeTruthy();
    expect(screen.getByText("en-US")).toBeTruthy();
  });

  it("renders controlled row selection and select-all controls", () => {
    const onToggleProfileSelection = vi.fn();
    const onToggleVisibleSelection = vi.fn();

    render(
      <ProfileTable
        profiles={profiles}
        healthByProfileId={healthByProfileId}
        onSelect={vi.fn()}
        selectedProfileIds={new Set(["good"])}
        onToggleProfileSelection={onToggleProfileSelection}
        onToggleVisibleSelection={onToggleVisibleSelection}
      />,
    );

    const headerCheckbox = screen.getByLabelText("Select all visible profiles") as HTMLInputElement;
    expect(headerCheckbox.indeterminate).toBe(true);
    expect(headerCheckbox.getAttribute("aria-checked")).toBe("mixed");
    expect(headerCheckbox.closest("label")?.getAttribute("data-state")).toBe("indeterminate");
    const selectedRowCheckbox = screen.getByLabelText("Select Good US") as HTMLInputElement;
    const uncheckedRowCheckbox = screen.getByLabelText("Select Broken Proxy") as HTMLInputElement;
    expect(selectedRowCheckbox.checked).toBe(true);
    expect(selectedRowCheckbox.closest("label")?.getAttribute("data-control")).toBe("selection-checkbox");
    expect(selectedRowCheckbox.closest("label")?.getAttribute("data-state")).toBe("checked");
    expect(uncheckedRowCheckbox.checked).toBe(false);
    expect(uncheckedRowCheckbox.closest("label")?.getAttribute("data-state")).toBe("unchecked");

    fireEvent.click(screen.getByLabelText("Select Broken Proxy"));
    expect(onToggleProfileSelection).toHaveBeenCalledWith("error");

    fireEvent.click(screen.getByLabelText("Select all visible profiles"));
    expect(onToggleVisibleSelection).toHaveBeenCalledWith(["good", "error"], true);
  });

  it("folds non-public runtime statuses before rendering table evidence", () => {
    const leakMarker = "profile-status-secret";
    const pollutedStatus = `running Authorization=Bearer ${leakMarker} token=${leakMarker}`;

    render(
      <ProfileTable
        profiles={[profile({ id: "polluted-status", status: pollutedStatus as Profile["status"] })]}
        healthByProfileId={{}}
        onSelect={vi.fn()}
      />,
    );

    expect(screen.getByText("unknown")).toBeTruthy();
    expect(screen.getByLabelText("Runtime unknown")).toBeTruthy();
    expect(document.body.textContent).not.toContain("Authorization");
    expect(document.body.textContent).not.toContain("Bearer");
    expect(document.body.textContent).not.toContain("token=");
    expect(document.body.innerHTML).not.toContain(leakMarker);
  });

  it("redacts persisted profile names from table rendered evidence", () => {
    const leakMarker = "profile-name-secret";
    const rawName =
      "Alpha Authorization=Bearer " +
      `${leakMarker} token=${leakMarker} /data/profile-name-secret 203.0.113.88`;
    const safeName = "Alpha [redacted] [redacted] [redacted-path] [redacted-ip]";

    render(
      <ProfileTable
        profiles={[profile({ id: "polluted-name", name: rawName })]}
        healthByProfileId={{}}
        onSelect={vi.fn()}
        selectedProfileIds={new Set()}
        onToggleProfileSelection={vi.fn()}
      />,
    );

    expect(screen.getByText(safeName)).toBeTruthy();
    expect(screen.getByLabelText(`Select ${safeName}`)).toBeTruthy();
    expect(screen.getByRole("button", { name: `Preview ${safeName}` })).toBeTruthy();
    expect(screen.getByRole("button", { name: `Open ${safeName}` })).toBeTruthy();

    const renderedEvidence = [
      document.body.textContent,
      ...Array.from(document.querySelectorAll("[title]")).map((element) => element.getAttribute("title") ?? ""),
      ...Array.from(document.querySelectorAll("[aria-label]")).map((element) => element.getAttribute("aria-label") ?? ""),
    ].join(" ");

    for (const leaked of [
      leakMarker,
      "Authorization",
      "Bearer",
      "token=",
      "/data/profile-name-secret",
      "203.0.113.88",
    ]) {
      expect(renderedEvidence).not.toContain(leaked);
    }
  });

  it("keeps the desktop header offset below the sticky bulk action bar", () => {
    render(
      <ProfileTable
        profiles={profiles}
        healthByProfileId={healthByProfileId}
        onSelect={vi.fn()}
        selectedProfileIds={new Set(["good"])}
      />,
    );

    expect(screen.getByRole("toolbar", { name: "Bulk profile actions" })).toBeTruthy();
    expect(document.querySelector("thead")?.className).toContain("top-11");
  });

  it("keeps horizontal scrolling isolated to the operations table region", () => {
    render(
      <ProfileTable
        profiles={profiles}
        healthByProfileId={healthByProfileId}
        onSelect={vi.fn()}
      />,
    );

    const region = screen.getByRole("region", { name: "Profile operations table" });
    expect(region.className).toContain("overflow-auto");
    expect(region.firstElementChild?.className).toContain("min-w-[840px]");
    expect(document.querySelector("col")?.getAttribute("style")).toContain("width: 42px");
  });

  it("marks selected and previewed rows without hiding row actions", () => {
    render(
      <ProfileTable
        profiles={profiles}
        healthByProfileId={healthByProfileId}
        onSelect={vi.fn()}
        selectedProfileIds={new Set(["good"])}
        previewProfileId="error"
      />,
    );

    const selectedRow = screen.getByRole("button", { name: "Preview Good US" }).closest("tr");
    expect(selectedRow?.getAttribute("data-state")).toBe("selected");
    expect(selectedRow?.className).toContain("animate-profile-selection");
    const previewedRow = screen.getByRole("button", { name: "Preview Broken Proxy" }).closest("tr");
    expect(previewedRow?.getAttribute("data-state")).toBe("previewed");
    expect(previewedRow?.className).toContain("animate-profile-preview");
    expect(screen.getByRole("button", { name: "Open Good US" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Open Broken Proxy" })).toBeTruthy();
  });

  it("prioritizes selected state over previewed state on the same desktop row", () => {
    render(
      <ProfileTable
        profiles={profiles}
        healthByProfileId={healthByProfileId}
        onSelect={vi.fn()}
        selectedProfileIds={new Set(["good"])}
        previewProfileId="good"
      />,
    );

    expect(screen.getByRole("button", { name: "Preview Good US" }).closest("tr")?.getAttribute("data-state")).toBe("selected");
  });

  it("keeps checkbox inputs focusable when selection handlers are available", () => {
    render(
      <ProfileTable
        profiles={profiles}
        healthByProfileId={healthByProfileId}
        onSelect={vi.fn()}
        selectedProfileIds={new Set()}
        onToggleProfileSelection={vi.fn()}
        onToggleVisibleSelection={vi.fn()}
      />,
    );

    const rowCheckbox = screen.getByLabelText("Select Good US") as HTMLInputElement;
    rowCheckbox.focus();
    expect(document.activeElement).toBe(rowCheckbox);
  });

  it("disables checkbox inputs when no selection handler is available", () => {
    render(
      <ProfileTable
        profiles={profiles}
        healthByProfileId={healthByProfileId}
        onSelect={vi.fn()}
        selectedProfileIds={new Set()}
      />,
    );

    expect((screen.getByLabelText("Select Good US") as HTMLInputElement).disabled).toBe(true);
    expect((screen.getByLabelText("Select all visible profiles") as HTMLInputElement).disabled).toBe(true);
  });

  it("shows a bulk action bar with selected profile health and runtime summary", () => {
    const onCheckHealth = vi.fn();
    const onExportSelected = vi.fn();
    const onLaunchSelected = vi.fn();
    const onStopSelected = vi.fn();
    const onTagSelected = vi.fn();
    const onDeleteSelected = vi.fn();

    render(
      <ProfileTable
        profiles={profiles}
        healthByProfileId={healthByProfileId}
        onSelect={vi.fn()}
        selectedProfileIds={new Set(["good", "error"])}
        onClearSelection={vi.fn()}
        onCheckSelectedHealth={onCheckHealth}
        onExportSelectedProfiles={onExportSelected}
        onLaunchSelectedProfiles={onLaunchSelected}
        onStopSelectedProfiles={onStopSelected}
        onAddTagsToSelectedProfiles={onTagSelected}
        onDeleteSelectedProfiles={onDeleteSelected}
      />,
    );

    const toolbar = screen.getByRole("toolbar", { name: "Bulk profile actions" });
    expect(toolbar.getAttribute("aria-busy")).toBe("false");
    expect(toolbar.parentElement?.className).toContain("animate-bulk-action-in");
    expect(screen.getByRole("group", { name: "Selected profile summary" })).toBeTruthy();
    expect(screen.getByRole("group", { name: "Bulk action commands" })).toBeTruthy();
    expect(screen.getByRole("group", { name: "Primary bulk action" })).toBeTruthy();
    expect(screen.getByRole("group", { name: "Secondary bulk actions" })).toBeTruthy();
    expect(screen.getByText("2 selected")).toBeTruthy();
    expect(screen.getByText("1 running")).toBeTruthy();
    expect(screen.getByText("1 stopped")).toBeTruthy();
    expect(screen.getByText("1 issue")).toBeTruthy();
    expect((screen.getByRole("button", { name: "Check health" }) as HTMLButtonElement).disabled).toBe(false);
    expect(screen.getByRole("button", { name: "Check health" }).textContent).toContain("Check health");
    fireEvent.click(screen.getByRole("button", { name: "Check health" }));
    expect(onCheckHealth).toHaveBeenCalledTimes(1);
    expect((screen.getByRole("button", { name: "Export config" }) as HTMLButtonElement).disabled).toBe(false);
    fireEvent.click(screen.getByRole("button", { name: "Export config" }));
    expect(onExportSelected).toHaveBeenCalledWith(["good", "error"]);
    expect((screen.getByRole("button", { name: "Launch selected" }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Launch selected" }));
    expect(onLaunchSelected).not.toHaveBeenCalled();
    expect((screen.getByRole("button", { name: "Stop selected" }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Stop selected" }));
    expect(onStopSelected).not.toHaveBeenCalled();
    expect((screen.getByRole("button", { name: "Tag selected" }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Tag selected" }));
    expect(onTagSelected).not.toHaveBeenCalled();
    expect((screen.getByRole("button", { name: "Delete selected" }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Delete selected" }));
    expect(onDeleteSelected).not.toHaveBeenCalled();
  });

  it("shows inline feedback for completed bulk health checks", () => {
    render(
      <ProfileTable
        profiles={profiles}
        healthByProfileId={healthByProfileId}
        onSelect={vi.fn()}
        selectedProfileIds={new Set(["good", "error"])}
        bulkFeedback={{
          tone: "success",
          message: "Health checked for 2 profiles.",
        }}
      />,
    );

    expect(screen.getByRole("status", { name: "Profile operation feedback" }).textContent).toBe("Health checked for 2 profiles.");
  });

  it("shows warning inline feedback for partial bulk health checks", () => {
    render(
      <ProfileTable
        profiles={profiles}
        healthByProfileId={healthByProfileId}
        onSelect={vi.fn()}
        selectedProfileIds={new Set(["good", "error"])}
        bulkFeedback={{
          tone: "warning",
          message: "Health check finished: 1 checked, 1 failed.",
        }}
      />,
    );

    expect(screen.getByRole("alert", { name: "Profile operation feedback" }).textContent).toBe("Health check finished: 1 checked, 1 failed.");
  });

  it("clears selected profiles from the bulk action bar with Escape", () => {
    const onClearSelection = vi.fn();

    render(
      <ProfileTable
        profiles={profiles}
        healthByProfileId={healthByProfileId}
        onSelect={vi.fn()}
        selectedProfileIds={new Set(["good", "error"])}
        onClearSelection={onClearSelection}
      />,
    );

    fireEvent.keyDown(window, { key: "Escape" });

    expect(onClearSelection).toHaveBeenCalledTimes(1);
  });

  it("keeps high-risk bulk deletion disabled even when stopped profiles are selected", () => {
    const onDeleteSelected = vi.fn();

    render(
      <ProfileTable
        profiles={profiles}
        healthByProfileId={healthByProfileId}
        onSelect={vi.fn()}
        selectedProfileIds={new Set(["good", "error"])}
        onDeleteSelectedProfiles={onDeleteSelected}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Delete selected" }));

    expect(onDeleteSelected).not.toHaveBeenCalled();
    expect(screen.queryByRole("dialog", { name: "Confirm bulk profile deletion" })).toBeNull();
  });

  it("keeps bulk delete disabled when only running profiles are selected", () => {
    render(
      <ProfileTable
        profiles={profiles}
        healthByProfileId={healthByProfileId}
        onSelect={vi.fn()}
        selectedProfileIds={new Set(["good"])}
        onDeleteSelectedProfiles={vi.fn()}
      />,
    );

    expect((screen.getByRole("button", { name: "Delete selected" }) as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByRole("button", { name: "Delete selected" }).getAttribute("title")).toBe("Bulk delete is disabled in this console");
  });

  it("keeps bulk tag disabled and does not open the tag form", () => {
    const onTagSelected = vi.fn();

    render(
      <ProfileTable
        profiles={profiles}
        healthByProfileId={healthByProfileId}
        onSelect={vi.fn()}
        selectedProfileIds={new Set(["good", "error"])}
        onAddTagsToSelectedProfiles={onTagSelected}
        onDeleteSelectedProfiles={vi.fn()}
      />,
    );

    expect((screen.getByRole("button", { name: "Tag selected" }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Tag selected" }));
    expect(screen.queryByLabelText("Bulk tag name")).toBeNull();
    expect(onTagSelected).not.toHaveBeenCalled();
  });

  it("keeps disabled bulk tag from opening a form while Escape still clears selection", () => {
    const onTagSelected = vi.fn();
    const onClearSelection = vi.fn();

    render(
      <ProfileTable
        profiles={profiles}
        healthByProfileId={healthByProfileId}
        onSelect={vi.fn()}
        selectedProfileIds={new Set(["good", "error"])}
        onClearSelection={onClearSelection}
        onAddTagsToSelectedProfiles={onTagSelected}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Tag selected" }));
    fireEvent.keyDown(screen.getByRole("button", { name: "Tag selected" }), { key: "Escape" });

    expect(onTagSelected).not.toHaveBeenCalled();
    expect(screen.queryByLabelText("Bulk tag name")).toBeNull();
    expect(screen.getByRole("button", { name: "Tag selected" })).toBeTruthy();
    expect(onClearSelection).toHaveBeenCalledTimes(1);
  });

  it("disables the bulk tag action while tags are applying", () => {
    render(
      <ProfileTable
        profiles={profiles}
        healthByProfileId={healthByProfileId}
        onSelect={vi.fn()}
        selectedProfileIds={new Set(["good", "error"])}
        onAddTagsToSelectedProfiles={vi.fn()}
        taggingSelectedProfiles
      />,
    );

    expect((screen.getByRole("button", { name: "Applying tag" }) as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByText("Applying...")).toBeTruthy();
  });

  it("disables the bulk launch button while launch is running", () => {
    render(
      <ProfileTable
        profiles={profiles}
        healthByProfileId={healthByProfileId}
        onSelect={vi.fn()}
        selectedProfileIds={new Set(["error"])}
        onLaunchSelectedProfiles={vi.fn()}
        launchingSelectedProfiles
      />,
    );

    expect((screen.getByRole("button", { name: "Launching selected" }) as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByText("Launching...")).toBeTruthy();
  });

  it("disables the bulk stop button while stop is running", () => {
    render(
      <ProfileTable
        profiles={profiles}
        healthByProfileId={healthByProfileId}
        onSelect={vi.fn()}
        selectedProfileIds={new Set(["good"])}
        onStopSelectedProfiles={vi.fn()}
        stoppingSelectedProfiles
      />,
    );

    expect((screen.getByRole("button", { name: "Stopping selected" }) as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByText("Stopping...")).toBeTruthy();
  });

  it("disables the bulk health check while checks are running", () => {
    render(
      <ProfileTable
        profiles={profiles}
        healthByProfileId={healthByProfileId}
        onSelect={vi.fn()}
        selectedProfileIds={new Set(["good"])}
        onCheckSelectedHealth={vi.fn()}
        checkingSelectedHealth
      />,
    );

    expect(screen.getByRole("toolbar", { name: "Bulk profile actions" }).getAttribute("aria-busy")).toBe("true");
    const checkButton = screen.getByRole("button", { name: "Checking health" }) as HTMLButtonElement;
    expect(checkButton.disabled).toBe(true);
    expect(checkButton.querySelector("svg")?.getAttribute("class")).toContain("animate-pulse");
    expect(screen.getByText("Checking...")).toBeTruthy();
  });

  it("disables export config while selected profiles are exporting", () => {
    render(
      <ProfileTable
        profiles={profiles}
        healthByProfileId={healthByProfileId}
        onSelect={vi.fn()}
        selectedProfileIds={new Set(["good"])}
        onExportSelectedProfiles={vi.fn()}
        exportingSelectedProfiles
      />,
    );

    expect(screen.getByRole("toolbar", { name: "Bulk profile actions" }).getAttribute("aria-busy")).toBe("true");
    const exportButton = screen.getByRole("button", { name: "Exporting config" }) as HTMLButtonElement;
    expect(exportButton.disabled).toBe(true);
    expect(exportButton.textContent).toContain("Exporting...");
  });

  it("opens the existing profile detail flow when a row action is clicked", () => {
    const onSelect = vi.fn();
    render(
      <ProfileTable
        profiles={profiles}
        healthByProfileId={healthByProfileId}
        onSelect={onSelect}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Open Broken Proxy" }));

    expect(onSelect).toHaveBeenCalledWith("error");
  });

  it("previews rows without reusing selection or open actions", () => {
    const onPreviewProfile = vi.fn();
    const onSelect = vi.fn();
    const onToggleProfileSelection = vi.fn();

    render(
      <ProfileTable
        profiles={profiles}
        healthByProfileId={healthByProfileId}
        onSelect={onSelect}
        selectedProfileIds={new Set()}
        onToggleProfileSelection={onToggleProfileSelection}
        previewProfileId="error"
        onPreviewProfile={onPreviewProfile}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Preview Broken Proxy" }));
    expect(onPreviewProfile).toHaveBeenCalledWith("error");
    expect(onSelect).not.toHaveBeenCalled();
    expect(onToggleProfileSelection).not.toHaveBeenCalled();

    fireEvent.click(screen.getByLabelText("Select Good US"));
    expect(onToggleProfileSelection).toHaveBeenCalledWith("good");
    expect(onPreviewProfile).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole("button", { name: "Open Good US" }));
    expect(onSelect).toHaveBeenCalledWith("good");
    expect(onPreviewProfile).toHaveBeenCalledTimes(1);
  });

  it("keeps the order provided by shared operations filters", () => {
    render(
      <ProfileTable
        profiles={profiles}
        healthByProfileId={healthByProfileId}
        onSelect={vi.fn()}
      />,
    );

    const rows = screen.getAllByRole("row").slice(1);
    expect(rows[0].textContent).toContain("Good US");
    expect(rows[1].textContent).toContain("Broken Proxy");
  });

  it("does not expose proxy credentials in visible text or title attributes", () => {
    render(
      <ProfileTable
        profiles={[
          profile({
            id: "credential-proxy",
            name: "Credential Proxy",
            proxy: "http://user:hiddenpass@proxy.example:8080",
          }),
        ]}
        healthByProfileId={{
          "credential-proxy": health("credential-proxy", {
            status: "error",
            warnings: [{
              code: "proxy_invalid",
              message: "Proxy URL missing port: http://user:hiddenpass@proxy.example",
              severity: "error",
              action: "修正 proxy 格式后重新检测。",
            }],
          }),
        }}
        onSelect={vi.fn()}
      />,
    );

    expect(screen.getByText("http://proxy.example:8080")).toBeTruthy();
    expect(screen.getByTitle("Proxy URL missing port: http://proxy.example")).toBeTruthy();
    expect(screen.queryByText(/hiddenpass/)).toBeNull();
    expect(screen.getByTitle("http://proxy.example:8080")).toBeTruthy();
    expect(document.body.innerHTML).not.toContain("user:hiddenpass");
  });

  it("renders a first-run empty state with a create action", () => {
    const onCreateProfile = vi.fn();
    render(
      <ProfileTable
        profiles={[]}
        healthByProfileId={{}}
        onSelect={vi.fn()}
        selectedProfileIds={new Set()}
        onToggleProfileSelection={vi.fn()}
        onToggleVisibleSelection={vi.fn()}
        totalProfileCount={0}
        onCreateProfile={onCreateProfile}
      />,
    );

    expect(screen.getByRole("status", { name: "No profiles yet" })).toBeTruthy();
    expect(screen.getByText("Create the first profile to start tracking runtime, proxy, GeoIP, and fingerprint health.")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Create profile" }));
    expect(onCreateProfile).toHaveBeenCalledTimes(1);
  });

  it("renders a filtered-empty state with a clear filters action", () => {
    const onClearFilters = vi.fn();
    render(
      <ProfileTable
        profiles={[]}
        healthByProfileId={{}}
        onSelect={vi.fn()}
        selectedProfileIds={new Set()}
        onToggleProfileSelection={vi.fn()}
        onToggleVisibleSelection={vi.fn()}
        totalProfileCount={8}
        hasActiveFilters
        onClearFilters={onClearFilters}
      />,
    );

    expect(screen.getByRole("status", { name: "No profiles match these filters" })).toBeTruthy();
    expect(screen.getByText("Clear or adjust filters to bring profiles back into the operations table.")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Clear filters" }));
    expect(onClearFilters).toHaveBeenCalledTimes(1);
  });

  it("surfaces the health-not-checked state without hiding profile rows", () => {
    render(
      <ProfileTable
        profiles={[profile({ id: "unknown-a", name: "Unknown A" }), profile({ id: "unknown-b", name: "Unknown B" })]}
        healthByProfileId={{}}
        onSelect={vi.fn()}
      />,
    );

    expect(screen.getByRole("status", { name: "Health not checked yet" })).toBeTruthy();
    expect(screen.getByText("2 visible profiles do not have health results yet. Select them and run Check health when ready.")).toBeTruthy();
    expect(screen.getByText("Unknown A")).toBeTruthy();
    expect(screen.getByText("Unknown B")).toBeTruthy();
  });

  it("renders a narrow card list without duplicating the desktop table", () => {
    setViewportWidth(390);

    render(
      <ProfileTable
        profiles={[profiles[1], profiles[0]]}
        healthByProfileId={healthByProfileId}
        onSelect={vi.fn()}
      />,
    );

    expect(screen.queryByRole("table")).toBeNull();
    expect(screen.getByRole("list", { name: "Profile cards" })).toBeTruthy();
    expect(screen.getByRole("listitem", { name: "Profile card Broken Proxy" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Open Broken Proxy" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Preview Broken Proxy" })).toBeTruthy();
    expect(screen.getByText("Invalid proxy")).toBeTruthy();
    expect(screen.getByText("http://proxy.example:8080")).toBeTruthy();
    expect(screen.getByText("23.144.4.92")).toBeTruthy();
    expect(screen.getByText("US").getAttribute("data-badge-type")).toBe("country");
    expect(screen.getByText("America/Los_Angeles")).toBeTruthy();
    expect(screen.getByText("en-US")).toBeTruthy();
  });

  it("keeps narrow card selection and select-all tied to the full filtered set", () => {
    setViewportWidth(390);
    const onToggleProfileSelection = vi.fn();
    const onToggleVisibleSelection = vi.fn();

    render(
      <ProfileTable
        profiles={profiles}
        healthByProfileId={healthByProfileId}
        onSelect={vi.fn()}
        selectedProfileIds={new Set(["good"])}
        onToggleProfileSelection={onToggleProfileSelection}
        onToggleVisibleSelection={onToggleVisibleSelection}
      />,
    );

    const headerCheckbox = screen.getByLabelText("Select all visible profiles") as HTMLInputElement;
    expect(headerCheckbox.indeterminate).toBe(true);
    expect(headerCheckbox.closest("label")?.getAttribute("data-state")).toBe("indeterminate");
    expect((screen.getByLabelText("Select Good US") as HTMLInputElement).checked).toBe(true);
    expect(screen.getByLabelText("Select Good US").closest("label")?.getAttribute("data-state")).toBe("checked");
    expect(screen.getByLabelText("Select Broken Proxy").closest("label")?.getAttribute("data-state")).toBe("unchecked");
    expect(screen.getByRole("toolbar", { name: "Profile card selection" }).className).toContain("top-11");

    fireEvent.click(screen.getByLabelText("Select Broken Proxy"));
    expect(onToggleProfileSelection).toHaveBeenCalledWith("error");

    fireEvent.click(screen.getByLabelText("Select all visible profiles"));
    expect(onToggleVisibleSelection).toHaveBeenCalledWith(["good", "error"], true);
  });

  it("prioritizes selected state over previewed state on the same narrow card", () => {
    setViewportWidth(390);

    render(
      <ProfileTable
        profiles={profiles}
        healthByProfileId={healthByProfileId}
        onSelect={vi.fn()}
        selectedProfileIds={new Set(["good"])}
        previewProfileId="good"
      />,
    );

    const selectedCard = screen.getByRole("listitem", { name: "Profile card Good US" });
    expect(selectedCard.getAttribute("data-state")).toBe("selected");
    expect(selectedCard.className).toContain("animate-profile-selection");
  });

  it("keeps narrow card preview, open, and proxy redaction separate", () => {
    setViewportWidth(390);
    const onPreviewProfile = vi.fn();
    const onSelect = vi.fn();

    render(
      <ProfileTable
        profiles={[
          profile({
            id: "credential-proxy",
            name: "Credential Proxy",
            proxy: "http://user:hiddenpass@proxy.example:8080",
          }),
        ]}
        healthByProfileId={{}}
        onSelect={onSelect}
        previewProfileId="credential-proxy"
        onPreviewProfile={onPreviewProfile}
      />,
    );

    const previewedCard = screen.getByRole("listitem", { name: "Profile card Credential Proxy" });
    expect(previewedCard.getAttribute("data-state")).toBe("previewed");
    expect(previewedCard.className).toContain("animate-profile-preview");
    expect(screen.getByText("http://proxy.example:8080")).toBeTruthy();
    expect(document.body.innerHTML).not.toContain("user:hiddenpass");

    fireEvent.click(screen.getByRole("button", { name: "Preview Credential Proxy" }));
    expect(onPreviewProfile).toHaveBeenCalledWith("credential-proxy");
    expect(onSelect).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Open Credential Proxy" }));
    expect(onSelect).toHaveBeenCalledWith("credential-proxy");
  });

  it("virtualizes large profile tables while keeping row actions usable", () => {
    const onSelect = vi.fn();
    const profiles = Array.from({ length: 300 }, (_, index) => tableProfile(index));

    render(
      <ProfileTable
        profiles={profiles}
        healthByProfileId={{}}
        onSelect={onSelect}
      />,
    );

    expect(screen.getByText("Table Profile 000")).toBeTruthy();
    expect(screen.queryByText("Table Profile 120")).toBeNull();

    const table = screen.getByRole("region", { name: "Profile operations table" });
    fireEvent.scroll(table, { target: { scrollTop: 64 * 120 } });

    expect(screen.queryByText("Table Profile 000")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Open Table Profile 120" }));
    expect(onSelect).toHaveBeenCalledWith("table-120");
  });

  it("selects the full filtered table set even when only a virtual window is rendered", () => {
    const onToggleVisibleSelection = vi.fn();
    const profiles = Array.from({ length: 300 }, (_, index) => tableProfile(index));

    render(
      <ProfileTable
        profiles={profiles}
        healthByProfileId={{}}
        onSelect={vi.fn()}
        selectedProfileIds={new Set()}
        onToggleVisibleSelection={onToggleVisibleSelection}
      />,
    );

    fireEvent.click(screen.getByLabelText("Select all visible profiles"));

    expect(onToggleVisibleSelection).toHaveBeenCalledWith(
      profiles.map((item) => item.id),
      true,
    );
  });

  it("virtualizes narrow profile cards while keeping full-set selection usable", () => {
    setViewportWidth(390);
    const onSelect = vi.fn();
    const onToggleVisibleSelection = vi.fn();
    const profiles = Array.from({ length: 300 }, (_, index) => tableProfile(index));

    render(
      <ProfileTable
        profiles={profiles}
        healthByProfileId={{}}
        onSelect={onSelect}
        selectedProfileIds={new Set()}
        onToggleVisibleSelection={onToggleVisibleSelection}
      />,
    );

    expect(screen.getByRole("list", { name: "Profile cards" })).toBeTruthy();
    expect(screen.getByText("Table Profile 000")).toBeTruthy();
    expect(screen.queryByText("Table Profile 120")).toBeNull();

    fireEvent.click(screen.getByLabelText("Select all visible profiles"));
    expect(onToggleVisibleSelection).toHaveBeenCalledWith(
      profiles.map((item) => item.id),
      true,
    );

    const region = screen.getByRole("region", { name: "Profile operations table" });
    fireEvent.scroll(region, { target: { scrollTop: 188 * 120 } });

    expect(screen.queryByText("Table Profile 000")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Open Table Profile 120" }));
    expect(onSelect).toHaveBeenCalledWith("table-120");
  });

  it("keeps row selection controlled after a virtualized row leaves and re-enters the DOM", () => {
    const profiles = Array.from({ length: 300 }, (_, index) => tableProfile(index));

    render(
      <ProfileTable
        profiles={profiles}
        healthByProfileId={{}}
        onSelect={vi.fn()}
        selectedProfileIds={new Set(["table-0"])}
        onToggleProfileSelection={vi.fn()}
      />,
    );

    const table = screen.getByRole("region", { name: "Profile operations table" });
    expect((screen.getByLabelText("Select Table Profile 000") as HTMLInputElement).checked).toBe(true);

    fireEvent.scroll(table, { target: { scrollTop: 64 * 120 } });
    expect(screen.queryByLabelText("Select Table Profile 000")).toBeNull();

    fireEvent.scroll(table, { target: { scrollTop: 0 } });
    expect((screen.getByLabelText("Select Table Profile 000") as HTMLInputElement).checked).toBe(true);
  });

  it("resets a large virtualized table to the empty state without stale rows", () => {
    const profiles = Array.from({ length: 300 }, (_, index) => tableProfile(index));
    const { rerender } = render(
      <ProfileTable
        profiles={profiles}
        healthByProfileId={{}}
        onSelect={vi.fn()}
      />,
    );

    const table = screen.getByRole("region", { name: "Profile operations table" });
    fireEvent.scroll(table, { target: { scrollTop: 64 * 120 } });
    expect(screen.getByText("Table Profile 120")).toBeTruthy();

    rerender(
      <ProfileTable
        profiles={[]}
        healthByProfileId={{}}
        onSelect={vi.fn()}
        selectedProfileIds={new Set()}
        onToggleProfileSelection={vi.fn()}
        onToggleVisibleSelection={vi.fn()}
      />,
    );

    expect(screen.getByRole("status", { name: "No profiles match these filters" })).toBeTruthy();
    expect(screen.queryByText("Table Profile 120")).toBeNull();
    expect((screen.getByLabelText("Select all visible profiles") as HTMLInputElement).disabled).toBe(true);
  });
});
