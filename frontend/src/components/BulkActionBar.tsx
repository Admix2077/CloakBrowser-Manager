import { Activity, AlertTriangle, HeartPulse, Play, Square, Tags, Trash2, X } from "lucide-react";
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
  onDelete?: (ids: string[]) => Promise<void> | void;
  deleting?: boolean;
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
  onDelete,
  deleting = false,
}: BulkActionBarProps) {
  const [tagEditorOpen, setTagEditorOpen] = useState(false);
  const [tagName, setTagName] = useState("");
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState("");
  const tagInputRef = useRef<HTMLInputElement>(null);
  const deleteInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (tagEditorOpen) tagInputRef.current?.focus();
  }, [tagEditorOpen]);

  const runningCount = selectedProfiles.filter((profile) => profile.status === "running").length;
  const stoppedProfiles = selectedProfiles.filter((profile) => profile.status === "stopped");
  const stoppedCount = stoppedProfiles.length;
  const issueCount = selectedProfiles.filter((profile) => {
    const status = healthByProfileId[profile.id]?.status;
    return status === "error" || status === "warning";
  }).length;
  const normalizedTagName = tagName.trim();
  const deleteEnabled = Boolean(onDelete) && !deleting && stoppedCount > 0;
  const deleteTitle = !onDelete
    ? "Bulk delete is not available"
    : stoppedCount === 0
      ? "Stop running profiles before bulk deletion"
      : "Delete selected stopped profiles";
  const deleteConfirmReady = deleteConfirmText === "DELETE";

  useEffect(() => {
    if (!deleteConfirmOpen || stoppedCount > 0) return;
    setDeleteConfirmOpen(false);
    setDeleteConfirmText("");
  }, [deleteConfirmOpen, stoppedCount]);

  useEffect(() => {
    if (deleteConfirmOpen) deleteInputRef.current?.focus();
  }, [deleteConfirmOpen]);

  const handleTagSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!onAddTags || !normalizedTagName || tagging) return;
    const result = onAddTags([{ tag: normalizedTagName, color: DEFAULT_BULK_TAG_COLOR }]);
    void Promise.resolve(result).then(() => {
      setTagName("");
      setTagEditorOpen(false);
    }).catch(() => undefined);
  };

  const handleDeleteSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!onDelete || !deleteConfirmReady || deleting || stoppedCount === 0) return;
    const stoppedIds = stoppedProfiles.map((profile) => profile.id);
    void Promise.resolve(onDelete(stoppedIds)).then(() => {
      setDeleteConfirmText("");
      setDeleteConfirmOpen(false);
    }).catch(() => undefined);
  };

  if (selectedCount === 0) return null;

  return (
    <div
      className="sticky top-0 z-20 h-11 border-b border-slate-200 bg-white/92 text-xs shadow-[0_8px_20px_rgba(15,23,42,0.055)] backdrop-blur"
    >
      <div
        role="toolbar"
        aria-label="Bulk profile actions"
        aria-busy={checkingHealth || launching || stopping || tagging || deleting}
        className="flex h-11 items-center gap-2 overflow-x-auto px-2.5"
      >
        <div
          role="group"
          aria-label="Selected profile summary"
          className="flex shrink-0 items-center gap-1 rounded-md border border-slate-200 bg-gradient-to-b from-white to-slate-50/90 p-1 shadow-[0_1px_2px_rgba(15,23,42,0.035),inset_0_1px_0_rgba(255,255,255,0.92)]"
        >
          <span
            role="status"
            aria-label="Selected profile count"
            className="inline-flex h-7 shrink-0 items-center rounded-md border border-blue-200 bg-white px-2.5 font-semibold tabular-nums text-blue-800 shadow-[0_1px_2px_rgba(37,99,235,0.08)] ring-1 ring-blue-600/[0.03]"
          >
            {selectedCount} selected
          </span>
          <SummaryPill icon={<Activity className="h-3.5 w-3.5" />} label={`${runningCount} running`} />
          <SummaryPill label={`${stoppedCount} stopped`} />
          <SummaryPill label={`${issueCount} issue${issueCount === 1 ? "" : "s"}`} tone={issueCount > 0 ? "warning" : "muted"} />
        </div>
        <div
          role="group"
          aria-label="Bulk action commands"
          className="ml-auto flex items-center gap-1 rounded-md border border-slate-200 bg-gradient-to-b from-white to-slate-50/60 p-1 shadow-[0_1px_2px_rgba(15,23,42,0.035),inset_0_1px_0_rgba(255,255,255,0.92)]"
        >
          <button
            type="button"
            disabled={!onCheckHealth || checkingHealth}
            aria-label={checkingHealth ? "Checking health" : "Check health"}
            className="inline-flex h-7 shrink-0 items-center gap-1 whitespace-nowrap rounded-md border border-blue-600 bg-gradient-to-b from-blue-500 to-blue-600 px-2.5 font-medium text-white shadow-[0_1px_2px_rgba(37,99,235,0.2),inset_0_1px_0_rgba(255,255,255,0.18)] transition-colors hover:border-blue-700 hover:from-blue-600 hover:to-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500/25 disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-none disabled:bg-slate-100 disabled:text-slate-400 disabled:shadow-none"
            onClick={() => void onCheckHealth?.()}
          >
            <HeartPulse className="h-3.5 w-3.5" />
            <span>{checkingHealth ? "Checking..." : "Check health"}</span>
          </button>
          <button
            type="button"
            disabled={!onLaunch || launching || stoppedCount === 0}
            aria-label={launching ? "Launching selected" : "Launch selected"}
            title={launching ? "Launching selected" : "Launch selected"}
            className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-slate-200 bg-white font-medium text-slate-700 shadow-hairline transition-colors hover:border-blue-200 hover:bg-white hover:text-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-50 disabled:text-slate-400 disabled:shadow-none"
            onClick={() => void onLaunch?.()}
          >
            <Play className="h-3.5 w-3.5" />
            <span className="sr-only">{launching ? "Launching..." : "Launch"}</span>
          </button>
          <button
            type="button"
            disabled={!onStop || stopping || runningCount === 0}
            aria-label={stopping ? "Stopping selected" : "Stop selected"}
            title={stopping ? "Stopping selected" : "Stop selected"}
            className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-slate-200 bg-white font-medium text-slate-700 shadow-hairline transition-colors hover:border-amber-200 hover:bg-white hover:text-amber-800 focus:outline-none focus:ring-2 focus:ring-amber-500/20 disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-50 disabled:text-slate-400 disabled:shadow-none"
            onClick={() => void onStop?.()}
          >
            <Square className="h-3.5 w-3.5" />
            <span className="sr-only">{stopping ? "Stopping..." : "Stop"}</span>
          </button>
          {tagEditorOpen ? (
            <form
              aria-label="Bulk tag form"
              className="flex shrink-0 items-center gap-1 rounded-md border border-blue-200 bg-white p-0.5 shadow-hairline ring-2 ring-blue-500/10"
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
                className="inline-flex h-7 shrink-0 items-center gap-1 whitespace-nowrap rounded-md border border-blue-600 bg-gradient-to-b from-blue-500 to-blue-600 px-2.5 font-medium text-white shadow-[0_1px_2px_rgba(37,99,235,0.22),inset_0_1px_0_rgba(255,255,255,0.18)] transition-colors hover:border-blue-700 hover:from-blue-600 hover:to-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-none disabled:bg-slate-100 disabled:text-slate-400 disabled:shadow-none"
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
              title={tagging ? "Applying tag" : "Tag selected"}
              className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-slate-200 bg-white font-medium text-slate-700 shadow-hairline transition-colors hover:border-blue-200 hover:bg-white hover:text-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-50 disabled:text-slate-400 disabled:shadow-none"
              onClick={() => setTagEditorOpen(true)}
            >
              <Tags className="h-3.5 w-3.5" />
              <span className="sr-only">{tagging ? "Applying..." : "Tag"}</span>
            </button>
          )}
          <button
            type="button"
            disabled={!deleteEnabled}
            aria-label={deleting ? "Deleting selected" : "Delete selected"}
            title={deleteTitle}
            className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-red-200 bg-white font-medium text-red-700 shadow-hairline transition-colors hover:border-red-300 hover:bg-white hover:text-red-800 focus:outline-none focus:ring-2 focus:ring-red-500/20 disabled:cursor-not-allowed disabled:border-red-100 disabled:bg-red-50/35 disabled:text-red-300 disabled:shadow-none"
            onClick={() => {
              setTagEditorOpen(false);
              setDeleteConfirmOpen(true);
            }}
          >
            <Trash2 className="h-3.5 w-3.5" />
            <span className="sr-only">{deleting ? "Deleting..." : "Delete"}</span>
          </button>
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
      {deleteConfirmOpen && (
        <form
          role="dialog"
          aria-label="Confirm bulk profile deletion"
          className="absolute right-2 top-12 z-30 w-[min(420px,calc(100vw-24px))] rounded-lg border border-red-200 bg-white p-3 text-xs text-slate-700 shadow-[0_18px_44px_rgba(127,29,29,0.16)] ring-1 ring-red-900/[0.03]"
          onSubmit={handleDeleteSubmit}
        >
          <div className="flex items-start gap-2">
            <span className="mt-0.5 inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-red-200 bg-red-50 text-red-700">
              <AlertTriangle className="h-4 w-4" />
            </span>
            <div className="min-w-0 flex-1">
              <div className="text-sm font-semibold text-slate-950">
                Delete {stoppedCount} stopped profile{stoppedCount === 1 ? "" : "s"}?
              </div>
              <p className="mt-1 text-slate-600">Browser data will be permanently removed.</p>
              {runningCount > 0 && (
                <p className="mt-1 text-amber-800">
                  {runningCount} running profile{runningCount === 1 ? "" : "s"} will be skipped. Stop {runningCount === 1 ? "it" : "them"} first if {runningCount === 1 ? "it also needs" : "they also need"} deletion.
                </p>
              )}
            </div>
          </div>
          <div className="mt-3 grid gap-2 sm:grid-cols-[1fr_auto_auto]">
            <input
              ref={deleteInputRef}
              aria-label="Type DELETE to confirm bulk deletion"
              value={deleteConfirmText}
              onChange={(event) => setDeleteConfirmText(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Escape" && !deleting) {
                  setDeleteConfirmText("");
                  setDeleteConfirmOpen(false);
                }
              }}
              className="h-8 rounded-md border border-slate-200 bg-slate-50 px-2 font-mono text-xs font-semibold tracking-[0.08em] text-slate-800 outline-none transition-colors placeholder:font-sans placeholder:font-medium placeholder:tracking-normal placeholder:text-slate-400 hover:border-slate-300 focus:border-red-500 focus:bg-white focus:ring-2 focus:ring-red-500/15"
              placeholder="Type DELETE"
              disabled={deleting}
            />
            <button
              type="submit"
              aria-label="Confirm bulk delete"
              disabled={!deleteConfirmReady || deleting}
              className="inline-flex h-8 shrink-0 items-center justify-center gap-1 rounded-md border border-red-600 bg-red-600 px-3 font-medium text-white shadow-[0_1px_2px_rgba(220,38,38,0.25),inset_0_1px_0_rgba(255,255,255,0.16)] transition-colors hover:border-red-700 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500/20 disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-100 disabled:text-slate-400 disabled:shadow-none"
            >
              <Trash2 className="h-3.5 w-3.5" />
              {deleting ? "Deleting..." : "Delete"}
            </button>
            <button
              type="button"
              aria-label="Cancel bulk delete"
              disabled={deleting}
              className="inline-flex h-8 shrink-0 items-center justify-center rounded-md border border-slate-200 bg-white px-3 font-medium text-slate-600 shadow-[0_1px_1px_rgba(15,23,42,0.04)] transition-colors hover:bg-slate-50 hover:text-slate-950 focus:outline-none focus:ring-2 focus:ring-slate-500/15 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400"
              onClick={() => {
                setDeleteConfirmText("");
                setDeleteConfirmOpen(false);
              }}
            >
              Cancel
            </button>
          </div>
        </form>
      )}
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
          ? "border-amber-200 bg-amber-50 text-amber-800 shadow-hairline"
          : "border-slate-200 bg-white text-slate-600 shadow-hairline"
      }`}
    >
      {icon}
      {label}
    </span>
  );
}
