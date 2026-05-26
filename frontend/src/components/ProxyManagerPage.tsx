import { Database, Globe2, Network, RefreshCw, Search, UserPlus, X } from "lucide-react";
import { useCallback, useDeferredValue, useEffect, useMemo, useState } from "react";
import { api, type Profile, type ProxyAsset } from "../lib/api";
import { formatTimestamp, redactUrlCredentials } from "../lib/profileDisplay";

type ProxyStatusTone = "good" | "warning" | "error" | "unknown";
const FILTER_ALL = "__all_proxy_filter__";

interface ProxyManagerPageProps {
  profiles?: Profile[];
  onProfilesAssigned?: () => Promise<unknown> | unknown;
}

export function ProxyManagerPage({
  profiles = [],
  onProfilesAssigned,
}: ProxyManagerPageProps = {}) {
  const [proxies, setProxies] = useState<ProxyAsset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedProxyIds, setSelectedProxyIds] = useState<Set<string>>(() => new Set());
  const [bulkChecking, setBulkChecking] = useState(false);
  const [bulkCheckNotice, setBulkCheckNotice] = useState<string | null>(null);
  const [bulkCheckError, setBulkCheckError] = useState<string | null>(null);
  const [assignDialogOpen, setAssignDialogOpen] = useState(false);
  const [assignSearchQuery, setAssignSearchQuery] = useState("");
  const [selectedAssignProfileIds, setSelectedAssignProfileIds] = useState<Set<string>>(() => new Set());
  const [assigning, setAssigning] = useState(false);
  const [assignNotice, setAssignNotice] = useState<string | null>(null);
  const [assignError, setAssignError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [countryFilter, setCountryFilter] = useState(FILTER_ALL);
  const [providerFilter, setProviderFilter] = useState(FILTER_ALL);
  const [tagFilter, setTagFilter] = useState(FILTER_ALL);
  const deferredSearchQuery = useDeferredValue(searchQuery);

  const loadProxies = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const nextProxies = await api.listProxies();
      setProxies(nextProxies);
      setSelectedProxyIds((current) => {
        const nextIds = new Set(nextProxies.map((proxy) => proxy.id));
        return new Set([...current].filter((id) => nextIds.has(id)));
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load proxy assets");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadProxies();
  }, [loadProxies]);

  const stats = useMemo(() => {
    const good = proxies.filter((proxy) => proxy.last_check_status === "good").length;
    const needsReview = proxies.filter((proxy) => {
      const status = getProxyStatusTone(proxy.last_check_status);
      return status === "warning" || status === "error";
    }).length;
    const unchecked = proxies.filter((proxy) => !proxy.last_check_status).length;

    return { total: proxies.length, good, needsReview, unchecked };
  }, [proxies]);

  const filterOptions = useMemo(() => ({
    countries: uniqueSorted(proxies.map((proxy) => proxy.country_code)),
    providers: uniqueSorted(proxies.map((proxy) => proxy.provider)),
    tags: uniqueSorted(proxies.flatMap((proxy) => proxy.tags.map((tag) => tag.tag))),
  }), [proxies]);

  const filteredProxies = useMemo(() => {
    const query = normalizeFilterValue(deferredSearchQuery);

    return proxies.filter((proxy) => {
      if (!matchesOptionFilter(proxy.country_code, countryFilter)) return false;
      if (!matchesOptionFilter(proxy.provider, providerFilter)) return false;
      if (tagFilter !== FILTER_ALL && !proxy.tags.some((tag) => matchesOptionFilter(tag.tag, tagFilter))) return false;
      if (!query) return true;

      return getProxySearchText(proxy).includes(query);
    });
  }, [countryFilter, deferredSearchQuery, providerFilter, proxies, tagFilter]);

  const hasActiveFilters = Boolean(searchQuery.trim())
    || countryFilter !== FILTER_ALL
    || providerFilter !== FILTER_ALL
    || tagFilter !== FILTER_ALL;

  const clearFilters = useCallback(() => {
    setSearchQuery("");
    setCountryFilter(FILTER_ALL);
    setProviderFilter(FILTER_ALL);
    setTagFilter(FILTER_ALL);
  }, []);

  const visibleProxyIds = useMemo(() => filteredProxies.map((proxy) => proxy.id), [filteredProxies]);
  const selectedCount = selectedProxyIds.size;
  const selectedProxy = selectedCount === 1
    ? proxies.find((proxy) => selectedProxyIds.has(proxy.id)) ?? null
    : null;
  const allVisibleSelected = visibleProxyIds.length > 0
    && visibleProxyIds.every((id) => selectedProxyIds.has(id));

  const toggleProxySelection = useCallback((proxyId: string) => {
    setSelectedProxyIds((current) => {
      const next = new Set(current);
      if (next.has(proxyId)) {
        next.delete(proxyId);
      } else {
        next.add(proxyId);
      }
      return next;
    });
  }, []);

  const toggleAllVisibleSelection = useCallback(() => {
    setSelectedProxyIds((current) => {
      const next = new Set(current);
      if (visibleProxyIds.length > 0 && visibleProxyIds.every((id) => next.has(id))) {
        visibleProxyIds.forEach((id) => next.delete(id));
      } else {
        visibleProxyIds.forEach((id) => next.add(id));
      }
      return next;
    });
  }, [visibleProxyIds]);

  const checkSelectedProxies = useCallback(async () => {
    if (selectedProxyIds.size === 0 || bulkChecking) return;

    const proxyIds = [...selectedProxyIds];
    setBulkChecking(true);
    setBulkCheckNotice(null);
    setBulkCheckError(null);

    try {
      const response = await api.bulkCheckProxies(proxyIds);
      const updatedById = new Map(
        response.results
          .filter((result) => result.proxy)
          .map((result) => [result.proxy_id, result.proxy as ProxyAsset]),
      );

      setProxies((current) => current.map((proxy) => updatedById.get(proxy.id) ?? proxy));
      setBulkCheckNotice(`Bulk check complete: ${response.succeeded} succeeded, ${response.failed} failed`);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to check selected proxies";
      setBulkCheckError(`Bulk check failed: ${redactUrlCredentials(message)}`);
    } finally {
      setBulkChecking(false);
    }
  }, [bulkChecking, selectedProxyIds]);

  const assignmentProfiles = useMemo(() => {
    const query = normalizeFilterValue(assignSearchQuery);
    if (!query) return profiles;

    return profiles.filter((profile) => getAssignmentProfileSearchText(profile).includes(query));
  }, [assignSearchQuery, profiles]);

  const visibleAssignmentProfileIds = useMemo(
    () => assignmentProfiles.map((profile) => profile.id),
    [assignmentProfiles],
  );
  const allVisibleAssignmentProfilesSelected = visibleAssignmentProfileIds.length > 0
    && visibleAssignmentProfileIds.every((id) => selectedAssignProfileIds.has(id));

  useEffect(() => {
    setSelectedAssignProfileIds((current) => {
      const profileIds = new Set(profiles.map((profile) => profile.id));
      const next = new Set([...current].filter((id) => profileIds.has(id)));
      return next.size === current.size ? current : next;
    });
  }, [profiles]);

  useEffect(() => {
    if (selectedProxy) return;
    setAssignDialogOpen(false);
    setSelectedAssignProfileIds(new Set());
  }, [selectedProxy]);

  const openAssignDialog = useCallback(() => {
    if (!selectedProxy || profiles.length === 0) return;
    setAssignSearchQuery("");
    setSelectedAssignProfileIds(new Set());
    setAssignError(null);
    setAssignDialogOpen(true);
  }, [profiles.length, selectedProxy]);

  const closeAssignDialog = useCallback(() => {
    if (assigning) return;
    setAssignDialogOpen(false);
    setAssignError(null);
  }, [assigning]);

  const toggleAssignProfileSelection = useCallback((profileId: string) => {
    setSelectedAssignProfileIds((current) => {
      const next = new Set(current);
      if (next.has(profileId)) {
        next.delete(profileId);
      } else {
        next.add(profileId);
      }
      return next;
    });
  }, []);

  const toggleVisibleAssignmentProfiles = useCallback(() => {
    setSelectedAssignProfileIds((current) => {
      const next = new Set(current);
      if (visibleAssignmentProfileIds.length > 0 && visibleAssignmentProfileIds.every((id) => next.has(id))) {
        visibleAssignmentProfileIds.forEach((id) => next.delete(id));
      } else {
        visibleAssignmentProfileIds.forEach((id) => next.add(id));
      }
      return next;
    });
  }, [visibleAssignmentProfileIds]);

  const assignSelectedProxyToProfiles = useCallback(async () => {
    if (!selectedProxy || selectedAssignProfileIds.size === 0 || assigning) return;

    setAssigning(true);
    setAssignError(null);
    setAssignNotice(null);
    const profileIds = [...selectedAssignProfileIds];

    try {
      const response = await api.assignProxyToProfiles(selectedProxy.id, profileIds);
      const notice = `Assigned proxy to ${response.succeeded} profile(s), ${response.failed} failed`;
      setAssignNotice(notice);
      setAssignDialogOpen(false);
      setSelectedAssignProfileIds(new Set());
      setAssignSearchQuery("");

      try {
        await onProfilesAssigned?.();
      } catch (refreshErr) {
        const message = refreshErr instanceof Error ? refreshErr.message : "Unable to refresh profile data";
        setAssignNotice(`${notice}. Refresh failed: ${redactUrlCredentials(message)}`);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to assign proxy";
      setAssignError(`Assign failed: ${redactUrlCredentials(message)}`);
    } finally {
      setAssigning(false);
    }
  }, [assigning, onProfilesAssigned, selectedAssignProfileIds, selectedProxy]);

  return (
    <section
      role="region"
      aria-label="Proxy Manager"
      className="flex h-full min-h-0 flex-col gap-3 p-3 sm:p-4 lg:p-5"
    >
      <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_auto] xl:items-end">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-[8px] border border-blue-100 bg-blue-50 text-blue-700 shadow-[inset_0_1px_0_rgba(255,255,255,0.85)]">
              <Network className="h-4 w-4" />
            </span>
            <div className="min-w-0">
              <h2 className="text-xl font-semibold tracking-tight text-slate-950">Proxy Manager</h2>
              <p className="mt-1 text-sm text-slate-500">
                Proxy inventory with credential-safe checks and profile assignment controls.
              </p>
            </div>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <ProxySummaryTile label="Proxies" value={stats.total} />
          <ProxySummaryTile label="Good" value={stats.good} tone="success" />
          <ProxySummaryTile label="Review" value={stats.needsReview} tone="warning" />
          <ProxySummaryTile label="Unchecked" value={stats.unchecked} />
        </div>
      </div>

      <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-[0_8px_24px_rgba(15,23,42,0.05),inset_0_1px_0_rgba(255,255,255,0.9)]">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 bg-[#fbfdff]/95 px-3 py-2.5">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-slate-950">Proxy assets</span>
              <span className="rounded-[999px] border border-slate-200 bg-slate-50 px-2 py-0.5 text-[11px] font-medium text-slate-500">
                {stats.total} proxies
              </span>
              <span className="rounded-[999px] border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-700">
                {stats.good} good
              </span>
              <span className="rounded-[999px] border border-amber-200 bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-800">
                {stats.needsReview} needs review
              </span>
              <span className="rounded-[999px] border border-blue-200 bg-blue-50 px-2 py-0.5 text-[11px] font-medium text-blue-700">
                {filteredProxies.length} of {stats.total} visible
              </span>
              <span className="rounded-[999px] border border-slate-200 bg-white px-2 py-0.5 text-[11px] font-medium text-slate-500">
                {selectedCount} selected
              </span>
            </div>
            <p className="mt-1 text-xs text-slate-500">
              URLs are rendered credential-safe. Bulk check and profile assignment are active; add, edit, delete, and CSV import remain disabled.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              className="btn-secondary inline-flex h-8 items-center gap-1.5 text-xs"
              onClick={() => void checkSelectedProxies()}
              disabled={selectedCount === 0 || bulkChecking}
              aria-label="Check selected proxies"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${bulkChecking ? "animate-spin" : ""}`} />
              {bulkChecking ? "Checking" : "Check selected"}
            </button>
            <button
              type="button"
              className="btn-secondary inline-flex h-8 items-center gap-1.5 text-xs"
              onClick={openAssignDialog}
              disabled={!selectedProxy || profiles.length === 0 || assigning}
              aria-label="Assign to profiles"
              title={selectedProxy ? "Assign selected proxy to profiles" : "Select exactly one proxy asset to assign"}
            >
              <UserPlus className="h-3.5 w-3.5" />
              Assign to profiles
            </button>
            <button
              type="button"
              className="btn-secondary inline-flex h-8 items-center gap-1.5 text-xs"
              onClick={() => void loadProxies()}
              disabled={loading}
              aria-label={loading ? "Loading proxy assets" : "Retry loading proxy assets"}
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </button>
          </div>
        </div>

        <ProxyFilterBar
          searchQuery={searchQuery}
          countryFilter={countryFilter}
          providerFilter={providerFilter}
          tagFilter={tagFilter}
          countries={filterOptions.countries}
          providers={filterOptions.providers}
          tags={filterOptions.tags}
          hasActiveFilters={hasActiveFilters}
          onSearchQueryChange={setSearchQuery}
          onCountryFilterChange={setCountryFilter}
          onProviderFilterChange={setProviderFilter}
          onTagFilterChange={setTagFilter}
          onClearFilters={clearFilters}
        />

        {error && (
          <div className="border-b border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
            {error}
          </div>
        )}

        {bulkCheckNotice && (
          <div className="border-b border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-700" role="status">
            {bulkCheckNotice}
          </div>
        )}

        {bulkCheckError && (
          <div className="border-b border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
            {bulkCheckError}
          </div>
        )}

        {assignNotice && (
          <div className="border-b border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-700" role="status">
            {assignNotice}
          </div>
        )}

        {loading && proxies.length === 0 ? (
          <div className="flex min-h-[320px] flex-1 items-center justify-center text-sm text-slate-500">
            Loading proxy assets...
          </div>
        ) : proxies.length === 0 ? (
          <ProxyEmptyState />
        ) : filteredProxies.length === 0 ? (
          <ProxyFilterEmptyState onClear={clearFilters} />
        ) : (
          <div
            role="region"
            aria-label="Proxy assets table"
            className="min-h-0 flex-1 overflow-auto bg-white [scrollbar-gutter:stable]"
          >
            <table
              aria-label="Proxy assets"
              className="min-w-[980px] w-full table-fixed border-separate border-spacing-0 bg-white text-left text-xs text-slate-700"
            >
              <thead className="sticky top-0 z-10 bg-[#fbfdff]/95 backdrop-blur">
                <tr className="text-slate-500 shadow-[inset_0_-1px_0_rgba(148,163,184,0.24)]">
                  <th className="w-[48px] px-3 py-2">
                    <label className="flex h-5 w-5 items-center justify-center">
                      <input
                        type="checkbox"
                        className="choice-checkbox m-0"
                        checked={allVisibleSelected}
                        onChange={toggleAllVisibleSelection}
                        aria-label="Select all visible proxy assets"
                      />
                    </label>
                  </th>
                  <HeaderCell className="w-[260px]">Proxy</HeaderCell>
                  <HeaderCell className="w-[150px]">Location</HeaderCell>
                  <HeaderCell className="w-[150px]">Provider</HeaderCell>
                  <HeaderCell className="w-[120px]">Health</HeaderCell>
                  <HeaderCell className="w-[210px]">Last check</HeaderCell>
                  <HeaderCell className="w-[170px]">Tags</HeaderCell>
                </tr>
              </thead>
              <tbody>
                {filteredProxies.map((proxy) => (
                  <ProxyRow
                    key={proxy.id}
                    proxy={proxy}
                    selected={selectedProxyIds.has(proxy.id)}
                    onToggleSelection={toggleProxySelection}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      {assignDialogOpen && selectedProxy && (
        <ProxyAssignDialog
          proxy={selectedProxy}
          profiles={assignmentProfiles}
          totalProfileCount={profiles.length}
          searchQuery={assignSearchQuery}
          selectedProfileIds={selectedAssignProfileIds}
          allVisibleSelected={allVisibleAssignmentProfilesSelected}
          assigning={assigning}
          error={assignError}
          onSearchQueryChange={setAssignSearchQuery}
          onToggleProfile={toggleAssignProfileSelection}
          onToggleVisible={toggleVisibleAssignmentProfiles}
          onAssign={() => void assignSelectedProxyToProfiles()}
          onClose={closeAssignDialog}
        />
      )}
    </section>
  );
}

function ProxyFilterBar({
  searchQuery,
  countryFilter,
  providerFilter,
  tagFilter,
  countries,
  providers,
  tags,
  hasActiveFilters,
  onSearchQueryChange,
  onCountryFilterChange,
  onProviderFilterChange,
  onTagFilterChange,
  onClearFilters,
}: {
  searchQuery: string;
  countryFilter: string;
  providerFilter: string;
  tagFilter: string;
  countries: string[];
  providers: string[];
  tags: string[];
  hasActiveFilters: boolean;
  onSearchQueryChange: (value: string) => void;
  onCountryFilterChange: (value: string) => void;
  onProviderFilterChange: (value: string) => void;
  onTagFilterChange: (value: string) => void;
  onClearFilters: () => void;
}) {
  return (
    <div className="grid gap-2 border-b border-slate-200 bg-white px-3 py-3 lg:grid-cols-[minmax(220px,1fr)_repeat(3,minmax(140px,180px))_auto] lg:items-end">
      <label className="min-w-0">
        <span className="label">Search</span>
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            aria-label="Search proxy assets"
            className="input pl-9"
            value={searchQuery}
            onChange={(event) => onSearchQueryChange(event.target.value)}
            placeholder="Name, endpoint, provider, country, tag"
          />
        </div>
      </label>
      <FilterSelect
        label="Country"
        ariaLabel="Country filter"
        value={countryFilter}
        options={countries}
        onChange={onCountryFilterChange}
      />
      <FilterSelect
        label="Provider"
        ariaLabel="Provider filter"
        value={providerFilter}
        options={providers}
        onChange={onProviderFilterChange}
      />
      <FilterSelect
        label="Tag"
        ariaLabel="Tag filter"
        value={tagFilter}
        options={tags}
        onChange={onTagFilterChange}
      />
      <button
        type="button"
        className="btn-secondary inline-flex h-9 items-center justify-center gap-1.5 whitespace-nowrap text-xs"
        onClick={onClearFilters}
        disabled={!hasActiveFilters}
        aria-label="Clear visible proxy filters"
      >
        <X className="h-3.5 w-3.5" />
        Clear
      </button>
    </div>
  );
}

function FilterSelect({
  label,
  ariaLabel,
  value,
  options,
  onChange,
}: {
  label: string;
  ariaLabel: string;
  value: string;
  options: string[];
  onChange: (value: string) => void;
}) {
  return (
    <label className="min-w-0">
      <span className="label">{label}</span>
      <select
        aria-label={ariaLabel}
        className="input"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value={FILTER_ALL}>All</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  );
}

function ProxyAssignDialog({
  proxy,
  profiles,
  totalProfileCount,
  searchQuery,
  selectedProfileIds,
  allVisibleSelected,
  assigning,
  error,
  onSearchQueryChange,
  onToggleProfile,
  onToggleVisible,
  onAssign,
  onClose,
}: {
  proxy: ProxyAsset;
  profiles: Profile[];
  totalProfileCount: number;
  searchQuery: string;
  selectedProfileIds: Set<string>;
  allVisibleSelected: boolean;
  assigning: boolean;
  error: string | null;
  onSearchQueryChange: (value: string) => void;
  onToggleProfile: (profileId: string) => void;
  onToggleVisible: () => void;
  onAssign: () => void;
  onClose: () => void;
}) {
  const safeProxyUrl = redactUrlCredentials(proxy.url);
  const selectedCount = selectedProfileIds.size;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/35 p-3 backdrop-blur-sm">
      <div
        role="dialog"
        aria-label="Assign proxy to profiles"
        aria-modal="true"
        className="flex max-h-[calc(100vh-24px)] w-[min(760px,calc(100vw-24px))] min-w-0 flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-[0_24px_80px_rgba(15,23,42,0.22),inset_0_1px_0_rgba(255,255,255,0.9)]"
      >
        <div className="flex items-start justify-between gap-3 border-b border-slate-200 bg-[#fbfdff] px-4 py-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-[8px] border border-blue-100 bg-blue-50 text-blue-700">
                <UserPlus className="h-4 w-4" />
              </span>
              <div className="min-w-0">
                <h3 className="text-sm font-semibold text-slate-950">Assign proxy to profiles</h3>
                <p className="mt-0.5 text-xs text-slate-500">
                  Choose profiles that should receive this proxy asset.
                </p>
              </div>
            </div>
          </div>
          <button
            type="button"
            className="icon-action h-7 w-7"
            onClick={onClose}
            disabled={assigning}
            aria-label="Close assign proxy dialog"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="border-b border-slate-200 bg-white px-4 py-3">
          <div className="grid gap-2 rounded-lg border border-slate-200 bg-slate-50/80 p-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
            <div className="min-w-0">
              <div className="truncate text-sm font-semibold text-slate-950" title={proxy.name}>
                {proxy.name}
              </div>
              <div className="mt-1 truncate font-mono text-[11px] text-slate-500" title={safeProxyUrl}>
                {safeProxyUrl}
              </div>
            </div>
            <span className="rounded-[999px] border border-blue-200 bg-blue-50 px-2 py-1 text-[11px] font-medium text-blue-700">
              {selectedCount} profiles selected
            </span>
          </div>
        </div>

        <div className="grid gap-2 border-b border-slate-200 px-4 py-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end">
          <label className="min-w-0">
            <span className="label">Search</span>
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                aria-label="Search profiles for assignment"
                className="input pl-9"
                value={searchQuery}
                onChange={(event) => onSearchQueryChange(event.target.value)}
                placeholder="Name, id, runtime, current proxy"
              />
            </div>
          </label>
          <label className="choice-card h-9 items-center px-2.5 py-2 text-xs">
            <input
              type="checkbox"
              className="choice-checkbox m-0"
              checked={allVisibleSelected}
              onChange={onToggleVisible}
              disabled={profiles.length === 0}
              aria-label="Select all visible assignment profiles"
            />
            Select visible
          </label>
        </div>

        {error && (
          <div className="border-b border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700" role="alert">
            {error}
          </div>
        )}

        <div className="min-h-[220px] flex-1 overflow-auto bg-white p-2">
          {profiles.length === 0 ? (
            <div
              role="status"
              aria-label={totalProfileCount === 0 ? "No profiles available for assignment" : "No assignment profiles match search"}
              className="flex min-h-[180px] items-center justify-center rounded-lg border border-dashed border-slate-300 bg-slate-50/70 p-6 text-center text-sm text-slate-500"
            >
              {totalProfileCount === 0
                ? "No profiles are available yet."
                : "No profiles match this assignment search."}
            </div>
          ) : (
            <div role="list" aria-label="Assignment profiles" className="grid gap-1.5">
              {profiles.map((profile) => (
                <AssignmentProfileRow
                  key={profile.id}
                  profile={profile}
                  checked={selectedProfileIds.has(profile.id)}
                  onToggle={() => onToggleProfile(profile.id)}
                />
              ))}
            </div>
          )}
        </div>

        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-200 bg-[#fbfdff] px-4 py-3">
          <div className="text-xs text-slate-500">
            Assignment writes through the Proxy Manager API and stores the raw endpoint server-side only.
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="btn-secondary h-8 text-xs"
              onClick={onClose}
              disabled={assigning}
            >
              Cancel
            </button>
            <button
              type="button"
              className="btn-primary inline-flex h-8 items-center gap-1.5 text-xs"
              onClick={onAssign}
              disabled={selectedCount === 0 || assigning}
            >
              <UserPlus className="h-3.5 w-3.5" />
              {assigning ? "Assigning" : "Assign proxy"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function AssignmentProfileRow({
  profile,
  checked,
  onToggle,
}: {
  profile: Profile;
  checked: boolean;
  onToggle: () => void;
}) {
  const safeProxy = profile.proxy ? redactUrlCredentials(profile.proxy) : "No proxy";

  return (
    <label className="choice-card items-center gap-2 px-3 py-2">
      <input
        type="checkbox"
        className="choice-checkbox m-0"
        checked={checked}
        onChange={onToggle}
        aria-label={`Assign ${profile.name}`}
      />
      <span className="min-w-0 flex-1">
        <span className="flex min-w-0 items-center gap-2">
          <span className="truncate text-sm font-semibold text-slate-900" title={profile.name}>
            {profile.name}
          </span>
          <span className={`rounded-[999px] border px-1.5 py-0.5 text-[10px] font-medium ${
            profile.status === "running"
              ? "border-emerald-200 bg-emerald-50 text-emerald-700"
              : "border-slate-200 bg-slate-50 text-slate-500"
          }`}>
            {profile.status}
          </span>
        </span>
        <span className="mt-1 grid min-w-0 gap-1 text-[11px] text-slate-500 sm:grid-cols-[120px_minmax(0,1fr)]">
          <span className="truncate font-mono" title={profile.id}>{profile.id}</span>
          <span className="truncate font-mono" title={safeProxy}>{safeProxy}</span>
        </span>
      </span>
    </label>
  );
}

function ProxyRow({
  proxy,
  selected,
  onToggleSelection,
}: {
  proxy: ProxyAsset;
  selected: boolean;
  onToggleSelection: (proxyId: string) => void;
}) {
  const safeUrl = redactUrlCredentials(proxy.url);
  const safeCheckError = proxy.last_check_error
    ? redactUrlCredentials(proxy.last_check_error)
    : null;
  const safeNotes = proxy.notes ? redactUrlCredentials(proxy.notes) : null;
  const location = [proxy.country_code, proxy.city].filter(Boolean).join(" · ") || "-";
  const checkLocation = [
    proxy.last_check_ip,
    proxy.last_check_country_code,
  ].filter(Boolean).join(" · ");

  return (
    <tr className="group shadow-[inset_0_-1px_0_rgba(226,232,240,0.8)] transition-colors hover:bg-blue-50/30">
      <td className="px-3 py-3 align-top">
        <label className="flex h-5 w-5 items-center justify-center">
          <input
            type="checkbox"
            className="choice-checkbox m-0"
            checked={selected}
            onChange={() => onToggleSelection(proxy.id)}
            aria-label={`Select ${proxy.name}`}
          />
        </label>
      </td>
      <td className="px-3 py-3 align-top">
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold text-slate-950" title={proxy.name}>
            {proxy.name}
          </div>
          <div className="mt-1 truncate font-mono text-[11px] text-slate-500" title={safeUrl}>
            {safeUrl}
          </div>
        </div>
      </td>
      <td className="px-3 py-3 align-top">
        <div className="flex items-center gap-1.5 text-sm font-medium text-slate-700">
          <Globe2 className="h-3.5 w-3.5 shrink-0 text-slate-400" />
          <span className="truncate" title={location}>{location}</span>
        </div>
        {proxy.asn && (
          <div className="mt-1 truncate font-mono text-[11px] text-slate-400" title={proxy.asn}>
            {proxy.asn}
          </div>
        )}
      </td>
      <td className="px-3 py-3 align-top">
        <span className="truncate text-sm font-medium text-slate-700" title={proxy.provider ?? "-"}>
          {proxy.provider ?? "-"}
        </span>
        {safeNotes && (
          <p className="mt-1 line-clamp-1 text-[11px] text-slate-400" title={safeNotes}>
            {safeNotes}
          </p>
        )}
      </td>
      <td className="px-3 py-3 align-top">
        <ProxyStatusBadge status={proxy.last_check_status} />
        {safeCheckError && (
          <div className="mt-1 truncate text-[11px] text-red-600" title={safeCheckError}>
            {safeCheckError}
          </div>
        )}
      </td>
      <td className="px-3 py-3 align-top">
        <div className="truncate font-mono text-[11px] text-slate-600" title={checkLocation || "-"}>
          {checkLocation || "-"}
        </div>
        <div className="mt-1 text-[11px] text-slate-400">
          {formatTimestamp(proxy.last_check_at)}
        </div>
      </td>
      <td className="px-3 py-3 align-top">
        {proxy.tags.length > 0 ? (
          <div className="flex max-w-full flex-wrap gap-1">
            {proxy.tags.slice(0, 3).map((tag) => (
              <span
                key={`${proxy.id}-${tag.tag}`}
                className="token-chip max-w-[128px] truncate"
                title={tag.tag}
              >
                <span
                  className="h-1.5 w-1.5 shrink-0 rounded-full"
                  style={{ backgroundColor: tag.color ?? "#94a3b8" }}
                />
                {tag.tag}
              </span>
            ))}
          </div>
        ) : (
          <span className="text-slate-400">-</span>
        )}
      </td>
    </tr>
  );
}

function ProxyStatusBadge({ status }: { status: string | null }) {
  const tone = getProxyStatusTone(status);
  const label = status ? statusLabel(status) : "Unchecked";
  const className = {
    good: "border-emerald-200 bg-emerald-50 text-emerald-700",
    warning: "border-amber-200 bg-amber-50 text-amber-800",
    error: "border-red-200 bg-red-50 text-red-700",
    unknown: "border-slate-200 bg-slate-50 text-slate-600",
  }[tone];
  const dotClassName = {
    good: "bg-emerald-500",
    warning: "bg-amber-500",
    error: "bg-red-500",
    unknown: "bg-slate-400",
  }[tone];

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-md border px-1.5 py-0.5 text-[11px] font-medium leading-4 ${className}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${dotClassName}`} />
      {label}
    </span>
  );
}

