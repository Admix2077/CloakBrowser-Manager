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

    expect((screen.getByLabelText("Select Good US") as HTMLInputElement).checked).toBe(true);
    expect((screen.getByLabelText("Select Broken Proxy") as HTMLInputElement).checked).toBe(false);

    fireEvent.click(screen.getByLabelText("Select Broken Proxy"));
    expect(onToggleProfileSelection).toHaveBeenCalledWith("error");

    fireEvent.click(screen.getByLabelText("Select all visible profiles"));
    expect(onToggleVisibleSelection).toHaveBeenCalledWith(["good", "error"], true);
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
        healthByProfileId={{}}
        onSelect={vi.fn()}
      />,
    );

    expect(screen.getByText("http://proxy.example:8080")).toBeTruthy();
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
});
