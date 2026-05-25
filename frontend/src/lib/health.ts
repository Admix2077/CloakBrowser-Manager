import type { HealthStatus, ProfileHealthResponse } from "./api";

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
      return "健康检查通过，可继续启动或使用";
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
        badgeClassName: "border-emerald-500/20 bg-emerald-500/10 text-emerald-300",
        dotClassName: "bg-emerald-400",
        summaryClassName: "text-emerald-300/80",
      };
    case "warning":
      return {
        badgeClassName: "border-amber-400/20 bg-amber-400/10 text-amber-300",
        dotClassName: "bg-amber-300",
        summaryClassName: "text-amber-200/80",
      };
    case "error":
      return {
        badgeClassName: "border-red-600/30 bg-red-600/15 text-red-400",
        dotClassName: "bg-red-400",
        summaryClassName: "text-red-300/80",
      };
    case "unknown":
    default:
      return {
        badgeClassName: "border-border bg-surface-3 text-gray-400",
        dotClassName: "bg-gray-500",
        summaryClassName: "text-gray-500",
      };
  }
}

export function getHealthWarningSummary(
  health: ProfileHealthResponse | null | undefined,
): string | null {
  return health?.warnings.find((warning) => warning.message.trim())?.message ?? null;
}

export function getHealthGeoipParts(
  health: ProfileHealthResponse | null | undefined,
): string[] {
  const geoip = health?.geoip;
  if (!geoip) return [];
  return [geoip.ip, geoip.country_code, geoip.timezone, geoip.locale].filter(
    (part): part is string => Boolean(part),
  );
}
