import { AlertCircle, CheckCircle2, FileSpreadsheet, RefreshCw, SearchCheck, X } from "lucide-react";
import { useMemo, useState } from "react";
import type { ReactNode } from "react";
import {
  api,
  type ProfileImportResponse,
  type ProfileImportResult,
  type ProfileImportPreviewResponse,
  type ProfileImportPreviewRow,
} from "../lib/api";
import { publicErrorMessage, publicErrorText } from "../lib/errorDisplay";
import { TagBadge } from "./Badge";

const PROFILE_CSV_SAMPLE = "name,proxy,tags,notes,template,platform,locale,timezone";
const PROFILE_CSV_SENSITIVE_FIELD_RE =
  /"?[^,\r\n"]*\b(?:api[_-]?key|x[_-]?api[_-]?key|access[_-]?token|refresh[_-]?token|auth[_-]?token|viewer[_-]?token|session[_-]?id|client[_-]?secret|private[_-]?key|token|password|passwd|secret|cookie|set-cookie)\b[^,\r\n"]*"?/gi;
const PROFILE_CSV_LABEL_SENSITIVE_RE =
  /\b(?:api[_-]?key|x[_-]?api[_-]?key|access[_-]?token|refresh[_-]?token|auth[_-]?token|viewer[_-]?token|session[_-]?id|client[_-]?secret|private[_-]?key|token|password|passwd|secret|cookie|set-cookie)\b/i;

interface ProfileCsvPreviewDialogProps {
  onClose: () => void;
  onImported?: () => Promise<unknown> | unknown;
}

export function ProfileCsvPreviewDialog({ onClose, onImported }: ProfileCsvPreviewDialogProps) {
  const [csvText, setCsvText] = useState("");
  const [preview, setPreview] = useState<ProfileImportPreviewResponse | null>(null);
  const [lastPreviewCsvText, setLastPreviewCsvText] = useState<string | null>(null);
  const [importResult, setImportResult] = useState<ProfileImportResponse | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [importNotice, setImportNotice] = useState<string | null>(null);
  const rows = (importResult?.results ?? preview?.rows ?? []).slice(0, 60);
  const canPreview = csvText.trim().length > 0 && !previewing;
  const canImport = Boolean(lastPreviewCsvText && preview && preview.valid > 0 && !previewing && !importing);

  const previewCsv = async () => {
    if (!canPreview) return;
    setPreviewing(true);
    setError(null);
    setImportNotice(null);
    setImportResult(null);
    try {
      const rawCsvText = csvText;
      const nextPreview = await api.previewProfileImport(csvText);
      setPreview(nextPreview);
      setLastPreviewCsvText(rawCsvText);
      setCsvText(publicProfileCsvVisibleText(rawCsvText));
    } catch (err) {
      setError(publicErrorMessage(err, "Unable to preview profile CSV"));
    } finally {
      setPreviewing(false);
    }
  };

  const importValidRows = async () => {
    if (!lastPreviewCsvText || !canImport) return;
    setImporting(true);
    setError(null);
    setImportNotice(null);
    try {
      const result = await api.importProfiles(lastPreviewCsvText);
      setImportResult(result);
      setImportNotice(`Imported ${result.succeeded} profile(s), ${result.failed} failed`);
      await onImported?.();
    } catch (err) {
      setError(publicErrorMessage(err, "Unable to import profile CSV"));
    } finally {
      setImporting(false);
    }
  };

  const summary = useMemo(() => ({
    total: importResult?.total ?? preview?.total ?? 0,
    valid: importResult?.succeeded ?? preview?.valid ?? 0,
    invalid: importResult?.failed ?? preview?.invalid ?? 0,
  }), [importResult, preview]);

  return (
    <div className="animate-dialog-backdrop fixed inset-0 z-50 flex items-center justify-center bg-slate-950/35 p-3 backdrop-blur-sm">
      <div
        role="dialog"
        aria-label="Import profile CSV preview"
        aria-modal="true"
        className="animate-dialog-in flex max-h-[calc(100vh-24px)] w-[min(980px,calc(100vw-24px))] min-w-0 flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-[0_24px_80px_rgba(15,23,42,0.22),inset_0_1px_0_rgba(255,255,255,0.9)]"
      >
        <div className="flex items-start justify-between gap-3 border-b border-slate-200 bg-[#fbfdff] px-4 py-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-[8px] border border-blue-100 bg-blue-50 text-blue-700">
                <FileSpreadsheet className="h-4 w-4" />
              </span>
              <div className="min-w-0">
                <h3 className="text-sm font-semibold text-slate-950">Import profile CSV preview</h3>
                <p className="mt-0.5 text-xs text-slate-500">
                  Paste rows and validate them against the backend import contract before creating profiles.
                </p>
              </div>
            </div>
          </div>
          <button
            type="button"
            className="icon-action h-7 w-7"
            onClick={onClose}
            disabled={previewing}
            aria-label="Close import profile CSV preview dialog"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="grid gap-3 border-b border-slate-200 bg-white px-4 py-3 lg:grid-cols-[minmax(0,1fr)_240px]">
          <label className="min-w-0">
            <span className="label">CSV content</span>
            <textarea
              aria-label="Profile CSV content"
              className="input min-h-[152px] resize-y font-mono text-xs leading-5"
              value={csvText}
              onChange={(event) => {
                setCsvText(event.target.value);
                setError(null);
                setImportNotice(null);
                setImportResult(null);
                setPreview(null);
                setLastPreviewCsvText(null);
              }}
              placeholder={`${PROFILE_CSV_SAMPLE}\nRetail JP,http://proxy.example:8080,asia|warmup,Tokyo account,Mac warmup,macos,ja-JP,Asia/Tokyo`}
              spellCheck={false}
            />
          </label>
          <div className="grid content-start gap-2">
            <div className="rounded-lg border border-slate-200 bg-slate-50/80 p-3">
              <div className="text-[11px] font-semibold uppercase tracking-[0.1em] text-slate-500">
                Supported fields
              </div>
              <p className="mt-2 break-words font-mono text-[11px] leading-5 text-slate-600">
                {PROFILE_CSV_SAMPLE}
              </p>
              <p className="mt-2 text-xs leading-5 text-slate-500">
                Template may be an id or unique name. This step only previews rows and does not create profiles.
              </p>
            </div>
            <div className="grid grid-cols-3 gap-2">
              <ImportCountPill label="total" value={summary.total} tone="neutral" />
              <ImportCountPill label="ready" value={summary.valid} tone="success" />
              <ImportCountPill label="blocked" value={summary.invalid} tone={summary.invalid > 0 ? "warning" : "neutral"} />
            </div>
          </div>
        </div>

        {error && (
          <div className="animate-notice-in border-b border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700" role="alert">
            {error}
          </div>
        )}

        {importNotice && (
          <div className="animate-notice-in border-b border-emerald-200 bg-emerald-50 px-4 py-2 text-sm font-medium text-emerald-700" role="status">
            {importNotice}
          </div>
        )}

        <div className="min-h-[260px] flex-1 overflow-auto bg-white p-2">
          {rows.length === 0 ? (
            <div
              role="status"
              aria-label="No profile CSV preview yet"
              className="flex min-h-[240px] items-center justify-center rounded-lg border border-dashed border-slate-300 bg-slate-50/70 p-6 text-center text-sm text-slate-500"
            >
              Paste a CSV header and rows, then run Preview CSV to inspect valid and blocked profile rows.
            </div>
          ) : (
            <div className="overflow-auto rounded-lg border border-slate-200">
              <table
                aria-label="Profile CSV preview"
                className="min-w-[860px] w-full table-fixed border-separate border-spacing-0 bg-white text-left text-xs text-slate-700"
              >
                <thead className="sticky top-0 z-10 bg-[#fbfdff]">
                  <tr className="text-slate-500 shadow-[inset_0_-1px_0_rgba(148,163,184,0.24)]">
                    <HeaderCell className="w-[80px]">Row</HeaderCell>
                    <HeaderCell className="w-[170px]">Profile</HeaderCell>
                    <HeaderCell className="w-[92px]">Platform</HeaderCell>
                    <HeaderCell className="w-[170px]">Locale / TZ</HeaderCell>
                    <HeaderCell className="w-[180px]">Proxy</HeaderCell>
                    <HeaderCell className="w-[130px]">Tags</HeaderCell>
                    <HeaderCell className="w-[190px]">Status</HeaderCell>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <ProfileCsvPreviewRowView key={`${row.line_number}-${row.profile?.name ?? row.errors.join("|")}`} row={row} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-200 bg-[#fbfdff] px-4 py-3">
          <div className="text-xs text-slate-500">
            Create submits valid rows only. Blocked rows stay visible with their backend validation errors.
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="btn-secondary h-8 text-xs"
              onClick={onClose}
              disabled={previewing || importing}
            >
              Close
            </button>
            <button
              type="button"
              className="btn-secondary inline-flex h-8 min-w-[146px] items-center justify-center gap-1.5 text-xs"
              onClick={() => void importValidRows()}
              disabled={!canImport}
            >
              {importing ? (
                <RefreshCw className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <CheckCircle2 className="h-3.5 w-3.5" />
              )}
              {importing ? "Creating" : "Create valid profiles"}
            </button>
            <button
              type="button"
              className="btn-primary inline-flex h-8 min-w-[116px] items-center justify-center gap-1.5 text-xs"
              onClick={() => void previewCsv()}
              disabled={!canPreview || importing}
            >
              {previewing ? (
                <RefreshCw className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <SearchCheck className="h-3.5 w-3.5" />
              )}
              {previewing ? "Previewing" : "Preview CSV"}
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

function ProfileCsvPreviewRowView({ row }: { row: ProfileImportPreviewRow | ProfileImportResult }) {
  const profile = row.profile;
  const proxy = profile?.proxy ?? row.source.proxy ?? "-";
  const name = profile?.name ?? row.source.name ?? "-";
  const platform = profile?.platform ?? row.source.platform ?? "-";
  const locale = profile?.locale ?? row.source.locale ?? "-";
  const timezone = profile?.timezone ?? row.source.timezone ?? "-";
  const tags = profile?.tags ?? [];
  const templateId = profile && "template_id" in profile ? profile.template_id : null;
  const safeName = publicProfileCsvPreviewLabel(name);
  const safePlatform = publicProfileCsvPreviewLabel(platform);
  const safeLocale = publicProfileCsvPreviewLabel(locale);
  const safeTimezone = publicProfileCsvPreviewLabel(timezone);
  const safeTemplateId = templateId ? publicProfileCsvPreviewLabel(templateId) : null;
  const safeProxy = publicProfileCsvPreviewLabel(proxy);

  return (
    <tr className={`shadow-[inset_0_-1px_0_rgba(226,232,240,0.8)] transition-colors ${
      row.ok ? "hover:bg-blue-50/30" : "bg-amber-50/45"
    }`}>
      <td className="px-3 py-2 align-top font-mono text-[11px] text-slate-500">
        Row {row.line_number}
      </td>
      <td className="px-3 py-2 align-top">
        <span className="block truncate text-sm font-semibold text-slate-900" title={safeName}>
          {safeName}
        </span>
        {safeTemplateId && (
          <span className="mt-0.5 block truncate font-mono text-[10px] text-slate-500" title={safeTemplateId}>
            {safeTemplateId}
          </span>
        )}
      </td>
      <td className="px-3 py-2 align-top">
        <span className="inline-flex rounded-md border border-slate-200 bg-slate-50 px-1.5 py-0.5 text-[11px] font-medium text-slate-700">
          {safePlatform}
        </span>
      </td>
      <td className="px-3 py-2 align-top text-xs text-slate-600">
        <div className="truncate" title={safeLocale}>{safeLocale}</div>
        <div className="mt-0.5 truncate font-mono text-[11px] text-slate-500" title={safeTimezone}>{safeTimezone}</div>
      </td>
      <td className="px-3 py-2 align-top">
        <span className="block truncate font-mono text-[11px] text-slate-600" title={safeProxy}>
          {safeProxy}
        </span>
      </td>
      <td className="px-3 py-2 align-top">
        <div className="flex max-h-12 flex-wrap gap-1 overflow-hidden">
          {tags.length > 0 ? tags.map((tag) => (
            <TagBadge key={tag.tag} tag={tag.tag} color={tag.color} />
          )) : (
            <span className="text-xs text-slate-500">-</span>
          )}
        </div>
      </td>
      <td className="px-3 py-2 align-top">
        {row.ok ? (
          <span className="inline-flex items-center gap-1 rounded-md border border-emerald-200 bg-emerald-50 px-1.5 py-0.5 text-[11px] font-medium text-emerald-700">
            <CheckCircle2 className="h-3 w-3" />
            Ready
          </span>
        ) : (
          <div className="grid gap-1">
            {row.errors.map((error) => (
              <span
                key={error}
                className="inline-flex w-fit items-center gap-1 rounded-md border border-amber-200 bg-amber-50 px-1.5 py-0.5 text-[11px] font-medium text-amber-800"
              >
                <AlertCircle className="h-3 w-3" />
                {publicErrorText(error)}
              </span>
            ))}
          </div>
        )}
      </td>
    </tr>
  );
}

function publicProfileCsvVisibleText(value: string): string {
  return value
    .split(/\r?\n/)
    .map((line) => publicErrorText(line).replace(PROFILE_CSV_SENSITIVE_FIELD_RE, "unknown"))
    .join("\n");
}

function publicProfileCsvPreviewLabel(value: string): string {
  const text = value.trim();
  if (!text) return "unknown";
  const publicText = publicErrorText(text);
  if (PROFILE_CSV_LABEL_SENSITIVE_RE.test(text) && publicText === text) return "unknown";
  return publicText || "unknown";
}

function HeaderCell({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <th className={`h-9 truncate border-b border-slate-200 bg-[#fbfdff] px-3 py-2 text-[10px] font-semibold uppercase tracking-[0.08em] text-slate-500 ${className}`}>
      {children}
    </th>
  );
}
