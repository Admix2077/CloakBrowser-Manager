"""Pydantic models for profile CRUD operations."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, StrictBool, field_validator, model_validator


class TagCreate(BaseModel):
    tag: str
    color: str | None = None  # hex color


class ProfileCreate(BaseModel):
    name: str
    template_id: str | None = None
    fingerprint_seed: int | None = None  # random if not set
    proxy: str | None = None  # "http://user:pass@host:port" or null
    timezone: str | None = None  # "America/New_York"
    locale: str | None = None  # "en-US"
    platform: Literal["windows", "macos", "linux"] = "windows"
    user_agent: str | None = None
    screen_width: int = 1920
    screen_height: int = 1080
    gpu_vendor: str | None = None
    gpu_renderer: str | None = None
    hardware_concurrency: int | None = None
    humanize: bool = False
    human_preset: Literal["default", "careful"] = "default"
    headless: bool = False
    geoip: bool = True
    clipboard_sync: bool = True
    auto_launch: bool = False
    color_scheme: Literal["light", "dark", "no-preference"] | None = None
    launch_args: list[str] = Field(default_factory=list)
    notes: str | None = None
    tags: list[TagCreate] | None = None


class ProfileUpdate(BaseModel):
    name: str | None = None
    fingerprint_seed: int | None = None
    proxy: str | None = Field(default=None)
    timezone: str | None = Field(default=None)
    locale: str | None = Field(default=None)
    platform: Literal["windows", "macos", "linux"] | None = None
    user_agent: str | None = Field(default=None)
    screen_width: int | None = None
    screen_height: int | None = None
    gpu_vendor: str | None = Field(default=None)
    gpu_renderer: str | None = Field(default=None)
    hardware_concurrency: int | None = Field(default=None)
    humanize: bool | None = None
    human_preset: Literal["default", "careful"] | None = None
    headless: bool | None = None
    geoip: bool | None = None
    clipboard_sync: bool | None = None
    auto_launch: bool | None = None
    color_scheme: Literal["light", "dark", "no-preference"] | None = Field(default=None)
    launch_args: list[str] | None = None
    notes: str | None = Field(default=None)
    tags: list[TagCreate] | None = None


class ProfileDeleteRequest(BaseModel):
    confirm_delete: StrictBool = False


class TagResponse(BaseModel):
    tag: str
    color: str | None = None


class ProfileTemplateCreate(BaseModel):
    name: str = Field(min_length=1)
    platform: Literal["windows", "macos", "linux"] = "windows"
    screen_width: int = 1920
    screen_height: int = 1080
    gpu_vendor: str | None = None
    gpu_renderer: str | None = None
    hardware_concurrency: int | None = None
    color_scheme: Literal["light", "dark", "no-preference"] | None = None
    humanize: bool = False
    human_preset: Literal["default", "careful"] = "default"
    launch_args: list[str] = Field(default_factory=list)
    geoip: bool = True


class ProfileTemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    platform: Literal["windows", "macos", "linux"] | None = None
    screen_width: int | None = None
    screen_height: int | None = None
    gpu_vendor: str | None = Field(default=None)
    gpu_renderer: str | None = Field(default=None)
    hardware_concurrency: int | None = Field(default=None)
    color_scheme: Literal["light", "dark", "no-preference"] | None = Field(default=None)
    humanize: bool | None = None
    human_preset: Literal["default", "careful"] | None = None
    launch_args: list[str] | None = None
    geoip: bool | None = None


class ProfileTemplateDeleteRequest(BaseModel):
    confirm_delete: StrictBool = False


class ProfileTemplateResponse(BaseModel):
    id: str
    name: str
    platform: str = "windows"
    screen_width: int = 1920
    screen_height: int = 1080
    gpu_vendor: str | None = None
    gpu_renderer: str | None = None
    hardware_concurrency: int | None = None
    color_scheme: str | None = None
    humanize: bool = False
    human_preset: str = "default"
    launch_args: list[str] = []
    geoip: bool = True
    created_at: str
    updated_at: str


class ProfileImportPreviewRequest(BaseModel):
    csv_text: str = Field(min_length=1)


class ProfileImportPreviewProfile(BaseModel):
    name: str
    template_id: str | None = None
    proxy: str | None = None
    timezone: str | None = None
    locale: str | None = None
    platform: str = "windows"
    screen_width: int = 1920
    screen_height: int = 1080
    gpu_vendor: str | None = None
    gpu_renderer: str | None = None
    hardware_concurrency: int | None = None
    color_scheme: str | None = None
    humanize: bool = False
    human_preset: str = "default"
    launch_args: list[str] = Field(default_factory=list)
    geoip: bool = True
    notes: str | None = None
    tags: list[TagResponse] = Field(default_factory=list)


class ProfileImportPreviewRow(BaseModel):
    line_number: int
    ok: bool
    errors: list[str] = Field(default_factory=list)
    source: dict[str, str] = Field(default_factory=dict)
    profile: ProfileImportPreviewProfile | None = None


class ProfileImportPreviewResponse(BaseModel):
    total: int
    valid: int
    invalid: int
    rows: list[ProfileImportPreviewRow] = Field(default_factory=list)


class ProxyCreate(BaseModel):
    name: str = Field(min_length=1)
    url: str = Field(min_length=1)
    country_code: str | None = None
    city: str | None = None
    asn: str | None = None
    provider: str | None = None
    tags: list[TagCreate] = Field(default_factory=list)
    notes: str | None = None


class ProxyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    url: str | None = Field(default=None, min_length=1)
    country_code: str | None = Field(default=None)
    city: str | None = Field(default=None)
    asn: str | None = Field(default=None)
    provider: str | None = Field(default=None)
    tags: list[TagCreate] | None = None
    notes: str | None = Field(default=None)


class ProxyDeleteRequest(BaseModel):
    confirm_delete: StrictBool = False


class ProxyProviderPresetCreate(BaseModel):
    name: str = Field(min_length=1)
    provider: str | None = None
    country_code: str | None = None
    tags: list[TagCreate] = Field(default_factory=list)
    notes: str | None = None


class ProxyProviderPresetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    provider: str | None = Field(default=None)
    country_code: str | None = Field(default=None)
    tags: list[TagCreate] | None = None
    notes: str | None = Field(default=None)


class ProxyProviderPresetDeleteRequest(BaseModel):
    confirm_delete: StrictBool = False


class ProxyProviderPresetResponse(BaseModel):
    id: str
    name: str
    provider: str | None = None
    country_code: str | None = None
    tags: list[TagResponse] = Field(default_factory=list)
    notes: str | None = None
    created_at: str
    updated_at: str


class ProxyResponse(BaseModel):
    id: str
    name: str
    url: str
    country_code: str | None = None
    city: str | None = None
    asn: str | None = None
    provider: str | None = None
    tags: list[TagResponse] = []
    notes: str | None = None
    last_check_status: str | None = None
    last_check_ip: str | None = None
    last_check_country_code: str | None = None
    last_check_timezone: str | None = None
    last_check_locale: str | None = None
    last_check_source: str | None = None
    last_check_error: str | None = None
    last_check_at: str | None = None
    created_at: str
    updated_at: str


class ProxyBulkCheckRequest(BaseModel):
    proxy_ids: list[str] = Field(min_length=1)


class ProxyBulkCheckResult(BaseModel):
    proxy_id: str
    ok: bool
    error: str | None = None
    proxy: ProxyResponse | None = None


class ProxyBulkCheckResponse(BaseModel):
    total: int
    succeeded: int
    failed: int
    results: list[ProxyBulkCheckResult]


class ProxyAssignRequest(BaseModel):
    profile_ids: list[str] = Field(min_length=1)


class ProxyAssignResult(BaseModel):
    profile_id: str
    ok: bool
    error: str | None = None


class ProxyAssignResponse(BaseModel):
    proxy_id: str
    proxy: ProxyResponse
    total: int
    succeeded: int
    failed: int
    results: list[ProxyAssignResult]


class ProxyRandomAssignRequest(BaseModel):
    profile_ids: list[str] = Field(min_length=1)
    provider_preset_id: str | None = None
    provider: str | None = None
    country_code: str | None = None
    tags: list[str] = Field(default_factory=list)


class ProxyRandomAssignResult(BaseModel):
    profile_id: str
    ok: bool
    error: str | None = None
    proxy_id: str | None = None
    proxy: ProxyResponse | None = None


class ProxyRandomAssignResponse(BaseModel):
    strategy: str = "random"
    provider_preset_id: str | None = None
    provider: str | None = None
    country_code: str | None = None
    tags: list[str] = Field(default_factory=list)
    candidate_count: int
    total: int
    succeeded: int
    failed: int
    results: list[ProxyRandomAssignResult] = Field(default_factory=list)


class ProxyFromProfileCreate(BaseModel):
    name: str = Field(min_length=1)
    country_code: str | None = None
    city: str | None = None
    asn: str | None = None
    provider: str | None = None
    tags: list[TagCreate] = Field(default_factory=list)
    notes: str | None = None


class ProfileResponse(BaseModel):
    id: str
    name: str
    fingerprint_seed: int
    proxy: str | None = None
    timezone: str | None = None
    locale: str | None = None
    platform: str = "windows"
    user_agent: str | None = None
    screen_width: int = 1920
    screen_height: int = 1080
    gpu_vendor: str | None = None
    gpu_renderer: str | None = None
    hardware_concurrency: int | None = None
    humanize: bool = False
    human_preset: str = "default"
    headless: bool = False
    geoip: bool = False
    clipboard_sync: bool = True
    auto_launch: bool = False
    last_geoip_ip: str | None = None
    last_geoip_country_code: str | None = None
    last_geoip_timezone: str | None = None
    last_geoip_locale: str | None = None
    last_geoip_source: str | None = None
    last_geoip_resolved_at: str | None = None

    @field_validator("clipboard_sync", mode="before")
    @classmethod
    def coerce_clipboard_sync(cls, v: object) -> bool:
        return v if v is not None else True

    color_scheme: str | None = None
    launch_args: list[str] = []
    notes: str | None = None
    user_data_dir: str
    created_at: str
    updated_at: str
    tags: list[TagResponse] = []
    status: str = "stopped"  # "running" | "stopped"
    vnc_ws_port: int | None = None
    automation_url: str | None = None


class ProfileImportResult(BaseModel):
    line_number: int
    ok: bool
    errors: list[str] = Field(default_factory=list)
    source: dict[str, str] = Field(default_factory=dict)
    profile: ProfileResponse | None = None


class ProfileImportResponse(BaseModel):
    total: int
    succeeded: int
    failed: int
    results: list[ProfileImportResult] = Field(default_factory=list)


class ProfileExportRequest(BaseModel):
    profile_ids: list[str] = Field(min_length=1)
    include_sensitive: StrictBool = False
    confirm_sensitive_export: StrictBool = False


class ProfileConfigExport(BaseModel):
    name: str
    fingerprint_seed: int
    proxy: str | None = None
    timezone: str | None = None
    locale: str | None = None
    platform: str = "windows"
    user_agent: str | None = None
    screen_width: int = 1920
    screen_height: int = 1080
    gpu_vendor: str | None = None
    gpu_renderer: str | None = None
    hardware_concurrency: int | None = None
    humanize: bool = False
    human_preset: str = "default"
    headless: bool = False
    geoip: bool = True
    clipboard_sync: bool = True
    auto_launch: bool = False
    color_scheme: str | None = None
    launch_args: list[str] = Field(default_factory=list)
    notes: str | None = None
    tags: list[TagResponse] = Field(default_factory=list)


class ProfileExportResult(BaseModel):
    profile_id: str
    ok: bool
    error: str | None = None
    config: ProfileConfigExport | None = None


class ProfileExportResponse(BaseModel):
    schema_version: int = 1
    total: int
    exported: int
    failed: int
    results: list[ProfileExportResult] = Field(default_factory=list)


class ProfileBundleExportRequest(BaseModel):
    include_sensitive_proxy: StrictBool = False
    confirm_sensitive_proxy_export: StrictBool = False
    include_cookies: StrictBool = False
    confirm_cookie_export: StrictBool = False
    include_local_storage: StrictBool = False
    confirm_local_storage_export: StrictBool = False
    local_storage_page_ref: str = Field(default="0", min_length=1, max_length=4096)


class ProfileBundleExportResponse(BaseModel):
    profile_id: str
    bundle: dict[str, Any]


class ProfileConfigImportRequest(BaseModel):
    schema_version: Literal[1] = 1
    configs: list[dict[str, Any]] = Field(min_length=1, max_length=1000)


class ProfileConfigImportResult(BaseModel):
    index: int
    ok: bool
    errors: list[str] = Field(default_factory=list)
    profile: ProfileResponse | None = None


class ProfileConfigImportResponse(BaseModel):
    schema_version: int = 1
    total: int
    imported: int
    failed: int
    results: list[ProfileConfigImportResult] = Field(default_factory=list)


class LaunchResponse(BaseModel):
    profile_id: str
    status: str = "running"
    vnc_ws_port: int
    display: str
    automation_url: str | None = None


class RuntimeSessionCreate(BaseModel):
    external_session_id: str = Field(min_length=1)
    profile_id: str | None = None
    template_id: str | None = None
    lease_seconds: int = Field(ge=1, le=86_400)

    @model_validator(mode="after")
    def validate_profile_source(self):
        if bool(self.profile_id) == bool(self.template_id):
            raise ValueError("Provide exactly one of profile_id or template_id")
        return self


class RuntimeSessionResponse(BaseModel):
    id: str
    profile_id: str
    external_session_id: str
    status: str
    lease_expires_at: str
    created_at: str
    updated_at: str


class RuntimeViewerTokenCreate(BaseModel):
    ttl_seconds: int = Field(ge=1, le=300)


class RuntimeViewerTokenResponse(BaseModel):
    viewer_url: str
    viewer_token: str
    expires_at: str


class RuntimeSessionRenew(BaseModel):
    lease_seconds: int = Field(ge=1, le=86_400)


class StatusResponse(BaseModel):
    running_count: int
    binary_version: str
    profiles_total: int


class ProfileStatusResponse(BaseModel):
    status: str  # "running" | "stopped"
    vnc_ws_port: int | None = None
    display: str | None = None
    automation_url: str | None = None


class AutomationInfoResponse(BaseModel):
    profile_id: str
    engine: str
    status: str
    pages_url: str


class AutomationPageResponse(BaseModel):
    page_id: str
    index: int
    url: str
    title: str


class AutomationPagesResponse(BaseModel):
    pages: list[AutomationPageResponse]


class AutomationConsoleLogEntry(BaseModel):
    type: str
    text: str
    location: dict[str, Any] = Field(default_factory=dict)


class AutomationConsoleLogsResponse(BaseModel):
    logs: list[AutomationConsoleLogEntry]


class AutomationNetworkEvent(BaseModel):
    event: str
    method: str | None = None
    url: str
    resource_type: str | None = None
    status: int | None = None
    failure: str | None = None


class AutomationNetworkSummaryResponse(BaseModel):
    events: list[AutomationNetworkEvent]


class AutomationGotoRequest(BaseModel):
    url: str
    wait_until: Literal["commit", "domcontentloaded", "load", "networkidle"] = "load"
    timeout_ms: int = Field(default=30_000, ge=1, le=300_000)


class AutomationWaitForSelectorRequest(BaseModel):
    selector: str = Field(min_length=1, max_length=10_000)
    state: Literal["attached", "detached", "visible", "hidden"] = "visible"
    timeout_ms: int = Field(default=30_000, ge=1, le=300_000)


class AutomationClickRequest(BaseModel):
    selector: str = Field(min_length=1, max_length=10_000)
    timeout_ms: int = Field(default=30_000, ge=1, le=300_000)


class AutomationFillRequest(BaseModel):
    selector: str = Field(min_length=1, max_length=10_000)
    value: str = Field(max_length=1_048_576)
    timeout_ms: int = Field(default=30_000, ge=1, le=300_000)


class AutomationKeyboardTypeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1_048_576)
    delay_ms: int = Field(default=0, ge=0, le=10_000)


class AutomationScrollRequest(BaseModel):
    delta_x: int = Field(default=0, ge=-100_000, le=100_000)
    delta_y: int = Field(default=0, ge=-100_000, le=100_000)


class AutomationEvaluateRequest(BaseModel):
    expression: str = Field(min_length=1, max_length=200_000)


class AutomationEvaluateResponse(BaseModel):
    result: Any


class AutomationScreenshotRequest(BaseModel):
    full_page: bool = False


class AutomationTaskCreate(BaseModel):
    profile_id: str = Field(min_length=1)
    steps: list[dict[str, Any]] = Field(min_length=1, max_length=200)


class AutomationTaskResponse(BaseModel):
    id: str
    profile_id: str
    status: str
    steps: list[dict[str, Any]]
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None


class AutomationTasksResponse(BaseModel):
    tasks: list[AutomationTaskResponse]


class CookieImportResponse(BaseModel):
    profile_id: str
    imported: int
    summary: dict[str, Any]


class NetscapeCookieImportRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10_000_000)


class CookieExportRequest(BaseModel):
    confirm_export: StrictBool = False


class CookieExportResponse(BaseModel):
    profile_id: str
    exported: int
    summary: dict[str, Any]
    document: dict[str, Any]


class NetscapeCookieExportResponse(BaseModel):
    profile_id: str
    exported: int
    summary: dict[str, Any]
    text: str


class ClipboardRequest(BaseModel):
    text: str = Field(max_length=1_048_576)  # 1MB max


class LoginRequest(BaseModel):
    token: str
