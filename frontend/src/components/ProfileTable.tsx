import { ArrowRight, Check, Minus } from "lucide-react";
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import type { Profile, ProfileHealthResponse } from "../lib/api";
import { formatProxyLabel, formatTimestamp } from "../lib/profileDisplay";
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
  previewProfileId?: string | null;
  onPreviewProfile?: (id: string) => void;
  onCheckSelectedHealth?: (ids: string[]) => Promise<void> | void;
  checkingSelectedHealth?: boolean;
  onLaunchSelectedProfiles?: (ids: string[]) => Promise<void> | void;
  launchingSelectedProfiles?: boolean;
  onStopSelectedProfiles?: (ids: string[]) => Promise<void> | void;
  stoppingSelectedProfiles?: boolean;
  onAddTagsToSelectedProfiles?: (ids: string[], tags: Profile["tags"]) => Promise<void> | void;
  taggingSelectedProfiles?: boolean;
  onDeleteSelectedProfiles?: (ids: string[]) => Promise<void> | void;
  deletingSelectedProfiles?: boolean;
}

export function ProfileTable({
  profiles,
  healthByProfileId,
  onSelect,
  selectedProfileIds = EMPTY_SELECTION,
  onToggleProfileSelection,
  onToggleVisibleSelection,
  onClearSelection,
  previewProfileId,
  onPreviewProfile,
  onCheckSelectedHealth,
  checkingSelectedHealth = false,
  onLaunchSelectedProfiles,
  launchingSelectedProfiles = false,
  onStopSelectedProfiles,
  stoppingSelectedProfiles = false,
  onAddTagsToSelectedProfiles,
  taggingSelectedProfiles = false,
  onDeleteSelectedProfiles,
  deletingSelectedProfiles = false,
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
      className="h-full overflow-auto bg-white [scrollbar-gutter:stable]"
      onScroll={(event) => setScrollTop(event.currentTarget.scrollTop)}
    >
      <div className="min-w-[840px]">
        {selectedCount > 0 && (
          <BulkActionBar
            selectedCount={selectedCount}
            selectedProfiles={selectedProfiles}
            healthByProfileId={healthByProfileId}
            onClearSelection={onClearSelection}
            onCheckHealth={() => onCheckSelectedHealth?.(selectedProfiles.map((profile) => profile.id))}
            checkingHealth={checkingSelectedHealth}
            onLaunch={() => onLaunchSelectedProfiles?.(
              selectedProfiles.filter((profile) => profile.status === "stopped").map((profile) => profile.id),
            )}
            launching={launchingSelectedProfiles}
            onStop={() => onStopSelectedProfiles?.(
              selectedProfiles.filter((profile) => profile.status === "running").map((profile) => profile.id),
            )}
            stopping={stoppingSelectedProfiles}
            onAddTags={onAddTagsToSelectedProfiles
              ? (tags) => onAddTagsToSelectedProfiles(
                selectedProfiles.map((profile) => profile.id),
                tags,
              )
              : undefined}
            tagging={taggingSelectedProfiles}
            onDelete={onDeleteSelectedProfiles
              ? (ids) => onDeleteSelectedProfiles(ids)
              : undefined}
            deleting={deletingSelectedProfiles}
          />
        )}
        <table className="w-full table-fixed border-separate border-spacing-0 text-left text-xs text-slate-700">
          <colgroup>
            <col style={{ width: 42 }} />
            <col style={{ width: 142 }} />
            <col style={{ width: 66 }} />
            <col style={{ width: 72 }} />
            <col style={{ width: 84 }} />
            <col style={{ width: 68 }} />
            <col style={{ width: 44 }} />
            <col style={{ width: 78 }} />
            <col style={{ width: 50 }} />
            <col style={{ width: 56 }} />
            <col style={{ width: 64 }} />
            <col style={{ width: 80 }} />
          </colgroup>
          <thead className={`sticky z-10 bg-slate-50/95 backdrop-blur ${selectedCount > 0 ? "top-11" : "top-0"}`}>
            <tr className="text-slate-500 shadow-[inset_0_-1px_0_rgba(148,163,184,0.28)]">
              <th aria-label="Select" className="w-9 border-b border-slate-200 bg-slate-50/95 px-1.5 py-1.5 font-semibold">
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
                <td colSpan={12} className="px-4 py-10 text-center text-slate-500">
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
                    previewed={previewProfileId === profile.id}
                    onPreview={onPreviewProfile}
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
    <th className="h-9 truncate border-b border-slate-200 bg-slate-50/95 px-2 py-2 text-[10px] font-semibold uppercase tracking-[0.08em] text-slate-500">
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
    <label
      className={`group/checkbox relative inline-flex h-7 w-7 items-center justify-center align-middle ${
        disabled ? "cursor-not-allowed opacity-50" : "cursor-pointer"
      }`}
    >
      <input
        ref={ref}
        type="checkbox"
        aria-label={label}
        aria-checked={indeterminate ? "mixed" : checked}
        checked={checked}
        disabled={disabled}
        onChange={onChange}
        className="peer sr-only"
      />
      <span
        aria-hidden="true"
        className={`flex h-4 w-4 items-center justify-center rounded-[5px] border shadow-[0_1px_1px_rgba(15,23,42,0.06)] ring-1 ring-transparent transition-all duration-150 peer-focus-visible:ring-2 peer-focus-visible:ring-blue-500/25 peer-focus-visible:ring-offset-2 peer-focus-visible:ring-offset-white ${
          checked || indeterminate
            ? "border-blue-600 bg-blue-600 text-white shadow-[0_1px_2px_rgba(37,99,235,0.22)]"
            : "border-slate-300 bg-white text-transparent group-hover/checkbox:border-blue-400 group-hover/checkbox:bg-blue-50"
        }`}
      >
        {indeterminate ? (
          <Minus className="h-3 w-3 stroke-[3]" />
        ) : checked ? (
          <Check className="h-3 w-3 stroke-[3]" />
        ) : null}
      </span>
    </label>
  );
}

