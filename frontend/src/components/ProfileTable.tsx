import { ArrowRight } from "lucide-react";
import type { Profile, ProfileHealthResponse } from "../lib/api";
import { HealthBadge } from "./HealthBadge";
import { StatusIndicator } from "./StatusIndicator";

interface ProfileTableProps {
  profiles: Profile[];
  healthByProfileId: Record<string, ProfileHealthResponse | undefined>;
  onSelect: (id: string) => void;
}

export function ProfileTable({ profiles, healthByProfileId, onSelect }: ProfileTableProps) {
  return (
    <div className="h-full overflow-auto">
      <div className="min-w-[980px]">
        <table className="w-full border-separate border-spacing-0 text-left text-xs">
          <thead className="sticky top-0 z-10 bg-surface-0/95 backdrop-blur">
            <tr className="text-gray-500">
              <HeaderCell>Profile</HeaderCell>
              <HeaderCell>Runtime</HeaderCell>
              <HeaderCell>Health</HeaderCell>
              <HeaderCell>Proxy</HeaderCell>
              <HeaderCell>IP</HeaderCell>
              <HeaderCell>Country</HeaderCell>
              <HeaderCell>Timezone</HeaderCell>
              <HeaderCell>Locale</HeaderCell>
              <HeaderCell>Tags</HeaderCell>
              <HeaderCell>Last checked</HeaderCell>
              <HeaderCell>Actions</HeaderCell>
            </tr>
          </thead>
          <tbody>
            {profiles.length === 0 ? (
              <tr>
                <td colSpan={11} className="px-4 py-10 text-center text-gray-500">
                  No profiles in this view
                </td>
              </tr>
            ) : (
              profiles.map((profile) => (
                <ProfileTableRow
                  key={profile.id}
                  profile={profile}
                  health={healthByProfileId[profile.id]}
                  onSelect={onSelect}
                />
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function HeaderCell({ children }: { children: string }) {
  return (
    <th className="border-b border-border px-3 py-2 font-medium">
      {children}
    </th>
  );
}

interface ProfileTableRowProps {
  profile: Profile;
  health?: ProfileHealthResponse;
  onSelect: (id: string) => void;
}

function ProfileTableRow({ profile, health, onSelect }: ProfileTableRowProps) {
  const geoip = health?.geoip;
  const ip = geoip?.ip ?? profile.last_geoip_ip;
  const country = geoip?.country_code ?? profile.last_geoip_country_code;
  const timezone = geoip?.timezone ?? profile.last_geoip_timezone;
  const locale = geoip?.locale ?? profile.last_geoip_locale;
  const lastChecked = health?.checked_at ?? profile.last_geoip_resolved_at;
  const proxyLabel = formatProxyLabel(profile.proxy);

  return (
    <tr className="group border-b border-border hover:bg-surface-1">
      <td className="border-b border-border px-3 py-2">
        <div className="max-w-[180px] truncate text-sm font-medium text-gray-100" title={profile.name}>
          {profile.name}
        </div>
        <div className="mt-0.5 text-[11px] text-gray-600">{profile.id.slice(0, 8)}</div>
      </td>
      <td className="border-b border-border px-3 py-2">
        <span className="inline-flex items-center gap-1.5 text-gray-300">
          <StatusIndicator status={profile.status} />
          <span>{profile.status}</span>
        </span>
      </td>
      <td className="border-b border-border px-3 py-2">
        <HealthBadge health={health} compact />
      </td>
      <td className="border-b border-border px-3 py-2">
        <span className="block max-w-[150px] truncate text-gray-400" title={proxyLabel}>
          {proxyLabel}
        </span>
      </td>
      <td className="border-b border-border px-3 py-2 text-gray-400">{ip ?? "-"}</td>
      <td className="border-b border-border px-3 py-2 text-gray-400">{country ?? "-"}</td>
      <td className="border-b border-border px-3 py-2 text-gray-400">{timezone ?? "-"}</td>
      <td className="border-b border-border px-3 py-2 text-gray-400">{locale ?? "-"}</td>
      <td className="border-b border-border px-3 py-2">
        <div className="flex max-w-[150px] flex-wrap gap-1">
          {profile.tags.length > 0 ? profile.tags.map((tag) => (
            <span
              key={tag.tag}
              className="rounded-full bg-surface-4 px-1.5 py-0.5 text-[10px] text-gray-400"
              style={tag.color ? { backgroundColor: `${tag.color}20`, color: tag.color } : undefined}
            >
              {tag.tag}
            </span>
          )) : (
            <span className="text-gray-600">-</span>
          )}
        </div>
      </td>
      <td className="border-b border-border px-3 py-2 text-gray-400">
        {formatTimestamp(lastChecked)}
      </td>
      <td className="border-b border-border px-3 py-2">
        <button
          type="button"
          className="inline-flex items-center gap-1 rounded-md border border-border bg-surface-2 px-2 py-1 text-xs text-gray-300 transition-colors hover:border-border-hover hover:bg-surface-3"
          onClick={() => onSelect(profile.id)}
          aria-label={`Open ${profile.name}`}
        >
          <ArrowRight className="h-3.5 w-3.5" />
          Open
        </button>
      </td>
    </tr>
  );
}

function formatTimestamp(value: string | null | undefined): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatProxyLabel(value: string | null | undefined): string {
  if (!value) return "-";

  try {
    const url = new URL(value);
    return `${url.protocol}//${url.host}`;
  } catch {
    return "Invalid proxy";
  }
}
