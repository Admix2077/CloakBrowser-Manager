/**
 * API client for Invisible Browser Manager backend.
 */

export interface Profile {
  id: string;
  name: string;
  fingerprint_seed: number;
  proxy: string | null;
  timezone: string | null;
  locale: string | null;
  platform: string;
  user_agent: string | null;
  screen_width: number;
  screen_height: number;
  gpu_vendor: string | null;
  gpu_renderer: string | null;
  hardware_concurrency: number | null;
  humanize: boolean;
  human_preset: string;
  headless: boolean;
  geoip: boolean;
  last_geoip_ip: string | null;
  last_geoip_country_code: string | null;
  last_geoip_timezone: string | null;
  last_geoip_locale: string | null;
  last_geoip_source: string | null;
  last_geoip_resolved_at: string | null;
  clipboard_sync: boolean;
  auto_launch: boolean;
  color_scheme: string | null;
  launch_args: string[];
  notes: string | null;
  user_data_dir: string;
  created_at: string;
  updated_at: string;
  tags: { tag: string; color: string | null }[];
  status: "running" | "stopped";
  vnc_ws_port: number | null;
  automation_url: string | null;
}

export interface ProfileCreateData {
  name: string;
  template_id?: string | null;
  fingerprint_seed?: number | null;
  proxy?: string | null;
  timezone?: string | null;
  locale?: string | null;
  platform?: string;
  user_agent?: string | null;
  screen_width?: number;
  screen_height?: number;
  gpu_vendor?: string | null;
  gpu_renderer?: string | null;
  hardware_concurrency?: number | null;
  humanize?: boolean;
  human_preset?: string;
  headless?: boolean;
  geoip?: boolean;
  clipboard_sync?: boolean;
  auto_launch?: boolean;
  color_scheme?: string | null;
  launch_args?: string[];
  notes?: string | null;
  tags?: { tag: string; color: string | null }[];
}

