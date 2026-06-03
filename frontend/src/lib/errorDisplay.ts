import { redactUrlCredentials } from "./profileDisplay";

const ERROR_AUTH_HEADER_RE = /\bAuthorization\s*[:=]\s*(?:(?:Bearer|Basic|Digest)\s+)?[^\s;,]+/gi;
const ERROR_BEARER_RE = /\bBearer\s+[^\s;,]+/gi;
const ERROR_SENSITIVE_ASSIGNMENT_RE =
  /\b(?:auth_token|viewer_token|token|password|passwd|secret|cookie|set-cookie)\s*[:=]\s*[^\s;,]+/gi;
const ERROR_LOCAL_PATH_RE = /(?:\/(?:data|tmp|home)\/|(?<![A-Za-z0-9])[A-Za-z]:[\\/])[^\s"'<>)]*/gi;

export function publicErrorText(value: string): string {
  return redactUrlCredentials(value)
    .replace(ERROR_AUTH_HEADER_RE, "[redacted]")
    .replace(ERROR_BEARER_RE, "[redacted]")
    .replace(ERROR_SENSITIVE_ASSIGNMENT_RE, "[redacted]")
    .replace(ERROR_LOCAL_PATH_RE, "[redacted-path]")
    .replace(/\s+/g, " ")
    .trim();
}

export function publicErrorMessage(err: unknown, fallback: string): string {
  if (!(err instanceof Error)) return fallback;
  const message = publicErrorText(err.message);
  return message || fallback;
}
