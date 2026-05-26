import { ArrowRight, Cpu, Globe2, Monitor, Network, ShieldAlert } from "lucide-react";
import type { ReactNode } from "react";
import type { Profile, ProfileHealthResponse } from "../lib/api";
import { formatProxyLabel, formatTimestamp } from "../lib/profileDisplay";
import { getHealthWarningSummary } from "../lib/health";
import { HealthBadge } from "./HealthBadge";
import { StatusIndicator } from "./StatusIndicator";

interface ProfileSummaryPanelProps {
  profile: Profile | null;
  health?: ProfileHealthResponse;
  onOpenProfile: (id: string) => void;
}

export function ProfileSummaryPanel({
  profile,
  health,
  onOpenProfile,
}: ProfileSummaryPanelProps) {
  if (!profile) {
    return (
      <aside
        role="complementary"
        aria-label="Profile summary"
        className="flex h-full min-h-0 flex-col overflow-hidden rounded-lg border border-dashed border-slate-300 bg-slate-50/70 p-4 text-sm text-slate-500"
      >
        <div className="flex items-center justify-between gap-2">
          <span className="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">
            Inspector
          </span>
          <span className="inline-flex h-6 w-6 items-center justify-center rounded-[6px] border border-slate-200 bg-white text-slate-400">
            <Monitor className="h-3.5 w-3.5" />
          </span>
        </div>
        <div className="mt-6 rounded-lg border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold text-slate-950">No profile selected</h2>
          <p className="mt-2 text-xs leading-5 text-slate-500">Preview a row to inspect runtime, health, proxy, and fingerprint context.</p>
        </div>
      </aside>
    );
  }

  const geoip = health?.geoip;
  const ip = geoip?.ip ?? profile.last_geoip_ip;
  const country = geoip?.country_code ?? profile.last_geoip_country_code;
  const timezone = geoip?.timezone ?? profile.last_geoip_timezone;
  const locale = geoip?.locale ?? profile.last_geoip_locale;
  const checkedAt = health?.checked_at ?? profile.last_geoip_resolved_at;
  const warningSummary = getHealthWarningSummary(health);
  const timezoneOverride = Boolean(health?.manual_overrides.timezone ?? profile.timezone);
  const localeOverride = Boolean(health?.manual_overrides.locale ?? profile.locale);
  const proxyLabel = formatProxyLabel(profile.proxy);

  return (
    <aside
      role="complementary"
      aria-label="Profile summary"
      className="flex h-full min-h-0 flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-[0_4px_18px_rgba(15,23,42,0.035)]"
    >
      <div className="border-b border-slate-200 bg-slate-50/60 p-4">
        <div className="mb-3 flex items-center justify-between gap-2">
          <span className="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">
            Previewing
          </span>
          <span className="rounded-[6px] border border-slate-200 bg-white px-2 py-0.5 text-[10px] font-medium text-slate-500">
            Inspector
          </span>
        </div>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="truncate text-sm font-semibold text-slate-950" title={profile.name}>
              {profile.name}
            </h2>
            <p className="mt-1 font-mono text-[11px] text-slate-400">{profile.id.slice(0, 8)}</p>
          </div>
          <HealthBadge health={health} compact />
        </div>
        <button
          type="button"
          className="mt-3 inline-flex h-8 w-full items-center justify-center gap-1 rounded-[6px] border border-slate-200 bg-white text-xs font-medium text-slate-700 transition-colors hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
          onClick={() => onOpenProfile(profile.id)}
          aria-label={`Open ${profile.name}`}
        >
          <ArrowRight className="h-3.5 w-3.5" />
          Open profile
        </button>
      </div>

      <div className="min-h-0 flex-1 divide-y divide-slate-100 overflow-y-auto bg-white">
        <SummarySection icon={<ShieldAlert className="h-3.5 w-3.5" />} title="Health">
          <div className="flex items-center justify-between gap-3">
            <span className="text-xs text-slate-500">Status</span>
            <HealthBadge health={health} compact />
          </div>
          {warningSummary && (
            <p className="mt-2 rounded-[6px] border border-amber-200 bg-amber-50 px-2 py-1.5 text-xs text-amber-800">
              {warningSummary}
            </p>
          )}
          <SummaryRow label="Last checked" value={formatTimestamp(checkedAt)} />
        </SummarySection>

        <SummarySection icon={<Monitor className="h-3.5 w-3.5" />} title="Runtime">
          <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
            <StatusIndicator status={profile.status} />
            <span>{profile.status}</span>
          </div>
          <SummaryRow label="VNC" value={profile.vnc_ws_port ? `:${profile.vnc_ws_port}` : "-"} />
          <SummaryRow label="Automation" value={profile.automation_url ? "available" : "-"} />
        </SummarySection>

        <SummarySection icon={<Globe2 className="h-3.5 w-3.5" />} title="GeoIP">
          <SummaryRow label="IP" value={ip ?? "-"} mono />
          <SummaryRow label="Country" value={country ?? "-"} />
          <SummaryRow label="Timezone" value={timezone ?? "-"} />
          <SummaryRow label="Locale" value={locale ?? "-"} />
          <div className="mt-2 flex flex-wrap gap-1">
            <OverridePill label="Timezone override" active={timezoneOverride} />
            <OverridePill label="Locale override" active={localeOverride} />
          </div>
        </SummarySection>

        <SummarySection icon={<Network className="h-3.5 w-3.5" />} title="Proxy">
          <SummaryRow label="Endpoint" value={proxyLabel} mono title={proxyLabel} />
        </SummarySection>

        <SummarySection icon={<Cpu className="h-3.5 w-3.5" />} title="Device">
          <SummaryRow label="Platform" value={profile.platform} />
          <SummaryRow label="Screen" value={`${profile.screen_width} x ${profile.screen_height}`} />
          <SummaryRow
            label="Cores"
            value={profile.hardware_concurrency ? `${profile.hardware_concurrency} cores` : "-"}
          />
          <SummaryRow label="GPU" value={profile.gpu_renderer ?? profile.gpu_vendor ?? "-"} title={profile.gpu_renderer ?? profile.gpu_vendor ?? undefined} />
        </SummarySection>
      </div>
    </aside>
  );
}

