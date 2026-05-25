import { ArrowRight } from "lucide-react";
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import type { Profile, ProfileHealthResponse } from "../lib/api";
import { BulkActionBar } from "./BulkActionBar";
import { HealthBadge } from "./HealthBadge";
import { StatusIndicator } from "./StatusIndicator";

const EMPTY_SELECTION = new Set<string>();
const PROFILE_TABLE_VIRTUAL_THRESHOLD = 120;
const PROFILE_TABLE_ROW_HEIGHT = 64;
const PROFILE_TABLE_OVERSCAN = 8;
const PROFILE_TABLE_FALLBACK_VIEWPORT_HEIGHT = 640;

interface ProfileTableProps {
  profiles: Profile[];
  healthByProfileId: Record<string, ProfileHealthResponse | undefined>;
  onSelect: (id: string) => void;
  selectedProfileIds?: Set<string>;
  onToggleProfileSelection?: (id: string) => void;
  onToggleVisibleSelection?: (ids: string[], shouldSelect: boolean) => void;
  onClearSelection?: () => void;
}

export function ProfileTable({
  profiles,
  healthByProfileId,
  onSelect,
  selectedProfileIds = EMPTY_SELECTION,
  onToggleProfileSelection,
  onToggleVisibleSelection,
  onClearSelection,
}: ProfileTableProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);
  const [viewportHeight, setViewportHeight] = useState(PROFILE_TABLE_FALLBACK_VIEWPORT_HEIGHT);
  const filteredIds = useMemo(() => profiles.map((profile) => profile.id), [profiles]);
  const selectedVisibleCount = filteredIds.filter((id) => selectedProfileIds.has(id)).length;
  const allVisibleSelected = profiles.length > 0 && selectedVisibleCount === profiles.length;
  const hasPartialVisibleSelection = selectedVisibleCount > 0 && !allVisibleSelected;
  const selectedCount = selectedProfileIds.size;
  const selectedProfiles = useMemo(
    () => profiles.filter((profile) => selectedProfileIds.has(profile.id)),
    [profiles, selectedProfileIds],
  );
  const shouldVirtualize = profiles.length > PROFILE_TABLE_VIRTUAL_THRESHOLD;
  const virtualWindow = useMemo(
    () => getProfileTableVirtualWindow(profiles.length, scrollTop, viewportHeight),
    [profiles.length, scrollTop, viewportHeight],
  );
  const visibleProfiles = shouldVirtualize
    ? profiles.slice(virtualWindow.start, virtualWindow.end)
    : profiles;
  const topSpacerHeight = shouldVirtualize ? virtualWindow.start * PROFILE_TABLE_ROW_HEIGHT : 0;
  const bottomSpacerHeight = shouldVirtualize
    ? (profiles.length - virtualWindow.end) * PROFILE_TABLE_ROW_HEIGHT
    : 0;
  const profileWindowKey = filteredIds.join("\u0000");

  useLayoutEffect(() => {
    const scrollContainer = scrollRef.current;
    if (!scrollContainer) return;

    const updateViewportHeight = () => {
      setViewportHeight(scrollContainer.clientHeight || PROFILE_TABLE_FALLBACK_VIEWPORT_HEIGHT);
    };

    updateViewportHeight();

    if (typeof ResizeObserver === "undefined") {
      window.addEventListener("resize", updateViewportHeight);
      return () => window.removeEventListener("resize", updateViewportHeight);
    }

    const observer = new ResizeObserver(updateViewportHeight);
    observer.observe(scrollContainer);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    setScrollTop(0);
    if (scrollRef.current) scrollRef.current.scrollTop = 0;
  }, [profileWindowKey]);

  return (
    <div
      ref={scrollRef}
      role="region"
      aria-label="Profile operations table"
      className="h-full overflow-auto"
      onScroll={(event) => setScrollTop(event.currentTarget.scrollTop)}
    >
      <div className="min-w-[1040px]">
        {selectedCount > 0 && (
          <BulkActionBar
            selectedCount={selectedCount}
            selectedProfiles={selectedProfiles}
            healthByProfileId={healthByProfileId}
            onClearSelection={onClearSelection}
          />
        )}
        <table className="w-full border-separate border-spacing-0 text-left text-xs">
          <thead className={`sticky z-10 bg-surface-0/95 backdrop-blur ${selectedCount > 0 ? "top-10" : "top-0"}`}>
            <tr className="text-gray-500">
              <th aria-label="Select" className="w-10 border-b border-border px-3 py-2 font-medium">
                <SelectionCheckbox
                  label="Select all visible profiles"
                  checked={allVisibleSelected}
                  indeterminate={hasPartialVisibleSelection}
                  disabled={profiles.length === 0 || !onToggleVisibleSelection}
                  onChange={() => onToggleVisibleSelection?.(filteredIds, !allVisibleSelected)}
                />
                <span className="sr-only">Select</span>
              </th>
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
                <td colSpan={12} className="px-4 py-10 text-center text-gray-500">
                  No profiles in this view
                </td>
              </tr>
            ) : (
              <>
                {topSpacerHeight > 0 && <ProfileTableSpacer height={topSpacerHeight} />}
                {visibleProfiles.map((profile) => (
                  <ProfileTableRow
                    key={profile.id}
                    profile={profile}
                    health={healthByProfileId[profile.id]}
                    onSelect={onSelect}
                    selected={selectedProfileIds.has(profile.id)}
                    onToggleSelection={onToggleProfileSelection}
                  />
                ))}
                {bottomSpacerHeight > 0 && <ProfileTableSpacer height={bottomSpacerHeight} />}
              </>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function getProfileTableVirtualWindow(
  total: number,
  scrollTop: number,
  viewportHeight: number,
): { start: number; end: number } {
  if (total === 0) return { start: 0, end: 0 };

  const visibleCount = Math.ceil(
    Math.max(viewportHeight, PROFILE_TABLE_FALLBACK_VIEWPORT_HEIGHT) / PROFILE_TABLE_ROW_HEIGHT,
  );
  const windowSize = visibleCount + PROFILE_TABLE_OVERSCAN * 2;
  const maxStart = Math.max(0, total - windowSize);
  const rawStart = Math.floor(scrollTop / PROFILE_TABLE_ROW_HEIGHT) - PROFILE_TABLE_OVERSCAN;
  const start = Math.min(Math.max(0, rawStart), maxStart);
  const end = Math.min(total, start + windowSize);
  return { start, end };
}

function ProfileTableSpacer({ height }: { height: number }) {
  return (
    <tr aria-hidden="true" style={{ height }}>
      <td colSpan={12} className="border-0 p-0" />
    </tr>
  );
}

function HeaderCell({ children }: { children: string }) {
  return (
    <th className="border-b border-border px-3 py-2 font-medium">
      {children}
    </th>
  );
}

interface SelectionCheckboxProps {
  label: string;
  checked: boolean;
  indeterminate?: boolean;
  disabled?: boolean;
  onChange: () => void;
}

function SelectionCheckbox({
  label,
  checked,
  indeterminate = false,
  disabled = false,
  onChange,
}: SelectionCheckboxProps) {
  const ref = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (ref.current) ref.current.indeterminate = indeterminate;
  }, [indeterminate]);

  return (
    <input
      ref={ref}
      type="checkbox"
      aria-label={label}
      checked={checked}
      disabled={disabled}
      onChange={onChange}
      className="h-4 w-4 rounded border-border bg-surface-2 text-accent focus:ring-1 focus:ring-accent/60"
    />
  );
}

