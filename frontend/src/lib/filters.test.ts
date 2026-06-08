import { describe, expect, it } from "vitest";
import type { Profile, ProfileHealthResponse } from "./api";
import { filterAndSortProfiles, getProfileFilterOptions } from "./filters";

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
    id: "alpha",
    name: "Alpha US",
    proxy: "http://proxy.example:8080",
    status: "running",
    tags: [{ tag: "client-a", color: null }],
    last_geoip_country_code: "US",
    last_geoip_resolved_at: "2026-05-25T01:00:00Z",
  }),
  profile({
    id: "beta",
    name: "Beta JP",
    status: "stopped",
    tags: [{ tag: "client-b", color: null }],
    last_geoip_country_code: "JP",
    last_geoip_resolved_at: "2026-05-25T02:00:00Z",
  }),
  profile({
    id: "gamma",
    name: "Gamma DE",
    proxy: "http://proxy2.example:8080",
    status: "stopped",
    tags: [{ tag: "client-a", color: null }],
    last_geoip_country_code: "DE",
    last_geoip_resolved_at: null,
  }),
];

const healthByProfileId = {
  alpha: health("alpha", { status: "good", checked_at: "2026-05-25T01:00:00Z" }),
  beta: health("beta", { status: "warning", checked_at: "2026-05-25T02:00:00Z" }),
  gamma: health("gamma", { status: "error" }),
};

describe("filterAndSortProfiles", () => {
  it("filters by search, status, health, proxy, country, and tag", () => {
    const result = filterAndSortProfiles(profiles, healthByProfileId, {
      search: "gamma",
      status: "stopped",
      health: "error",
      proxy: "with_proxy",
      country: "DE",
      tag: "client-a",
      sortBy: "name",
    });

    expect(result.map((item) => item.id)).toEqual(["gamma"]);
  });

  it("uses public profile names for search matching", () => {
    const leakMarker = "filter-profile-name-secret";
    const polluted = profile({
      id: "polluted",
      name:
        "Alpha Authorization=Bearer " +
        `${leakMarker} token=${leakMarker} /data/filter-profile-name 203.0.113.92`,
    });

    const rawMatch = filterAndSortProfiles([polluted], {}, {
      search: leakMarker,
      status: "all",
      health: "all",
      proxy: "all",
      country: "all",
      tag: "all",
      sortBy: "name",
    });
    expect(rawMatch).toEqual([]);

    const publicMatch = filterAndSortProfiles([polluted], {}, {
      search: "alpha",
      status: "all",
      health: "all",
      proxy: "all",
      country: "all",
      tag: "all",
      sortBy: "name",
    });
    expect(publicMatch.map((item) => item.id)).toEqual(["polluted"]);
  });

  it("treats sensitive search evidence as a no-match filter", () => {
    const polluted = profile({
      id: "polluted-search",
      name: "Unknown Alpha",
    });

    const result = filterAndSortProfiles([polluted], {}, {
      search: "viewer_token=secret /data/profile-search 203.0.113.78",
      status: "all",
      health: "all",
      proxy: "all",
      country: "all",
      tag: "all",
      sortBy: "name",
    });

    expect(result).toEqual([]);
  });

  it("sorts health by risk first for operations triage", () => {
    const result = filterAndSortProfiles(profiles, healthByProfileId, {
      search: "",
      status: "all",
      health: "all",
      proxy: "all",
      country: "all",
      tag: "all",
      sortBy: "health",
    });

    expect(result.map((item) => item.id)).toEqual(["gamma", "beta", "alpha"]);
  });

  it("sorts last checked profiles with newest health data first", () => {
    const result = filterAndSortProfiles(profiles, healthByProfileId, {
      search: "",
      status: "all",
      health: "all",
      proxy: "all",
      country: "all",
      tag: "all",
      sortBy: "last_checked",
    });

    expect(result.map((item) => item.id)).toEqual(["beta", "alpha", "gamma"]);
  });
});

describe("getProfileFilterOptions", () => {
  it("returns countries and tags from profile data", () => {
    const options = getProfileFilterOptions(profiles, healthByProfileId);

    expect(options.countries).toEqual(["DE", "JP", "US"]);
    expect(options.tags).toEqual(["client-a", "client-b"]);
  });

  it("redacts polluted geoip country options while keeping country filters usable", () => {
    const leakMarker = "filter-country-secret";
    const polluted = profile({
      id: "polluted-country",
      name: "Polluted country",
    });
    const pollutedHealth = health("polluted-country", {
      geoip: {
        ip: "203.0.113.120",
        country_code:
          "JP Authorization=Bearer " +
          `${leakMarker} token=${leakMarker} /data/filter-country 203.0.113.121`,
        timezone: "Asia/Tokyo",
        locale: "ja-JP",
        source: "qa",
        resolved_at: "2026-05-25T00:00:00Z",
      },
    });
    const safeCountry = "JP [redacted] [redacted] [redacted-path] [redacted-ip]";

    const options = getProfileFilterOptions([polluted], {
      "polluted-country": pollutedHealth,
    });

    expect(options.countries).toEqual([safeCountry]);
    expect(options.countries.join(" ")).not.toContain(leakMarker);
    expect(options.countries.join(" ")).not.toContain("/data/filter-country");

    const result = filterAndSortProfiles([polluted], { "polluted-country": pollutedHealth }, {
      search: "",
      status: "all",
      health: "all",
      proxy: "all",
      country: safeCountry,
      tag: "all",
      sortBy: "name",
    });
    expect(result.map((item) => item.id)).toEqual(["polluted-country"]);
  });

  it("redacts polluted tag options while keeping tag filters usable", () => {
    const leakMarker = "filter-tag-secret";
    const polluted = profile({
      id: "polluted-tag",
      name: "Polluted tag",
      tags: [{
        tag:
          "client-a Authorization=Bearer " +
          `${leakMarker} token=${leakMarker} /data/filter-tag 203.0.113.122`,
        color: null,
      }],
    });
    const safeTag = "client-a [redacted] [redacted] [redacted-path] [redacted-ip]";

    const options = getProfileFilterOptions([polluted], {});

    expect(options.tags).toEqual([safeTag]);
    expect(options.tags.join(" ")).not.toContain(leakMarker);
    expect(options.tags.join(" ")).not.toContain("/data/filter-tag");

    const result = filterAndSortProfiles([polluted], {}, {
      search: "",
      status: "all",
      health: "all",
      proxy: "all",
      country: "all",
      tag: safeTag,
      sortBy: "name",
    });
    expect(result.map((item) => item.id)).toEqual(["polluted-tag"]);
  });
});
