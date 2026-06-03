import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ProfileList } from "./ProfileList";
import type { Profile, ProfileHealthResponse } from "../lib/api";
import { defaultProfileFilters } from "../lib/filters";

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

const runningProfile: Profile = {
  ...profile,
  id: "profile-running",
  name: "Running US Profile",
  status: "running",
  last_geoip_country_code: "US",
  tags: [{ tag: "client-a", color: null }],
};

const stoppedProfile: Profile = {
  ...profile,
  id: "profile-stopped",
  name: "Stopped JP Profile",
  proxy: null,
  status: "stopped",
  last_geoip_country_code: "JP",
  tags: [{ tag: "client-b", color: null }],
};

const errorHealth: ProfileHealthResponse = {
  ...warningHealth,
  profile_id: "profile-stopped",
  status: "error",
  geoip: {
    ...warningHealth.geoip!,
    country_code: "JP",
  },
  checked_at: "2026-05-25T02:00:00Z",
};

const runningWarningHealth: ProfileHealthResponse = {
  ...warningHealth,
  profile_id: "profile-running",
  geoip: {
    ...warningHealth.geoip!,
    ip: "23.144.4.92",
    country_code: "US",
    timezone: "America/Los_Angeles",
    locale: "en-US",
  },
};

function bulkProfile(index: number): Profile {
  const id = `bulk-${index.toString().padStart(3, "0")}`;
  return {
    ...profile,
    id,
    name: `Bulk Profile ${index.toString().padStart(3, "0")}`,
    proxy: null,
    tags: [],
    status: "stopped",
  };
}

describe("ProfileList phase-one identity display", () => {
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
    expect(screen.getByText("Proxy").getAttribute("data-badge-type")).toBe("proxy");
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

    expect(screen.getByLabelText("存在需关注项，建议检查后继续")).toBeTruthy();
    expect(screen.getByText("手动 timezone 为 America/Los_Angeles，当前出口建议为 Asia/Tokyo。")).toBeTruthy();
    expect(screen.getByText("203.0.113.20")).toBeTruthy();
    expect(screen.getAllByText("JP").some((node) => node.getAttribute("data-badge-type") === "country")).toBe(true);
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

  it("redacts persisted profile names from rail rendering and search evidence", () => {
    const leakMarker = "rail-profile-name-secret";
    const rawName =
      "Stored Authorization=Bearer " +
      `${leakMarker} token=${leakMarker} /data/rail-profile-name 203.0.113.91`;
    const safeName = "Stored [redacted] [redacted] [redacted-path] [redacted-ip]";

    render(
      <ProfileList
        profiles={[{ ...profile, name: rawName }]}
        selectedId={null}
        onSelect={vi.fn()}
        onNew={vi.fn()}
      />,
    );

    expect(screen.getByText(safeName)).toBeTruthy();

    fireEvent.change(screen.getByPlaceholderText("Search profiles..."), {
      target: { value: leakMarker },
    });
    expect(screen.getByText("No matches")).toBeTruthy();
    expect(screen.queryByText(safeName)).toBeNull();

    fireEvent.change(screen.getByPlaceholderText("Search profiles..."), {
      target: { value: "stored" },
    });
    expect(screen.getByText(safeName)).toBeTruthy();

    const renderedEvidence = document.body.textContent ?? "";
    for (const leaked of [
      leakMarker,
      "Authorization",
      "Bearer",
      "token=",
      "/data/rail-profile-name",
      "203.0.113.91",
    ]) {
      expect(renderedEvidence).not.toContain(leaked);
    }
  });
});

