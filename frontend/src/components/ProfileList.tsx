import { Plus, Monitor } from "lucide-react";
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
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-border">
        <div className="flex items-center gap-2 mb-3">
          <Monitor className="h-4 w-4 text-accent" />
          <h1 className="text-sm font-semibold tracking-tight">Invisible Browser Manager</h1>
        </div>
        {runningCount > 0 && (
          <div className="text-xs text-gray-500 mb-3">
            {runningCount} running
          </div>
        )}
        <ProfileFilters
          value={filters}
          options={filterOptions}
          onChange={setFilters}
        />
      </div>

      {/* Profile list */}
      <div
        ref={listRef}
        role="region"
        aria-label="Profiles list"
        className="flex-1 overflow-y-auto p-2"
        onScroll={(event) => setScrollTop(event.currentTarget.scrollTop)}
      >
        {filtered.length === 0 && (
          <div className="text-center text-gray-500 text-xs py-8">
            {profiles.length === 0 ? "No profiles yet" : "No matches"}
          </div>
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
      <div className="p-3 border-t border-border">
        <button onClick={onNew} className="btn-secondary w-full flex items-center justify-center gap-1.5">
          <Plus className="h-3.5 w-3.5" />
          <span>New Profile</span>
        </button>
      </div>
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
      className={`w-full text-left px-3 py-2.5 rounded-md mb-1 transition-colors ${
        virtualized ? "h-[108px] overflow-hidden" : ""
      } ${
        selected
          ? "bg-surface-3 border border-border-hover"
          : "hover:bg-surface-2 border border-transparent"
      }`}
    >
      <div className="flex min-w-0 items-center gap-2">
        <StatusIndicator status={profile.status} />
        <span className="min-w-0 flex-1 truncate text-sm font-medium">{profile.name}</span>
        <span className="ml-auto shrink-0">
          <HealthBadge health={health} compact />
        </span>
      </div>

      {hasMeta && (
        <div className="mt-1 ml-4 flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
          {profile.proxy && (
            <span className="text-xs text-gray-500">Proxy</span>
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
            <span key={part} className="text-xs text-gray-500">
              {part}
            </span>
          ))}
        </div>
      )}

      {profile.tags.length > 0 && (
        <div className="flex gap-1 mt-1.5 ml-4 flex-wrap">
          {profile.tags.map((t) => (
            <span
              key={t.tag}
              className="text-[10px] px-1.5 py-0.5 rounded-full bg-surface-4 text-gray-400"
              style={t.color ? { backgroundColor: `${t.color}20`, color: t.color } : undefined}
            >
              {t.tag}
            </span>
          ))}
        </div>
      )}
    </button>
  );
}
