import { AlertTriangle, FilterX, Layers3, Play, Plus, PlusCircle, ShieldAlert, Square, WifiOff } from "lucide-react";
import type { ReactNode } from "react";
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import type { Profile, ProfileHealthResponse } from "../lib/api";
import {
  defaultProfileFilters,
  filterAndSortProfiles,
  getProfileFilterOptions,
  type ProfileFilterOptions,
  type ProfileFilterState,
} from "../lib/filters";
import {
  getHealthGeoipParts,
  getHealthTone,
  getHealthWarningSummary,
} from "../lib/health";
import { CountryBadge, ProxyBadge, TagBadge } from "./Badge";
import { HealthBadge } from "./HealthBadge";
import { ProfileFilters } from "./ProfileFilters";
import { StatusIndicator } from "./StatusIndicator";

const PROFILE_LIST_VIRTUAL_THRESHOLD = 80;
const PROFILE_LIST_ITEM_HEIGHT = 112;
const PROFILE_LIST_OVERSCAN = 6;
const PROFILE_LIST_FALLBACK_VIEWPORT_HEIGHT = 560;

interface ProfileListProps {
  profiles: Profile[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  healthByProfileId?: Record<string, ProfileHealthResponse | undefined>;
  filters?: ProfileFilterState;
  filterOptions?: ProfileFilterOptions;
  onFiltersChange?: (filters: ProfileFilterState) => void;
  showFilters?: boolean;
}

export function ProfileList({
  profiles,
  selectedId,
  onSelect,
  onNew,
  healthByProfileId = {},
  filters: controlledFilters,
  filterOptions: controlledFilterOptions,
  onFiltersChange,
  showFilters = true,
}: ProfileListProps) {
  const [internalFilters, setInternalFilters] = useState<ProfileFilterState>(defaultProfileFilters);
  const filters = controlledFilters ?? internalFilters;
  const setFilters = onFiltersChange ?? setInternalFilters;

  const filterOptions = useMemo(
    () => controlledFilterOptions ?? getProfileFilterOptions(profiles, healthByProfileId),
    [controlledFilterOptions, healthByProfileId, profiles],
  );
  const filtered = useMemo(
    () => filterAndSortProfiles(profiles, healthByProfileId, filters),
    [filters, healthByProfileId, profiles],
  );
  const runningCount = profiles.filter((p) => p.status === "running").length;
  const quickViews = useMemo(
    () => buildQuickViews(profiles, healthByProfileId),
    [healthByProfileId, profiles],
  );
  const listRef = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);
  const [viewportHeight, setViewportHeight] = useState(PROFILE_LIST_FALLBACK_VIEWPORT_HEIGHT);
  const shouldVirtualize = filtered.length > PROFILE_LIST_VIRTUAL_THRESHOLD;
  const virtualWindow = useMemo(
    () => getVirtualWindow(filtered.length, scrollTop, viewportHeight),
    [filtered.length, scrollTop, viewportHeight],
  );
  const visibleProfiles = shouldVirtualize
    ? filtered.slice(virtualWindow.start, virtualWindow.end)
    : filtered;

  useLayoutEffect(() => {
    const list = listRef.current;
    if (!list) return;

    const updateViewportHeight = () => {
      setViewportHeight(list.clientHeight || PROFILE_LIST_FALLBACK_VIEWPORT_HEIGHT);
    };

    updateViewportHeight();

    if (typeof ResizeObserver === "undefined") {
      window.addEventListener("resize", updateViewportHeight);
      return () => window.removeEventListener("resize", updateViewportHeight);
    }

    const observer = new ResizeObserver(updateViewportHeight);
    observer.observe(list);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    setScrollTop(0);
    if (listRef.current) listRef.current.scrollTop = 0;
  }, [filters]);

