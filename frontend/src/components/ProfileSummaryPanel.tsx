import { ArrowRight, Cookie, Cpu, Globe2, Monitor, Network, ShieldAlert } from "lucide-react";
import type { ReactNode } from "react";
import type { Profile, ProfileHealthResponse } from "../lib/api";
import { publicErrorText, publicProfileGeoipLabel, publicProfileIdLabel, publicProfileName } from "../lib/errorDisplay";
import { formatProxyLabel, formatTimestamp, publicRuntimeStatus } from "../lib/profileDisplay";
import { getHealthWarningSummary } from "../lib/health";
import { Badge, CountryBadge } from "./Badge";
import { HealthBadge } from "./HealthBadge";
import { ProfileCookieManager } from "./ProfileCookieManager";
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
        className="flex h-full min-h-0 flex-col overflow-hidden rounded-lg border border-dashed border-slate-300 bg-slate-50/70 p-4 text-sm text-slate-500 shadow-[inset_0_1px_0_rgba(255,255,255,0.85)]"
      >
        <div className="flex items-center justify-between gap-2">
          <span className="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-600">
            Inspector
          </span>
          <span className="inline-flex h-6 w-6 items-center justify-center rounded-[6px] border border-slate-200 bg-white text-slate-500">
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
  const safeIp = ip ? publicProfileGeoipLabel(ip) : "-";
  const safeCountry = country ? publicProfileGeoipLabel(country) : null;
  const safeTimezone = timezone ? publicProfileGeoipLabel(timezone) : "-";
  const safeLocale = locale ? publicProfileGeoipLabel(locale) : "-";
  const warningSummary = getHealthWarningSummary(health);
  const timezoneOverride = Boolean(health?.manual_overrides.timezone ?? profile.timezone);
  const localeOverride = Boolean(health?.manual_overrides.locale ?? profile.locale);
  const proxyLabel = formatProxyLabel(profile.proxy);
  const runtimeStatus = publicRuntimeStatus(profile.status);
  const safeVncPort = publicVncPortLabel(profile.vnc_ws_port);
  const safeName = publicProfileName(profile.name);
  const safeProfileId = publicProfileIdLabel(profile.id);
  const safePlatform = publicProfileDeviceLabel(profile.platform);
  const safeScreen = `${publicProfileDeviceLabel(profile.screen_width)} x ${publicProfileDeviceLabel(profile.screen_height)}`;
  const safeHardwareConcurrency = profile.hardware_concurrency
    ? `${publicProfileDeviceLabel(profile.hardware_concurrency)} cores`
    : "-";
  const gpuLabel = profile.gpu_renderer ?? profile.gpu_vendor;
  const safeGpu = gpuLabel ? publicProfileDeviceLabel(gpuLabel) : "-";

  return (
    <aside
      role="complementary"
      aria-label="Profile summary"
      className="flex h-full min-h-0 flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-[0_8px_24px_rgba(15,23,42,0.05),inset_0_1px_0_rgba(255,255,255,0.85)]"
    >
      <div
        key={profile.id}
        data-testid="inspector-profile-content"
        className="animate-inspector-in flex min-h-0 flex-1 flex-col"
      >
        <div className="border-b border-slate-200 bg-gradient-to-b from-slate-50 to-white p-4">
          <div className="mb-3 flex items-center justify-between gap-2">
            <span className="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-500">
              Previewing
            </span>
            <span className="rounded-[6px] border border-slate-200 bg-white px-2 py-0.5 text-[10px] font-medium text-slate-500 shadow-[0_1px_1px_rgba(15,23,42,0.04)]">
              Inspector
            </span>
          </div>
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <h2 className="truncate text-sm font-semibold text-slate-950" title={safeName}>
                {safeName}
              </h2>
              <p className="mt-1 font-mono text-[11px] text-slate-600">{safeProfileId}</p>
            </div>
            <HealthBadge health={health} compact />
          </div>
          <button
            type="button"
            className="mt-3 inline-flex h-8 w-full items-center justify-center gap-1 rounded-[6px] border border-slate-200 bg-white text-xs font-medium text-slate-700 shadow-[0_1px_1px_rgba(15,23,42,0.04)] transition-[background-color,border-color,color,box-shadow] hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700 hover:shadow-[0_1px_2px_rgba(15,23,42,0.08)] focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            onClick={() => onOpenProfile(profile.id)}
            aria-label={`Open ${safeName}`}
          >
            <ArrowRight className="h-3.5 w-3.5" />
            Open profile
          </button>
        </div>

        <div className="min-h-0 flex-1 divide-y divide-slate-100 overflow-y-auto bg-white">
          <SummarySection icon={<ShieldAlert className="h-3.5 w-3.5" />} title="Health" priority="primary">
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

          <SummarySection icon={<Monitor className="h-3.5 w-3.5" />} title="Runtime" priority="primary">
            <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
              <StatusIndicator status={profile.status} />
              <Badge type="runtime" tone={runtimeStatus === "running" ? "success" : "muted"}>
                {runtimeStatus}
              </Badge>
            </div>
            <SummaryRow label="VNC" value={safeVncPort} />
            <SummaryRow label="Automation" value={profile.automation_url ? "available" : "-"} />
          </SummarySection>

          <SummarySection icon={<Globe2 className="h-3.5 w-3.5" />} title="GeoIP" priority="secondary">
            <SummaryRow label="IP" value={safeIp} mono />
            <SummaryRow
              label="Country"
              value={safeCountry ? <CountryBadge country={safeCountry} /> : "-"}
              title={safeCountry ?? "-"}
            />
            <SummaryRow label="Timezone" value={safeTimezone} />
            <SummaryRow label="Locale" value={safeLocale} />
            <div className="mt-2 flex flex-wrap gap-1">
              <OverridePill label="Timezone override" active={timezoneOverride} />
              <OverridePill label="Locale override" active={localeOverride} />
            </div>
          </SummarySection>

          <SummarySection icon={<Network className="h-3.5 w-3.5" />} title="Proxy" priority="secondary">
            <SummaryRow label="Endpoint" value={proxyLabel} mono title={proxyLabel} />
          </SummarySection>

          <SummarySection icon={<Cookie className="h-3.5 w-3.5" />} title="Cookies" priority="secondary">
            <ProfileCookieManager profile={profile} />
          </SummarySection>

          <SummarySection icon={<Cpu className="h-3.5 w-3.5" />} title="Device" priority="secondary">
            <SummaryRow label="Platform" value={safePlatform} />
            <SummaryRow label="Screen" value={safeScreen} />
            <SummaryRow
              label="Cores"
              value={safeHardwareConcurrency}
            />
            <SummaryRow label="GPU" value={safeGpu} title={safeGpu === "-" ? undefined : safeGpu} />
          </SummarySection>
        </div>
      </div>
    </aside>
  );
}

