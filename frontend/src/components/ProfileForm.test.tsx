import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ProfileForm } from "./ProfileForm";
import type { Profile } from "../lib/api";

const humanizedProfile: Profile = {
  id: "profile-1",
  name: "Humanized",
  fingerprint_seed: 12345,
  proxy: null,
  timezone: null,
  locale: null,
  platform: "macos",
  user_agent: "custom",
  screen_width: 1920,
  screen_height: 1080,
  gpu_vendor: null,
  gpu_renderer: null,
  hardware_concurrency: null,
  humanize: true,
  human_preset: "careful",
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
  cdp_url: null,
};

describe("ProfileForm launch arguments", () => {
  it("describes launch args as invisible_playwright Firefox arguments", () => {
    render(
      <ProfileForm
        profile={null}
        onSave={vi.fn()}
        onCancel={vi.fn()}
      />,
    );

    expect(screen.getByText("Firefox Launch Args")).toBeTruthy();
    expect(screen.getByText(/Custom Firefox arguments passed to invisible_playwright/)).toBeTruthy();
    expect(screen.getByText(/Chromium\/CDP\/profile flags are ignored/)).toBeTruthy();
    expect(screen.getByPlaceholderText("--private-window")).toBeTruthy();
  });
});

describe("ProfileForm invisible_playwright phase-one fields", () => {
  it("does not expose unsupported identity controls as editable settings", () => {
    render(
      <ProfileForm
        profile={null}
        onSave={vi.fn()}
        onCancel={vi.fn()}
      />,
    );

    expect(screen.queryByLabelText("Platform")).toBeNull();
    expect(screen.queryByText(/Auto-detect timezone\/locale from proxy IP/)).toBeNull();
    expect(screen.queryByLabelText("User Agent")).toBeNull();
  });

  it("does not expose the ignored human preset even when a stored profile has one", () => {
    render(
      <ProfileForm
        profile={humanizedProfile}
        onSave={vi.fn()}
        onCancel={vi.fn()}
      />,
    );

    expect(screen.getByText("Human-like mouse, keyboard, and scroll behavior")).toBeTruthy();
    expect(screen.queryByLabelText("Human Preset")).toBeNull();
  });
});