  return (
    <div className="flex h-full flex-col bg-surface-1">
      {/* Header */}
      <div className="border-b border-border p-4">
        <div className="mb-4 flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-blue-100 bg-blue-50 text-accent">
            <Layers3 className="h-4 w-4" />
          </div>
          <div className="min-w-0">
            <h1 className="truncate text-sm font-semibold tracking-tight text-slate-950">
              CloakBrowser
            </h1>
            <p className="text-[11px] font-medium text-slate-500">Operations rail</p>
          </div>
        </div>
        <div className="mb-4 grid grid-cols-2 gap-2">
          <RailMetric label="Profiles" value={profiles.length} />
          <RailMetric label="Running" value={runningCount} />
        </div>
        <div>
          <div className="mb-2 flex items-center justify-between">
            <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500">
              Saved views
            </span>
            <span className="text-[11px] text-slate-600">{filtered.length} shown</span>
          </div>
          <div className="grid gap-1.5">
            {quickViews.map((view) => (
              <QuickViewButton
                key={view.label}
                icon={view.icon}
                label={view.label}
                count={view.count}
                active={matchesQuickView(filters, view.filters)}
                onClick={() => setFilters(view.filters)}
              />
            ))}
          </div>
        </div>
        {showFilters && (
          <div className="mt-4 border-t border-border pt-4">
            <ProfileFilters
              value={filters}
              options={filterOptions}
              onChange={setFilters}
            />
          </div>
        )}
      </div>

      {/* Profile list */}
      <div className="border-b border-border px-4 py-2">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500">
            Profile shortcuts
          </span>
          <span className="text-[11px] text-slate-600">filtered</span>
        </div>
      </div>
      <div
        ref={listRef}
        role="region"
        aria-label="Profiles list"
        className="flex-1 overflow-y-auto p-2"
        onScroll={(event) => setScrollTop(event.currentTarget.scrollTop)}
      >
        {filtered.length === 0 && (
          <ProfileListEmptyState
            kind={profiles.length === 0 ? "first-run" : "filtered"}
            onCreateProfile={onNew}
            onClearFilters={() => setFilters(defaultProfileFilters)}
          />
        )}
        {shouldVirtualize ? (
          <div
            className="relative"
            style={{ height: filtered.length * PROFILE_LIST_ITEM_HEIGHT }}
          >
            {visibleProfiles.map((profile, index) => (
              <div
                key={profile.id}
                className="absolute left-0 right-0"
                style={{
                  height: PROFILE_LIST_ITEM_HEIGHT,
                  transform: `translateY(${(virtualWindow.start + index) * PROFILE_LIST_ITEM_HEIGHT}px)`,
                }}
              >
                <ProfileListItem
                  profile={profile}
                  selected={selectedId === profile.id}
                  health={healthByProfileId[profile.id]}
                  onSelect={onSelect}
                  virtualized
                />
              </div>
            ))}
          </div>
        ) : (
          visibleProfiles.map((profile) => (
            <ProfileListItem
              key={profile.id}
              profile={profile}
              selected={selectedId === profile.id}
              health={healthByProfileId[profile.id]}
              onSelect={onSelect}
            />
          ))
        )}
      </div>

      {/* New profile button */}
      <div className="border-t border-border p-3">
        <button onClick={onNew} className="btn-secondary w-full flex items-center justify-center gap-1.5">
          <Plus className="h-3.5 w-3.5" />
          <span>New Profile</span>
        </button>
      </div>
    </div>
  );
}

interface QuickView {
  label: string;
  count: number;
  icon: ReactNode;
  filters: ProfileFilterState;
}

