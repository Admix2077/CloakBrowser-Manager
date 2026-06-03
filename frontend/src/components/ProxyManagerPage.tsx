import { AlertCircle, CheckCircle2, Database, FileSpreadsheet, Globe2, Network, Pencil, RefreshCw, Search, Settings2, Shuffle, Trash2, Upload, UserPlus, X } from "lucide-react";
import { useCallback, useDeferredValue, useEffect, useMemo, useState } from "react";
import { api, type Profile, type ProxyAsset, type ProxyCreateData, type ProxyProviderPreset, type ProxyProviderPresetCreateData, type ProxyRandomAssignRequestData } from "../lib/api";
import { publicErrorMessage, publicErrorText } from "../lib/errorDisplay";
import { formatTimestamp, publicRuntimeStatus, redactUrlCredentials } from "../lib/profileDisplay";

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

interface ProviderPresetFormState {
  name: string;
  provider: string;
  country_code: string;
  tags: string;
  notes: string;
}

export function ProxyManagerPage({
  profiles = [],
  onProfilesAssigned,
}: ProxyManagerPageProps = {}) {
  const [proxies, setProxies] = useState<ProxyAsset[]>([]);
  const [providerPresets, setProviderPresets] = useState<ProxyProviderPreset[]>([]);
  const [providerPresetDialogOpen, setProviderPresetDialogOpen] = useState(false);
  const [providerPresetForm, setProviderPresetForm] = useState<ProviderPresetFormState>(() => emptyProviderPresetForm());
  const [editingProviderPresetId, setEditingProviderPresetId] = useState<string | null>(null);
  const [providerPresetSaving, setProviderPresetSaving] = useState(false);
  const [providerPresetDeletingId, setProviderPresetDeletingId] = useState<string | null>(null);
  const [providerPresetNotice, setProviderPresetNotice] = useState<string | null>(null);
  const [providerPresetError, setProviderPresetError] = useState<string | null>(null);
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
  const [randomAssignDialogOpen, setRandomAssignDialogOpen] = useState(false);
  const [randomAssignSearchQuery, setRandomAssignSearchQuery] = useState("");
  const [selectedRandomAssignProfileIds, setSelectedRandomAssignProfileIds] = useState<Set<string>>(() => new Set());
  const [randomAssigning, setRandomAssigning] = useState(false);
  const [randomAssignNotice, setRandomAssignNotice] = useState<string | null>(null);
  const [randomAssignError, setRandomAssignError] = useState<string | null>(null);
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
      setError(publicErrorMessage(err, "Unable to load proxy assets"));
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

  const randomAssignCandidateProxies = useMemo(() => (
    proxies.filter((proxy) => {
      if (!matchesOptionFilter(proxy.country_code, countryFilter)) return false;
      if (!matchesOptionFilter(proxy.provider, providerFilter)) return false;
      if (tagFilter !== FILTER_ALL && !proxy.tags.some((tag) => matchesOptionFilter(tag.tag, tagFilter))) return false;
      return true;
    })
  ), [countryFilter, providerFilter, proxies, tagFilter]);

  const randomAssignSelection = useMemo(
    () => buildRandomAssignSelection(countryFilter, providerFilter, tagFilter),
    [countryFilter, providerFilter, tagFilter],
  );

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
      setBulkCheckError(`Bulk check failed: ${publicErrorMessage(err, "Unable to check selected proxies")}`);
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
        setAssignNotice(`${notice}. Refresh failed: ${publicErrorMessage(refreshErr, "Unable to refresh profile data")}`);
      }
    } catch (err) {
      setAssignError(`Assign failed: ${publicErrorMessage(err, "Unable to assign proxy")}`);
    } finally {
      setAssigning(false);
    }
  }, [assigning, onProfilesAssigned, selectedAssignProfileIds, selectedProxy]);

  const randomAssignmentProfiles = useMemo(() => {
    const query = normalizeFilterValue(randomAssignSearchQuery);
    if (!query) return profiles;

    return profiles.filter((profile) => getAssignmentProfileSearchText(profile).includes(query));
  }, [profiles, randomAssignSearchQuery]);

  const visibleRandomAssignmentProfileIds = useMemo(
    () => randomAssignmentProfiles.map((profile) => profile.id),
    [randomAssignmentProfiles],
  );
  const allVisibleRandomAssignmentProfilesSelected = visibleRandomAssignmentProfileIds.length > 0
    && visibleRandomAssignmentProfileIds.every((id) => selectedRandomAssignProfileIds.has(id));

  useEffect(() => {
    setSelectedRandomAssignProfileIds((current) => {
      const profileIds = new Set(profiles.map((profile) => profile.id));
      const next = new Set([...current].filter((id) => profileIds.has(id)));
      return next.size === current.size ? current : next;
    });
  }, [profiles]);

  const openRandomAssignDialog = useCallback(() => {
    if (profiles.length === 0 || randomAssignCandidateProxies.length === 0) return;
    setRandomAssignSearchQuery("");
    setSelectedRandomAssignProfileIds(new Set());
    setRandomAssignError(null);
    setRandomAssignDialogOpen(true);
  }, [profiles.length, randomAssignCandidateProxies.length]);

  const closeRandomAssignDialog = useCallback(() => {
    if (randomAssigning) return;
    setRandomAssignDialogOpen(false);
    setRandomAssignError(null);
  }, [randomAssigning]);

  const toggleRandomAssignProfileSelection = useCallback((profileId: string) => {
    setSelectedRandomAssignProfileIds((current) => {
      const next = new Set(current);
      if (next.has(profileId)) {
        next.delete(profileId);
      } else {
        next.add(profileId);
      }
      return next;
    });
  }, []);

  const toggleVisibleRandomAssignmentProfiles = useCallback(() => {
    setSelectedRandomAssignProfileIds((current) => {
      const next = new Set(current);
      if (visibleRandomAssignmentProfileIds.length > 0 && visibleRandomAssignmentProfileIds.every((id) => next.has(id))) {
        visibleRandomAssignmentProfileIds.forEach((id) => next.delete(id));
      } else {
        visibleRandomAssignmentProfileIds.forEach((id) => next.add(id));
      }
      return next;
    });
  }, [visibleRandomAssignmentProfileIds]);

  const assignRandomProxyToProfiles = useCallback(async () => {
    if (selectedRandomAssignProfileIds.size === 0 || randomAssigning) return;

    setRandomAssigning(true);
    setRandomAssignError(null);
    setRandomAssignNotice(null);
    const profileIds = [...selectedRandomAssignProfileIds];
    const request: ProxyRandomAssignRequestData = {
      ...randomAssignSelection,
      profile_ids: profileIds,
    };

    try {
      const response = await api.assignRandomProxyToProfiles(request);
      const notice = `Random assigned proxy to ${response.succeeded} profile(s), ${response.failed} failed`;
      setRandomAssignNotice(notice);
      setRandomAssignDialogOpen(false);
      setSelectedRandomAssignProfileIds(new Set());
      setRandomAssignSearchQuery("");

      try {
        await onProfilesAssigned?.();
      } catch (refreshErr) {
        setRandomAssignNotice(`${notice}. Refresh failed: ${publicErrorMessage(refreshErr, "Unable to refresh profile data")}`);
      }
    } catch (err) {
      setRandomAssignError(`Random assign failed: ${publicErrorMessage(err, "Unable to assign random proxy")}`);
    } finally {
      setRandomAssigning(false);
    }
  }, [onProfilesAssigned, randomAssigning, randomAssignSelection, selectedRandomAssignProfileIds]);

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

  const openProviderPresetDialog = useCallback(() => {
    setProviderPresetDialogOpen(true);
    setProviderPresetError(null);
  }, []);

  const closeProviderPresetDialog = useCallback(() => {
    if (providerPresetSaving || providerPresetDeletingId) return;
    setProviderPresetDialogOpen(false);
    setProviderPresetError(null);
  }, [providerPresetDeletingId, providerPresetSaving]);

  const resetProviderPresetForm = useCallback(() => {
    setEditingProviderPresetId(null);
    setProviderPresetForm(emptyProviderPresetForm());
    setProviderPresetError(null);
  }, []);

  const editProviderPreset = useCallback((preset: ProxyProviderPreset) => {
    setEditingProviderPresetId(preset.id);
    setProviderPresetForm(providerPresetToForm(preset));
    setProviderPresetError(null);
  }, []);

  const saveProviderPreset = useCallback(async () => {
    if (providerPresetSaving) return;

    let payload: ProxyProviderPresetCreateData;
    try {
      payload = buildProviderPresetPayload(providerPresetForm);
    } catch (err) {
      setProviderPresetError(err instanceof Error ? err.message : "Unable to save provider preset");
      return;
    }

    setProviderPresetSaving(true);
    setProviderPresetError(null);
    setProviderPresetNotice(null);

    try {
      const savedPreset = editingProviderPresetId
        ? await api.updateProxyProviderPreset(editingProviderPresetId, payload)
        : await api.createProxyProviderPreset(payload);

      setProviderPresets((current) => upsertProviderPreset(current, savedPreset));
      setProviderPresetNotice(`Saved provider preset ${publicProviderPresetLabel(savedPreset.name)}`);
      setEditingProviderPresetId(savedPreset.id);
      setProviderPresetForm(providerPresetToForm(savedPreset));
    } catch (err) {
      setProviderPresetError(`Save failed: ${publicErrorMessage(err, "Unable to save provider preset")}`);
    } finally {
      setProviderPresetSaving(false);
    }
  }, [editingProviderPresetId, providerPresetForm, providerPresetSaving]);

  const deleteProviderPreset = useCallback(async (preset: ProxyProviderPreset) => {
    if (providerPresetDeletingId || providerPresetSaving) return;

    setProviderPresetDeletingId(preset.id);
    setProviderPresetError(null);
    setProviderPresetNotice(null);

    try {
      await api.deleteProxyProviderPreset(preset.id);
      setProviderPresets((current) => current.filter((item) => item.id !== preset.id));
      setSelectedImportPresetId((current) => current === preset.id ? "" : current);
      if (editingProviderPresetId === preset.id) {
        setEditingProviderPresetId(null);
        setProviderPresetForm(emptyProviderPresetForm());
      }
      setProviderPresetNotice(`Deleted provider preset ${publicProviderPresetLabel(preset.name)}`);
    } catch (err) {
      setProviderPresetError(`Delete failed: ${publicErrorMessage(err, "Unable to delete provider preset")}`);
    } finally {
      setProviderPresetDeletingId(null);
    }
  }, [editingProviderPresetId, providerPresetDeletingId, providerPresetSaving]);

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
        failures.push({
          rowNumber: row.rowNumber,
          message: publicErrorMessage(err, "Unable to create proxy asset"),
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
              URL credentials are hidden in the UI. Bulk check, profile assignment, provider presets, and CSV import are active; proxy asset add, edit, and delete remain disabled.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              className="btn-secondary inline-flex h-8 items-center gap-1.5 text-xs"
              onClick={openProviderPresetDialog}
              disabled={providerPresetSaving}
              aria-label="Manage presets"
            >
              <Settings2 className="h-3.5 w-3.5" />
              Manage presets
            </button>
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
              onClick={openRandomAssignDialog}
              disabled={profiles.length === 0 || randomAssignCandidateProxies.length === 0 || randomAssigning}
              aria-label="Random assign"
              title={randomAssignCandidateProxies.length > 0 ? "Randomly assign matching proxy assets to profiles" : "No proxy assets match the current country, provider, and tag filters"}
            >
              <Shuffle className="h-3.5 w-3.5" />
              Random assign
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

        {randomAssignNotice && (
          <div className="animate-notice-in border-b border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-700" role="status">
            {randomAssignNotice}
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
      {randomAssignDialogOpen && (
        <ProxyRandomAssignDialog
          candidateCount={randomAssignCandidateProxies.length}
          selection={randomAssignSelection}
          profiles={randomAssignmentProfiles}
          totalProfileCount={profiles.length}
          searchQuery={randomAssignSearchQuery}
          selectedProfileIds={selectedRandomAssignProfileIds}
          allVisibleSelected={allVisibleRandomAssignmentProfilesSelected}
          assigning={randomAssigning}
          error={randomAssignError}
          onSearchQueryChange={setRandomAssignSearchQuery}
          onToggleProfile={toggleRandomAssignProfileSelection}
          onToggleVisible={toggleVisibleRandomAssignmentProfiles}
          onAssign={() => void assignRandomProxyToProfiles()}
          onClose={closeRandomAssignDialog}
        />
      )}
      {providerPresetDialogOpen && (
        <ProxyProviderPresetDialog
          presets={providerPresets}
          form={providerPresetForm}
          editingPresetId={editingProviderPresetId}
          saving={providerPresetSaving}
          deletingId={providerPresetDeletingId}
          notice={providerPresetNotice}
          error={providerPresetError}
          onFormChange={setProviderPresetForm}
          onReset={resetProviderPresetForm}
          onEdit={editProviderPreset}
          onSave={() => void saveProviderPreset()}
          onDelete={(preset) => void deleteProviderPreset(preset)}
          onClose={closeProviderPresetDialog}
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

function ProxyProviderPresetDialog({
  presets,
  form,
  editingPresetId,
  saving,
  deletingId,
  notice,
  error,
  onFormChange,
  onReset,
  onEdit,
  onSave,
  onDelete,
  onClose,
}: {
  presets: ProxyProviderPreset[];
  form: ProviderPresetFormState;
  editingPresetId: string | null;
  saving: boolean;
  deletingId: string | null;
  notice: string | null;
  error: string | null;
  onFormChange: (form: ProviderPresetFormState) => void;
  onReset: () => void;
  onEdit: (preset: ProxyProviderPreset) => void;
  onSave: () => void;
  onDelete: (preset: ProxyProviderPreset) => void;
  onClose: () => void;
}) {
  const editingPreset = presets.find((preset) => preset.id === editingPresetId) ?? null;
  const busy = saving || Boolean(deletingId);
  const saveLabel = editingPreset ? "Save changes" : "Save preset";
  const canSave = form.name.trim().length > 0 && !busy;

  return (
    <div className="animate-dialog-backdrop fixed inset-0 z-50 flex items-center justify-center bg-slate-950/35 p-3 backdrop-blur-sm">
      <div
        role="dialog"
        aria-label="Manage provider presets"
        aria-modal="true"
        className="animate-dialog-in flex max-h-[calc(100vh-24px)] w-[min(900px,calc(100vw-24px))] min-w-0 flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-[0_24px_80px_rgba(15,23,42,0.22),inset_0_1px_0_rgba(255,255,255,0.9)]"
      >
        <div className="flex items-start justify-between gap-3 border-b border-slate-200 bg-[#fbfdff] px-4 py-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-[8px] border border-blue-100 bg-blue-50 text-blue-700">
                <Settings2 className="h-4 w-4" />
              </span>
              <div className="min-w-0">
                <h3 className="text-sm font-semibold text-slate-950">Manage provider presets</h3>
                <p className="mt-0.5 text-xs text-slate-500">
                  Save reusable provider, country, tag, and notes defaults for proxy import workflows.
                </p>
              </div>
            </div>
          </div>
          <button
            type="button"
            className="icon-action h-7 w-7"
            onClick={onClose}
            disabled={busy}
            aria-label="Close manage provider presets dialog"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {notice && (
          <div className="animate-notice-in border-b border-emerald-200 bg-emerald-50 px-4 py-2 text-sm font-medium text-emerald-700" role="status">
            {notice}
          </div>
        )}

        {error && (
          <div className="animate-notice-in border-b border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700" role="alert">
            {error}
          </div>
        )}

        <div className="grid min-h-0 flex-1 gap-0 overflow-y-auto lg:grid-cols-[minmax(0,1fr)_340px] lg:overflow-hidden">
          <div className="min-h-[240px] overflow-auto border-b border-slate-200 bg-white p-3 lg:border-b-0 lg:border-r">
            {presets.length === 0 ? (
              <div
                role="status"
                aria-label="No provider presets yet"
                className="flex min-h-[220px] items-center justify-center rounded-lg border border-dashed border-slate-300 bg-slate-50/70 p-6 text-center text-sm text-slate-500"
              >
                No provider presets yet.
              </div>
            ) : (
              <div role="list" aria-label="Provider presets" className="grid gap-2">
                {presets.map((preset) => (
                  <ProviderPresetRow
                    key={preset.id}
                    preset={preset}
                    selected={preset.id === editingPresetId}
                    deleting={deletingId === preset.id}
                    disabled={busy && deletingId !== preset.id}
                    onEdit={() => onEdit(preset)}
                    onDelete={() => onDelete(preset)}
                  />
                ))}
              </div>
            )}
          </div>

          <div className="grid content-start gap-3 bg-[#fbfdff] p-4">
            <div className="flex items-center justify-between gap-2">
              <div className="min-w-0">
                <div className="text-sm font-semibold text-slate-950">
                  {editingPreset ? "Edit preset" : "New preset"}
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  These values fill empty fields during CSV import.
                </p>
              </div>
              {editingPreset && (
                <button
                  type="button"
                  className="btn-secondary h-8 text-xs"
                  onClick={onReset}
                  disabled={busy}
                >
                  New
                </button>
              )}
            </div>

            <label className="min-w-0">
              <span className="label">Name</span>
              <input
                aria-label="Preset name"
                className="input"
                value={form.name}
                onChange={(event) => onFormChange({ ...form, name: event.target.value })}
                disabled={busy}
                placeholder="Japan mobile default"
              />
            </label>
            <label className="min-w-0">
              <span className="label">Provider</span>
              <input
                aria-label="Preset provider"
                className="input"
                value={form.provider}
                onChange={(event) => onFormChange({ ...form, provider: event.target.value })}
                disabled={busy}
                placeholder="ProxyJP"
              />
            </label>
            <label className="min-w-0">
              <span className="label">Country</span>
              <input
                aria-label="Preset country"
                className="input uppercase"
                value={form.country_code}
                onChange={(event) => onFormChange({ ...form, country_code: event.target.value })}
                disabled={busy}
                placeholder="JP"
                maxLength={8}
              />
            </label>
            <label className="min-w-0">
              <span className="label">Tags</span>
              <input
                aria-label="Preset tags"
                className="input"
                value={form.tags}
                onChange={(event) => onFormChange({ ...form, tags: event.target.value })}
                disabled={busy}
                placeholder="mobile, warmup"
              />
            </label>
            <label className="min-w-0">
              <span className="label">Notes</span>
              <textarea
                aria-label="Preset notes"
                className="input min-h-[84px] resize-y text-sm leading-5"
                value={form.notes}
                onChange={(event) => onFormChange({ ...form, notes: event.target.value })}
                disabled={busy}
                placeholder="Tokyo exits"
              />
            </label>

            <div className="flex flex-wrap items-center justify-end gap-2 border-t border-slate-200 pt-3">
              <button
                type="button"
                className="btn-secondary h-8 text-xs"
                onClick={onClose}
                disabled={busy}
              >
                Done
              </button>
              <button
                type="button"
                className="btn-primary inline-flex h-8 min-w-[112px] items-center justify-center gap-1.5 text-xs"
                onClick={onSave}
                disabled={!canSave}
              >
                {saving ? (
                  <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Settings2 className="h-3.5 w-3.5" />
                )}
                {saving ? "Saving" : saveLabel}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function ProviderPresetRow({
  preset,
  selected,
  deleting,
  disabled,
  onEdit,
  onDelete,
}: {
  preset: ProxyProviderPreset;
  selected: boolean;
  deleting: boolean;
  disabled: boolean;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const safeName = publicProviderPresetLabel(preset.name);
  const safeNotes = preset.notes ? publicErrorText(preset.notes) : null;
  const tagText = preset.tags.map((tag) => tag.tag).join(", ") || "-";
  const summary = [preset.provider, preset.country_code, tagText !== "-" ? tagText : null]
    .filter(Boolean)
    .join(" / ") || "No defaults";

  return (
    <div
      role="listitem"
      className={`rounded-lg border bg-white p-3 shadow-hairline transition-colors ${
        selected ? "border-blue-300 ring-2 ring-blue-500/10" : "border-slate-200 hover:border-blue-200"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold text-slate-950" title={safeName}>
            {safeName}
          </div>
          <div className="mt-1 truncate text-xs text-slate-500" title={summary}>
            {summary}
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          <button
            type="button"
            className="icon-action h-7 w-7"
            onClick={onEdit}
            disabled={disabled || deleting}
            aria-label={`Edit ${safeName}`}
          >
            <Pencil className="h-3.5 w-3.5" />
          </button>
          <button
            type="button"
            className="icon-action h-7 w-7 text-red-500 hover:border-red-200 hover:text-red-700"
            onClick={onDelete}
            disabled={disabled || deleting}
            aria-label={`Delete ${safeName}`}
          >
            {deleting ? (
              <RefreshCw className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Trash2 className="h-3.5 w-3.5" />
            )}
          </button>
        </div>
      </div>
      <div className="mt-2 flex flex-wrap gap-1">
        {preset.provider && (
          <span className="token-chip max-w-[160px] truncate" title={preset.provider}>
            {preset.provider}
          </span>
        )}
        {preset.country_code && (
          <span className="token-chip max-w-[72px] truncate" title={preset.country_code}>
            {preset.country_code}
          </span>
        )}
        {preset.tags.map((tag) => (
          <span key={`${preset.id}-${tag.tag}`} className="token-chip max-w-[128px] truncate" title={tag.tag}>
            <span
              className="h-1.5 w-1.5 shrink-0 rounded-full"
              style={{ backgroundColor: tag.color ?? "#94a3b8" }}
            />
            {tag.tag}
          </span>
        ))}
      </div>
      {safeNotes && (
        <p className="mt-2 line-clamp-2 text-xs leading-5 text-slate-500" title={safeNotes}>
          {safeNotes}
        </p>
      )}
    </div>
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

function ProxyRandomAssignDialog({
  candidateCount,
  selection,
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
  candidateCount: number;
  selection: Omit<ProxyRandomAssignRequestData, "profile_ids">;
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
  const selectedCount = selectedProfileIds.size;
  const filterPills = [
    ["Country", selection.country_code ?? "All"],
    ["Provider", selection.provider ?? "All"],
    ["Tag", selection.tags && selection.tags.length > 0 ? selection.tags.join(", ") : "All"],
  ];

  return (
    <div className="animate-dialog-backdrop fixed inset-0 z-50 flex items-center justify-center bg-slate-950/35 p-3 backdrop-blur-sm">
      <div
        role="dialog"
        aria-label="Random proxy assignment"
        aria-modal="true"
        className="animate-dialog-in flex max-h-[calc(100vh-24px)] w-[min(760px,calc(100vw-24px))] min-w-0 flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-[0_24px_80px_rgba(15,23,42,0.22),inset_0_1px_0_rgba(255,255,255,0.9)]"
      >
        <div className="flex items-start justify-between gap-3 border-b border-slate-200 bg-[#fbfdff] px-4 py-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-[8px] border border-blue-100 bg-blue-50 text-blue-700">
                <Shuffle className="h-4 w-4" />
              </span>
              <div className="min-w-0">
                <h3 className="text-sm font-semibold text-slate-950">Random proxy assignment</h3>
                <p className="mt-0.5 text-xs text-slate-500">
                  Choose profiles and assign a random proxy from the current country, provider, and tag pool.
                </p>
              </div>
            </div>
          </div>
          <button
            type="button"
            className="icon-action h-7 w-7"
            onClick={onClose}
            disabled={assigning}
            aria-label="Close random proxy assignment dialog"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="border-b border-slate-200 bg-white px-4 py-3">
          <div className="grid gap-2 rounded-lg border border-slate-200 bg-slate-50/80 p-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="rounded-[999px] border border-blue-200 bg-blue-50 px-2 py-1 text-[11px] font-semibold text-blue-700">
                  {candidateCount} candidate {candidateCount === 1 ? "proxy" : "proxies"}
                </span>
                {filterPills.map(([label, value]) => (
                  <span
                    key={label}
                    className="inline-flex max-w-full items-center gap-1 rounded-[999px] border border-slate-200 bg-white px-2 py-1 text-[11px] font-medium text-slate-600"
                  >
                    <span className="text-slate-400">{label}</span>
                    <span className="truncate text-slate-800" title={value}>{value}</span>
                  </span>
                ))}
              </div>
              <p className="mt-2 text-xs text-slate-500">
                Search text is for choosing profiles only; proxy candidates come from the selected filters.
              </p>
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
                aria-label="Search profiles for random assignment"
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
              aria-label="Select all visible random assignment profiles"
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
              aria-label={totalProfileCount === 0 ? "No profiles available for random assignment" : "No random assignment profiles match search"}
              className="flex min-h-[180px] items-center justify-center rounded-lg border border-dashed border-slate-300 bg-slate-50/70 p-6 text-center text-sm text-slate-500"
            >
              {totalProfileCount === 0
                ? "No profiles are available yet."
                : "No profiles match this random assignment search."}
            </div>
          ) : (
            <div role="list" aria-label="Random assignment profiles" className="grid gap-1.5">
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
            Each selected profile receives one random matching proxy through the Proxy Manager API.
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
              {assigning ? (
                <RefreshCw className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Shuffle className="h-3.5 w-3.5" />
              )}
              {assigning ? "Assigning" : "Assign random proxy"}
            </button>
          </div>
        </div>
      </div>
    </div>
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
  const runtimeStatus = publicRuntimeStatus(profile.status);

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
            runtimeStatus === "running"
              ? "border-emerald-200 bg-emerald-50 text-emerald-700"
              : "border-slate-200 bg-slate-50 text-slate-500"
          }`}>
            {runtimeStatus}
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
    ? publicErrorText(proxy.last_check_error)
    : null;
  const safeNotes = proxy.notes ? publicErrorText(proxy.notes) : null;
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

function emptyProviderPresetForm(): ProviderPresetFormState {
  return {
    name: "",
    provider: "",
    country_code: "",
    tags: "",
    notes: "",
  };
}

function publicProviderPresetLabel(value: string): string {
  return publicErrorText(value) || "unknown";
}

function providerPresetToForm(preset: ProxyProviderPreset): ProviderPresetFormState {
  return {
    name: preset.name,
    provider: preset.provider ?? "",
    country_code: preset.country_code ?? "",
    tags: preset.tags.map((tag) => tag.tag).join(", "),
    notes: preset.notes ?? "",
  };
}

function buildProviderPresetPayload(form: ProviderPresetFormState): ProxyProviderPresetCreateData {
  const name = form.name.trim();
  if (!name) {
    throw new Error("Preset name is required");
  }

  return {
    name,
    provider: optionalTrimmed(form.provider),
    country_code: optionalTrimmed(form.country_code)?.toUpperCase() ?? null,
    tags: parseCsvTags(form.tags),
    notes: optionalTrimmed(form.notes),
  };
}

function upsertProviderPreset(
  presets: ProxyProviderPreset[],
  nextPreset: ProxyProviderPreset,
): ProxyProviderPreset[] {
  const exists = presets.some((preset) => preset.id === nextPreset.id);
  const next = exists
    ? presets.map((preset) => preset.id === nextPreset.id ? nextPreset : preset)
    : [...presets, nextPreset];

  return [...next].sort((a, b) => a.name.localeCompare(b.name));
}

function optionalTrimmed(value: string): string | null {
  const trimmed = value.trim();
  return trimmed || null;
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

function buildRandomAssignSelection(
  countryFilter: string,
  providerFilter: string,
  tagFilter: string,
): Omit<ProxyRandomAssignRequestData, "profile_ids"> {
  const selection: Omit<ProxyRandomAssignRequestData, "profile_ids"> = {};
  const country = normalizeRequestFilterValue(countryFilter);
  const provider = normalizeRequestFilterValue(providerFilter);
  const tag = normalizeRequestFilterValue(tagFilter);

  if (country) selection.country_code = country.toUpperCase();
  if (provider) selection.provider = provider;
  if (tag) selection.tags = [tag];

  return selection;
}

function normalizeRequestFilterValue(value: string): string {
  return value === FILTER_ALL ? "" : value.trim();
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
    proxy.notes ? publicErrorText(proxy.notes) : null,
    proxy.last_check_status,
    proxy.last_check_ip,
    proxy.last_check_country_code,
    proxy.last_check_timezone,
    proxy.last_check_locale,
    proxy.last_check_source,
    proxy.last_check_error ? publicErrorText(proxy.last_check_error) : null,
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
    publicRuntimeStatus(profile.status),
    profile.proxy ? redactUrlCredentials(profile.proxy) : "no proxy",
  ]
    .map(normalizeFilterValue)
    .filter(Boolean)
    .join(" ");
}
