import { Database, Globe2, Network, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { api, type ProxyAsset } from "../lib/api";
import { formatTimestamp, redactUrlCredentials } from "../lib/profileDisplay";

type ProxyStatusTone = "good" | "warning" | "error" | "unknown";

export function ProxyManagerPage() {
  const [proxies, setProxies] = useState<ProxyAsset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadProxies = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setProxies(await api.listProxies());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load proxy assets");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadProxies();
  }, [loadProxies]);

  const stats = useMemo(() => {
    const good = proxies.filter((proxy) => proxy.last_check_status === "good").length;
    const needsReview = proxies.filter((proxy) => {
      const status = getProxyStatusTone(proxy.last_check_status);
      return status === "warning" || status === "error";
    }).length;
    const unchecked = proxies.filter((proxy) => !proxy.last_check_status).length;

    return { total: proxies.length, good, needsReview, unchecked };
  }, [proxies]);

  return (
    <section
      role="region"
      aria-label="Proxy Manager"
      className="flex h-full min-h-0 flex-col gap-3 p-3 sm:p-4 lg:p-5"
    >
      <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_auto] xl:items-end">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-[8px] border border-blue-100 bg-blue-50 text-blue-700 shadow-[inset_0_1px_0_rgba(255,255,255,0.85)]">
              <Network className="h-4 w-4" />
            </span>
            <div className="min-w-0">
              <h2 className="text-xl font-semibold tracking-tight text-slate-950">Proxy Manager</h2>
              <p className="mt-1 text-sm text-slate-500">
                Read-only proxy inventory. Mutation actions will be wired in later closed loops.
              </p>
            </div>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <ProxySummaryTile label="Proxies" value={stats.total} />
          <ProxySummaryTile label="Good" value={stats.good} tone="success" />
          <ProxySummaryTile label="Review" value={stats.needsReview} tone="warning" />
          <ProxySummaryTile label="Unchecked" value={stats.unchecked} />
        </div>
      </div>

      <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-[0_8px_24px_rgba(15,23,42,0.05),inset_0_1px_0_rgba(255,255,255,0.9)]">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 bg-[#fbfdff]/95 px-3 py-2.5">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-slate-950">Proxy assets</span>
              <span className="rounded-[999px] border border-slate-200 bg-slate-50 px-2 py-0.5 text-[11px] font-medium text-slate-500">
                {stats.total} proxies
              </span>
              <span className="rounded-[999px] border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-700">
                {stats.good} good
              </span>
              <span className="rounded-[999px] border border-amber-200 bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-800">
                {stats.needsReview} needs review
              </span>
            </div>
            <p className="mt-1 text-xs text-slate-500">
              URLs are rendered credential-safe. Add, edit, check, assign, and CSV import remain disabled in this view.
            </p>
          </div>
          <button
            type="button"
            className="btn-secondary inline-flex h-8 items-center gap-1.5 text-xs"
            onClick={() => void loadProxies()}
            disabled={loading}
            aria-label={loading ? "Loading proxy assets" : "Retry loading proxy assets"}
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>

        {error && (
          <div className="border-b border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
            {error}
          </div>
        )}

        {loading && proxies.length === 0 ? (
          <div className="flex min-h-[320px] flex-1 items-center justify-center text-sm text-slate-500">
            Loading proxy assets...
          </div>
        ) : proxies.length === 0 ? (
          <ProxyEmptyState />
        ) : (
          <div
            role="region"
            aria-label="Proxy assets table"
            className="min-h-0 flex-1 overflow-auto bg-white [scrollbar-gutter:stable]"
          >
            <table
              aria-label="Proxy assets"
              className="min-w-[920px] w-full table-fixed border-separate border-spacing-0 bg-white text-left text-xs text-slate-700"
            >
              <thead className="sticky top-0 z-10 bg-[#fbfdff]/95 backdrop-blur">
                <tr className="text-slate-500 shadow-[inset_0_-1px_0_rgba(148,163,184,0.24)]">
                  <HeaderCell className="w-[260px]">Proxy</HeaderCell>
                  <HeaderCell className="w-[150px]">Location</HeaderCell>
                  <HeaderCell className="w-[150px]">Provider</HeaderCell>
                  <HeaderCell className="w-[120px]">Health</HeaderCell>
                  <HeaderCell className="w-[210px]">Last check</HeaderCell>
                  <HeaderCell className="w-[170px]">Tags</HeaderCell>
                </tr>
              </thead>
              <tbody>
                {proxies.map((proxy) => (
                  <ProxyRow key={proxy.id} proxy={proxy} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}

function ProxyRow({ proxy }: { proxy: ProxyAsset }) {
  const safeUrl = redactUrlCredentials(proxy.url);
  const location = [proxy.country_code, proxy.city].filter(Boolean).join(" · ") || "-";
  const checkLocation = [
    proxy.last_check_ip,
    proxy.last_check_country_code,
  ].filter(Boolean).join(" · ");

  return (
    <tr className="group shadow-[inset_0_-1px_0_rgba(226,232,240,0.8)] transition-colors hover:bg-blue-50/30">
      <td className="px-3 py-3 align-top">
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold text-slate-950" title={proxy.name}>
            {proxy.name}
          </div>
          <div className="mt-1 truncate font-mono text-[11px] text-slate-500" title={safeUrl}>
            {safeUrl}
          </div>
        </div>
      </td>
      <td className="px-3 py-3 align-top">
        <div className="flex items-center gap-1.5 text-sm font-medium text-slate-700">
          <Globe2 className="h-3.5 w-3.5 shrink-0 text-slate-400" />
          <span className="truncate" title={location}>{location}</span>
        </div>
        {proxy.asn && (
          <div className="mt-1 truncate font-mono text-[11px] text-slate-400" title={proxy.asn}>
            {proxy.asn}
          </div>
        )}
      </td>
      <td className="px-3 py-3 align-top">
        <span className="truncate text-sm font-medium text-slate-700" title={proxy.provider ?? "-"}>
          {proxy.provider ?? "-"}
        </span>
        {proxy.notes && (
          <p className="mt-1 line-clamp-1 text-[11px] text-slate-400" title={proxy.notes}>
            {proxy.notes}
          </p>
        )}
      </td>
      <td className="px-3 py-3 align-top">
        <ProxyStatusBadge status={proxy.last_check_status} />
        {proxy.last_check_error && (
          <div className="mt-1 truncate text-[11px] text-red-600" title={proxy.last_check_error}>
            {redactUrlCredentials(proxy.last_check_error)}
          </div>
        )}
      </td>
      <td className="px-3 py-3 align-top">
        <div className="truncate font-mono text-[11px] text-slate-600" title={checkLocation || "-"}>
          {checkLocation || "-"}
        </div>
        <div className="mt-1 text-[11px] text-slate-400">
          {formatTimestamp(proxy.last_check_at)}
        </div>
      </td>
      <td className="px-3 py-3 align-top">
        {proxy.tags.length > 0 ? (
          <div className="flex max-w-full flex-wrap gap-1">
            {proxy.tags.slice(0, 3).map((tag) => (
              <span
                key={`${proxy.id}-${tag.tag}`}
                className="token-chip max-w-[128px] truncate"
                title={tag.tag}
              >
                <span
                  className="h-1.5 w-1.5 shrink-0 rounded-full"
                  style={{ backgroundColor: tag.color ?? "#94a3b8" }}
                />
                {tag.tag}
              </span>
            ))}
          </div>
        ) : (
          <span className="text-slate-400">-</span>
        )}
      </td>
    </tr>
  );
}

function ProxyStatusBadge({ status }: { status: string | null }) {
  const tone = getProxyStatusTone(status);
  const label = status ? statusLabel(status) : "Unchecked";
  const className = {
    good: "border-emerald-200 bg-emerald-50 text-emerald-700",
    warning: "border-amber-200 bg-amber-50 text-amber-800",
    error: "border-red-200 bg-red-50 text-red-700",
    unknown: "border-slate-200 bg-slate-50 text-slate-600",
  }[tone];
  const dotClassName = {
    good: "bg-emerald-500",
    warning: "bg-amber-500",
    error: "bg-red-500",
    unknown: "bg-slate-400",
  }[tone];

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-md border px-1.5 py-0.5 text-[11px] font-medium leading-4 ${className}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${dotClassName}`} />
      {label}
    </span>
  );
}

function ProxyEmptyState() {
  return (
    <div
      role="status"
      aria-label="No proxy assets yet"
      className="flex min-h-[320px] flex-1 items-center justify-center p-6"
    >
      <div className="mx-auto max-w-[420px] rounded-lg border border-dashed border-slate-300 bg-slate-50/70 px-6 py-8 text-center shadow-[inset_0_1px_0_rgba(255,255,255,0.9)]">
        <span className="mx-auto mb-3 inline-flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-500 shadow-hairline">
          <Database className="h-4 w-4" />
        </span>
        <h3 className="text-sm font-semibold text-slate-950">No proxy assets yet</h3>
        <p className="mt-2 text-xs leading-5 text-slate-500">
          Proxy assets created through the API will appear here.
        </p>
      </div>
    </div>
  );
}

function HeaderCell({ children, className = "" }: { children: string; className?: string }) {
  return (
    <th className={`px-3 py-2 text-[10px] font-semibold uppercase tracking-[0.12em] ${className}`}>
      {children}
    </th>
  );
}

function ProxySummaryTile({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: number;
  tone?: "neutral" | "success" | "warning";
}) {
  const toneClassName = {
    neutral: "border-slate-200 bg-white text-slate-700 before:bg-slate-300",
    success: "border-emerald-200 bg-emerald-50/80 text-emerald-700 before:bg-emerald-500",
    warning: "border-amber-200 bg-amber-50/80 text-amber-800 before:bg-amber-500",
  }[tone];

  return (
    <div className={`relative min-w-[92px] overflow-hidden rounded-lg border px-3 py-2 shadow-[0_1px_2px_rgba(15,23,42,0.04),inset_0_1px_0_rgba(255,255,255,0.8)] before:absolute before:inset-x-0 before:top-0 before:h-0.5 ${toneClassName}`}>
      <div className="text-lg font-semibold leading-5 tabular-nums">{value}</div>
      <div className="mt-1 text-[10px] font-semibold uppercase tracking-[0.1em] opacity-75">
        {label}
      </div>
    </div>
  );
}

function getProxyStatusTone(status: string | null): ProxyStatusTone {
  if (status === "good") return "good";
  if (status === "error" || status === "failed") return "error";
  if (status === "warning") return "warning";
  return "unknown";
}

function statusLabel(status: string): string {
  return status.replace(/_/g, " ");
}