function buildQuickViews(
  profiles: Profile[],
  healthByProfileId: Record<string, ProfileHealthResponse | undefined>,
): QuickView[] {
  const countHealth = (status: NonNullable<ProfileHealthResponse["status"]>) =>
    profiles.filter((profile) => (healthByProfileId[profile.id]?.status ?? "unknown") === status).length;

  return [
    {
      label: "All profiles",
      count: profiles.length,
      icon: <Layers3 className="h-3.5 w-3.5" />,
      filters: defaultProfileFilters,
    },
    {
      label: "Running profiles",
      count: profiles.filter((profile) => profile.status === "running").length,
      icon: <Play className="h-3.5 w-3.5" />,
      filters: { ...defaultProfileFilters, status: "running" },
    },
    {
      label: "Stopped profiles",
      count: profiles.filter((profile) => profile.status === "stopped").length,
      icon: <Square className="h-3.5 w-3.5" />,
      filters: { ...defaultProfileFilters, status: "stopped" },
    },
    {
      label: "Unavailable profiles",
      count: countHealth("error"),
      icon: <ShieldAlert className="h-3.5 w-3.5" />,
      filters: { ...defaultProfileFilters, health: "error" },
    },
    {
      label: "Needs attention",
      count: countHealth("warning"),
      icon: <AlertTriangle className="h-3.5 w-3.5" />,
      filters: { ...defaultProfileFilters, health: "warning" },
    },
    {
      label: "No proxy",
      count: profiles.filter((profile) => !profile.proxy).length,
      icon: <WifiOff className="h-3.5 w-3.5" />,
      filters: { ...defaultProfileFilters, proxy: "without_proxy" },
    },
  ];
}

function matchesQuickView(current: ProfileFilterState, target: ProfileFilterState): boolean {
  return Object.keys(defaultProfileFilters).every((key) => {
    const filterKey = key as keyof ProfileFilterState;
    return current[filterKey] === target[filterKey];
  });
}

function RailMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-border bg-surface-2 px-2.5 py-2">
      <div className="text-base font-semibold tabular-nums text-slate-950">{value}</div>
      <div className="text-[10px] font-medium uppercase tracking-[0.08em] text-slate-500">{label}</div>
    </div>
  );
}

function QuickViewButton({
  icon,
  label,
  count,
  active,
  onClick,
}: {
  icon: ReactNode;
  label: string;
  count: number;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      aria-pressed={active}
      onClick={onClick}
      className={`flex h-9 w-full items-center gap-2 rounded-lg border px-2.5 text-left text-xs font-medium transition-[background-color,border-color,color,box-shadow,transform] duration-150 active:translate-y-px focus:outline-none focus:ring-2 focus:ring-blue-500/15 ${
        active
          ? "border-blue-200 bg-blue-50 text-blue-700 shadow-[inset_3px_0_0_rgba(37,99,235,0.45)]"
          : "border-transparent text-slate-600 hover:border-border hover:bg-surface-2 hover:text-slate-950 hover:shadow-[0_1px_2px_rgba(15,23,42,0.04)]"
      }`}
    >
      <span className={active ? "text-blue-600" : "text-slate-500"}>{icon}</span>
      <span className="min-w-0 flex-1 truncate">{label}</span>
      <span aria-hidden="true" className={`tabular-nums ${active ? "text-blue-600" : "text-slate-600"}`}>{count}</span>
    </button>
  );
}

function ProfileListEmptyState({
  kind,
  onCreateProfile,
  onClearFilters,
}: {
  kind: "first-run" | "filtered";
  onCreateProfile: () => void;
  onClearFilters: () => void;
}) {
  const isFirstRun = kind === "first-run";
  const label = isFirstRun ? "No profiles yet" : "No matching profile shortcuts";
  const title = isFirstRun ? "No profiles yet" : "No matches";
  const description = isFirstRun
    ? "Create the first profile to start building shortcuts."
    : "Clear filters to bring profile shortcuts back.";
  const actionLabel = isFirstRun ? "Create profile" : "Clear filters";
  const action = isFirstRun ? onCreateProfile : onClearFilters;
  const Icon = isFirstRun ? PlusCircle : FilterX;

  return (
    <div
      role="status"
      aria-label={label}
      className="m-2 rounded-lg border border-dashed border-slate-300 bg-white px-3 py-5 text-center shadow-[inset_0_1px_0_rgba(255,255,255,0.85)]"
    >
      <span className="mx-auto mb-3 flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 bg-slate-50 text-slate-500">
        <Icon className="h-4 w-4" />
      </span>
      <div className="text-sm font-semibold text-slate-950">{title}</div>
      <p className="mx-auto mt-1 max-w-[210px] text-xs leading-5 text-slate-500">{description}</p>
      <button
        type="button"
        className="mt-3 inline-flex h-8 items-center justify-center gap-1.5 rounded-[6px] border border-slate-200 bg-white px-3 text-xs font-medium text-slate-700 shadow-[0_1px_1px_rgba(15,23,42,0.04)] transition-[background-color,border-color,color,box-shadow,transform] duration-150 hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700 active:translate-y-px focus:outline-none focus:ring-2 focus:ring-blue-500/20"
        onClick={action}
      >
        <Icon className="h-3.5 w-3.5" />
        {actionLabel}
      </button>
    </div>
  );
}

