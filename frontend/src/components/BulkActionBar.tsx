import { Activity, HeartPulse, Play, Square, Tags, Trash2, X } from "lucide-react";
import type { ReactNode } from "react";
import type { Profile, ProfileHealthResponse } from "../lib/api";

interface BulkActionBarProps {
  selectedCount: number;
  selectedProfiles: Profile[];
  healthByProfileId: Record<string, ProfileHealthResponse | undefined>;
  onClearSelection?: () => void;
  onCheckHealth?: () => Promise<void> | void;
  checkingHealth?: boolean;
  onLaunch?: () => Promise<void> | void;
  launching?: boolean;
  onStop?: () => Promise<void> | void;
  stopping?: boolean;
}

export function BulkActionBar({
  selectedCount,
  selectedProfiles,
  healthByProfileId,
  onClearSelection,
  onCheckHealth,
  checkingHealth = false,
  onLaunch,
  launching = false,
  onStop,
  stopping = false,
}: BulkActionBarProps) {
  if (selectedCount === 0) return null;

  const runningCount = selectedProfiles.filter((profile) => profile.status === "running").length;
  const stoppedCount = selectedProfiles.filter((profile) => profile.status === "stopped").length;
  const issueCount = selectedProfiles.filter((profile) => {
    const status = healthByProfileId[profile.id]?.status;
    return status === "error" || status === "warning";
  }).length;

  return (
    <div
      role="toolbar"
      aria-label="Bulk profile actions"
      className="sticky top-0 z-20 flex h-11 items-center gap-2 overflow-x-auto border-b border-slate-200 bg-white/95 px-3 text-xs shadow-[0_8px_18px_rgba(15,23,42,0.06)] backdrop-blur"
    >
      <span className="inline-flex h-7 shrink-0 items-center rounded-md border border-blue-200 bg-blue-50 px-2.5 font-semibold tabular-nums text-blue-800">
        {selectedCount} selected
      </span>
      <SummaryPill icon={<Activity className="h-3.5 w-3.5" />} label={`${runningCount} running`} />
      <SummaryPill label={`${stoppedCount} stopped`} />
      <SummaryPill label={`${issueCount} issue${issueCount === 1 ? "" : "s"}`} tone={issueCount > 0 ? "warning" : "muted"} />
      <div className="ml-auto flex items-center gap-1.5">
        <button
          type="button"
          disabled={!onCheckHealth || checkingHealth}
          aria-label={checkingHealth ? "Checking health" : "Check health"}
          className="inline-flex h-7 shrink-0 items-center gap-1 whitespace-nowrap rounded-md border border-blue-600 bg-blue-600 px-2.5 font-medium text-white shadow-[0_1px_2px_rgba(37,99,235,0.25)] transition-colors hover:border-blue-700 hover:bg-blue-700 disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-100 disabled:text-slate-400 disabled:shadow-none"
          onClick={() => void onCheckHealth?.()}
        >
          <HeartPulse className="h-3.5 w-3.5" />
          <span>{checkingHealth ? "Checking..." : "Check health"}</span>
        </button>
        <button
          type="button"
          disabled={!onLaunch || launching || stoppedCount === 0}
          aria-label={launching ? "Launching selected" : "Launch selected"}
          className="inline-flex h-7 shrink-0 items-center gap-1 whitespace-nowrap rounded-md border border-slate-200 bg-white px-2.5 font-medium text-slate-700 shadow-[0_1px_1px_rgba(15,23,42,0.04)] transition-colors hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400 disabled:shadow-none"
          onClick={() => void onLaunch?.()}
        >
          <Play className="h-3.5 w-3.5" />
          <span>{launching ? "Launching..." : "Launch selected"}</span>
        </button>
        <button
          type="button"
          disabled={!onStop || stopping || runningCount === 0}
          aria-label={stopping ? "Stopping selected" : "Stop selected"}
          className="inline-flex h-7 shrink-0 items-center gap-1 whitespace-nowrap rounded-md border border-slate-200 bg-white px-2.5 font-medium text-slate-700 shadow-[0_1px_1px_rgba(15,23,42,0.04)] transition-colors hover:border-amber-200 hover:bg-amber-50 hover:text-amber-800 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400 disabled:shadow-none"
          onClick={() => void onStop?.()}
        >
          <Square className="h-3.5 w-3.5" />
          <span>{stopping ? "Stopping..." : "Stop selected"}</span>
        </button>
        <DisabledAction icon={<Tags className="h-3.5 w-3.5" />} label="Tag selected" />
        <DisabledAction icon={<Trash2 className="h-3.5 w-3.5" />} label="Delete selected" danger />
        {onClearSelection && (
          <button
            type="button"
            className="inline-flex h-7 shrink-0 items-center gap-1 whitespace-nowrap rounded-md border border-slate-200 bg-white px-2.5 font-medium text-slate-600 shadow-[0_1px_1px_rgba(15,23,42,0.04)] transition-colors hover:border-slate-300 hover:bg-slate-50 hover:text-slate-950"
            onClick={onClearSelection}
          >
            <X className="h-3.5 w-3.5" />
            Clear
          </button>
        )}
      </div>
    </div>
  );
}

function SummaryPill({
  icon,
  label,
  tone = "muted",
}: {
  icon?: ReactNode;
  label: string;
  tone?: "muted" | "warning";
}) {
  return (
    <span
      className={`inline-flex h-7 shrink-0 items-center gap-1 rounded-md border px-2 font-medium ${
        tone === "warning"
          ? "border-amber-200 bg-amber-50 text-amber-800"
          : "border-slate-200 bg-slate-50 text-slate-600"
      }`}
    >
      {icon}
      {label}
    </span>
  );
}

function DisabledAction({
  icon,
  label,
  danger = false,
}: {
  icon: ReactNode;
  label: string;
  danger?: boolean;
}) {
  return (
    <button
      type="button"
      disabled
      aria-label={label}
      className={`inline-flex h-7 shrink-0 cursor-not-allowed items-center gap-1 whitespace-nowrap rounded-md border px-2.5 font-medium ${
        danger
          ? "border-red-100 bg-red-50/70 text-red-400"
          : "border-slate-200 bg-slate-50 text-slate-400"
      }`}
    >
      {icon}
      <span>{label}</span>
    </button>
  );
}
