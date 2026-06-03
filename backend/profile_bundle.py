"""Profile bundle manifest helpers."""

from __future__ import annotations

import hashlib
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool

from .cookie_formats import COOKIE_JSON_FORMAT, CookieJsonDocument, cookie_json_audit_summary
from .models import ProfileConfigExport
from .profile_import import sanitize_profile_config_export_data


PROFILE_BUNDLE_FORMAT = "cloakbrowser.profile-bundle.v1"


class ProfileBundleProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    config: ProfileConfigExport


class ProfileBundleCookies(BaseModel):
    model_config = ConfigDict(extra="forbid")

    included: bool = False
    format: Literal["cloakbrowser.cookie-json.v1"] = COOKIE_JSON_FORMAT
    schema_version: Literal[1] = 1
    summary: dict[str, Any] = Field(default_factory=lambda: {"cookie_count": 0})
    document: dict[str, Any] | None = Field(default=None, repr=False)


class ProfileBundleLocalStorage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    included: bool = False
    format: Literal["cloakbrowser.local-storage.v1"] | None = None
    schema_version: Literal[1] | None = None
    origin: str | None = None
    origin_count: int = 0
    entry_count: int | None = None
    entries: list[dict[str, str]] | None = Field(default=None, repr=False)


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


class ProfileBundleConfigImportProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")

    config: ProfileConfigExport


class ProfileBundleConfigImportDocument(BaseModel):
    model_config = ConfigDict(extra="ignore")

    format: Literal["cloakbrowser.profile-bundle.v1"] = PROFILE_BUNDLE_FORMAT
    schema_version: Literal[1] = 1
    profile: ProfileBundleConfigImportProfile


class ProfileBundleImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bundle: ProfileBundleConfigImportDocument
    confirm_import: StrictBool = False



def _profile_config_for_bundle(
    profile: dict[str, Any],
    *,
    include_sensitive_proxy: bool,
) -> ProfileConfigExport:
    config = sanitize_profile_config_export_data(
        profile,
        include_sensitive_proxy=include_sensitive_proxy,
    )
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


def add_cookie_document_to_bundle(
    bundle: ProfileBundleDocument,
    document: CookieJsonDocument,
) -> ProfileBundleDocument:
    bundle.cookies = ProfileBundleCookies(
        included=True,
        summary=cookie_json_audit_summary(document),
        document=document.model_dump(mode="json", by_alias=True, exclude_none=True),
    )
    bundle.metadata.cookies_included = True
    return bundle


def local_storage_audit_metadata(origin: str, entries: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "format": "cloakbrowser.local-storage.v1",
        "schema_version": 1,
        "entry_count": len(entries),
        "total_value_bytes": sum(len(entry.get("value", "")) for entry in entries),
        "origin_hash": hashlib.sha256(origin.encode("utf-8")).hexdigest(),
    }


def add_local_storage_entries_to_bundle(
    bundle: ProfileBundleDocument,
    *,
    origin: str,
    entries: list[dict[str, str]],
) -> ProfileBundleDocument:
    bundle.local_storage = ProfileBundleLocalStorage(
        included=True,
        format="cloakbrowser.local-storage.v1",
        schema_version=1,
        origin=origin,
        origin_count=1,
        entry_count=len(entries),
        entries=entries,
    )
    bundle.metadata.local_storage_included = True
    return bundle