function getVirtualWindow(
  total: number,
  scrollTop: number,
  viewportHeight: number,
): { start: number; end: number } {
  if (total === 0) return { start: 0, end: 0 };

  const visibleCount = Math.ceil(
    Math.max(viewportHeight, PROFILE_LIST_FALLBACK_VIEWPORT_HEIGHT) / PROFILE_LIST_ITEM_HEIGHT,
  );
  const windowSize = visibleCount + PROFILE_LIST_OVERSCAN * 2;
  const maxStart = Math.max(0, total - windowSize);
  const rawStart = Math.floor(scrollTop / PROFILE_LIST_ITEM_HEIGHT) - PROFILE_LIST_OVERSCAN;
  const start = Math.min(Math.max(0, rawStart), maxStart);
  const end = Math.min(total, start + windowSize);
  return { start, end };
}

interface ProfileListItemProps {
  profile: Profile;
  selected: boolean;
  health?: ProfileHealthResponse;
  onSelect: (id: string) => void;
  virtualized?: boolean;
}

function ProfileListItem({
  profile,
  selected,
  health,
  onSelect,
  virtualized = false,
}: ProfileListItemProps) {
  const warningSummary = getHealthWarningSummary(health);
  const geoipParts = getHealthGeoipParts(health);
  const healthTone = getHealthTone(health?.status);
  const hasMeta = Boolean(profile.proxy || warningSummary || geoipParts.length);

  return (
    <button
      onClick={() => onSelect(profile.id)}
      className={`mb-1 w-full rounded-lg px-3 py-2.5 text-left transition-colors focus:outline-none focus:ring-2 focus:ring-accent/20 ${
        virtualized ? "h-[108px] overflow-hidden" : ""
      } ${
        selected
          ? "animate-profile-selection border border-blue-200 bg-blue-50 shadow-[inset_3px_0_0_#2563eb,0_1px_1px_rgba(15,23,42,0.04)]"
          : "border border-transparent hover:border-border hover:bg-surface-2"
      }`}
    >
      <div className="flex min-w-0 items-center gap-2">
        <StatusIndicator status={profile.status} />
        <span className="min-w-0 flex-1 truncate text-sm font-medium text-slate-900">{profile.name}</span>
        <span className="ml-auto shrink-0">
          <HealthBadge health={health} compact />
        </span>
      </div>

      {hasMeta && (
        <div className="mt-1 ml-4 flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
          {profile.proxy && (
            <ProxyBadge />
          )}
          {warningSummary && (
            <span
              className={`max-w-full truncate text-xs ${healthTone.summaryClassName}`}
              title={warningSummary}
            >
              {warningSummary}
            </span>
          )}
          {geoipParts.map((part) => (
            isCountryCode(part) ? (
              <CountryBadge key={part} country={part} />
            ) : (
              <span key={part} className="text-xs text-slate-500">
                {part}
              </span>
            )
          ))}
        </div>
      )}

      {profile.tags.length > 0 && (
        <div className="flex gap-1 mt-1.5 ml-4 flex-wrap">
          {profile.tags.map((t) => (
            <TagBadge key={t.tag} tag={t.tag} color={t.color} />
          ))}
        </div>
      )}
    </button>
  );
}

function isCountryCode(part: string): boolean {
  return /^[A-Z]{2}$/.test(part);
}