export interface ProfileTemplate {
  id: string;
  name: string;
  platform: string;
  screen_width: number;
  screen_height: number;
  gpu_vendor: string | null;
  gpu_renderer: string | null;
  hardware_concurrency: number | null;
  color_scheme: string | null;
  humanize: boolean;
  human_preset: string;
  launch_args: string[];
  geoip: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProfileTemplateCreateData {
  name: string;
  platform?: string;
  screen_width?: number;
  screen_height?: number;
  gpu_vendor?: string | null;
  gpu_renderer?: string | null;
  hardware_concurrency?: number | null;
  color_scheme?: string | null;
  humanize?: boolean;
  human_preset?: string;
  launch_args?: string[];
  geoip?: boolean;
}

export type ProfileTemplateUpdateData = Partial<ProfileTemplateCreateData>;

export interface ProfileImportPreviewProfile {
  name: string;
  template_id: string | null;
  proxy: string | null;
  timezone: string | null;
  locale: string | null;
  platform: string;
  screen_width: number;
  screen_height: number;
  gpu_vendor: string | null;
  gpu_renderer: string | null;
  hardware_concurrency: number | null;
  color_scheme: string | null;
  humanize: boolean;
  human_preset: string;
  launch_args: string[];
  geoip: boolean;
  notes: string | null;
  tags: { tag: string; color: string | null }[];
}

export interface ProfileImportPreviewRow {
  line_number: number;
  ok: boolean;
  errors: string[];
  source: Record<string, string>;
  profile: ProfileImportPreviewProfile | null;
}

export interface ProfileImportPreviewResponse {
  total: number;
  valid: number;
  invalid: number;
  rows: ProfileImportPreviewRow[];
}

export interface ProfileImportResult {
  line_number: number;
  ok: boolean;
  errors: string[];
  source: Record<string, string>;
  profile: Profile | null;
}

export interface ProfileImportResponse {
  total: number;
  succeeded: number;
  failed: number;
  results: ProfileImportResult[];
}

export interface ProfileConfigExport {
  name: string;
  fingerprint_seed: number;
  proxy: string | null;
  timezone: string | null;
  locale: string | null;
  platform: string;
  user_agent: string | null;
  screen_width: number;
  screen_height: number;
  gpu_vendor: string | null;
  gpu_renderer: string | null;
  hardware_concurrency: number | null;
  humanize: boolean;
  human_preset: string;
  headless: boolean;
  geoip: boolean;
  clipboard_sync: boolean;
  auto_launch: boolean;
  color_scheme: string | null;
  launch_args: string[];
  notes: string | null;
  tags: { tag: string; color: string | null }[];
}

export interface ProfileExportResult {
  profile_id: string;
  ok: boolean;
  error: string | null;
  config: ProfileConfigExport | null;
}

export interface ProfileExportResponse {
  schema_version: number;
  total: number;
  exported: number;
  failed: number;
  results: ProfileExportResult[];
}

export interface CookieJsonCookie {
  name: string;
  value: string;
  domain?: string | null;
  url?: string | null;
  path?: string;
  expires?: number | null;
  secure?: boolean;
  httpOnly?: boolean;
  sameSite?: "Strict" | "Lax" | "None" | null;
}

export interface CookieJsonDocument {
  format?: "cloakbrowser.cookie-json.v1";
  schema_version: number;
  profile_id?: string | null;
  exported_at?: string | null;
  cookies: CookieJsonCookie[];
}

export interface CookieSummary {
  cookie_count?: number;
  secure_count?: number;
  http_only_count?: number;
  session_cookie_count?: number;
  persistent_cookie_count?: number;
  [key: string]: unknown;
}

export interface CookieImportResponse {
  profile_id: string;
  imported: number;
  summary: CookieSummary;
}

export interface CookieExportResponse {
  profile_id: string;
  exported: number;
  summary: CookieSummary;
  document: CookieJsonDocument;
}

export interface NetscapeCookieExportResponse {
  profile_id: string;
  exported: number;
  summary: CookieSummary;
  text: string;
}

export interface ProxyAsset {
  id: string;
  name: string;
  url: string;
  country_code: string | null;
  city: string | null;
  asn: string | null;
  provider: string | null;
  tags: { tag: string; color: string | null }[];
  notes: string | null;
  last_check_status: string | null;
  last_check_ip: string | null;
  last_check_country_code: string | null;
  last_check_timezone: string | null;
  last_check_locale: string | null;
  last_check_source: string | null;
  last_check_error: string | null;
  last_check_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProxyProviderPreset {
  id: string;
  name: string;
  provider: string | null;
  country_code: string | null;
  tags: { tag: string; color: string | null }[];
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProxyProviderPresetCreateData {
  name: string;
  provider?: string | null;
  country_code?: string | null;
  tags?: { tag: string; color: string | null }[];
  notes?: string | null;
}

export type ProxyProviderPresetUpdateData = Partial<ProxyProviderPresetCreateData>;

export interface ProxyCreateData {
  name: string;
  url: string;
  country_code?: string | null;
  city?: string | null;
  asn?: string | null;
  provider?: string | null;
  tags?: { tag: string; color: string | null }[];
  notes?: string | null;
}

export type ProxyUpdateData = Partial<ProxyCreateData>;

export interface ProxyBulkCheckResult {
  proxy_id: string;
  ok: boolean;
  error: string | null;
  proxy: ProxyAsset | null;
}

export interface ProxyBulkCheckResponse {
  total: number;
  succeeded: number;
  failed: number;
  results: ProxyBulkCheckResult[];
}

export interface ProxyAssignResult {
  profile_id: string;
  ok: boolean;
  error: string | null;
}

export interface ProxyAssignResponse {
  proxy_id: string;
  proxy: ProxyAsset;
  total: number;
  succeeded: number;
  failed: number;
  results: ProxyAssignResult[];
}

export interface ProxyRandomAssignRequestData {
  profile_ids: string[];
  provider_preset_id?: string | null;
  provider?: string | null;
  country_code?: string | null;
  tags?: string[];
}

export interface ProxyRandomAssignResult extends ProxyAssignResult {
  proxy_id: string | null;
  proxy: ProxyAsset | null;
}

export interface ProxyRandomAssignResponse {
  strategy: "random";
  provider_preset_id: string | null;
  provider: string | null;
  country_code: string | null;
  tags: string[];
  candidate_count: number;
  total: number;
  succeeded: number;
  failed: number;
  results: ProxyRandomAssignResult[];
}

export type ProxyFromProfileCreateData = Omit<ProxyCreateData, "url">;

export interface LaunchResult {
  profile_id: string;
  status: string;
  vnc_ws_port: number;
  display: string;
  automation_url: string | null;
}

export type HealthStatus = "unknown" | "good" | "warning" | "error";

export type HealthWarningCode =
  | "geoip_missing"
  | "geoip_stale"
  | "proxy_invalid"
  | "geoip_lookup_failed"
  | "manual_timezone_mismatch"
  | "manual_locale_mismatch"
  | "runtime_vnc_missing"
  | "runtime_automation_missing"
  | "launch_failed";

export interface HealthWarning {
  code: HealthWarningCode;
  message: string;
  severity: "info" | "warning" | "error";
  action: string | null;
}

export interface HealthGeoIP {
  ip: string | null;
  country_code: string | null;
  timezone: string | null;
  locale: string | null;
  source: string | null;
  resolved_at: string | null;
}

export interface ProfileHealthResponse {
  profile_id: string;
  status: HealthStatus;
  geoip: HealthGeoIP | null;
  manual_overrides: Record<string, boolean>;
  runtime: {
    status: string;
    vnc_ws_port: number | null;
    automation_url: string | null;
  };
  warnings: HealthWarning[];
  checked_at: string;
}

export interface SystemStatus {
  running_count: number;
  launching_count: number;
  failed_count: number;
  binary_version: string;
  profiles_total: number;
  proxy_count: number;
  task_queue_count: number;
  automation_task_counts: Record<string, number>;
}

export interface SystemDiagnostics {
  status: "ok";
  binary_version: string;
  storage: {
    data_dir_exists: boolean;
    db_exists: boolean;
  };
  counts: {
    running: number;
    launching: number;
    profiles_total: number;
    proxy_count: number;
    queued_tasks: number;
    failed_tasks: number;
    automation_task_counts: Record<string, number>;
  };
  runtime: {
    active_displays: number[];
    active_vnc_ws_ports: number[];
    max_running_profiles: number | null;
    managed_user_agent_version: string | null;
    invisible_playwright_version: string | null;
    firefox_binary_version: string | null;
    firefox_binary_build_id: string | null;
  };
  automation_worker: {
    enabled: boolean;
    lease_seconds: number;
    idle_sleep_seconds: number;
    shutdown_timeout_seconds: number;
  };
}

export interface AutomationTaskStep {
  type: string;
  page_ref?: string;
  ms?: number;
  wait_until?: string;
  timeout_ms?: number;
  state?: string;
  delta_x?: number;
  delta_y?: number;
  delay_ms?: number;
  full_page?: boolean;
  [key: string]: unknown;
}

export interface AutomationTaskResultStep {
  index: number;
  type: string;
  status: string;
  [key: string]: unknown;
}

export interface AutomationTaskResult {
  steps: AutomationTaskResultStep[];
  [key: string]: unknown;
}

export interface AutomationTask {
  id: string;
  profile_id: string;
  status: string;
  steps: AutomationTaskStep[];
  result: AutomationTaskResult | null;
  error: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface AutomationTasksResponse {
  tasks: AutomationTask[];
}

export interface AutomationTaskListParams {
  profileId?: string;
  limit?: number;
  offset?: number;
}

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

// Global 401 callback — set by App to trigger login page on auth failure
let _onUnauthorized: (() => void) | null = null;
export function setOnUnauthorized(cb: (() => void) | null) {
  _onUnauthorized = cb;
}

async function request<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    if (res.status === 401 && _onUnauthorized) {
      _onUnauthorized();
      throw new ApiError(401, "Unauthorized");
    }
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail || res.statusText);
  }
  return res.json();
}

function buildAutomationTasksPath(params: AutomationTaskListParams = {}): string {
  const query = new URLSearchParams();
  if (params.profileId) query.set("profile_id", params.profileId);
  if (params.limit !== undefined) query.set("limit", String(params.limit));
  if (params.offset !== undefined) query.set("offset", String(params.offset));
  const search = query.toString();
  return search ? `/api/tasks?${search}` : "/api/tasks";
}

export const api = {
  authStatus: () =>
    request<{ auth_required: boolean; authenticated: boolean }>("/api/auth/status"),

  login: (token: string) =>
    request<{ ok: boolean }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ token }),
    }),

  logout: () =>
    request<{ ok: boolean }>("/api/auth/logout", { method: "POST" }),

  listProfiles: () => request<Profile[]>("/api/profiles"),

  getProfile: (id: string) => request<Profile>(`/api/profiles/${id}`),

  createProfile: (data: ProfileCreateData) =>
    request<Profile>("/api/profiles", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  previewProfileImport: (csvText: string) =>
    request<ProfileImportPreviewResponse>("/api/profiles/import/preview", {
      method: "POST",
      body: JSON.stringify({ csv_text: csvText }),
    }),

  importProfiles: (csvText: string) =>
    request<ProfileImportResponse>("/api/profiles/import", {
      method: "POST",
      body: JSON.stringify({ csv_text: csvText, confirm_import: true }),
    }),

  exportProfiles: (
    profileIds: string[],
    options?: { includeSensitive?: boolean },
  ) =>
    request<ProfileExportResponse>("/api/profiles/export", {
      method: "POST",
      body: JSON.stringify({
        profile_ids: profileIds,
        ...(options?.includeSensitive
          ? { include_sensitive: true, confirm_sensitive_export: true }
          : {}),
      }),
    }),

  importProfileCookies: (profileId: string, document: CookieJsonDocument) =>
    request<CookieImportResponse>(`/api/profiles/${profileId}/cookies/import`, {
      method: "POST",
      body: JSON.stringify({ ...document, confirm_import: true }),
    }),

  exportProfileCookies: (profileId: string) =>
    request<CookieExportResponse>(`/api/profiles/${profileId}/cookies/export`, {
      method: "POST",
      body: JSON.stringify({ confirm_export: true }),
    }),

  importProfileCookiesNetscape: (profileId: string, text: string) =>
    request<CookieImportResponse>(`/api/profiles/${profileId}/cookies/import/netscape`, {
      method: "POST",
      body: JSON.stringify({ text, confirm_import: true }),
    }),

  exportProfileCookiesNetscape: (profileId: string) =>
    request<NetscapeCookieExportResponse>(`/api/profiles/${profileId}/cookies/export/netscape`, {
      method: "POST",
      body: JSON.stringify({ confirm_export: true }),
    }),

  updateProfile: (id: string, data: Partial<ProfileCreateData>) =>
    request<Profile>(`/api/profiles/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  deleteProfile: (id: string) =>
    request<{ ok: boolean }>(`/api/profiles/${id}`, {
      method: "DELETE",
      body: JSON.stringify({ confirm_delete: true }),
    }),

  listProfileTemplates: () =>
    request<ProfileTemplate[]>("/api/profile-templates"),

  createProfileTemplate: (data: ProfileTemplateCreateData) =>
    request<ProfileTemplate>("/api/profile-templates", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateProfileTemplate: (id: string, data: ProfileTemplateUpdateData) =>
    request<ProfileTemplate>(`/api/profile-templates/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  deleteProfileTemplate: (id: string) =>
    request<{ ok: boolean }>(`/api/profile-templates/${id}`, {
      method: "DELETE",
      body: JSON.stringify({ confirm_delete: true }),
    }),

  launchProfile: (id: string) =>
    request<LaunchResult>(`/api/profiles/${id}/launch`, {
      method: "POST",
      body: JSON.stringify({ confirm_launch: true }),
    }),

  stopProfile: (id: string) =>
    request<{ ok: boolean }>(`/api/profiles/${id}/stop`, {
      method: "POST",
      body: JSON.stringify({ confirm_stop: true }),
    }),

  getProfileHealth: (id: string) =>
    request<ProfileHealthResponse>(`/api/profiles/${id}/health`),

  checkProfileHealth: (id: string) =>
    request<ProfileHealthResponse>(`/api/profiles/${id}/health/check`, {
      method: "POST",
    }),

  listProxies: () => request<ProxyAsset[]>("/api/proxies"),

  getProxy: (id: string) => request<ProxyAsset>(`/api/proxies/${id}`),

  listProxyProviderPresets: () =>
    request<ProxyProviderPreset[]>("/api/proxy-provider-presets"),

  createProxyProviderPreset: (data: ProxyProviderPresetCreateData) =>
    request<ProxyProviderPreset>("/api/proxy-provider-presets", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateProxyProviderPreset: (id: string, data: ProxyProviderPresetUpdateData) =>
    request<ProxyProviderPreset>(`/api/proxy-provider-presets/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  deleteProxyProviderPreset: (id: string) =>
    request<{ ok: boolean }>(`/api/proxy-provider-presets/${id}`, {
      method: "DELETE",
      body: JSON.stringify({ confirm_delete: true }),
    }),

  createProxy: (data: ProxyCreateData) =>
    request<ProxyAsset>("/api/proxies", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateProxy: (id: string, data: ProxyUpdateData) =>
    request<ProxyAsset>(`/api/proxies/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  deleteProxy: (id: string) =>
    request<{ ok: boolean }>(`/api/proxies/${id}`, {
      method: "DELETE",
      body: JSON.stringify({ confirm_delete: true }),
    }),

  checkProxy: (id: string) =>
    request<ProxyAsset>(`/api/proxies/${id}/check`, { method: "POST" }),

  bulkCheckProxies: (proxyIds: string[]) =>
    request<ProxyBulkCheckResponse>("/api/proxies/bulk/check", {
      method: "POST",
      body: JSON.stringify({ proxy_ids: proxyIds, confirm_bulk_check: true }),
    }),

  assignProxyToProfiles: (id: string, profileIds: string[]) =>
    request<ProxyAssignResponse>(`/api/proxies/${id}/assign`, {
      method: "POST",
      body: JSON.stringify({ profile_ids: profileIds, confirm_assign: true }),
    }),

  assignRandomProxyToProfiles: (data: ProxyRandomAssignRequestData) =>
    request<ProxyRandomAssignResponse>("/api/proxies/assign/random", {
      method: "POST",
      body: JSON.stringify({ ...data, confirm_assign: true }),
    }),

  listAutomationTasks: (params?: AutomationTaskListParams) =>
    request<AutomationTasksResponse>(buildAutomationTasksPath(params)),

  saveProfileProxyAsAsset: (profileId: string, data: ProxyFromProfileCreateData) =>
    request<ProxyAsset>(`/api/profiles/${profileId}/proxy-asset`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getStatus: () => request<SystemStatus>("/api/status"),

  getDiagnostics: () => request<SystemDiagnostics>("/api/diagnostics"),

  setClipboard: (id: string, text: string) =>
    request<{ ok: boolean }>(`/api/profiles/${id}/clipboard`, {
      method: "POST",
      body: JSON.stringify({ text }),
    }),

  getClipboard: (id: string) =>
    request<{ text: string }>(`/api/profiles/${id}/clipboard`),
};
