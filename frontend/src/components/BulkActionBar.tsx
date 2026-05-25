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
}

export function BulkActionBar({
  selectedCount,
  selectedProfiles,
  healthByProfileId,
  onClearSelection,
  onCheckHealth,
  checkingHealth = false,
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
      className="sticky top-0 z-20 flex h-11 items-center gap-3 overflow-x-auto border-b border-blue-100 bg-blue-50/95 px-3 text-xs backdrop-blur"
    >
      <span className="font-semibold text-blue-900">{selectedCount} selected</span>
      <SummaryPill icon={<Activity className="h-3.5 w-3.5" />} label={`${runningCount} running`} />
      <SummaryPill label={`${stoppedCount} stopped`} />
      <SummaryPill label={`${issueCount} issue${issueCount === 1 ? "" : "s"}`} tone={issueCount > 0 ? "warning" : "muted"} />
      <div className="ml-auto flex items-center gap-2">
        <button
          type="button"
          disabled={!onCheckHealth || checkingHealth}
          aria-label={checkingHealth ? "Checking health" : "Check health"}
          className="inline-flex items-center gap-1 rounded-lg border border-blue-200 bg-white px-2 py-1 font-medium text-blue-700 shadow-hairline transition-colors hover:border-blue-300 hover:bg-blue-100 disabled:cursor-not-allowed disabled:opacity-60"
          onClick={() => void onCheckHealth?.()}
        >
          <HeartPulse className="h-3.5 w-3.5" />
          <span>{checkingHealth ? "Checking..." : "Check health"}</span>
        </button>
        <DisabledAction icon={<Play className="h-3.5 w-3.5" />} label="Launch selected" />
        <DisabledAction icon={<Square className="h-3.5 w-3.5" />} label="Stop selected" />
        <DisabledAction icon={<Tags className="h-3.5 w-3.5" />} label="Tag selected" />
        <DisabledAction icon={<Trash2 className="h-3.5 w-3.5" />} label="Delete selected" danger />
        {onClearSelection && (
          <button
            type="button"
            className="inline-flex items-center gap-1 rounded-lg border border-blue-200 bg-white px-2 py-1 font-medium text-blue-700 shadow-hairline transition-colors hover:border-blue-300 hover:bg-blue-100"
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
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 ${
        tone === "warning"
          ? "border-amber-200 bg-amber-50 text-amber-800"
          : "border-blue-100 bg-white text-slate-600"
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
      className={`inline-flex items-center gap-1 rounded-lg border px-2 py-1 opacity-60 ${
        danger
          ? "border-red-200 bg-red-50 text-red-700"
          : "border-blue-100 bg-white text-slate-500"
      }`}
    >
      {icon}
      <span>{label}</span>
    </button>
  );
}
