import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
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

describe("ProfileTable", () => {
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
    expect(screen.getByText("US")).toBeTruthy();
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
    expect((screen.getByLabelText("Select Good US") as HTMLInputElement).checked).toBe(true);
    expect((screen.getByLabelText("Select Broken Proxy") as HTMLInputElement).checked).toBe(false);

    fireEvent.click(screen.getByLabelText("Select Broken Proxy"));
    expect(onToggleProfileSelection).toHaveBeenCalledWith("error");

    fireEvent.click(screen.getByLabelText("Select all visible profiles"));
    expect(onToggleVisibleSelection).toHaveBeenCalledWith(["good", "error"], true);
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

    expect(screen.getByRole("button", { name: "Preview Good US" }).closest("tr")?.getAttribute("data-state")).toBe("selected");
    expect(screen.getByRole("button", { name: "Preview Broken Proxy" }).closest("tr")?.getAttribute("data-state")).toBe("previewed");
    expect(screen.getByRole("button", { name: "Open Good US" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Open Broken Proxy" })).toBeTruthy();
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
    const onLaunchSelected = vi.fn();
    const onStopSelected = vi.fn();

    render(
      <ProfileTable
        profiles={profiles}
        healthByProfileId={healthByProfileId}
        onSelect={vi.fn()}
        selectedProfileIds={new Set(["good", "error"])}
        onClearSelection={vi.fn()}
        onCheckSelectedHealth={onCheckHealth}
        onLaunchSelectedProfiles={onLaunchSelected}
        onStopSelectedProfiles={onStopSelected}
      />,
    );

    expect(screen.getByRole("toolbar", { name: "Bulk profile actions" }).getAttribute("aria-busy")).toBe("false");
    expect(screen.getByText("2 selected")).toBeTruthy();
    expect(screen.getByText("1 running")).toBeTruthy();
    expect(screen.getByText("1 stopped")).toBeTruthy();
    expect(screen.getByText("1 issue")).toBeTruthy();
    expect((screen.getByRole("button", { name: "Check health" }) as HTMLButtonElement).disabled).toBe(false);
    expect(screen.getByRole("button", { name: "Check health" }).textContent).toContain("Check health");
    fireEvent.click(screen.getByRole("button", { name: "Check health" }));
    expect(onCheckHealth).toHaveBeenCalledTimes(1);
    expect((screen.getByRole("button", { name: "Launch selected" }) as HTMLButtonElement).disabled).toBe(false);
    fireEvent.click(screen.getByRole("button", { name: "Launch selected" }));
    expect(onLaunchSelected).toHaveBeenCalledWith(["error"]);
    expect((screen.getByRole("button", { name: "Stop selected" }) as HTMLButtonElement).disabled).toBe(false);
    fireEvent.click(screen.getByRole("button", { name: "Stop selected" }));
    expect(onStopSelected).toHaveBeenCalledWith(["good"]);
    expect((screen.getByRole("button", { name: "Tag selected" }) as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByRole("button", { name: "Delete selected" }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("requires typed confirmation before deleting selected stopped profiles", () => {
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

    expect(screen.getByText("Delete 1 stopped profile?")).toBeTruthy();
    expect(screen.getByText("1 running profile will be skipped. Stop it first if it also needs deletion.")).toBeTruthy();
    expect(screen.getByText("Browser data will be permanently removed.")).toBeTruthy();
    expect((screen.getByRole("button", { name: "Confirm bulk delete" }) as HTMLButtonElement).disabled).toBe(true);

    fireEvent.change(screen.getByLabelText("Type DELETE to confirm bulk deletion"), { target: { value: "delete" } });
    expect((screen.getByRole("button", { name: "Confirm bulk delete" }) as HTMLButtonElement).disabled).toBe(true);

    fireEvent.change(screen.getByLabelText("Type DELETE to confirm bulk deletion"), { target: { value: "DELETE" } });
    fireEvent.click(screen.getByRole("button", { name: "Confirm bulk delete" }));

    expect(onDeleteSelected).toHaveBeenCalledWith(["error"]);
  });

  it("cancels bulk delete confirmation without deleting profiles", () => {
    const onDeleteSelected = vi.fn();

    render(
      <ProfileTable
        profiles={profiles}
        healthByProfileId={healthByProfileId}
        onSelect={vi.fn()}
        selectedProfileIds={new Set(["error"])}
        onDeleteSelectedProfiles={onDeleteSelected}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Delete selected" }));
    fireEvent.click(screen.getByRole("button", { name: "Cancel bulk delete" }));

    expect(onDeleteSelected).not.toHaveBeenCalled();
    expect(screen.queryByText("Browser data will be permanently removed.")).toBeNull();
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
    expect(screen.getByRole("button", { name: "Delete selected" }).getAttribute("title")).toBe("Stop running profiles before bulk deletion");
  });

  it("opens a bulk tag form and submits a new tag for selected profiles", () => {
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

    expect((screen.getByRole("button", { name: "Tag selected" }) as HTMLButtonElement).disabled).toBe(false);
    fireEvent.click(screen.getByRole("button", { name: "Tag selected" }));
    expect(document.activeElement).toBe(screen.getByLabelText("Bulk tag name"));
    fireEvent.change(screen.getByLabelText("Bulk tag name"), { target: { value: "ops" } });
    fireEvent.click(screen.getByRole("button", { name: "Apply tag" }));

    expect(onTagSelected).toHaveBeenCalledWith(
      ["good", "error"],
      [{ tag: "ops", color: "#6366f1" }],
    );
    expect((screen.getByRole("button", { name: "Delete selected" }) as HTMLButtonElement).disabled).toBe(false);
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
    expect((screen.getByRole("button", { name: "Checking health" }) as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByText("Checking...")).toBeTruthy();
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

  it("renders a filtered-empty state without hiding table controls", () => {
    render(
      <ProfileTable
        profiles={[]}
        healthByProfileId={{}}
        onSelect={vi.fn()}
        selectedProfileIds={new Set()}
        onToggleProfileSelection={vi.fn()}
        onToggleVisibleSelection={vi.fn()}
      />,
    );

    expect(screen.getByText("No profiles in this view")).toBeTruthy();
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

    expect(screen.getByText("No profiles in this view")).toBeTruthy();
    expect(screen.queryByText("Table Profile 120")).toBeNull();
    expect((screen.getByLabelText("Select all visible profiles") as HTMLInputElement).disabled).toBe(true);
  });
});