function SummarySection({
  icon,
  title,
  children,
}: {
  icon: ReactNode;
  title: string;
  children: ReactNode;
}) {
  return (
    <section
      aria-label={title}
      className="bg-white px-4 py-3.5"
    >
      <div className="mb-3 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-500">
        <span className="flex h-5 w-5 items-center justify-center rounded-[5px] border border-slate-200 bg-slate-50 text-slate-400">
          {icon}
        </span>
        {title}
      </div>
      <div className="space-y-1.5">
        {children}
      </div>
    </section>
  );
}

function SummaryRow({
  label,
  value,
  mono = false,
  title,
}: {
  label: string;
  value: string;
  mono?: boolean;
  title?: string;
}) {
  return (
    <div className="grid grid-cols-[76px_minmax(0,1fr)] items-center gap-2 rounded-[6px] px-1.5 py-1 text-xs transition-colors hover:bg-slate-50">
      <span className="text-slate-500">{label}</span>
      <span
        className={`truncate text-right font-medium text-slate-700 ${mono ? "font-mono text-[11px]" : ""}`}
        title={title ?? value}
      >
        {value}
      </span>
    </div>
  );
}

function OverridePill({ label, active }: { label: string; active: boolean }) {
  return (
    <span
      className={`rounded-[5px] border px-2 py-0.5 text-[10px] font-medium ${
        active
          ? "border-amber-200 bg-amber-50 text-amber-800"
          : "border-border bg-white text-slate-500"
      }`}
    >
      {label}
    </span>
  );
}
