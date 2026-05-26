import { AlertTriangle, X } from "lucide-react";
import { useEffect } from "react";

interface ConfirmDialogProps {
  title: string;
  description: string;
  subject?: string;
  confirmLabel: string;
  cancelLabel?: string;
  loading?: boolean;
  tone?: "danger" | "default";
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({
  title,
  description,
  subject,
  confirmLabel,
  cancelLabel = "Cancel",
  loading = false,
  tone = "default",
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !loading) {
        onCancel();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [loading, onCancel]);

  const isDanger = tone === "danger";

  return (
    <div className="animate-dialog-backdrop fixed inset-0 z-50 flex items-center justify-center bg-slate-950/35 p-3 backdrop-blur-sm">
      <div
        role="dialog"
        aria-label={title}
        aria-modal="true"
        className="animate-dialog-in w-[min(460px,calc(100vw-24px))] overflow-hidden rounded-lg border border-slate-200 bg-white shadow-[0_24px_80px_rgba(15,23,42,0.22),inset_0_1px_0_rgba(255,255,255,0.9)]"
      >
        <div className="flex items-start justify-between gap-3 border-b border-slate-200 bg-[#fbfdff] px-4 py-3">
          <div className="flex min-w-0 items-center gap-2">
            <span className={`inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-[8px] border ${
              isDanger
                ? "border-red-200 bg-red-50 text-red-700"
                : "border-blue-100 bg-blue-50 text-blue-700"
            }`}>
              <AlertTriangle className="h-4 w-4" />
            </span>
            <div className="min-w-0">
              <h3 className="text-sm font-semibold text-slate-950">{title}</h3>
              <p className="mt-0.5 text-xs text-slate-500">{description}</p>
            </div>
          </div>
          <button
            type="button"
            className="icon-action h-7 w-7"
            onClick={onCancel}
            disabled={loading}
            aria-label={`Close ${title}`}
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {subject && (
          <div className="border-b border-slate-200 px-4 py-3">
            <div className="rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2 text-sm font-semibold text-slate-950">
              {subject}
            </div>
          </div>
        )}

        <div className="flex flex-wrap items-center justify-end gap-2 bg-white px-4 py-3">
          <button
            type="button"
            className="btn-secondary h-8 text-xs"
            onClick={onCancel}
            disabled={loading}
            aria-label={`${cancelLabel} delete`}
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            className={`inline-flex h-8 min-w-[142px] items-center justify-center gap-1.5 rounded-md border px-3 text-xs font-medium shadow-hairline transition-[background-color,border-color,color,box-shadow,transform] duration-150 active:translate-y-px focus:outline-none focus:ring-2 disabled:cursor-not-allowed disabled:translate-y-0 disabled:border-slate-200 disabled:bg-slate-100 disabled:text-slate-400 disabled:shadow-none ${
              isDanger
                ? "border-red-600 bg-red-600 text-white hover:border-red-700 hover:bg-red-700 focus:ring-red-500/20"
                : "border-blue-600 bg-blue-600 text-white hover:border-blue-700 hover:bg-blue-700 focus:ring-blue-500/20"
            }`}
            onClick={onConfirm}
            disabled={loading}
            aria-label={confirmLabel}
          >
            {loading ? "Deleting..." : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