interface ProfileTableRowProps {
  profile: Profile;
  health?: ProfileHealthResponse;
  onSelect: (id: string) => void;
  selected: boolean;
  onToggleSelection?: (id: string) => void;
  previewed?: boolean;
  onPreview?: (id: string) => void;
}

function ProfileTableRow({
  profile,
  health,
  onSelect,
  selected,
  onToggleSelection,
  previewed = false,
  onPreview,
}: ProfileTableRowProps) {
  const geoip = health?.geoip;
  const ip = geoip?.ip ?? profile.last_geoip_ip;
  const country = geoip?.country_code ?? profile.last_geoip_country_code;
  const timezone = geoip?.timezone ?? profile.last_geoip_timezone;
  const locale = geoip?.locale ?? profile.last_geoip_locale;
  const lastChecked = health?.checked_at ?? profile.last_geoip_resolved_at;
  const proxyLabel = formatProxyLabel(profile.proxy);

  return (
    <tr
      data-state={selected ? "selected" : previewed ? "previewed" : undefined}
      className={`group transition-colors duration-150 ${
        selected
          ? "bg-blue-50/75 hover:bg-blue-50"
          : previewed
            ? "bg-slate-50/95 hover:bg-slate-100/70"
            : "odd:bg-white even:bg-slate-50/35 hover:bg-blue-50/35"
      }`}
      style={{ height: PROFILE_TABLE_ROW_HEIGHT }}
    >
      <td
        className={`border-b border-slate-100 border-l-2 px-1.5 py-2 ${
          selected ? "border-l-blue-500" : previewed ? "border-l-slate-400" : "border-l-transparent"
        }`}
      >
        <SelectionCheckbox
          label={`Select ${profile.name}`}
          checked={selected}
          disabled={!onToggleSelection}
          onChange={() => onToggleSelection?.(profile.id)}
        />
      </td>
      <td className="border-b border-slate-100 px-2 py-2">
        <button
          type="button"
          className={`block max-w-[180px] truncate rounded-md text-left text-sm font-semibold transition-colors hover:text-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 ${
            selected ? "text-blue-950" : "text-slate-950"
          }`}
          title={profile.name}
          aria-label={`Preview ${profile.name}`}
          onClick={() => onPreview?.(profile.id)}
        >
          {profile.name}
        </button>
        <div className="mt-0.5 font-mono text-[11px] text-slate-400">{profile.id.slice(0, 8)}</div>
      </td>
      <td className="truncate border-b border-slate-100 px-2 py-2">
        <span className="inline-flex items-center gap-1.5 font-medium text-slate-700">
          <StatusIndicator status={profile.status} />
          <span>{profile.status}</span>
        </span>
      </td>
      <td className="border-b border-slate-100 px-2 py-2">
        <HealthBadge health={health} compact />
      </td>
      <td className="border-b border-slate-100 px-2 py-2">
        <span className="block truncate font-mono text-[11px] text-slate-600" title={proxyLabel}>
          {proxyLabel}
        </span>
      </td>
      <td className="truncate border-b border-slate-100 px-2 py-2 font-mono text-[11px] text-slate-600" title={ip ?? undefined}>{ip ?? "-"}</td>
      <td className="truncate border-b border-slate-100 px-2 py-2 font-medium text-slate-600" title={country ?? undefined}>{country ?? "-"}</td>
      <td className="truncate border-b border-slate-100 px-2 py-2 text-slate-600" title={timezone ?? undefined}>{timezone ?? "-"}</td>
      <td className="truncate border-b border-slate-100 px-2 py-2 text-slate-600" title={locale ?? undefined}>{locale ?? "-"}</td>
      <td className="border-b border-slate-100 px-2 py-2">
        <div className="flex max-h-10 max-w-[150px] flex-wrap gap-1 overflow-hidden">
          {profile.tags.length > 0 ? profile.tags.map((tag) => (
            <span
              key={tag.tag}
              className="rounded-md border border-slate-200 bg-slate-50 px-1.5 py-0.5 text-[10px] font-medium text-slate-600 shadow-[inset_0_1px_0_rgba(255,255,255,0.75)]"
              style={tag.color ? { backgroundColor: `${tag.color}20`, color: tag.color } : undefined}
            >
              {tag.tag}
            </span>
          )) : (
            <span className="text-slate-400">-</span>
          )}
        </div>
      </td>
      <td className="truncate border-b border-slate-100 px-2 py-2 text-slate-500">
        {formatTimestamp(lastChecked)}
      </td>
      <td className="border-b border-slate-100 px-2 py-2">
        <button
          type="button"
          className="inline-flex h-7 items-center gap-1 rounded-md border border-slate-200 bg-white px-2 text-xs font-medium text-slate-700 shadow-[0_1px_1px_rgba(15,23,42,0.04)] transition-colors hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 group-hover:border-slate-300"
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
