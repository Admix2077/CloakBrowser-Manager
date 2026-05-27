import { Cookie, Download, RefreshCw, Upload } from "lucide-react";
import { useState } from "react";
import { api, type CookieJsonDocument, type CookieSummary, type Profile } from "../lib/api";

const COOKIE_JSON_FORMAT = "cloakbrowser.cookie-json.v1";
const INVALID_JSON_MESSAGE = "Invalid Cookie JSON document";
const IMPORT_FAILED_MESSAGE = "Cookie import failed";
const EXPORT_FAILED_MESSAGE = "Cookie export failed";

interface ProfileCookieManagerProps {
  profile: Profile;
}

export function ProfileCookieManager({ profile }: ProfileCookieManagerProps) {
  const [cookieText, setCookieText] = useState("");
  const [confirmExport, setConfirmExport] = useState(false);
  const [summary, setSummary] = useState<CookieSummary | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyAction, setBusyAction] = useState<"import" | "export" | null>(null);
  const isRunning = profile.status === "running";
  const canImport = isRunning && cookieText.trim().length > 0 && busyAction === null;
  const canExport = isRunning && confirmExport && busyAction === null;

  const importCookies = async () => {
    if (!canImport) return;
    let document: CookieJsonDocument;
    try {
      document = JSON.parse(cookieText) as CookieJsonDocument;
    } catch {
      setError(INVALID_JSON_MESSAGE);
      setNotice(null);
      setSummary(null);
      setCookieText("");
      return;
    }

    setBusyAction("import");
    setError(null);
    setNotice(null);
    try {
      const response = await api.importProfileCookies(profile.id, document);
      setSummary(response.summary);
      setNotice(`Imported ${response.imported} cookie(s)`);
      setCookieText("");
    } catch (err) {
      setSummary(null);
      setError(safeCookieError(err, IMPORT_FAILED_MESSAGE));
      setCookieText("");
    } finally {
      setBusyAction(null);
    }
  };

  const exportCookies = async () => {
    if (!canExport) return;

    setBusyAction("export");
    setError(null);
    setNotice(null);
    try {
      const response = await api.exportProfileCookies(profile.id);
      setSummary(response.summary);
      const downloaded = downloadCookieDocument(profile.id, response.document);
      setNotice(downloaded
        ? `Exported ${response.exported} cookie(s)`
        : `Exported ${response.exported} cookie(s); download unavailable`);
    } catch (err) {
      setSummary(null);
      setError(safeCookieError(err, EXPORT_FAILED_MESSAGE));
    } finally {
      setBusyAction(null);
    }
  };

  return (
    <div
      role="region"
      aria-label="Cookie management"
      className="grid gap-3 rounded-[7px] border border-slate-200 bg-slate-50/70 p-3"
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <span className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-[6px] border border-blue-100 bg-blue-50 text-blue-700">
            <Cookie className="h-3.5 w-3.5" />
          </span>
          <div className="min-w-0">
            <h3 className="text-xs font-semibold text-slate-950">Cookies</h3>
            <p className="mt-0.5 text-[11px] text-slate-500">{COOKIE_JSON_FORMAT}</p>
          </div>
        </div>
        <span className={`rounded-md border px-2 py-0.5 text-[10px] font-semibold ${
          isRunning
            ? "border-emerald-200 bg-emerald-50 text-emerald-700"
            : "border-slate-200 bg-white text-slate-500"
        }`}>
          {isRunning ? "running" : "stopped"}
        </span>
      </div>

      {!isRunning && (
        <p className="rounded-md border border-amber-200 bg-amber-50 px-2 py-1.5 text-xs text-amber-800">
          Launch the profile before importing or exporting cookies.
        </p>
      )}

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 px-2 py-1.5 text-xs text-red-700" role="alert">
          {error}
        </div>
      )}

      {notice && (
        <div className="rounded-md border border-emerald-200 bg-emerald-50 px-2 py-1.5 text-xs font-medium text-emerald-700" role="status">
          {notice}
        </div>
      )}

      <label className="grid gap-1">
        <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-500">
          Cookie JSON
        </span>
        <textarea
          aria-label="Cookie JSON v1 document"
          className="input min-h-[108px] resize-y font-mono text-[11px] leading-5"
          value={cookieText}
          onChange={(event) => {
            setCookieText(event.target.value);
            setError(null);
            setNotice(null);
          }}
          placeholder='{"format":"cloakbrowser.cookie-json.v1","schema_version":1,"cookies":[]}'
          spellCheck={false}
          disabled={!isRunning || busyAction !== null}
        />
      </label>

      <div className="grid grid-cols-2 gap-2">
        <button
          type="button"
          className="btn-secondary inline-flex h-8 items-center justify-center gap-1.5 text-xs disabled:cursor-not-allowed disabled:opacity-60"
          onClick={() => void importCookies()}
          disabled={!canImport}
        >
          {busyAction === "import" ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <Upload className="h-3.5 w-3.5" />}
          Import cookies
        </button>
        <button
          type="button"
          className="btn-secondary inline-flex h-8 items-center justify-center gap-1.5 text-xs disabled:cursor-not-allowed disabled:opacity-60"
          onClick={() => void exportCookies()}
          disabled={!canExport}
        >
          {busyAction === "export" ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
          Export cookies
        </button>
      </div>

      <label className="flex items-start gap-2 rounded-md border border-slate-200 bg-white px-2 py-1.5 text-xs text-slate-600">
        <input
          type="checkbox"
          className="mt-0.5 h-3.5 w-3.5 rounded border-slate-300 text-blue-600 focus:ring-blue-500/20"
          checked={confirmExport}
          onChange={(event) => setConfirmExport(event.target.checked)}
          disabled={!isRunning || busyAction !== null}
          aria-label="Confirm cookie export"
        />
        <span>Export requires explicit local confirmation.</span>
      </label>

      {summary && <CookieSummaryPills summary={summary} />}
    </div>
  );
}

