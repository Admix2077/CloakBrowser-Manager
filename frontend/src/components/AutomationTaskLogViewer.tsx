import { AlertCircle, CheckCircle2, Clock, ListChecks, RefreshCw, XCircle } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { api, type AutomationTask, type AutomationTaskResultStep, type AutomationTaskStep } from "../lib/api";
import { formatTimestamp } from "../lib/profileDisplay";

const DEFAULT_TASK_LIMIT = 50;

const STATUS_STYLES: Record<string, string> = {
  queued: "border-slate-200 bg-slate-50 text-slate-700",
  running: "border-blue-200 bg-blue-50 text-blue-700",
  succeeded: "border-emerald-200 bg-emerald-50 text-emerald-700",
  failed: "border-red-200 bg-red-50 text-red-700",
  cancelled: "border-amber-200 bg-amber-50 text-amber-700",
};

export function AutomationTaskLogViewer() {
  const [tasks, setTasks] = useState<AutomationTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadTasks = useCallback(async ({ quiet = false }: { quiet?: boolean } = {}) => {
    if (quiet) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    setError(null);

    try {
      const response = await api.listAutomationTasks({ limit: DEFAULT_TASK_LIMIT });
      setTasks(response.tasks);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load automation tasks");
    } finally {
      if (quiet) {
        setRefreshing(false);
      } else {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    void loadTasks();
  }, [loadTasks]);

  const stats = useMemo(() => {
    const running = tasks.filter((task) => task.status === "running").length;
    const failed = tasks.filter((task) => task.status === "failed").length;
    const finished = tasks.filter((task) => task.status === "succeeded" || task.status === "cancelled").length;
    return { total: tasks.length, running, failed, finished };
  }, [tasks]);

  return (
    <section
      role="region"
      aria-label="Automation tasks"
      className="flex h-full min-h-0 flex-col gap-3 p-3 sm:p-4 lg:p-5"
    >
      <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_auto] xl:items-end">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <ListChecks className="h-4 w-4 text-blue-600" />
            <h2 className="text-xl font-semibold tracking-tight text-slate-950">Automation tasks</h2>
          </div>
          <p className="mt-1 text-sm text-slate-600">
            Read-only task log with redacted step payloads and result summaries.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <TaskStat label="Recent" value={stats.total} />
          <TaskStat label="Running" value={stats.running} tone="blue" />
          <TaskStat label="Finished" value={stats.finished} tone="green" />
          <TaskStat label="Failed" value={stats.failed} tone="red" />
        </div>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-3 shadow-[0_1px_2px_rgba(15,23,42,0.04),inset_0_1px_0_rgba(255,255,255,0.9)]">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">Trusted management API</p>
            <p className="mt-1 text-sm text-slate-600">
              Showing latest {DEFAULT_TASK_LIMIT} tasks. Steps display only low-risk fields.
            </p>
          </div>
          <button
            type="button"
            onClick={() => void loadTasks({ quiet: true })}
            disabled={refreshing}
            className="btn-secondary inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap disabled:cursor-not-allowed disabled:opacity-60"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`} />
            Refresh automation tasks
          </button>
        </div>
      </div>

      {error && (
        <div
          role="alert"
          className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
        >
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <div
        role="region"
        aria-label="Automation task log table"
        className="min-h-[420px] min-w-0 flex-1 overflow-auto rounded-lg border border-slate-200 bg-white shadow-[0_8px_24px_rgba(15,23,42,0.05),inset_0_1px_0_rgba(255,255,255,0.9)]"
      >
        {loading ? (
          <div
            role="status"
            aria-label="Loading automation tasks"
            className="flex h-full min-h-[320px] items-center justify-center text-sm text-slate-500"
          >
            Loading automation tasks...
          </div>
        ) : tasks.length === 0 ? (
          <div
            role="status"
            aria-label="No automation tasks yet"
            className="flex h-full min-h-[320px] flex-col items-center justify-center px-4 text-center"
          >
            <Clock className="h-8 w-8 text-slate-300" />
            <p className="mt-3 text-sm font-semibold text-slate-900">No automation tasks yet</p>
            <p className="mt-1 max-w-md text-sm text-slate-500">
              Queued scripts will appear here after they are created through the trusted management API.
            </p>
          </div>
        ) : (
          <table aria-label="Automation task log" className="min-w-[1080px] w-full border-separate border-spacing-0 bg-white text-left text-xs text-slate-700">
            <thead className="sticky top-0 z-10 bg-[#fbfdff]/95 backdrop-blur">
              <tr className="text-slate-500 shadow-[inset_0_-1px_0_rgba(148,163,184,0.24)]">
                <HeaderCell>Task</HeaderCell>
                <HeaderCell>Profile</HeaderCell>
                <HeaderCell>Status</HeaderCell>
                <HeaderCell>Steps</HeaderCell>
                <HeaderCell>Result</HeaderCell>
                <HeaderCell>Error</HeaderCell>
                <HeaderCell>Created</HeaderCell>
                <HeaderCell>Finished</HeaderCell>
              </tr>
            </thead>
            <tbody>
              {tasks.map((task) => (
                <tr
                  key={task.id}
                  className="group transition-[background-color,box-shadow] odd:bg-white even:bg-slate-50/30 hover:bg-slate-100/60"
                  style={{ height: 76 }}
                >
                  <BodyCell>
                    <span className="font-mono text-[11px] font-semibold text-slate-900">{shortId(task.id)}</span>
                  </BodyCell>
                  <BodyCell>
                    <span className="font-mono text-[11px] text-slate-600">{shortId(task.profile_id)}</span>
                  </BodyCell>
                  <BodyCell>
                    <StatusPill status={task.status} />
                  </BodyCell>
                  <BodyCell>
                    <StepList steps={task.steps} />
                  </BodyCell>
                  <BodyCell>
                    <ResultList steps={task.result?.steps ?? []} />
                  </BodyCell>
                  <BodyCell>
                    <span className="line-clamp-2 text-slate-600">{task.error ?? "-"}</span>
                  </BodyCell>
                  <BodyCell>
                    <span className="text-slate-500">{formatTimestamp(task.created_at)}</span>
                  </BodyCell>
                  <BodyCell>
                    <span className="text-slate-500">{formatTimestamp(task.finished_at)}</span>
                  </BodyCell>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}

function TaskStat({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: number;
  tone?: "neutral" | "blue" | "green" | "red";
}) {
  const toneClass = {
    neutral: "border-slate-200 bg-white text-slate-950",
    blue: "border-blue-100 bg-blue-50 text-blue-700",
    green: "border-emerald-100 bg-emerald-50 text-emerald-700",
    red: "border-red-100 bg-red-50 text-red-700",
  }[tone];

  return (
    <div className={`rounded-lg border px-3 py-2 shadow-[0_1px_2px_rgba(15,23,42,0.04)] ${toneClass}`}>
      <div className="text-lg font-semibold tabular-nums">{value}</div>
      <div className="text-[10px] font-semibold uppercase tracking-[0.08em] text-slate-500">{label}</div>
    </div>
  );
}

function HeaderCell({ children }: { children: React.ReactNode }) {
  return (
    <th className="h-9 truncate border-b border-slate-200 bg-[#fbfdff]/95 px-2 py-2 text-[10px] font-semibold uppercase tracking-[0.08em] text-slate-500">
      {children}
    </th>
  );
}

function BodyCell({ children }: { children: React.ReactNode }) {
  return (
    <td className="border-b border-slate-100 px-2 py-2 align-top">
      {children}
    </td>
  );
}

function StatusPill({ status }: { status: string }) {
  const icon = status === "succeeded"
    ? <CheckCircle2 className="h-3.5 w-3.5" />
    : status === "failed" || status === "cancelled"
      ? <XCircle className="h-3.5 w-3.5" />
      : <Clock className="h-3.5 w-3.5" />;

  return (
    <span className={`inline-flex items-center gap-1 rounded-[999px] border px-2 py-0.5 text-[11px] font-semibold ${STATUS_STYLES[status] ?? STATUS_STYLES.queued}`}>
      {icon}
      {status}
    </span>
  );
}

function StepList({ steps }: { steps: AutomationTaskStep[] }) {
  if (steps.length === 0) return <span className="text-slate-400">-</span>;

  return (
    <div className="flex max-w-[320px] flex-col gap-1">
      {steps.slice(0, 4).map((step, index) => (
        <div key={`${step.type}-${index}`} className="flex flex-wrap items-center gap-1.5">
          <span className="rounded-[5px] border border-slate-200 bg-slate-50 px-1.5 py-0.5 font-mono text-[11px] font-semibold text-slate-700">
            {safeLabel(step.type)}
          </span>
          {stepSummary(step).map((item) => (
            <span key={item} className="rounded-[5px] bg-slate-100 px-1.5 py-0.5 text-[11px] text-slate-600">
              {item}
            </span>
          ))}
        </div>
      ))}
      {steps.length > 4 && (
        <span className="text-[11px] text-slate-500">+{steps.length - 4} more steps</span>
      )}
    </div>
  );
}

function ResultList({ steps }: { steps: AutomationTaskResultStep[] }) {
  if (steps.length === 0) return <span className="text-slate-400">-</span>;

  return (
    <div className="flex max-w-[260px] flex-col gap-1">
      {steps.slice(0, 4).map((step) => (
        <span key={`${step.index}-${step.type}-${step.status}`} className="font-mono text-[11px] text-slate-700">
          {step.index} {safeLabel(step.type)} {safeLabel(step.status)}
        </span>
      ))}
      {steps.length > 4 && (
        <span className="text-[11px] text-slate-500">+{steps.length - 4} more results</span>
      )}
    </div>
  );
}

function stepSummary(step: AutomationTaskStep): string[] {
  const parts: string[] = [];
  if (typeof step.page_ref === "string") parts.push(`page ${safeLabel(step.page_ref)}`);
  if (typeof step.ms === "number") parts.push(`${step.ms}ms`);
  if (typeof step.wait_until === "string") parts.push(`wait_until ${safeLabel(step.wait_until)}`);
  if (typeof step.state === "string") parts.push(`state ${safeLabel(step.state)}`);
  if (typeof step.timeout_ms === "number") parts.push(`timeout ${step.timeout_ms}ms`);
  if (typeof step.delay_ms === "number") parts.push(`delay ${step.delay_ms}ms`);
  if (typeof step.delta_x === "number" || typeof step.delta_y === "number") {
    parts.push(`delta ${typeof step.delta_x === "number" ? step.delta_x : 0}/${typeof step.delta_y === "number" ? step.delta_y : 0}`);
  }
  if (typeof step.full_page === "boolean") parts.push(step.full_page ? "full page" : "viewport");
  return parts;
}

function shortId(value: string): string {
  if (!value) return "-";
  return value.length > 8 ? `${value.slice(0, 8)}...` : value;
}

function safeLabel(value: string): string {
  return value.replace(/[^a-zA-Z0-9_.:-]/g, "").slice(0, 40) || "-";
}
