import { redactUrlCredentials } from "./profileDisplay";

const ERROR_AUTH_HEADER_RE = /\bAuthorization\s*[:=]\s*(?:(?:Bearer|Basic|Digest)\s+)?[^\s;,]+/gi;
const ERROR_BEARER_RE = /\bBearer\s+[^\s;,]+/gi;
const ERROR_SENSITIVE_ASSIGNMENT_RE =
  /\b(?:api[_-]?key|x[_-]?api[_-]?key|access[_-]?token|refresh[_-]?token|auth[_-]?token|viewer[_-]?token|session[_-]?id|client[_-]?secret|private[_-]?key|token|password|passwd|secret|cookie|set-cookie)\s*[:=]\s*[^\s;,]+/gi;
const ERROR_LOCAL_PATH_RE = /(?:\/(?:data|tmp|home)\/|(?<![A-Za-z0-9])[A-Za-z]:[\\/])[^\s"'<>)]*/gi;
const PROFILE_GEOIP_SENSITIVE_RE =
  /\bAuthorization\b|\bBearer\b|\b(?:auth_token|viewer_token|token|password|passwd|secret|cookie|set-cookie)\s*[:=]|(?:\/(?:data|tmp|home)\/|(?<![A-Za-z0-9])[A-Za-z]:[\\/])/i;
const PUBLIC_PROFILE_ID_RE = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/;
const SENSITIVE_PROFILE_ID_RE =
  /(?:https?:\/\/|[/?#&=\\]|\bauthorization\b|\bbearer\b|\bapi[_-]?key\b|\bx[_-]?api[_-]?key\b|\baccess[_-]?token\b|\bauth[_-]?token\b|\brefresh[_-]?token\b|\bsession[_-]?id\b|\bviewer[_-]?token\b|\bclient[_-]?secret\b|\bprivate[_-]?key\b|\btoken\b|\bpassword\b|\bsecret\b|\bcookie\b|\s)/i;
const ERROR_IPV4_RE = /\b\d{1,3}(?:\.\d{1,3}){3}\b/g;
const ERROR_BRACKETED_IPV6_RE = /\[([0-9a-fA-F:.]{2,})\]/g;
const ERROR_BARE_IPV6_RE = /(?<![A-Za-z0-9_.:[\]-])(?:[0-9a-fA-F]{1,4}:){2,}[0-9a-fA-F:.]*(?![A-Za-z0-9_.:[\]-])/g;
const ERROR_URL_RE = /\b(?:https?|socks5):\/\/[^\s"'<>]+/gi;

function isValidIpv4Candidate(candidate: string): boolean {
  const parts = candidate.split(".");
  return parts.length === 4 && parts.every((part) => {
    if (!/^\d{1,3}$/.test(part)) return false;
    const value = Number(part);
    return value >= 0 && value <= 255;
  });
}

function isValidIpv6Candidate(candidate: string): boolean {
  if (!candidate.includes(":")) return false;
  try {
    new URL(`http://[${candidate}]`);
    return true;
  } catch {
    return false;
  }
}

function redactIpLiterals(text: string): string {
  return text
    .replace(ERROR_BRACKETED_IPV6_RE, (match, candidate: string) => (
      isValidIpv6Candidate(candidate) ? "[redacted-ip]" : match
    ))
    .replace(ERROR_BARE_IPV6_RE, (candidate: string) => (
      isValidIpv6Candidate(candidate) ? "[redacted-ip]" : candidate
    ))
    .replace(ERROR_IPV4_RE, (candidate: string) => (
      isValidIpv4Candidate(candidate) ? "[redacted-ip]" : candidate
    ));
}

function publicUrlText(value: string): string {
  try {
    const url = new URL(value);
    const path = url.pathname === "/" ? "" : url.pathname;
    return `${url.protocol}//${url.host}${path}`;
  } catch {
    return value.replace(/([?#]).*$/u, "");
  }
}

function redactUrlEvidence(text: string): string {
  return text.replace(ERROR_URL_RE, (match) => publicUrlText(match));
}

export function publicErrorText(value: string): string {
  return redactIpLiterals(redactUrlEvidence(redactUrlCredentials(value)))
    .replace(ERROR_AUTH_HEADER_RE, "[redacted]")
    .replace(ERROR_BEARER_RE, "[redacted]")
    .replace(ERROR_SENSITIVE_ASSIGNMENT_RE, "[redacted]")
    .replace(ERROR_LOCAL_PATH_RE, "[redacted-path]")
    .replace(/\s+/g, " ")
    .trim();
}

export function publicProfileName(value: string): string {
  return publicErrorText(value) || "unknown";
}

export function publicProfileIdLabel(value: string): string {
  const trimmed = value.trim();
  if (!trimmed || !PUBLIC_PROFILE_ID_RE.test(trimmed)) return "unknown";
  if (SENSITIVE_PROFILE_ID_RE.test(trimmed)) return "unknown";
  return trimmed.slice(0, 8);
}

export function publicProfileTagLabel(value: string): string {
  return publicErrorText(value) || "unknown";
}

export function publicProfileGeoipLabel(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) return "unknown";
  if (!PROFILE_GEOIP_SENSITIVE_RE.test(trimmed) && redactUrlCredentials(trimmed) === trimmed) {
    return trimmed;
  }
  return publicErrorText(trimmed) || "unknown";
}

export function publicErrorMessage(err: unknown, fallback: string): string {
  if (!(err instanceof Error)) return fallback;
  const message = publicErrorText(err.message);
  return message || fallback;
}
