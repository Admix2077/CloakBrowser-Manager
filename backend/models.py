"""Pydantic models for profile CRUD operations."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class TagCreate(BaseModel):
    tag: str
    color: str | None = None  # hex color


class ProfileCreate(BaseModel):
    name: str
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


class TagResponse(BaseModel):
    tag: str
    color: str | None = None


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


class LaunchResponse(BaseModel):
    profile_id: str
    status: str = "running"
    vnc_ws_port: int
    display: str
    automation_url: str | None = None


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


class AutomationGotoRequest(BaseModel):
    url: str
    wait_until: Literal["commit", "domcontentloaded", "load", "networkidle"] = "load"
    timeout_ms: int = Field(default=30_000, ge=1, le=300_000)


class AutomationEvaluateRequest(BaseModel):
    expression: str = Field(min_length=1, max_length=200_000)


class AutomationEvaluateResponse(BaseModel):
    result: Any


class AutomationScreenshotRequest(BaseModel):
    full_page: bool = False


class ClipboardRequest(BaseModel):
    text: str = Field(max_length=1_048_576)  # 1MB max


class LoginRequest(BaseModel):
    token: str
