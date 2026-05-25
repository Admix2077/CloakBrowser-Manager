import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ProfileList } from "./ProfileList";
import type { Profile } from "../lib/api";

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
  cdp_url: null,
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