function CookieSummaryPills({ summary }: { summary: CookieSummary }) {
  const total = numericSummary(summary.cookie_count);
  const secure = numericSummary(summary.secure_count);
  const httpOnly = numericSummary(summary.http_only_count);
  const session = numericSummary(summary.session_cookie_count);
  const persistent = numericSummary(summary.persistent_cookie_count);

  return (
    <div className="grid grid-cols-2 gap-1.5 text-[11px] sm:grid-cols-5">
      <SummaryPill label="total" value={total} />
      <SummaryPill label="secure" value={secure} />
      <SummaryPill label="httpOnly" value={httpOnly} />
      <SummaryPill label="session" value={session} />
      <SummaryPill label="persistent" value={persistent} />
    </div>
  );
}

function SummaryPill({ label, value }: { label: string; value: number }) {
  return (
    <span className="inline-flex items-center justify-center rounded-md border border-slate-200 bg-white px-1.5 py-1 font-semibold text-slate-600">
      {value} {label}
    </span>
  );
}

function numericSummary(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function safeCookieError(err: unknown, fallback: string): string {
  const message = err instanceof Error ? err.message : "";
  if (
    message === "Invalid cookie JSON document" ||
    message === "Profile not running" ||
    message === "Cookie import failed" ||
    message === "Cookie export failed" ||
    message === "Cookie export requires explicit confirmation"
  ) {
    return message;
  }
  return fallback;
}

function downloadCookieDocument(profileId: string, cookieDocument: CookieJsonDocument): boolean {
  if (
    typeof window === "undefined" ||
    typeof window.URL?.createObjectURL !== "function" ||
    typeof document === "undefined"
  ) {
    return false;
  }

  const blob = new Blob([JSON.stringify(cookieDocument, null, 2)], {
    type: "application/json",
  });
  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `cloakbrowser-cookies-${profileId}.json`;
  anchor.rel = "noopener";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(url);
  return true;
}
