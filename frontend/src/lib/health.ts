import type { HealthStatus, ProfileHealthResponse } from "./api";
import { isOnlyRedactedText, publicErrorText, publicProfileGeoipLabel } from "./errorDisplay";

const HEALTH_WARNING_SENSITIVE_RE =
  /\b(?:api[_-]?key|x[_-]?api[_-]?key|access[_-]?token|refresh[_-]?token|auth[_-]?token|viewer[_-]?token|session[_-]?id|client[_-]?secret|private[_-]?key|token|password|passwd|secret|cookie|set-cookie)\b/i;

export function getHealthLabel(status: HealthStatus | undefined): string {
  switch (status) {
    case "good":
      return "可继续";
    case "warning":
      return "需关注";
    case "error":
      return "不可用";
    case "unknown":
    default:
      return "未检测";
  }
}

export function getHealthAriaLabel(health: ProfileHealthResponse | null | undefined): string {
  switch (health?.status) {
    case "good":
      return "健康检查通过，可尝试启动或使用";
    case "warning":
      return "存在需关注项，建议检查后继续";
    case "error":
      return "健康检查失败，当前不可用";
    case "unknown":
    default:
      return "尚未完成健康检测";
  }
}

export function getHealthTone(status: HealthStatus | undefined): {
  badgeClassName: string;
  dotClassName: string;
  summaryClassName: string;
} {
  switch (status) {
    case "good":
      return {
        badgeClassName: "border-emerald-200 bg-emerald-50 text-emerald-700",
        dotClassName: "bg-emerald-500",
        summaryClassName: "text-emerald-700",
      };
    case "warning":
      return {
        badgeClassName: "border-amber-200 bg-amber-50 text-amber-800",
        dotClassName: "bg-amber-500",
        summaryClassName: "text-amber-800",
      };
    case "error":
      return {
        badgeClassName: "border-red-200 bg-red-50 text-red-700",
        dotClassName: "bg-red-500",
        summaryClassName: "text-red-700",
      };
    case "unknown":
    default:
      return {
        badgeClassName: "border-border bg-surface-2 text-slate-600",
        dotClassName: "bg-slate-400",
        summaryClassName: "text-slate-500",
      };
  }
}

export function getHealthWarningSummary(
  health: ProfileHealthResponse | null | undefined,
): string | null {
  const message = health?.warnings.find((warning) => warning.message.trim())?.message;
  if (!message) return null;
  const publicText = publicErrorText(message);
  if (HEALTH_WARNING_SENSITIVE_RE.test(message) && (publicText === message || isOnlyRedactedText(publicText))) return "unknown";
  return publicText || "unknown";
}

export function getHealthGeoipParts(
  health: ProfileHealthResponse | null | undefined,
): string[] {
  const geoip = health?.geoip;
  if (!geoip) return [];
  return [geoip.ip, geoip.country_code, geoip.timezone, geoip.locale]
    .filter((part): part is string => Boolean(part))
    .map((part) => publicProfileGeoipLabel(part));
}