function ProxyEmptyState() {
  return (
    <div
      role="status"
      aria-label="No proxy assets yet"
      className="flex min-h-[320px] flex-1 items-center justify-center p-6"
    >
      <div className="mx-auto max-w-[420px] rounded-lg border border-dashed border-slate-300 bg-slate-50/70 px-6 py-8 text-center shadow-[inset_0_1px_0_rgba(255,255,255,0.9)]">
        <span className="mx-auto mb-3 inline-flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-500 shadow-hairline">
          <Database className="h-4 w-4" />
        </span>
        <h3 className="text-sm font-semibold text-slate-950">No proxy assets yet</h3>
        <p className="mt-2 text-xs leading-5 text-slate-500">
          Proxy assets created through the API will appear here.
        </p>
      </div>
    </div>
  );
}

function ProxyFilterEmptyState({ onClear }: { onClear: () => void }) {
  return (
    <div
      role="status"
      aria-label="No proxy assets match filters"
      className="flex min-h-[320px] flex-1 items-center justify-center p-6"
    >
      <div className="mx-auto max-w-[440px] rounded-lg border border-dashed border-blue-200 bg-blue-50/60 px-6 py-8 text-center shadow-[inset_0_1px_0_rgba(255,255,255,0.9)]">
        <span className="mx-auto mb-3 inline-flex h-9 w-9 items-center justify-center rounded-lg border border-blue-100 bg-white text-blue-600 shadow-hairline">
          <Search className="h-4 w-4" />
        </span>
        <h3 className="text-sm font-semibold text-slate-950">No proxy assets match filters</h3>
        <p className="mt-2 text-xs leading-5 text-slate-500">
          Clear the current filters to return to the full proxy inventory.
        </p>
        <button
          type="button"
          className="btn-secondary mt-4 inline-flex h-8 items-center gap-1.5 text-xs"
          onClick={onClear}
          aria-label="Clear proxy filters"
        >
          <X className="h-3.5 w-3.5" />
          Clear filters
        </button>
      </div>
    </div>
  );
}

