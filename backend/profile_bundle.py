"""Profile bundle manifest helpers."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .cookie_formats import COOKIE_JSON_FORMAT
from .models import ProfileConfigExport
from .proxies import redact_proxy_asset_url


PROFILE_BUNDLE_FORMAT = "cloakbrowser.profile-bundle.v1"


class ProfileBundleProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    config: ProfileConfigExport


class ProfileBundleCookies(BaseModel):
    model_config = ConfigDict(extra="forbid")

    included: bool = False
    format: Literal["cloakbrowser.cookie-json.v1"] = COOKIE_JSON_FORMAT
    schema_version: Literal[1] = 1
    summary: dict[str, int] = Field(default_factory=lambda: {"cookie_count": 0})


class ProfileBundleLocalStorage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    included: bool = False
    origin_count: int = 0


class ProfileBundleProfileDir(BaseModel):
    model_config = ConfigDict(extra="forbid")

    included: bool = False
    file_count: int = 0
    total_bytes: int = 0
    excluded_file_count: int = 0
    archive: None = None


class ProfileBundleMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    app_name: str = "cloakbrowser-invisible-manager"
    app_version: str | None = None
    source_profile_id: str
    source_profile_name: str
    fingerprint_seed_included: bool
    sensitive_proxy_included: bool
    cookies_included: bool = False
    local_storage_included: bool = False
    profile_dir_archive_included: bool = False


class ProfileBundleDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format: Literal["cloakbrowser.profile-bundle.v1"] = PROFILE_BUNDLE_FORMAT
    schema_version: Literal[1] = 1
    exported_at: str
    profile: ProfileBundleProfile = Field(repr=False)
    cookies: ProfileBundleCookies = Field(default_factory=ProfileBundleCookies)
    local_storage: ProfileBundleLocalStorage = Field(default_factory=ProfileBundleLocalStorage)
    profile_dir: ProfileBundleProfileDir = Field(default_factory=ProfileBundleProfileDir)
    metadata: ProfileBundleMetadata


def _profile_config_for_bundle(
    profile: dict[str, Any],
    *,
    include_sensitive_proxy: bool,
) -> ProfileConfigExport:
    config = dict(profile)
    if not include_sensitive_proxy and config.get("proxy"):
        config["proxy"] = redact_proxy_asset_url(str(config["proxy"]))
    return ProfileConfigExport(**config)


def build_profile_config_bundle(
    profile: dict[str, Any],
    *,
    exported_at: str,
    app_version: str | None = None,
    include_sensitive_proxy: bool = False,
) -> ProfileBundleDocument:
    """Build a config-only bundle manifest without reading browser profile data."""

    config = _profile_config_for_bundle(
        profile,
        include_sensitive_proxy=include_sensitive_proxy,
    )
    source_profile_id = str(profile.get("id") or "")

    return ProfileBundleDocument(
        exported_at=exported_at,
        profile=ProfileBundleProfile(config=config),
        metadata=ProfileBundleMetadata(
            app_version=app_version,
            source_profile_id=source_profile_id,
            source_profile_name=config.name,
            fingerprint_seed_included=config.fingerprint_seed is not None,
            sensitive_proxy_included=include_sensitive_proxy and bool(config.proxy),
        ),
    )
