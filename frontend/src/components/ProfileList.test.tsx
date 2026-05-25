import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ProfileList } from "./ProfileList";
import type { Profile, ProfileHealthResponse } from "../lib/api";

const profile: Profile = {
  id: "profile-1",
  name: "Stored Platform Profile",
  fingerprint_seed: 12345,
  proxy: "http://proxy.example:8080",
  timezone: null,
  locale: null,
  platform: "macos",
  user_agent: null,
  screen_width: 1920,
  screen_height: 1080,
  gpu_vendor: null,
  gpu_renderer: null,
  hardware_concurrency: null,
  humanize: false,
  human_preset: "default",
  headless: false,
  geoip: false,
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
};

const warningHealth: ProfileHealthResponse = {
  profile_id: "profile-1",
  status: "warning",
  geoip: {
    ip: "203.0.113.20",
    country_code: "JP",
    timezone: "Asia/Tokyo",
    locale: "ja-JP",
    source: "ipwho.is",
    resolved_at: "2026-05-25T00:00:00Z",
  },
  manual_overrides: { timezone: true, locale: false },
  runtime: { status: "stopped", vnc_ws_port: null, automation_url: null },
  warnings: [
    {
      code: "manual_timezone_mismatch",
      message: "手动 timezone 为 America/Los_Angeles，当前出口建议为 Asia/Tokyo。",
      severity: "warning",
      action: "确认是否需要保留手动覆盖。",
    },
  ],
  checked_at: "2026-05-25T01:00:00Z",
};

describe("ProfileList invisible_playwright identity display", () => {
  it("does not display stored platform as an active fingerprint label", () => {
    render(
      <ProfileList
        profiles={[profile]}
        selectedId={null}
        onSelect={vi.fn()}
        onNew={vi.fn()}
      />,
    );

    expect(screen.getByText("Stored Platform Profile")).toBeTruthy();
    expect(screen.getByText("Proxy")).toBeTruthy();
    expect(screen.queryByText("macos")).toBeNull();
  });
});

describe("ProfileList health display", () => {
  it("shows the health badge and warning summary on the profile row", () => {
    render(
      <ProfileList
        profiles={[profile]}
        selectedId={null}
        onSelect={vi.fn()}
        onNew={vi.fn()}
        healthByProfileId={{ "profile-1": warningHealth }}
      />,
    );

    expect(screen.getByText("需关注")).toBeTruthy();
    expect(screen.getByText("手动 timezone 为 America/Los_Angeles，当前出口建议为 Asia/Tokyo。")).toBeTruthy();
    expect(screen.getByText("203.0.113.20")).toBeTruthy();
    expect(screen.getByText("JP")).toBeTruthy();
  });

  it("does not include health labels in profile name search", () => {
    render(
      <ProfileList
        profiles={[profile]}
        selectedId={null}
        onSelect={vi.fn()}
        onNew={vi.fn()}
        healthByProfileId={{ "profile-1": warningHealth }}
      />,
    );

    fireEvent.change(screen.getByPlaceholderText("Search profiles..."), {
      target: { value: "需关注" },
    });

    expect(screen.getByText("No matches")).toBeTruthy();
    expect(screen.queryByText("Stored Platform Profile")).toBeNull();
  });
});
