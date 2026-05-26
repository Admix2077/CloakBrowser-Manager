import { AlertCircle, CheckCircle2, Database, FileSpreadsheet, Globe2, Network, RefreshCw, Search, Upload, UserPlus, X } from "lucide-react";
import { useCallback, useDeferredValue, useEffect, useMemo, useState } from "react";
import { api, type Profile, type ProxyAsset, type ProxyCreateData, type ProxyProviderPreset } from "../lib/api";
import { formatTimestamp, redactUrlCredentials } from "../lib/profileDisplay";

type ProxyStatusTone = "good" | "warning" | "error" | "unknown";
const FILTER_ALL = "__all_proxy_filter__";
const CSV_SAMPLE = "name,url,country_code,city,asn,provider,tags,notes";

interface ProxyManagerPageProps {
  profiles?: Profile[];
  onProfilesAssigned?: () => Promise<unknown> | unknown;
}

interface ProxyCsvImportRow {
  rowNumber: number;
  data: ProxyCreateData;
  issues: string[];
}

interface ProxyCsvImportPreview {
  rows: ProxyCsvImportRow[];
  parseError: string | null;
}

interface ProxyCsvImportFailure {
  rowNumber: number;
  message: string;
}

export function ProxyManagerPage({
  profiles = [],
  onProfilesAssigned,
}: ProxyManagerPageProps = {}) {
  const [proxies, setProxies] = useState<ProxyAsset[]>([]);
  const [providerPresets, setProviderPresets] = useState<ProxyProviderPreset[]>([]);
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
  const [importDialogOpen, setImportDialogOpen] = useState(false);
  const [importText, setImportText] = useState("");
  const [importSourceText, setImportSourceText] = useState("");
  const [selectedImportPresetId, setSelectedImportPresetId] = useState("");
  const [importing, setImporting] = useState(false);
  const [importNotice, setImportNotice] = useState<string | null>(null);
  const [importError, setImportError] = useState<string | null>(null);
  const [importFailures, setImportFailures] = useState<ProxyCsvImportFailure[]>([]);
  const [recentlyImportedProxyIds, setRecentlyImportedProxyIds] = useState<Set<string>>(() => new Set());
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

  useEffect(() => {
    let active = true;

    api.listProxyProviderPresets()
      .then((presets) => {
        if (active) setProviderPresets(presets);
      })
      .catch(() => {
        if (active) setProviderPresets([]);
      });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (recentlyImportedProxyIds.size === 0) return;

    const timer = window.setTimeout(() => {
      setRecentlyImportedProxyIds(new Set());
    }, 1600);

    return () => window.clearTimeout(timer);
  }, [recentlyImportedProxyIds]);

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

  const selectedImportPreset = useMemo(
    () => providerPresets.find((preset) => preset.id === selectedImportPresetId) ?? null,
    [providerPresets, selectedImportPresetId],
  );
  const importPreview = useMemo(
    () => parseProxyCsvImport(importSourceText, selectedImportPreset),
    [importSourceText, selectedImportPreset],
  );
  const validImportRows = useMemo(
    () => importPreview.rows.filter((row) => row.issues.length === 0),
    [importPreview.rows],
  );
  const blockedImportCount = importPreview.rows.length - validImportRows.length;

  const openImportDialog = useCallback(() => {
    setImportText("");
    setImportSourceText("");
    setSelectedImportPresetId("");
    setImportNotice(null);
    setImportError(null);
    setImportFailures([]);
    setImportDialogOpen(true);
  }, []);

  const closeImportDialog = useCallback(() => {
    if (importing) return;
    setImportDialogOpen(false);
    setImportError(null);
  }, [importing]);

  const importValidCsvRows = useCallback(async () => {
    if (importing) return;

    if (importPreview.parseError) {
      setImportError(importPreview.parseError);
      setImportFailures([]);
      return;
    }

    const invalidFailures = importPreview.rows
      .filter((row) => row.issues.length > 0)
      .map((row) => ({
        rowNumber: row.rowNumber,
        message: row.issues.join(", "),
      }));

    if (validImportRows.length === 0) {
      setImportError("No valid proxy rows to import");
      setImportFailures(invalidFailures);
      return;
    }

    setImporting(true);
    setImportError(null);
    setImportNotice(null);
    setImportFailures([]);

    let createdCount = 0;
    const failures: ProxyCsvImportFailure[] = [...invalidFailures];
    const createdIds: string[] = [];

    for (const row of validImportRows) {
      try {
        const createdProxy = await api.createProxy(row.data);
        createdCount += 1;
        createdIds.push(createdProxy.id);
      } catch (err) {
        const message = err instanceof Error ? err.message : "Unable to create proxy asset";
        failures.push({
          rowNumber: row.rowNumber,
          message: redactUrlCredentials(message),
        });
      }
    }

    const notice = `Imported ${createdCount} proxy asset(s), ${failures.length} failed`;
    setImportNotice(notice);
    setImportFailures(failures.sort((a, b) => a.rowNumber - b.rowNumber));

    if (createdCount > 0) {
      setRecentlyImportedProxyIds(new Set(createdIds));
      await loadProxies();
    }

    setImporting(false);
  }, [importPreview, importing, loadProxies, validImportRows]);

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
                Proxy inventory with credential-redacted checks and profile assignment controls.
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
              URL credentials are hidden in the UI. Bulk check, profile assignment, and CSV import are active; add, edit, and delete remain disabled.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              className="btn-secondary inline-flex h-8 items-center gap-1.5 text-xs"
              onClick={openImportDialog}
              disabled={importing}
              aria-label="Import CSV"
            >
              <FileSpreadsheet className="h-3.5 w-3.5" />
              Import CSV
            </button>
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
          <div className="animate-notice-in border-b border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-700" role="status">
            {assignNotice}
          </div>
        )}

        {importNotice && (
          <div className="animate-notice-in border-b border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-700" role="status">
            {importNotice}
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
                    highlighted={recentlyImportedProxyIds.has(proxy.id)}
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
      {importDialogOpen && (
        <ProxyCsvImportDialog
          text={importText}
          preview={importPreview}
          providerPresets={providerPresets}
          selectedPresetId={selectedImportPresetId}
          validCount={validImportRows.length}
          blockedCount={blockedImportCount}
          importing={importing}
          notice={importNotice}
          error={importError}
          failures={importFailures}
          onTextChange={(value) => {
            setImportSourceText(value);
            setImportText(redactUrlCredentials(value));
            setImportError(null);
            setImportFailures([]);
            setImportNotice(null);
          }}
          onPresetChange={(presetId) => {
            setSelectedImportPresetId(presetId);
            setImportError(null);
            setImportFailures([]);
            setImportNotice(null);
          }}
          onImport={() => void importValidCsvRows()}
          onClose={closeImportDialog}
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

function ProxyCsvImportDialog({
  text,
  preview,
  providerPresets,
  selectedPresetId,
  validCount,
  blockedCount,
  importing,
  notice,
  error,
  failures,
  onTextChange,
  onPresetChange,
  onImport,
  onClose,
}: {
  text: string;
  preview: ProxyCsvImportPreview;
  providerPresets: ProxyProviderPreset[];
  selectedPresetId: string;
  validCount: number;
  blockedCount: number;
  importing: boolean;
  notice: string | null;
  error: string | null;
  failures: ProxyCsvImportFailure[];
  onTextChange: (value: string) => void;
  onPresetChange: (presetId: string) => void;
  onImport: () => void;
  onClose: () => void;
}) {
  const previewRows = preview.rows.slice(0, 60);
  const canImport = validCount > 0 && !preview.parseError && !importing;
  const selectedPreset = providerPresets.find((preset) => preset.id === selectedPresetId) ?? null;
  const selectedPresetSummary = selectedPreset
    ? [
        selectedPreset.provider,
        selectedPreset.country_code,
        selectedPreset.tags.map((tag) => tag.tag).join(", "),
      ].filter(Boolean).join(" · ")
    : null;

  return (
    <div className="animate-dialog-backdrop fixed inset-0 z-50 flex items-center justify-center bg-slate-950/35 p-3 backdrop-blur-sm">
      <div
        role="dialog"
        aria-label="Import proxy CSV"
        aria-modal="true"
        className="animate-dialog-in flex max-h-[calc(100vh-24px)] w-[min(880px,calc(100vw-24px))] min-w-0 flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-[0_24px_80px_rgba(15,23,42,0.22),inset_0_1px_0_rgba(255,255,255,0.9)]"
      >
        <div className="flex items-start justify-between gap-3 border-b border-slate-200 bg-[#fbfdff] px-4 py-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-[8px] border border-blue-100 bg-blue-50 text-blue-700">
                <FileSpreadsheet className="h-4 w-4" />
              </span>
              <div className="min-w-0">
                <h3 className="text-sm font-semibold text-slate-950">Import proxy CSV</h3>
                <p className="mt-0.5 text-xs text-slate-500">
                  Paste rows, preview validation, then create valid proxy assets through the existing API.
                </p>
              </div>
            </div>
          </div>
          <button
            type="button"
            className="icon-action h-7 w-7"
            onClick={onClose}
            disabled={importing}
            aria-label="Close import proxy CSV dialog"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="grid gap-3 border-b border-slate-200 bg-white px-4 py-3 lg:grid-cols-[minmax(0,1fr)_220px]">
          <label className="min-w-0">
            <span className="label">CSV content</span>
            <textarea
              aria-label="Proxy CSV content"
              className="input min-h-[152px] resize-y font-mono text-xs leading-5"
              value={text}
              onChange={(event) => onTextChange(event.target.value)}
              placeholder={`${CSV_SAMPLE}\nUS Pool,http://proxy.example:8080,US,Los Angeles,AS12345,ProxyCo,stable|primary,Primary pool`}
              spellCheck={false}
            />
          </label>
          <div className="grid content-start gap-2">
            <label className="min-w-0">
              <span className="label">Provider preset</span>
              <select
                aria-label="Provider preset"
                className="input"
                value={selectedPresetId}
                onChange={(event) => onPresetChange(event.target.value)}
                disabled={providerPresets.length === 0 || importing}
              >
                <option value="">No preset</option>
                {providerPresets.map((preset) => (
                  <option key={preset.id} value={preset.id}>
                    {preset.name}
                  </option>
                ))}
              </select>
              {selectedPresetSummary && (
                <p className="mt-1 truncate text-xs text-slate-500" title={selectedPresetSummary}>
                  {selectedPresetSummary}
                </p>
              )}
            </label>
            <div className="rounded-lg border border-slate-200 bg-slate-50/80 p-3">
              <div className="text-[11px] font-semibold uppercase tracking-[0.1em] text-slate-500">
                Supported fields
              </div>
              <p className="mt-2 break-words font-mono text-[11px] leading-5 text-slate-600">
                {CSV_SAMPLE}
              </p>
              <p className="mt-2 text-xs leading-5 text-slate-500">
                Tags split by comma, semicolon, or pipe. Name and URL are required.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <ImportCountPill label="ready" value={validCount} tone="success" />
              <ImportCountPill label="blocked" value={blockedCount} tone={blockedCount > 0 ? "warning" : "neutral"} />
            </div>
          </div>
        </div>

        {(preview.parseError || error) && (
          <div className="animate-notice-in border-b border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700" role="alert">
            {preview.parseError ?? error}
          </div>
        )}

        {notice && (
          <div className="animate-notice-in border-b border-emerald-200 bg-emerald-50 px-4 py-2 text-sm font-medium text-emerald-700" role="status">
            {notice}
          </div>
        )}

        {failures.length > 0 && (
          <div className="animate-notice-in border-b border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-900" role="alert">
            <div className="font-semibold">Import issues</div>
            <ul className="mt-1 grid gap-1">
              {failures.slice(0, 8).map((failure) => (
                <li key={`${failure.rowNumber}-${failure.message}`}>
                  Row {failure.rowNumber}: {failure.message}
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="min-h-[240px] flex-1 overflow-auto bg-white p-2">
          {previewRows.length === 0 ? (
            <div
              role="status"
              aria-label="No CSV rows ready for preview"
              className="flex min-h-[220px] items-center justify-center rounded-lg border border-dashed border-slate-300 bg-slate-50/70 p-6 text-center text-sm text-slate-500"
            >
              Paste a CSV header and rows to preview proxy assets before import.
            </div>
          ) : (
            <div className="overflow-auto rounded-lg border border-slate-200">
              <table
                aria-label="Proxy CSV preview"
                className="min-w-[760px] w-full table-fixed border-separate border-spacing-0 bg-white text-left text-xs text-slate-700"
              >
                <thead className="sticky top-0 z-10 bg-[#fbfdff]">
                  <tr className="text-slate-500 shadow-[inset_0_-1px_0_rgba(148,163,184,0.24)]">
                    <HeaderCell className="w-[86px]">Row</HeaderCell>
                    <HeaderCell className="w-[180px]">Name</HeaderCell>
                    <HeaderCell className="w-[240px]">Endpoint</HeaderCell>
                    <HeaderCell className="w-[130px]">Provider</HeaderCell>
                    <HeaderCell className="w-[130px]">Tags</HeaderCell>
                    <HeaderCell className="w-[150px]">Status</HeaderCell>
                  </tr>
                </thead>
                <tbody>
                  {previewRows.map((row) => (
                    <ProxyCsvPreviewRow key={`${row.rowNumber}-${row.data.name}-${row.data.url}`} row={row} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-200 bg-[#fbfdff] px-4 py-3">
          <div className="text-xs text-slate-500">
            Import creates valid rows only. Invalid rows stay visible and are not submitted.
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="btn-secondary h-8 text-xs"
              onClick={onClose}
              disabled={importing}
            >
              Done
            </button>
            <button
              type="button"
              className="btn-primary inline-flex h-8 min-w-[132px] items-center justify-center gap-1.5 text-xs"
              onClick={onImport}
              disabled={!canImport}
            >
              {importing ? (
                <RefreshCw className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Upload className="h-3.5 w-3.5" />
              )}
              {importing ? "Importing" : "Import valid rows"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function ImportCountPill({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: "neutral" | "success" | "warning";
}) {
  const className = {
    neutral: "border-slate-200 bg-white text-slate-600",
    success: "border-emerald-200 bg-emerald-50 text-emerald-700",
    warning: "border-amber-200 bg-amber-50 text-amber-800",
  }[tone];

  return (
    <span className={`inline-flex items-center justify-center rounded-md border px-2.5 py-1.5 text-xs font-semibold ${className}`}>
      {value} {label}
    </span>
  );
}

function ProxyCsvPreviewRow({ row }: { row: ProxyCsvImportRow }) {
  const hasIssues = row.issues.length > 0;
  const safeUrl = row.data.url ? redactUrlCredentials(row.data.url) : "-";
  const tags = row.data.tags?.map((tag) => tag.tag).join(", ") || "-";

  return (
    <tr className={`shadow-[inset_0_-1px_0_rgba(226,232,240,0.8)] transition-colors ${
      hasIssues ? "bg-amber-50/40" : "hover:bg-blue-50/30"
    }`}>
      <td className="px-3 py-2 align-top font-mono text-[11px] text-slate-500">
        Row {row.rowNumber}
      </td>
      <td className="px-3 py-2 align-top">
        <span className="block truncate text-sm font-semibold text-slate-900" title={row.data.name || "-"}>
          {row.data.name || "-"}
        </span>
      </td>
      <td className="px-3 py-2 align-top">
        <span className="block truncate font-mono text-[11px] text-slate-600" title={safeUrl}>
          {safeUrl}
        </span>
      </td>
      <td className="px-3 py-2 align-top">
        <span className="block truncate text-sm text-slate-700" title={row.data.provider ?? "-"}>
          {row.data.provider ?? "-"}
        </span>
      </td>
      <td className="px-3 py-2 align-top">
        <span className="block truncate text-xs text-slate-500" title={tags}>
          {tags}
        </span>
      </td>
      <td className="px-3 py-2 align-top">
        {hasIssues ? (
          <span className="inline-flex items-center gap-1 rounded-md border border-amber-200 bg-amber-50 px-1.5 py-0.5 text-[11px] font-medium text-amber-800">
            <AlertCircle className="h-3 w-3" />
            {row.issues.join(", ")}
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 rounded-md border border-emerald-200 bg-emerald-50 px-1.5 py-0.5 text-[11px] font-medium text-emerald-700">
            <CheckCircle2 className="h-3 w-3" />
            Ready
          </span>
        )}
      </td>
    </tr>
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
  highlighted,
  onToggleSelection,
}: {
  proxy: ProxyAsset;
  selected: boolean;
  highlighted: boolean;
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
    <tr className={`group shadow-[inset_0_-1px_0_rgba(226,232,240,0.8)] transition-colors hover:bg-blue-50/30 ${
      highlighted ? "animate-proxy-row-enter bg-emerald-50/40" : ""
    }`}>
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

function parseProxyCsvImport(text: string, preset: ProxyProviderPreset | null = null): ProxyCsvImportPreview {
  if (!text.trim()) {
    return { rows: [], parseError: null };
  }

  let records: string[][];
  try {
    records = parseCsvRecords(text);
  } catch (err) {
    return {
      rows: [],
      parseError: err instanceof Error ? err.message : "Unable to parse CSV",
    };
  }

  const nonEmptyRecords = records
    .map((cells, index) => ({ cells, rowNumber: index + 1 }))
    .filter((record) => record.cells.some((cell) => cell.trim()));

  if (nonEmptyRecords.length === 0) {
    return { rows: [], parseError: null };
  }

  const headerRecord = nonEmptyRecords[0];
  if (!headerRecord) {
    return { rows: [], parseError: null };
  }

  const headers = headerRecord.cells.map(normalizeCsvHeader);
  const missingHeaders = ["name", "url"].filter((header) => !headers.includes(header));

  if (missingHeaders.length > 0) {
    return {
      rows: [],
      parseError: `CSV header must include ${missingHeaders.join(" and ")}`,
    };
  }

  const rows = nonEmptyRecords.slice(1).map((record) => {
    const getField = (field: string) => {
      const index = headers.indexOf(field);
      return index >= 0 ? (record.cells[index] ?? "").trim() : "";
    };

    const name = getField("name");
    const url = getField("url");
    const countryCode = getField("country_code") || preset?.country_code || "";
    const city = getField("city");
    const asn = getField("asn");
    const provider = getField("provider") || preset?.provider || "";
    const notes = getField("notes") || preset?.notes || "";
    const tags = mergeTags(preset?.tags ?? [], parseCsvTags(getField("tags")));

    const issues: string[] = [];
    if (!name) issues.push("Missing name");
    if (!url) issues.push("Missing url");

    const data: ProxyCreateData = {
      name,
      url,
      ...(countryCode ? { country_code: countryCode } : {}),
      ...(city ? { city } : {}),
      ...(asn ? { asn } : {}),
      ...(provider ? { provider } : {}),
      ...(tags.length > 0 ? { tags } : {}),
      ...(notes ? { notes } : {}),
    };

    return {
      rowNumber: record.rowNumber,
      data,
      issues,
    };
  });

  return { rows, parseError: null };
}

function parseCsvRecords(text: string): string[][] {
  const records: string[][] = [];
  let record: string[] = [];
  let field = "";
  let inQuotes = false;

  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];

    if (inQuotes) {
      if (char === "\"") {
        if (text[index + 1] === "\"") {
          field += "\"";
          index += 1;
        } else {
          inQuotes = false;
        }
      } else {
        field += char;
      }
      continue;
    }

    if (char === "\"") {
      inQuotes = true;
      continue;
    }

    if (char === ",") {
      record.push(field);
      field = "";
      continue;
    }

    if (char === "\n") {
      record.push(field);
      records.push(record);
      record = [];
      field = "";
      continue;
    }

    if (char !== "\r") {
      field += char;
    }
  }

  if (inQuotes) {
    throw new Error("CSV has an unclosed quoted field");
  }

  record.push(field);
  records.push(record);
  return records;
}

function normalizeCsvHeader(header: string): string {
  const normalized = header.trim().toLowerCase().replace(/[\s-]+/g, "_");
  if (normalized === "endpoint" || normalized === "proxy" || normalized === "proxy_url") return "url";
  if (normalized === "country") return "country_code";
  return normalized;
}

function parseCsvTags(value: string): { tag: string; color: string | null }[] {
  return value
    .split(/[|;,]/)
    .map((tag) => tag.trim())
    .filter(Boolean)
    .map((tag) => ({ tag, color: null }));
}

function mergeTags(
  presetTags: { tag: string; color: string | null }[],
  rowTags: { tag: string; color: string | null }[],
): { tag: string; color: string | null }[] {
  const seen = new Set<string>();
  const merged: { tag: string; color: string | null }[] = [];

  for (const tag of [...presetTags, ...rowTags]) {
    const key = normalizeFilterValue(tag.tag);
    if (!key || seen.has(key)) continue;
    seen.add(key);
    merged.push(tag);
  }

  return merged;
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
