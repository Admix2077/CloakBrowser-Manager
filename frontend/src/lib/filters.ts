import type { HealthStatus, Profile, ProfileHealthResponse } from "./api";
import { publicProfileName } from "./errorDisplay";

export type RuntimeStatusFilter = "all" | Profile["status"];
export type HealthStatusFilter = "all" | HealthStatus;
export type ProxyFilter = "all" | "with_proxy" | "without_proxy";
export type ProfileSortKey = "name" | "status" | "health" | "country" | "last_checked";

export interface ProfileFilterState {
  search: string;
  status: RuntimeStatusFilter;
  health: HealthStatusFilter;
  proxy: ProxyFilter;
  country: string;
  tag: string;
  sortBy: ProfileSortKey;
}

export interface ProfileFilterOptions {
  countries: string[];
  tags: string[];
}

export const defaultProfileFilters: ProfileFilterState = {
  search: "",
  status: "all",
  health: "all",
  proxy: "all",
  country: "all",
  tag: "all",
  sortBy: "health",
};

const HEALTH_RISK_RANK: Record<HealthStatus, number> = {
  error: 0,
  warning: 1,
  unknown: 2,
  good: 3,
};

function profileHealth(
  profile: Profile,
  healthByProfileId: Record<string, ProfileHealthResponse | undefined>,
): ProfileHealthResponse | undefined {
  return healthByProfileId[profile.id];
}

function healthStatus(
  profile: Profile,
  healthByProfileId: Record<string, ProfileHealthResponse | undefined>,
): HealthStatus {
  return profileHealth(profile, healthByProfileId)?.status ?? "unknown";
}

function countryCode(
  profile: Profile,
  healthByProfileId: Record<string, ProfileHealthResponse | undefined>,
): string | null {
  return profileHealth(profile, healthByProfileId)?.geoip?.country_code
    ?? profile.last_geoip_country_code
    ?? null;
}

function lastCheckedAt(
  profile: Profile,
  healthByProfileId: Record<string, ProfileHealthResponse | undefined>,
): string | null {
  return profileHealth(profile, healthByProfileId)?.checked_at
    ?? profile.last_geoip_resolved_at
    ?? null;
}

function compareNullableText(a: string | null, b: string | null): number {
  if (a && b) return a.localeCompare(b);
  if (a) return -1;
  if (b) return 1;
  return 0;
}

function compareNullableDateDesc(a: string | null, b: string | null): number {
  if (a && b) return b.localeCompare(a);
  if (a) return -1;
  if (b) return 1;
  return 0;
}

function compareProfileNames(a: Profile, b: Profile): number {
  return publicProfileName(a.name).localeCompare(publicProfileName(b.name)) || a.id.localeCompare(b.id);
}

export function filterAndSortProfiles(
  profiles: Profile[],
  healthByProfileId: Record<string, ProfileHealthResponse | undefined>,
  filters: ProfileFilterState,
): Profile[] {
  const search = filters.search.trim().toLowerCase();
  const filtered = profiles.filter((profile) => {
    if (search && !publicProfileName(profile.name).toLowerCase().includes(search)) return false;
    if (filters.status !== "all" && profile.status !== filters.status) return false;
    if (filters.health !== "all" && healthStatus(profile, healthByProfileId) !== filters.health) return false;
    if (filters.proxy === "with_proxy" && !profile.proxy) return false;
    if (filters.proxy === "without_proxy" && profile.proxy) return false;
    if (filters.country !== "all" && countryCode(profile, healthByProfileId) !== filters.country) return false;
    if (filters.tag !== "all" && !profile.tags.some((tag) => tag.tag === filters.tag)) return false;
    return true;
  });

  return [...filtered].sort((a, b) => {
    switch (filters.sortBy) {
      case "status":
        return a.status.localeCompare(b.status) || compareProfileNames(a, b);
      case "health":
        return HEALTH_RISK_RANK[healthStatus(a, healthByProfileId)]
          - HEALTH_RISK_RANK[healthStatus(b, healthByProfileId)]
          || compareProfileNames(a, b);
      case "country":
        return compareNullableText(
          countryCode(a, healthByProfileId),
          countryCode(b, healthByProfileId),
        ) || compareProfileNames(a, b);
      case "last_checked":
        return compareNullableDateDesc(
          lastCheckedAt(a, healthByProfileId),
          lastCheckedAt(b, healthByProfileId),
        ) || compareProfileNames(a, b);
      case "name":
      default:
        return compareProfileNames(a, b);
    }
  });
}

export function getProfileFilterOptions(
  profiles: Profile[],
  healthByProfileId: Record<string, ProfileHealthResponse | undefined>,
): ProfileFilterOptions {
  const countries = new Set<string>();
  const tags = new Set<string>();

  profiles.forEach((profile) => {
    const country = countryCode(profile, healthByProfileId);
    if (country) countries.add(country);
    profile.tags.forEach((tag) => tags.add(tag.tag));
  });

  return {
    countries: [...countries].sort(),
    tags: [...tags].sort(),
  };
}
