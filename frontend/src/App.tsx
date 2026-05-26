import { useState, useCallback, useEffect, useMemo } from "react";
import { FileSpreadsheet, Lock, Network, PanelLeftClose, PanelLeft, Plus } from "lucide-react";
import { useProfiles, type BulkHealthResult } from "./hooks/useProfiles";
import { api, setOnUnauthorized, type Profile, type ProfileCreateData, type ProfileTemplate } from "./lib/api";
import { ProfileList } from "./components/ProfileList";
import { ProfileForm } from "./components/ProfileForm";
import { ProfileViewer } from "./components/ProfileViewer";
import { ProfileTable } from "./components/ProfileTable";
import { ProfileCsvPreviewDialog } from "./components/ProfileCsvPreviewDialog";
import { ProfileFilters } from "./components/ProfileFilters";
import { ProfileSummaryPanel } from "./components/ProfileSummaryPanel";
import { ProxyManagerPage } from "./components/ProxyManagerPage";
import { LaunchButton } from "./components/LaunchButton";
import { StatusIndicator } from "./components/StatusIndicator";
import { LoginPage } from "./components/LoginPage";
import {
  defaultProfileFilters,
  filterAndSortProfiles,
  getProfileFilterOptions,
  type ProfileFilterState,
} from "./lib/filters";

type AuthState = "checking" | "required" | "ok" | "error";
type View = "empty" | "create" | "edit" | "view";
type ConsoleSection = "profiles" | "proxies";
type BulkFeedback = {
  tone: "success" | "warning";
  message: string;
} | null;

function getInitialSidebarOpen(): boolean {
  return typeof window === "undefined" || window.innerWidth >= 768;
}

function profileFiltersEqual(a: ProfileFilterState, b: ProfileFilterState): boolean {
  return a.search === b.search
    && a.status === b.status
    && a.health === b.health
    && a.proxy === b.proxy
    && a.country === b.country
    && a.tag === b.tag
    && a.sortBy === b.sortBy;
}