interface ProfileTableRowProps {
  profile: Profile;
  health?: ProfileHealthResponse;
  onSelect: (id: string) => void;
  selected: boolean;
  onToggleSelection?: (id: string) => void;
}

function ProfileTableRow({
  profile,
  health,
  onSelect,
  selected,
  onToggleSelection,
}: ProfileTableRowProps) {
  const geoip = health?.geoip;
  const ip = geoip?.ip ?? profile.last_geoip_ip;
  const country = geoip?.country_code ?? profile.last_geoip_country_code;
  const timezone = geoip?.timezone ?? profile.last_geoip_timezone;
  const locale = geoip?.locale ?? profile.last_geoip_locale;
  const lastChecked = health?.checked_at ?? profile.last_geoip_resolved_at;
  const proxyLabel = formatProxyLabel(profile.proxy);

  return (
    <tr className="group border-b border-border hover:bg-surface-1" style={{ height: PROFILE_TABLE_ROW_HEIGHT }}>
      <td className="border-b border-border px-3 py-2">
        <SelectionCheckbox
          label={`Select ${profile.name}`}
          checked={selected}
          disabled={!onToggleSelection}
          onChange={() => onToggleSelection?.(profile.id)}
        />
      </td>
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
        <div className="flex max-h-10 max-w-[150px] flex-wrap gap-1 overflow-hidden">
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
