import { Activity, HeartPulse, Play, Square, Tags, Trash2, X } from "lucide-react";
import type { ReactNode } from "react";
import { useEffect, useRef, useState } from "react";
import type { Profile, ProfileHealthResponse } from "../lib/api";

const DEFAULT_BULK_TAG_COLOR = "#6366f1";

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
  onAddTags?: (tags: Profile["tags"]) => Promise<void> | void;
  tagging?: boolean;
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
  onAddTags,
  tagging = false,
}: BulkActionBarProps) {
  const [tagEditorOpen, setTagEditorOpen] = useState(false);
  const [tagName, setTagName] = useState("");
  const tagInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (tagEditorOpen) tagInputRef.current?.focus();
  }, [tagEditorOpen]);

  if (selectedCount === 0) return null;

  const runningCount = selectedProfiles.filter((profile) => profile.status === "running").length;
  const stoppedCount = selectedProfiles.filter((profile) => profile.status === "stopped").length;
  const issueCount = selectedProfiles.filter((profile) => {
    const status = healthByProfileId[profile.id]?.status;
    return status === "error" || status === "warning";
  }).length;
  const normalizedTagName = tagName.trim();

  const handleTagSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!onAddTags || !normalizedTagName || tagging) return;
    const result = onAddTags([{ tag: normalizedTagName, color: DEFAULT_BULK_TAG_COLOR }]);
    void Promise.resolve(result).then(() => {
      setTagName("");
      setTagEditorOpen(false);
    }).catch(() => undefined);
  };

  return (
    <div
      role="toolbar"
      aria-label="Bulk profile actions"
      aria-busy={checkingHealth || launching || stopping || tagging}
      className="sticky top-0 z-20 flex h-11 items-center gap-2 overflow-x-auto border-b border-blue-100/80 bg-gradient-to-r from-white via-blue-50/70 to-white px-2.5 text-xs shadow-[0_12px_28px_rgba(15,23,42,0.08)] backdrop-blur"
    >
      <span
        role="status"
        aria-label="Selected profile summary"
        className="inline-flex h-7 shrink-0 items-center rounded-md border border-blue-200 bg-gradient-to-b from-blue-50 to-blue-100/80 px-2.5 font-semibold tabular-nums text-blue-800 shadow-[0_1px_2px_rgba(37,99,235,0.08),inset_0_1px_0_rgba(255,255,255,0.9)]"
      >
        {selectedCount} selected
      </span>
      <SummaryPill icon={<Activity className="h-3.5 w-3.5" />} label={`${runningCount} running`} />
      <SummaryPill label={`${stoppedCount} stopped`} />
      <SummaryPill label={`${issueCount} issue${issueCount === 1 ? "" : "s"}`} tone={issueCount > 0 ? "warning" : "muted"} />
      <div className="ml-auto flex items-center gap-1 rounded-lg border border-slate-200/90 bg-white/80 p-1 shadow-[0_1px_2px_rgba(15,23,42,0.05),inset_0_1px_0_rgba(255,255,255,0.9)] ring-1 ring-slate-900/[0.02]">
        <button
          type="button"
          disabled={!onCheckHealth || checkingHealth}
          aria-label={checkingHealth ? "Checking health" : "Check health"}
          className="inline-flex h-7 shrink-0 items-center gap-1 whitespace-nowrap rounded-md border border-blue-600 bg-blue-600 px-2.5 font-medium text-white shadow-[0_1px_2px_rgba(37,99,235,0.25),inset_0_1px_0_rgba(255,255,255,0.18)] transition-colors hover:border-blue-700 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500/25 disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-100 disabled:text-slate-400 disabled:shadow-none"
          onClick={() => void onCheckHealth?.()}
        >
          <HeartPulse className="h-3.5 w-3.5" />
          <span>{checkingHealth ? "Checking..." : "Check health"}</span>
        </button>
        <button
          type="button"
          disabled={!onLaunch || launching || stoppedCount === 0}
          aria-label={launching ? "Launching selected" : "Launch selected"}
          className="inline-flex h-7 shrink-0 items-center gap-1 whitespace-nowrap rounded-md border border-slate-200 bg-white px-2.5 font-medium text-slate-700 shadow-[0_1px_1px_rgba(15,23,42,0.04)] transition-colors hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-50 disabled:text-slate-400 disabled:shadow-none"
          onClick={() => void onLaunch?.()}
        >
          <Play className="h-3.5 w-3.5" />
          <span>{launching ? "Launching..." : "Launch"}</span>
        </button>
        <button
          type="button"
          disabled={!onStop || stopping || runningCount === 0}
          aria-label={stopping ? "Stopping selected" : "Stop selected"}
          className="inline-flex h-7 shrink-0 items-center gap-1 whitespace-nowrap rounded-md border border-slate-200 bg-white px-2.5 font-medium text-slate-700 shadow-[0_1px_1px_rgba(15,23,42,0.04)] transition-colors hover:border-amber-200 hover:bg-amber-50 hover:text-amber-800 focus:outline-none focus:ring-2 focus:ring-amber-500/20 disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-50 disabled:text-slate-400 disabled:shadow-none"
          onClick={() => void onStop?.()}
        >
          <Square className="h-3.5 w-3.5" />
          <span>{stopping ? "Stopping..." : "Stop"}</span>
        </button>
        {tagEditorOpen ? (
          <form
            aria-label="Bulk tag form"
            className="flex shrink-0 items-center gap-1 rounded-md border border-blue-100 bg-white p-0.5 shadow-[0_1px_2px_rgba(37,99,235,0.08)] ring-2 ring-blue-500/10"
            onSubmit={handleTagSubmit}
          >
            <input
              ref={tagInputRef}
              aria-label="Bulk tag name"
              value={tagName}
              onChange={(event) => setTagName(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Escape" && !tagging) {
                  setTagName("");
                  setTagEditorOpen(false);
                }
              }}
              className="h-7 w-36 rounded-md border border-slate-200 bg-slate-50/80 px-2 text-xs font-medium text-slate-700 shadow-[inset_0_1px_0_rgba(255,255,255,0.85)] outline-none transition-colors placeholder:text-slate-400 hover:border-slate-300 focus:border-blue-500 focus:bg-white focus:ring-2 focus:ring-blue-500/15"
              placeholder="Tag name"
              disabled={tagging}
            />
            <button
              type="submit"
              disabled={!normalizedTagName || tagging}
              aria-label={tagging ? "Applying tag" : "Apply tag"}
              className="inline-flex h-7 shrink-0 items-center gap-1 whitespace-nowrap rounded-md border border-blue-600 bg-blue-600 px-2.5 font-medium text-white shadow-[0_1px_2px_rgba(37,99,235,0.22)] transition-colors hover:border-blue-700 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-100 disabled:text-slate-400 disabled:shadow-none"
            >
              <Tags className="h-3.5 w-3.5" />
              {tagging ? "Applying..." : "Apply tag"}
            </button>
            <button
              type="button"
              aria-label="Cancel tagging"
              disabled={tagging}
              className="inline-flex h-7 shrink-0 items-center gap-1 whitespace-nowrap rounded-md border border-transparent bg-white px-2 font-medium text-slate-500 transition-colors hover:bg-slate-50 hover:text-slate-950 focus:outline-none focus:ring-2 focus:ring-slate-500/15 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400 disabled:shadow-none"
              onClick={() => {
                setTagName("");
                setTagEditorOpen(false);
              }}
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </form>
        ) : (
          <button
            type="button"
            disabled={!onAddTags || tagging}
            aria-label={tagging ? "Applying tag" : "Tag selected"}
            className="inline-flex h-7 shrink-0 items-center gap-1 whitespace-nowrap rounded-md border border-slate-200 bg-white px-2.5 font-medium text-slate-700 shadow-[0_1px_1px_rgba(15,23,42,0.04)] transition-colors hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-50 disabled:text-slate-400 disabled:shadow-none"
            onClick={() => setTagEditorOpen(true)}
          >
            <Tags className="h-3.5 w-3.5" />
            <span>{tagging ? "Applying..." : "Tag"}</span>
          </button>
        )}
        <DisabledAction icon={<Trash2 className="h-3.5 w-3.5" />} label="Delete selected" displayLabel="Delete" danger />
        {onClearSelection && (
          <>
            <span aria-hidden="true" className="mx-0.5 h-5 w-px bg-slate-200" />
            <button
              type="button"
              className="inline-flex h-7 shrink-0 items-center gap-1 whitespace-nowrap rounded-md border border-transparent bg-transparent px-2.5 font-medium text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-950 focus:outline-none focus:ring-2 focus:ring-slate-500/15"
              onClick={onClearSelection}
            >
              <X className="h-3.5 w-3.5" />
              Clear
            </button>
          </>
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
          ? "border-amber-200 bg-amber-50 text-amber-800 shadow-[inset_0_1px_0_rgba(255,255,255,0.85)]"
          : "border-slate-200 bg-white/85 text-slate-600 shadow-[inset_0_1px_0_rgba(255,255,255,0.85)]"
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
  displayLabel = label,
  danger = false,
}: {
  icon: ReactNode;
  label: string;
  displayLabel?: string;
  danger?: boolean;
}) {
  return (
    <button
      type="button"
      disabled
      aria-label={label}
      className={`inline-flex h-7 shrink-0 cursor-not-allowed items-center gap-1 whitespace-nowrap rounded-md border px-2.5 font-medium ${
        danger
          ? "border-red-100 bg-red-50/35 text-red-300"
          : "border-slate-200 bg-white/70 text-slate-400"
      }`}
    >
      {icon}
      <span>{displayLabel}</span>
    </button>
  );
}
