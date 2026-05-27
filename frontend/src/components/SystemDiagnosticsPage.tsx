import { useCallback, useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { api, type SystemDiagnostics } from "../lib/api";

export function SystemDiagnosticsPage() {
  const [diagnostics, setDiagnostics] = useState<SystemDiagnostics | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  const loadDiagnostics = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      setDiagnostics(await api.getDiagnostics());
    } catch {
      setDiagnostics(null);
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadDiagnostics();
  }, [loadDiagnostics]);

  return (
    <section
      aria-label="System diagnostics"
      className="flex h-full min-h-0 flex-col gap-4 p-3 sm:p-4 lg:p-5"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-xl font-semibold tracking-tight text-slate-950">System diagnostics</h2>
          <p className="mt-1 text-sm text-slate-600">
            Runtime counts, storage checks, and worker settings from the protected diagnostics API.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void loadDiagnostics()}
          disabled={loading}
          className="btn-secondary inline-flex h-8 shrink-0 items-center gap-1.5 text-xs disabled:cursor-not-allowed disabled:opacity-60"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh diagnostics
        </button>
      </div>

      {error && (
        <div role="alert" className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          Unable to load diagnostics
        </div>
      )}

      {!diagnostics && !error && (
        <div role="status" aria-label="Loading diagnostics" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {[0, 1, 2, 3].map((index) => (
            <div key={index} data-skeleton className="h-24 rounded-lg border border-slate-200 bg-white" />
          ))}
        </div>
      )}

      {diagnostics && (
        <div className="grid min-h-0 gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
          <div className="min-w-0 space-y-4">
            <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-[0_1px_2px_rgba(15,23,42,0.04),inset_0_1px_0_rgba(255,255,255,0.9)]">
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <DiagnosticTile label="Status" value={diagnostics.status} tone="success" />
                <DiagnosticTile label="Profiles" value={diagnostics.counts.profiles_total} />
                <DiagnosticTile label="Running" value={diagnostics.counts.running} tone="success" />
                <DiagnosticTile label="Launching" value={diagnostics.counts.launching} />
                <DiagnosticTile label="Failed tasks" value={diagnostics.counts.failed_tasks} tone="warning" />
                <DiagnosticTile label="Queued tasks" value={diagnostics.counts.queued_tasks} />
                <DiagnosticTile label="Proxies" value={diagnostics.counts.proxy_count} />
                <DiagnosticTile label="Max running" value={diagnostics.runtime.max_running_profiles ?? "unlimited"} />
              </div>
            </section>

            <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-[0_1px_2px_rgba(15,23,42,0.04),inset_0_1px_0_rgba(255,255,255,0.9)]">
              <h3 className="text-sm font-semibold text-slate-950">Runtime</h3>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                <InfoRow label="Active displays" value={formatDisplays(diagnostics.runtime.active_displays)} />
                <InfoRow label="Active VNC ports" value={formatNumbers(diagnostics.runtime.active_vnc_ws_ports)} />
              </div>
            </section>
          </div>

          <aside className="min-w-0 space-y-4">
            <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-[0_1px_2px_rgba(15,23,42,0.04),inset_0_1px_0_rgba(255,255,255,0.9)]">
              <h3 className="text-sm font-semibold text-slate-950">Storage</h3>
              <div className="mt-3 space-y-2">
                <InfoRow label="Data directory" value={diagnostics.storage.data_dir_exists ? "available" : "missing"} />
                <InfoRow label="Database" value={diagnostics.storage.db_exists ? "available" : "missing"} />
                <InfoRow label="Binary" value={diagnostics.binary_version} />
              </div>
            </section>

            <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-[0_1px_2px_rgba(15,23,42,0.04),inset_0_1px_0_rgba(255,255,255,0.9)]">
              <h3 className="text-sm font-semibold text-slate-950">Automation worker</h3>
              <div className="mt-3 space-y-2">
                <InfoRow label="State" value={diagnostics.automation_worker.enabled ? "enabled" : "disabled"} />
                <InfoRow label="Lease" value={`${diagnostics.automation_worker.lease_seconds}s`} />
                <InfoRow label="Idle sleep" value={`${diagnostics.automation_worker.idle_sleep_seconds}s`} />
                <InfoRow label="Shutdown wait" value={`${diagnostics.automation_worker.shutdown_timeout_seconds}s`} />
              </div>
            </section>

            <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-[0_1px_2px_rgba(15,23,42,0.04),inset_0_1px_0_rgba(255,255,255,0.9)]">
              <h3 className="text-sm font-semibold text-slate-950">Task status counts</h3>
              <div className="mt-3 space-y-2">
                {Object.entries(diagnostics.counts.automation_task_counts).length === 0 ? (
                  <InfoRow label="Tasks" value="none" />
                ) : (
                  Object.entries(diagnostics.counts.automation_task_counts)
                    .sort(([left], [right]) => left.localeCompare(right))
                    .map(([status, count]) => (
                      <InfoRow key={status} label={status.replaceAll("_", " ")} value={count} />
                    ))
                )}
              </div>
            </section>
          </aside>
        </div>
      )}
    </section>
  );
}

function DiagnosticTile({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: number | string;
  tone?: "neutral" | "success" | "warning";
}) {
  const toneClassName = {
    neutral: "border-slate-200 bg-white text-slate-700 before:bg-slate-300",
    success: "border-emerald-200 bg-emerald-50/80 text-emerald-700 before:bg-emerald-500",
    warning: "border-amber-200 bg-amber-50/80 text-amber-800 before:bg-amber-500",
  }[tone];

  return (
    <div
      role="group"
      aria-label={`${label}: ${value}`}
      className={`relative overflow-hidden rounded-lg border px-3 py-2 shadow-[0_1px_2px_rgba(15,23,42,0.04),inset_0_1px_0_rgba(255,255,255,0.8)] before:absolute before:inset-x-0 before:top-0 before:h-0.5 ${toneClassName}`}
    >
      <div className="text-lg font-semibold leading-5 tabular-nums">{value}</div>
      <div className="mt-1 text-[10px] font-semibold uppercase tracking-[0.1em] opacity-75">
        {label}
      </div>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: number | string }) {
  return (
    <div
      role="group"
      aria-label={`${label}: ${value}`}
      className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 rounded-md border border-slate-100 bg-slate-50/70 px-3 py-2"
    >
      <span className="truncate text-xs font-medium text-slate-500">{label}</span>
      <span className="max-w-[180px] truncate text-right text-xs font-semibold tabular-nums text-slate-800">
        {value}
      </span>
    </div>
  );
}

function formatNumbers(values: number[]): string {
  return values.length > 0 ? values.join(", ") : "none";
}

function formatDisplays(values: number[]): string {
  return values.length > 0 ? values.map((value) => `:${value}`).join(", ") : "none";
}
