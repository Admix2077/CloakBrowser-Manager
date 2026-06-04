import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ProfileSummaryPanel } from "./ProfileSummaryPanel";
import type { Profile, ProfileHealthResponse } from "../lib/api";

function profile(overrides: Partial<Profile>): Profile {
  return {
    id: "profile-1",
    name: "Seller US",
    fingerprint_seed: 12345,
    proxy: "http://user:hiddenpass@proxy.example:8080",
    timezone: "Europe/Berlin",
    locale: null,
    platform: "windows",
    user_agent: null,
    screen_width: 1920,
    screen_height: 1080,
    gpu_vendor: "Google Inc. (NVIDIA)",
    gpu_renderer: "ANGLE NVIDIA",
    hardware_concurrency: 8,
    humanize: false,
    human_preset: "default",
    headless: false,
    geoip: true,
    last_geoip_ip: "23.144.4.92",
    last_geoip_country_code: "US",
    last_geoip_timezone: "America/Los_Angeles",
    last_geoip_locale: "en-US",
    last_geoip_source: "qa",
    last_geoip_resolved_at: "2026-05-25T00:00:00Z",
    clipboard_sync: true,
    auto_launch: false,
    color_scheme: "light",
    launch_args: [],
    notes: "Warm account",
    user_data_dir: "/data/profiles/profile-1",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    tags: [{ tag: "ready", color: "#22c55e" }],
    status: "stopped",
    vnc_ws_port: null,
    automation_url: null,
    ...overrides,
  };
}

function health(overrides: Partial<ProfileHealthResponse>): ProfileHealthResponse {
  return {
    profile_id: "profile-1",
    status: "error",
    geoip: {
      ip: "23.144.4.92",
      country_code: "US",
      timezone: "America/Los_Angeles",
      locale: "en-US",
      source: "qa",
      resolved_at: "2026-05-25T00:00:00Z",
    },
    manual_overrides: { timezone: true, locale: false },
    runtime: { status: "stopped", vnc_ws_port: null, automation_url: null },
    warnings: [{
      code: "proxy_invalid",
      message: "Proxy URL missing port: http://user:hiddenpass@proxy.example",
      severity: "error",
      action: "修正 proxy 格式后重新检测。",
    }],
    checked_at: "2026-05-25T01:00:00Z",
    ...overrides,
  };
}