function HeaderCell({ children, className = "" }: { children: string; className?: string }) {
  return (
    <th className={`px-3 py-2 text-[10px] font-semibold uppercase tracking-[0.12em] ${className}`}>
      {children}
    </th>
  );
}

function ProxySummaryTile({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: number;
  tone?: "neutral" | "success" | "warning";
}) {
  const toneClassName = {
    neutral: "border-slate-200 bg-white text-slate-700 before:bg-slate-300",
    success: "border-emerald-200 bg-emerald-50/80 text-emerald-700 before:bg-emerald-500",
    warning: "border-amber-200 bg-amber-50/80 text-amber-800 before:bg-amber-500",
  }[tone];

  return (
    <div className={`relative min-w-[92px] overflow-hidden rounded-lg border px-3 py-2 shadow-[0_1px_2px_rgba(15,23,42,0.04),inset_0_1px_0_rgba(255,255,255,0.8)] before:absolute before:inset-x-0 before:top-0 before:h-0.5 ${toneClassName}`}>
      <div className="text-lg font-semibold leading-5 tabular-nums">{value}</div>
      <div className="mt-1 text-[10px] font-semibold uppercase tracking-[0.1em] opacity-75">
        {label}
      </div>
    </div>
  );
}

function getProxyStatusTone(status: string | null): ProxyStatusTone {
  if (status === "good") return "good";
  if (status === "error" || status === "failed") return "error";
  if (status === "warning") return "warning";
  return "unknown";
}

