import { Activity, HeartPulse, Play, Square, Tags, Trash2, X } from "lucide-react";
import type { ReactNode } from "react";
import type { Profile, ProfileHealthResponse } from "../lib/api";

interface BulkActionBarProps {
  selectedCount: number;
  selectedProfiles: Profile[];
  healthByProfileId: Record<string, ProfileHealthResponse | undefined>;
  onClearSelection?: () => void;
}

export function BulkActionBar({
  selectedCount,
  selectedProfiles,
  healthByProfileId,
  onClearSelection,
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
      className="sticky top-0 z-20 flex h-10 items-center gap-3 border-b border-border bg-surface-1 px-3 text-xs"
    >
      <span className="font-medium text-gray-200">{selectedCount} selected</span>
      <SummaryPill icon={<Activity className="h-3.5 w-3.5" />} label={`${runningCount} running`} />
      <SummaryPill label={`${stoppedCount} stopped`} />
      <SummaryPill label={`${issueCount} issue${issueCount === 1 ? "" : "s"}`} tone={issueCount > 0 ? "warning" : "muted"} />
      <div className="ml-auto flex items-center gap-2">
        <DisabledAction icon={<HeartPulse className="h-3.5 w-3.5" />} label="Check health" />
        <DisabledAction icon={<Play className="h-3.5 w-3.5" />} label="Launch selected" />
        <DisabledAction icon={<Square className="h-3.5 w-3.5" />} label="Stop selected" />
        <DisabledAction icon={<Tags className="h-3.5 w-3.5" />} label="Tag selected" />
        <DisabledAction icon={<Trash2 className="h-3.5 w-3.5" />} label="Delete selected" danger />
        {onClearSelection && (
          <button
            type="button"
            className="inline-flex items-center gap-1 rounded-md border border-border bg-surface-2 px-2 py-1 text-gray-300 transition-colors hover:border-border-hover hover:bg-surface-3"
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
          ? "border-amber-500/25 bg-amber-500/10 text-amber-300"
          : "border-border bg-surface-2 text-gray-400"
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
      className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 opacity-60 ${
        danger
          ? "border-red-500/20 bg-red-500/10 text-red-300"
          : "border-border bg-surface-2 text-gray-400"
      }`}
    >
      {icon}
      <span>{label}</span>
    </button>
  );
}
