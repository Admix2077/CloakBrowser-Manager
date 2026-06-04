export function formatProxyLabel(value: string | null | undefined): string {
  if (!value) return "-";

  try {
    const url = new URL(value);
    return `${url.protocol}//${url.host}`;
  } catch {
    return "Invalid proxy";
  }
}

export type PublicRuntimeStatus = "running" | "stopped" | "unknown";

export function publicRuntimeStatus(value: unknown): PublicRuntimeStatus {
  return value === "running" || value === "stopped" ? value : "unknown";
}

const URL_PATTERN = /\b(?:https?|socks5):\/\/[^\s"'<>]+/gi;
const LEGACY_PROXY_PATTERN = /(^|[\s"'(<>])([a-z0-9.-]+:\d{2,5}):[^:\s"'<>]+:[^:\s"'<>]+(?=$|[\s"')<>])/gi;

export function redactUrlCredentials(value: string): string {
  return value.replace(URL_PATTERN, (match) => {
    try {
      const url = new URL(match);
      if (!url.username && !url.password) return match;

      const path = url.pathname === "/" ? "" : url.pathname;
      return `${url.protocol}//${url.host}${path}${url.search}${url.hash}`;
    } catch {
      return match.replace(
        /(\b(?:https?|socks5):\/\/)[^@\s/"'<>]+@/i,
        "$1",
      );
    }
  }).replace(LEGACY_PROXY_PATTERN, "$1$2");
}

export function formatTimestamp(value: string | null | undefined): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Invalid timestamp";
  return date.toLocaleString(undefined, {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}