describe("ProfileList empty states", () => {
  it("renders a styled first-run empty state with a create action", () => {
    const onNew = vi.fn();

    render(
      <ProfileList
        profiles={[]}
        selectedId={null}
        onSelect={vi.fn()}
        onNew={onNew}
      />,
    );

    expect(screen.getByRole("status", { name: "No profiles yet" })).toBeTruthy();
    expect(screen.getByText("Create the first profile to start building shortcuts.")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Create profile" }));
    expect(onNew).toHaveBeenCalledTimes(1);
  });

  it("renders a styled filtered empty state with a clear filters action", () => {
    const onFiltersChange = vi.fn();

    render(
      <ProfileList
        profiles={[profile]}
        selectedId={null}
        onSelect={vi.fn()}
        onNew={vi.fn()}
        filters={{ ...defaultProfileFilters, search: "missing" }}
        onFiltersChange={onFiltersChange}
      />,
    );

    expect(screen.getByRole("status", { name: "No matching profile shortcuts" })).toBeTruthy();
    expect(screen.getByText("No matches")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Clear filters" }));
    expect(onFiltersChange).toHaveBeenCalledWith(defaultProfileFilters);
  });
});

describe("ProfileList operations filters", () => {
  it("filters profiles by runtime status, health, proxy, country, and tag", () => {
    render(
      <ProfileList
        profiles={[runningProfile, stoppedProfile]}
        selectedId={null}
        onSelect={vi.fn()}
        onNew={vi.fn()}
        healthByProfileId={{
          "profile-running": runningWarningHealth,
          "profile-stopped": errorHealth,
        }}
      />,
    );

    fireEvent.change(screen.getByLabelText("Runtime status"), {
      target: { value: "running" },
    });
    expect(screen.getByText("Running US Profile")).toBeTruthy();
    expect(screen.queryByText("Stopped JP Profile")).toBeNull();

    fireEvent.change(screen.getByLabelText("Runtime status"), {
      target: { value: "all" },
    });
    fireEvent.change(screen.getByLabelText("Health status"), {
      target: { value: "error" },
    });
    expect(screen.queryByText("Running US Profile")).toBeNull();
    expect(screen.getByText("Stopped JP Profile")).toBeTruthy();

    fireEvent.change(screen.getByLabelText("Health status"), {
      target: { value: "all" },
    });
    fireEvent.change(screen.getByLabelText("Proxy filter"), {
      target: { value: "with_proxy" },
    });
    expect(screen.getByText("Running US Profile")).toBeTruthy();
    expect(screen.queryByText("Stopped JP Profile")).toBeNull();

    fireEvent.change(screen.getByLabelText("Proxy filter"), {
      target: { value: "all" },
    });
    fireEvent.change(screen.getByLabelText("Country filter"), {
      target: { value: "JP" },
    });
    expect(screen.queryByText("Running US Profile")).toBeNull();
    expect(screen.getByText("Stopped JP Profile")).toBeTruthy();

    fireEvent.change(screen.getByLabelText("Country filter"), {
      target: { value: "all" },
    });
    fireEvent.change(screen.getByLabelText("Tag filter"), {
      target: { value: "client-a" },
    });
    expect(screen.getByText("Running US Profile")).toBeTruthy();
    expect(screen.queryByText("Stopped JP Profile")).toBeNull();
  });

  it("sorts visible profiles by health risk and last checked time", () => {
    render(
      <ProfileList
        profiles={[runningProfile, stoppedProfile]}
        selectedId={null}
        onSelect={vi.fn()}
        onNew={vi.fn()}
        healthByProfileId={{
          "profile-running": runningWarningHealth,
          "profile-stopped": errorHealth,
        }}
      />,
    );

    let rows = screen.getAllByRole("button", { name: /Profile/ });
    expect(rows[0].textContent).toContain("Stopped JP Profile");
    expect(rows[1].textContent).toContain("Running US Profile");

    fireEvent.change(screen.getByLabelText("Sort profiles"), {
      target: { value: "last_checked" },
    });

    rows = screen.getAllByRole("button", { name: /Profile/ });
    expect(rows[0].textContent).toContain("Stopped JP Profile");
    expect(rows[1].textContent).toContain("Running US Profile");
  });

  it("keeps filtered profile selection and create action usable", () => {
    const onSelect = vi.fn();
    const onNew = vi.fn();

    render(
      <ProfileList
        profiles={[runningProfile, stoppedProfile]}
        selectedId={null}
        onSelect={onSelect}
        onNew={onNew}
        healthByProfileId={{
          "profile-running": runningWarningHealth,
          "profile-stopped": errorHealth,
        }}
      />,
    );

    fireEvent.change(screen.getByLabelText("Runtime status"), {
      target: { value: "running" },
    });
    fireEvent.click(screen.getByText("Running US Profile"));
    fireEvent.click(screen.getByText("New Profile"));

    expect(onSelect).toHaveBeenCalledWith("profile-running");
    expect(onNew).toHaveBeenCalled();
  });

  it("can be controlled by shared operations filters", () => {
    render(
      <ProfileList
        profiles={[runningProfile, stoppedProfile]}
        selectedId={null}
        onSelect={vi.fn()}
        onNew={vi.fn()}
        healthByProfileId={{
          "profile-running": runningWarningHealth,
          "profile-stopped": errorHealth,
        }}
        filters={{ ...defaultProfileFilters, status: "running" }}
        onFiltersChange={vi.fn()}
      />,
    );

    expect(screen.getByText("Running US Profile")).toBeTruthy();
    expect(screen.queryByText("Stopped JP Profile")).toBeNull();
  });

  it("adds non-layout motion feedback to active quick views and selected shortcuts", () => {
    render(
      <ProfileList
        profiles={[runningProfile, stoppedProfile]}
        selectedId="profile-running"
        onSelect={vi.fn()}
        onNew={vi.fn()}
        healthByProfileId={{
          "profile-running": runningWarningHealth,
          "profile-stopped": errorHealth,
        }}
        filters={{ ...defaultProfileFilters, status: "running" }}
        onFiltersChange={vi.fn()}
      />,
    );

    expect(screen.getByRole("button", { name: "Running profiles" }).className).toContain("transition-[background-color,border-color,color,box-shadow,transform]");
    expect(screen.getByRole("button", { name: "Running profiles" }).className).toContain("active:translate-y-px");
    expect(screen.getByRole("button", { name: /Running US Profile/ }).className).toContain("animate-profile-selection");
  });

  it("virtualizes large profile lists while keeping selection usable", () => {
    const onSelect = vi.fn();
    const profiles = Array.from({ length: 300 }, (_, index) => bulkProfile(index));

    render(
      <ProfileList
        profiles={profiles}
        selectedId={null}
        onSelect={onSelect}
        onNew={vi.fn()}
      />,
    );

    expect(screen.getByText("Bulk Profile 000")).toBeTruthy();
    expect(screen.queryByText("Bulk Profile 120")).toBeNull();

    const list = screen.getByRole("region", { name: "Profiles list" });
    fireEvent.scroll(list, { target: { scrollTop: 112 * 120 } });

    expect(screen.queryByText("Bulk Profile 000")).toBeNull();
    fireEvent.click(screen.getByText("Bulk Profile 120"));
    expect(onSelect).toHaveBeenCalledWith("bulk-120");
    expect(screen.getByText("New Profile")).toBeTruthy();
  });
});