function LoadingShell() {
  return (
    <div className="flex h-screen items-center justify-center bg-surface-0 px-4">
      <div
        role="status"
        aria-label="Loading operations console"
        className="animate-app-skeleton w-[min(520px,100%)] rounded-lg border border-slate-200 bg-white p-4 shadow-[0_16px_48px_rgba(15,23,42,0.08),inset_0_1px_0_rgba(255,255,255,0.9)]"
      >
        <div className="flex items-center gap-3">
          <span data-skeleton className="h-9 w-9 shrink-0 rounded-lg bg-slate-200" />
          <div className="min-w-0 flex-1 space-y-2">
            <div data-skeleton className="h-3 w-36 rounded-full bg-slate-200" />
            <div data-skeleton className="h-2.5 w-52 max-w-full rounded-full bg-slate-100" />
          </div>
        </div>
        <div className="mt-4 space-y-2">
          {[0, 1, 2].map((index) => (
            <div
              key={index}
              aria-label="Loading skeleton row"
              data-skeleton
              className="h-8 rounded-md bg-slate-100"
            />
          ))}
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const [authState, setAuthState] = useState<AuthState>("checking");
  const [authRequired, setAuthRequired] = useState(false);

  useEffect(() => {
    setOnUnauthorized(() => setAuthState("required"));

    api.authStatus()
      .then(({ auth_required, authenticated }) => {
        setAuthRequired(auth_required);
        if (!auth_required || authenticated) {
          setAuthState("ok");
        } else {
          setAuthState("required");
        }
      })
      .catch((err) => {
        console.warn("[auth] status check failed:", err);
        setAuthState("error");
      });

    return () => setOnUnauthorized(null);
  }, []);

  if (authState === "checking") {
    return <LoadingShell />;
  }

  if (authState === "error") {
    return (
      <div className="h-screen flex items-center justify-center bg-surface-0">
        <div className="text-center">
          <p className="mb-2 text-sm text-red-700">Unable to reach the server</p>
          <button
            onClick={() => {
              setAuthState("checking");
              api.authStatus()
                .then(({ auth_required, authenticated }) => {
                  setAuthRequired(auth_required);
                  setAuthState(!auth_required || authenticated ? "ok" : "required");
                })
                .catch(() => setAuthState("error"));
            }}
            className="text-xs text-slate-500 underline hover:text-slate-900"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (authState === "required") {
    return <LoginPage onSuccess={() => setAuthState("ok")} />;
  }

  return (
    <AppContent
      authRequired={authRequired}
      onLogout={async () => {
        await api.logout();
        setAuthState("required");
      }}
    />
  );
}

interface AppContentProps {
  authRequired: boolean;
  onLogout: () => void;
}

function AppContent({ authRequired, onLogout }: AppContentProps) {
  const {
    profiles,
    healthByProfileId,
    loading,
    error,
    refresh,
    create,
    update,
    remove,
    launch,
    launchProfiles,
    stop,
    stopProfiles,
    checkHealth,
    addTagsToProfiles,
    deleteProfiles,
  } = useProfiles();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [view, setView] = useState<View>("empty");
  const [section, setSection] = useState<ConsoleSection>("profiles");
  const [sidebarOpen, setSidebarOpen] = useState(getInitialSidebarOpen);
  const [filters, setFilters] = useState<ProfileFilterState>(defaultProfileFilters);
  const [selectedProfileIds, setSelectedProfileIds] = useState<Set<string>>(() => new Set());
  const [previewProfileId, setPreviewProfileId] = useState<string | null>(null);
  const [bulkHealthChecking, setBulkHealthChecking] = useState(false);
  const [bulkLaunching, setBulkLaunching] = useState(false);
  const [bulkStopping, setBulkStopping] = useState(false);
  const [bulkTagging, setBulkTagging] = useState(false);
  const [bulkDeleting, setBulkDeleting] = useState(false);
  const [bulkFeedback, setBulkFeedback] = useState<BulkFeedback>(null);
  const [profileTemplates, setProfileTemplates] = useState<ProfileTemplate[]>([]);
  const [profileImportDialogOpen, setProfileImportDialogOpen] = useState(false);

  const selected = profiles.find((p) => p.id === selectedId) ?? null;
  const filterOptions = useMemo(
    () => getProfileFilterOptions(profiles, healthByProfileId),
    [healthByProfileId, profiles],
  );
  const filteredProfiles = useMemo(
    () => filterAndSortProfiles(profiles, healthByProfileId, filters),
    [filters, healthByProfileId, profiles],
  );
  const hasActiveFilters = useMemo(
    () => !profileFiltersEqual(filters, defaultProfileFilters),
    [filters],
  );
  const previewProfile = useMemo(() => {
    const firstProfile = filteredProfiles[0];
    if (!firstProfile) return null;
    return filteredProfiles.find((profile) => profile.id === previewProfileId) ?? firstProfile;
  }, [filteredProfiles, previewProfileId]);
  const consoleStats = useMemo(() => {
    const issueCount = profiles.filter((profile) => {
      const status = healthByProfileId[profile.id]?.status;
      return status === "error" || status === "warning";
    }).length;
    const unavailableCount = profiles.filter((profile) => healthByProfileId[profile.id]?.status === "error").length;

    return {
      total: profiles.length,
      visible: filteredProfiles.length,
      running: profiles.filter((profile) => profile.status === "running").length,
      stopped: profiles.filter((profile) => profile.status === "stopped").length,
      issues: issueCount,
      unavailable: unavailableCount,
    };
  }, [filteredProfiles.length, healthByProfileId, profiles]);

  useEffect(() => {
    const visibleIds = new Set(filteredProfiles.map((profile) => profile.id));
    setSelectedProfileIds((prev) => {
      const next = new Set([...prev].filter((id) => visibleIds.has(id)));
      return next.size === prev.size ? prev : next;
    });
  }, [filteredProfiles]);

  useEffect(() => {
    let active = true;
    api.listProfileTemplates()
      .then((templates) => {
        if (active) setProfileTemplates(templates);
      })
      .catch(() => {
        if (active) setProfileTemplates([]);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    setBulkFeedback(null);
  }, [filters, section]);

  useEffect(() => {
    setPreviewProfileId((prev) => {
      const firstProfile = filteredProfiles[0];
      if (!firstProfile) return null;
      if (prev && filteredProfiles.some((profile) => profile.id === prev)) return prev;
      return firstProfile.id;
    });
  }, [filteredProfiles]);

  const handleSelect = useCallback((id: string) => {
    setSelectedId(id);
    const profile = profiles.find((p) => p.id === id);
    setView(profile?.status === "running" ? "view" : "edit");
  }, [profiles]);

  const handleSidebarFiltersChange = useCallback((nextFilters: ProfileFilterState) => {
    setSection("profiles");
    setFilters(nextFilters);
    setSelectedId(null);
    setView("empty");
  }, []);

  const handleNew = useCallback(() => {
    setSection("profiles");
    setSelectedId(null);
    setView("create");
  }, []);

  const handleCreate = useCallback(async (data: ProfileCreateData) => {
    const profile = await create(data);
    if (profile) {
      setSelectedId(profile.id);
      setView("edit");
    }
  }, [create]);

  const handleUpdate = useCallback(async (data: ProfileCreateData) => {
    if (!selectedId) return;
    await update(selectedId, data);
  }, [selectedId, update]);

  const handleDelete = useCallback(async () => {
    if (!selectedId) return;
    await remove(selectedId);
    setSelectedId(null);
    setView("empty");
  }, [selectedId, remove]);

  const handleLaunch = useCallback(async () => {
    if (!selectedId) return;
    const result = await launch(selectedId);
    if (result) setView("view");
  }, [selectedId, launch]);

  const handleStop = useCallback(async () => {
    if (!selectedId) return;
    await stop(selectedId);
    setView("edit");
  }, [selectedId, stop]);

  const handleVncDisconnect = useCallback(() => {
    setView("edit");
  }, []);

  const handleToggleProfileSelection = useCallback((id: string) => {
    setBulkFeedback(null);
    setSelectedProfileIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const handleToggleVisibleSelection = useCallback((ids: string[], shouldSelect: boolean) => {
    setBulkFeedback(null);
    setSelectedProfileIds((prev) => {
      const next = new Set(prev);
      ids.forEach((id) => {
        if (shouldSelect) {
          next.add(id);
        } else {
          next.delete(id);
        }
      });
      return next;
    });
  }, []);

  const handleCheckSelectedHealth = useCallback(async (ids: string[]) => {
    if (ids.length === 0) return;
    setBulkFeedback(null);
    setBulkHealthChecking(true);
    try {
      const result = await checkHealth(ids) as BulkHealthResult | undefined;
      if (!result || result.requestedCount === 0) return;
      setBulkFeedback(result.failedCount > 0
        ? {
          tone: "warning",
          message: `Health check finished: ${result.checkedCount} checked, ${result.failedCount} failed.`,
        }
        : {
          tone: "success",
          message: `Health checked for ${result.checkedCount} profile${result.checkedCount === 1 ? "" : "s"}.`,
        });
    } finally {
      setBulkHealthChecking(false);
    }
  }, [checkHealth]);

  const handleLaunchSelectedProfiles = useCallback(async (ids: string[]) => {
    if (ids.length === 0) return;
    setBulkLaunching(true);
    try {
      await launchProfiles(ids);
    } finally {
      setBulkLaunching(false);
    }
  }, [launchProfiles]);

  const handleStopSelectedProfiles = useCallback(async (ids: string[]) => {
    if (ids.length === 0) return;
    setBulkStopping(true);
    try {
      await stopProfiles(ids);
    } finally {
      setBulkStopping(false);
    }
  }, [stopProfiles]);

  const handleAddTagsToSelectedProfiles = useCallback(async (ids: string[], tags: Profile["tags"]) => {
    if (ids.length === 0 || tags.length === 0) return;
    setBulkTagging(true);
    try {
      await addTagsToProfiles(ids, tags);
    } finally {
      setBulkTagging(false);
    }
  }, [addTagsToProfiles]);

  const handleDeleteSelectedProfiles = useCallback(async (ids: string[]) => {
    if (ids.length === 0) return;
    setBulkDeleting(true);
    try {
      const result = await deleteProfiles(ids);
      const deletedIds = new Set(result.deletedIds);
      if (deletedIds.size === 0) return;

      setSelectedProfileIds((prev) => {
        const next = new Set(prev);
        deletedIds.forEach((id) => next.delete(id));
        return next;
      });
      setPreviewProfileId((prev) => (prev && deletedIds.has(prev) ? null : prev));
      if (selectedId && deletedIds.has(selectedId)) {
        setSelectedId(null);
        setView("empty");
      }
    } finally {
      setBulkDeleting(false);
    }
  }, [deleteProfiles, selectedId]);

  if (loading) {
    return <LoadingShell />;
  }

  return (
    <div className="flex h-screen bg-[#f6f7f9] text-slate-900">
      {/* Sidebar */}
      {section === "profiles" && sidebarOpen && (
        <>
          <button
            type="button"
            aria-label="Close sidebar backdrop"
            className="fixed inset-0 z-30 bg-slate-950/20 md:hidden"
            onClick={() => setSidebarOpen(false)}
          />
          <div className="fixed inset-y-0 left-0 z-40 w-[264px] border-r border-slate-200 bg-white shadow-panel md:relative md:inset-auto md:z-auto md:flex-shrink-0 md:shadow-hairline">
            <ProfileList
              profiles={profiles}
              selectedId={selectedId}
              onSelect={handleSelect}
              onNew={handleNew}
              healthByProfileId={healthByProfileId}
              filters={filters}
              filterOptions={filterOptions}
              onFiltersChange={handleSidebarFiltersChange}
              showFilters={false}
            />
          </div>
        </>
      )}

      {/* Main panel */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <div className="flex min-h-14 items-center justify-between overflow-hidden border-b border-slate-200/90 bg-white/95 px-3 py-2.5 shadow-[0_1px_2px_rgba(15,23,42,0.04)] backdrop-blur sm:px-4">
          <div className="flex items-center gap-3">
            {section === "profiles" && (
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="rounded-lg p-1.5 text-slate-500 transition-colors hover:bg-surface-2 hover:text-slate-900 focus:outline-none focus:ring-2 focus:ring-accent/20"
                title={sidebarOpen ? "Hide sidebar" : "Show sidebar"}
              >
                {sidebarOpen ? <PanelLeftClose className="h-4 w-4" /> : <PanelLeft className="h-4 w-4" />}
              </button>
            )}
            <div className="flex items-center gap-1 rounded-[8px] border border-slate-200 bg-slate-50 p-1 shadow-[inset_0_1px_0_rgba(255,255,255,0.85)]">
              <button
                type="button"
                aria-pressed={section === "profiles"}
                onClick={() => setSection("profiles")}
                className={`inline-flex h-7 items-center rounded-[6px] px-2.5 text-xs font-medium transition-[background-color,color,box-shadow,transform] duration-150 active:translate-y-px focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/20 ${
                  section === "profiles"
                    ? "bg-white text-slate-950 shadow-[0_1px_2px_rgba(15,23,42,0.08)]"
                    : "text-slate-500 hover:bg-white/70 hover:text-slate-900"
                }`}
              >
                Profiles
              </button>
              <button
                type="button"
                aria-pressed={section === "proxies"}
                onClick={() => setSection("proxies")}
                className={`inline-flex h-7 items-center gap-1.5 rounded-[6px] px-2.5 text-xs font-medium transition-[background-color,color,box-shadow,transform] duration-150 active:translate-y-px focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/20 ${
                  section === "proxies"
                    ? "bg-white text-slate-950 shadow-[0_1px_2px_rgba(15,23,42,0.08)]"
                    : "text-slate-500 hover:bg-white/70 hover:text-slate-900"
                }`}
              >
                <Network className="h-3.5 w-3.5" />
                Proxy Manager
              </button>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-slate-950">
                  {section === "profiles" ? "Profiles" : "Proxy Manager"}
                </span>
                {section === "profiles" && (
                  <span className="rounded-[999px] border border-slate-200 bg-slate-50 px-2 py-0.5 text-[11px] font-medium text-slate-500">
                    {consoleStats.visible} shown
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-500">
                {section === "profiles"
                  ? `${consoleStats.total} profiles · ${consoleStats.running} running · ${consoleStats.issues} need review`
                  : "Proxy inventory · redacted URLs · assignment controls"}
              </p>
            </div>
            {section === "profiles" && selected && (
              <div className="hidden items-center gap-2 rounded-[7px] border border-slate-200 bg-slate-50 px-2.5 py-1.5 md:flex">
                <StatusIndicator status={selected.status} size="md" />
                <span className="max-w-[220px] truncate text-sm font-medium text-slate-700">{selected.name}</span>
              </div>
            )}
          </div>
          <div className="flex min-w-0 shrink-0 items-center gap-2">
            {section === "profiles" && (
              <>
                <button
                  type="button"
                  onClick={() => setProfileImportDialogOpen(true)}
                  className="btn-secondary inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap"
                >
                  <FileSpreadsheet className="h-3.5 w-3.5" />
                  Import CSV
                </button>
                <button
                  type="button"
                  onClick={handleNew}
                  className="btn-primary inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap"
                >
                  <Plus className="h-3.5 w-3.5" />
                  New Profile
                </button>
              </>
            )}
            {section === "profiles" && selected && (
              <LaunchButton
                status={selected.status}
                onLaunch={handleLaunch}
                onStop={handleStop}
              />
            )}
            {authRequired && (
              <button
                onClick={onLogout}
                className="rounded-lg p-1.5 text-slate-500 transition-colors hover:bg-surface-2 hover:text-slate-900"
                title="Log out"
              >
                <Lock className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        </div>

        {/* Error banner */}
        {error && (
          <div className="border-b border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700" role="alert">
            {error}
          </div>
        )}

        {/* Content */}
        <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain">
          {section === "proxies" && (
            <div data-console-section="proxies" className="animate-console-section-in h-full min-h-0">
              <ProxyManagerPage profiles={profiles} onProfilesAssigned={refresh} />
            </div>
          )}

          {section === "profiles" && view === "empty" && (
            <div data-console-section="profiles" className="animate-console-section-in flex h-full min-h-0 flex-col gap-3 p-3 sm:p-4 lg:p-5">
              <section className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_auto] xl:items-end">
                <div className="min-w-0">
                  <h2 className="text-xl font-semibold tracking-tight text-slate-950">Profile operations</h2>
                  <p className="mt-1 text-sm text-slate-600">
                    {consoleStats.total} profiles · {consoleStats.running} running · {consoleStats.issues} need review
                  </p>
                </div>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                  <SummaryTile label="Running" value={consoleStats.running} tone="success" />
                  <SummaryTile label="Stopped" value={consoleStats.stopped} />
                  <SummaryTile label="Issues" value={consoleStats.issues} tone="warning" />
                  <SummaryTile label="Unavailable" value={consoleStats.unavailable} tone="danger" />
                </div>
              </section>
              <section className="rounded-lg border border-slate-200 bg-white p-3 shadow-[0_1px_2px_rgba(15,23,42,0.04),inset_0_1px_0_rgba(255,255,255,0.9)]">
                <ProfileFilters
                  value={filters}
                  options={filterOptions}
                  onChange={setFilters}
                  layout="toolbar"
                />
              </section>
              <section className="grid min-h-0 flex-1 gap-4 lg:grid-cols-[minmax(0,1fr)_280px]">
                <div className="min-h-[420px] min-w-0 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-[0_8px_24px_rgba(15,23,42,0.05),inset_0_1px_0_rgba(255,255,255,0.9)] lg:min-h-0">
                  <ProfileTable
                    profiles={filteredProfiles}
                    healthByProfileId={healthByProfileId}
                    onSelect={handleSelect}
                    selectedProfileIds={selectedProfileIds}
                    onToggleProfileSelection={handleToggleProfileSelection}
                    onToggleVisibleSelection={handleToggleVisibleSelection}
                    onClearSelection={() => {
                      setBulkFeedback(null);
                      setSelectedProfileIds(new Set());
                    }}
                    previewProfileId={previewProfile?.id ?? null}
                    onPreviewProfile={setPreviewProfileId}
                    onCheckSelectedHealth={handleCheckSelectedHealth}
                    checkingSelectedHealth={bulkHealthChecking}
                    bulkFeedback={bulkFeedback}
                    onLaunchSelectedProfiles={handleLaunchSelectedProfiles}
                    launchingSelectedProfiles={bulkLaunching}
                    onStopSelectedProfiles={handleStopSelectedProfiles}
                    stoppingSelectedProfiles={bulkStopping}
                    onAddTagsToSelectedProfiles={handleAddTagsToSelectedProfiles}
                    taggingSelectedProfiles={bulkTagging}
                    onDeleteSelectedProfiles={handleDeleteSelectedProfiles}
                    deletingSelectedProfiles={bulkDeleting}
                    totalProfileCount={profiles.length}
                    hasActiveFilters={hasActiveFilters}
                    onCreateProfile={handleNew}
                    onClearFilters={() => setFilters(defaultProfileFilters)}
                  />
                </div>
                <div className="min-h-[360px] min-w-0 lg:min-h-0">
                  <ProfileSummaryPanel
                    profile={previewProfile}
                    health={previewProfile ? healthByProfileId[previewProfile.id] : undefined}
                    onOpenProfile={handleSelect}
                  />
                </div>
              </section>
            </div>
          )}

          {section === "profiles" && view === "create" && (
            <ProfileForm
              profile={null}
              templates={profileTemplates}
              onSave={handleCreate}
              onCancel={() => setView("empty")}
            />
          )}

          {section === "profiles" && view === "edit" && selected && (
            <ProfileForm
              profile={selected}
              onSave={handleUpdate}
              onDelete={handleDelete}
              onCancel={() => {
                setSelectedId(null);
                setView("empty");
              }}
            />
          )}

          {section === "profiles" && view === "view" && selected && selected.status === "running" && (
            <ProfileViewer
              key={selected.id}
              profileId={selected.id}
              automationUrl={selected.automation_url}
              clipboardSync={selected.clipboard_sync}
              onDisconnect={handleVncDisconnect}
            />
          )}
        </div>
      </div>
      {profileImportDialogOpen && (
        <ProfileCsvPreviewDialog onClose={() => setProfileImportDialogOpen(false)} />
      )}
    </div>
  );
}

function SummaryTile({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: number;
  tone?: "neutral" | "success" | "warning" | "danger";
}) {
  const toneClassName = {
    neutral: "border-slate-200 bg-white text-slate-700 before:bg-slate-300",
    success: "border-emerald-200 bg-emerald-50/80 text-emerald-700 before:bg-emerald-500",
    warning: "border-amber-200 bg-amber-50/80 text-amber-800 before:bg-amber-500",
    danger: "border-red-200 bg-red-50/80 text-red-700 before:bg-red-500",
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