function publicProfileDeviceLabel(value: unknown): string {
  const text = String(value ?? "").trim();
  if (!text) return "-";
  return publicErrorText(text) || "unknown";
}

function publicVncPortLabel(value: unknown): string {
  const port = typeof value === "number"
    ? value
    : typeof value === "string" && /^\d+$/.test(value.trim())
      ? Number(value.trim())
      : null;
  if (port === null || !Number.isInteger(port) || port < 1 || port > 65535) return "-";
  return `:${port}`;
}

function SummarySection({
  icon,
  title,
  priority,
  children,
}: {
  icon: ReactNode;
  title: string;
  priority: "primary" | "secondary";
  children: ReactNode;
}) {
  return (
    <section
      aria-label={title}
      data-priority={priority}
      className={`bg-white px-4 py-3.5 ${
        priority === "primary" ? "shadow-[inset_3px_0_0_rgba(37,99,235,0.24)]" : ""
      }`}
    >
      <div className={`mb-3 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.08em] ${
        priority === "primary" ? "text-slate-700" : "text-slate-500"
      }`}>
        <span className={`flex h-5 w-5 items-center justify-center rounded-[5px] border ${
          priority === "primary"
            ? "border-blue-100 bg-blue-50 text-blue-600"
            : "border-slate-200 bg-slate-50 text-slate-600"
        }`}>
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
  value: ReactNode;
  mono?: boolean;
  title?: string;
}) {
  const valueTitle = title ?? (typeof value === "string" ? value : undefined);

  return (
    <div className="grid grid-cols-[76px_minmax(0,1fr)] items-center gap-2 rounded-[6px] px-1.5 py-1 text-xs transition-colors hover:bg-slate-50">
      <span className="text-slate-500">{label}</span>
      <span
        className={`flex min-w-0 justify-end truncate text-right font-medium text-slate-700 ${mono ? "font-mono text-[11px]" : ""}`}
        title={valueTitle}
      >
        {value}
      </span>
    </div>
  );
}

function OverridePill({ label, active }: { label: string; active: boolean }) {
  return (
    <Badge
      type="tag"
      tone={active ? "warning" : "muted"}
      className="text-[10px]"
    >
      {label}
    </Badge>
  );
}