describe("ProfileSummaryPanel", () => {
  it("renders a quiet empty inspector state when no profile is previewed", () => {
    render(
      <ProfileSummaryPanel
        profile={null}
        onOpenProfile={vi.fn()}
      />,
    );

    const summary = screen.getByRole("complementary", { name: "Profile summary" });
    expect(within(summary).getByText("Inspector")).toBeTruthy();
    expect(within(summary).getByText("No profile selected")).toBeTruthy();
    expect(within(summary).getByText("Preview a row to inspect runtime, health, proxy, and fingerprint context.")).toBeTruthy();
  });

  it("summarizes health, runtime, geoip, overrides, proxy, and device without exposing proxy credentials", () => {
    const onOpen = vi.fn();

    render(
      <ProfileSummaryPanel
        profile={profile({})}
        health={health({})}
        onOpenProfile={onOpen}
      />,
    );

    expect(screen.getByRole("complementary", { name: "Profile summary" })).toBeTruthy();
    const summary = screen.getByRole("complementary", { name: "Profile summary" });
    expect(within(summary).getByTestId("inspector-profile-content").className).toContain("animate-inspector-in");
    expect(within(summary).getByRole("region", { name: "Health" })).toBeTruthy();
    expect(within(summary).getByRole("region", { name: "Runtime" })).toBeTruthy();
    expect(within(summary).getByRole("region", { name: "GeoIP" })).toBeTruthy();
    expect(within(summary).getByRole("region", { name: "Proxy" })).toBeTruthy();
    expect(within(summary).getByRole("region", { name: "Device" })).toBeTruthy();
    expect(within(summary).getByRole("region", { name: "Health" }).getAttribute("data-priority")).toBe("primary");
    expect(within(summary).getByRole("region", { name: "Runtime" }).getAttribute("data-priority")).toBe("primary");
    expect(within(summary).getByRole("region", { name: "GeoIP" }).getAttribute("data-priority")).toBe("secondary");
    expect(screen.getByText("Seller US")).toBeTruthy();
    expect(screen.getByText("Inspector")).toBeTruthy();
    expect(screen.getAllByText("不可用").length).toBeGreaterThan(0);
    expect(screen.getByText("Proxy URL missing port: http://proxy.example")).toBeTruthy();
    expect(
      within(within(summary).getByRole("region", { name: "Runtime" }))
        .getByText("stopped")
        .closest("[data-badge-type]")
        ?.getAttribute("data-badge-type"),
    ).toBe("runtime");
    expect(screen.getByText("23.144.4.92")).toBeTruthy();
    expect(screen.getByText("US")).toBeTruthy();
    expect(screen.getByText("America/Los_Angeles")).toBeTruthy();
    expect(screen.getByText("en-US")).toBeTruthy();
    expect(screen.getByText("Timezone override")).toBeTruthy();
    expect(screen.getByText("Timezone override").getAttribute("data-badge-type")).toBe("tag");
    expect(screen.getByText("Locale override").getAttribute("data-badge-type")).toBe("tag");
    expect(screen.getByText("http://proxy.example:8080")).toBeTruthy();
    expect(screen.getByText("1920 x 1080")).toBeTruthy();
    expect(screen.getByText("8 cores")).toBeTruthy();
    expect(document.body.innerHTML).not.toContain("hiddenpass");
    expect(document.body.innerHTML).not.toContain("user:");

    fireEvent.click(screen.getByRole("button", { name: "Open Seller US" }));
    expect(onOpen).toHaveBeenCalledWith("profile-1");
  });

  it("folds non-public runtime statuses before rendering summary evidence", () => {
    const leakMarker = "summary-status-secret";
    const pollutedStatus = `stopped Authorization=Bearer ${leakMarker} token=${leakMarker}`;

    render(
      <ProfileSummaryPanel
        profile={profile({ status: pollutedStatus as Profile["status"] })}
        health={health({})}
        onOpenProfile={vi.fn()}
      />,
    );

    const runtime = within(screen.getByRole("complementary", { name: "Profile summary" }))
      .getByRole("region", { name: "Runtime" });
    expect(within(runtime).getByText("unknown")).toBeTruthy();
    expect(screen.getByLabelText("Runtime unknown")).toBeTruthy();
    expect(document.body.textContent).not.toContain("Authorization");
    expect(document.body.textContent).not.toContain("Bearer");
    expect(document.body.textContent).not.toContain("token=");
    expect(document.body.innerHTML).not.toContain(leakMarker);
  });

  it("folds non-public VNC ports before rendering summary evidence", () => {
    const leakMarker = "summary-vnc-port-secret";
    const pollutedPort =
      "6100 Authorization=Bearer " +
      `${leakMarker} token=${leakMarker} /data/summary-vnc-port 203.0.113.118`;

    render(
      <ProfileSummaryPanel
        profile={profile({
          vnc_ws_port: pollutedPort as unknown as number,
          automation_url: "/api/profiles/profile-1/automation",
        })}
        health={health({})}
        onOpenProfile={vi.fn()}
      />,
    );

    const runtime = within(screen.getByRole("complementary", { name: "Profile summary" }))
      .getByRole("region", { name: "Runtime" });
    expect(within(runtime).getByText("-")).toBeTruthy();
    expect(within(runtime).getByText("available")).toBeTruthy();

    const renderedEvidence = [
      document.body.textContent,
      ...Array.from(document.querySelectorAll("[title]")).map((element) => element.getAttribute("title") ?? ""),
    ].join(" ");

    for (const leaked of [
      leakMarker,
      "Authorization",
      "Bearer",
      "token=",
      "/data/summary-vnc-port",
      "203.0.113.118",
    ]) {
      expect(renderedEvidence).not.toContain(leaked);
    }
  });

  it("redacts persisted profile names from summary rendered evidence", () => {
    const leakMarker = "summary-profile-name-secret";
    const rawName =
      "Seller Authorization=Bearer " +
      `${leakMarker} token=${leakMarker} /data/summary-profile-name 203.0.113.90`;
    const safeName = "Seller [redacted] [redacted] [redacted-path] [redacted-ip]";

    render(
      <ProfileSummaryPanel
        profile={profile({ name: rawName })}
        health={health({})}
        onOpenProfile={vi.fn()}
      />,
    );

    expect(screen.getByText(safeName)).toBeTruthy();
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
      "/data/summary-profile-name",
      "203.0.113.90",
    ]) {
      expect(renderedEvidence).not.toContain(leaked);
    }
  });

  it("redacts non-public profile ids from summary rendered evidence", () => {
    const leakMarker = "summary-profile-id-secret";
    const rawProfileId =
      "profile-id Authorization=Bearer " +
      `${leakMarker} token=${leakMarker} /data/summary-profile-id 203.0.113.120`;

    render(
      <ProfileSummaryPanel
        profile={profile({ id: rawProfileId, name: "Polluted Id Summary" })}
        health={health({})}
        onOpenProfile={vi.fn()}
      />,
    );

    expect(screen.getByText("unknown")).toBeTruthy();
    expect(screen.getByText("Polluted Id Summary")).toBeTruthy();

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
      "/data/summary-profile-id",
      "203.0.113.120",
    ]) {
      expect(renderedEvidence).not.toContain(leaked);
    }
  });

  it("redacts persisted geoip labels from summary rendered evidence", () => {
    const leakMarker = "summary-geoip-secret";
    const pollutedHealth = health({
      geoip: {
        ip:
          "23.144.4.92 Authorization=Bearer " +
          `${leakMarker} token=${leakMarker} /data/summary-geoip-ip 203.0.113.105`,
        country_code:
          "US Authorization=Bearer " +
          `${leakMarker} token=${leakMarker} /data/summary-geoip-country 203.0.113.106`,
        timezone:
          "America/Los_Angeles Authorization=Bearer " +
          `${leakMarker} token=${leakMarker} /data/summary-geoip-timezone 203.0.113.107`,
        locale:
          "en-US Authorization=Bearer " +
          `${leakMarker} token=${leakMarker} /data/summary-geoip-locale 203.0.113.108`,
        source: "qa",
        resolved_at: "2026-05-25T00:00:00Z",
      },
    });

    render(
      <ProfileSummaryPanel
        profile={profile({})}
        health={pollutedHealth}
        onOpenProfile={vi.fn()}
      />,
    );

    expect(screen.getByText("[redacted-ip] [redacted] [redacted] [redacted-path] [redacted-ip]")).toBeTruthy();
    expect(screen.getAllByText("unknown").length).toBeGreaterThan(0);
    expect(screen.getByText("America/Los_Angeles [redacted] [redacted] [redacted-path] [redacted-ip]")).toBeTruthy();
    expect(screen.getByText("en-US [redacted] [redacted] [redacted-path] [redacted-ip]")).toBeTruthy();

    const renderedEvidence = [
      document.body.textContent,
      ...Array.from(document.querySelectorAll("[title]")).map((element) => element.getAttribute("title") ?? ""),
    ].join(" ");

    for (const leaked of [
      leakMarker,
      "Authorization",
      "Bearer",
      "token=",
      "/data/summary-geoip-ip",
      "/data/summary-geoip-country",
      "/data/summary-geoip-timezone",
      "/data/summary-geoip-locale",
      "203.0.113.105",
      "203.0.113.106",
      "203.0.113.107",
      "203.0.113.108",
    ]) {
      expect(renderedEvidence).not.toContain(leaked);
    }
  });

  it("redacts persisted device labels from summary rendered evidence", () => {
    const leakMarker = "summary-device-secret";
    const pollutedProfile = profile({
      platform:
        "windows Authorization=Bearer " +
        `${leakMarker} token=${leakMarker} /data/summary-device-platform 203.0.113.113`,
      screen_width:
        ("1920 Authorization=Bearer " +
          `${leakMarker} token=${leakMarker} /data/summary-device-screen-width 203.0.113.114`) as unknown as number,
      screen_height:
        ("1080 Authorization=Bearer " +
          `${leakMarker} token=${leakMarker} /data/summary-device-screen-height 203.0.113.115`) as unknown as number,
      hardware_concurrency:
        ("8 Authorization=Bearer " +
          `${leakMarker} token=${leakMarker} /data/summary-device-cores 203.0.113.116`) as unknown as number,
      gpu_renderer:
        "ANGLE NVIDIA Authorization=Bearer " +
        `${leakMarker} token=${leakMarker} /data/summary-device-gpu 203.0.113.117`,
    });

    render(
      <ProfileSummaryPanel
        profile={pollutedProfile}
        health={health({})}
        onOpenProfile={vi.fn()}
      />,
    );

    expect(screen.getByText("windows [redacted] [redacted] [redacted-path] [redacted-ip]")).toBeTruthy();
    expect(screen.getByText(
      "1920 [redacted] [redacted] [redacted-path] [redacted-ip] x 1080 [redacted] [redacted] [redacted-path] [redacted-ip]",
    )).toBeTruthy();
    expect(screen.getByText("8 [redacted] [redacted] [redacted-path] [redacted-ip] cores")).toBeTruthy();
    expect(screen.getByText("ANGLE NVIDIA [redacted] [redacted] [redacted-path] [redacted-ip]")).toBeTruthy();

    const renderedEvidence = [
      document.body.textContent,
      ...Array.from(document.querySelectorAll("[title]")).map((element) => element.getAttribute("title") ?? ""),
    ].join(" ");

    for (const leaked of [
      leakMarker,
      "Authorization",
      "Bearer",
      "token=",
      "/data/summary-device-platform",
      "/data/summary-device-screen-width",
      "/data/summary-device-screen-height",
      "/data/summary-device-cores",
      "/data/summary-device-gpu",
      "203.0.113.113",
      "203.0.113.114",
      "203.0.113.115",
      "203.0.113.116",
      "203.0.113.117",
    ]) {
      expect(renderedEvidence).not.toContain(leaked);
    }
  });
});