function statusLabel(status: string): string {
  return status.replace(/_/g, " ");
}

function uniqueSorted(values: Array<string | null | undefined>): string[] {
  return Array.from(new Set(values.map((value) => value?.trim()).filter(Boolean) as string[]))
    .sort((a, b) => a.localeCompare(b));
}

function matchesOptionFilter(value: string | null | undefined, filter: string): boolean {
  if (filter === FILTER_ALL) return true;
  return (value?.trim() ?? "") === filter;
}

function normalizeFilterValue(value: string | null | undefined): string {
  return value?.trim().toLowerCase() ?? "";
}

function getProxySearchText(proxy: ProxyAsset): string {
  return [
    proxy.name,
    redactUrlCredentials(proxy.url),
    proxy.country_code,
    proxy.city,
    proxy.asn,
    proxy.provider,
    proxy.notes ? redactUrlCredentials(proxy.notes) : null,
    proxy.last_check_status,
    proxy.last_check_ip,
    proxy.last_check_country_code,
    proxy.last_check_timezone,
    proxy.last_check_locale,
    proxy.last_check_source,
    proxy.last_check_error ? redactUrlCredentials(proxy.last_check_error) : null,
    ...proxy.tags.map((tag) => tag.tag),
  ]
    .map(normalizeFilterValue)
    .filter(Boolean)
    .join(" ");
}

function getAssignmentProfileSearchText(profile: Profile): string {
  return [
    profile.id,
    profile.name,
    profile.status,
    profile.proxy ? redactUrlCredentials(profile.proxy) : "no proxy",
  ]
    .map(normalizeFilterValue)
    .filter(Boolean)
    .join(" ");
}
