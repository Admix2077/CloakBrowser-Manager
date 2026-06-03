"""CSV profile import preview helpers."""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from . import database as db
from .browser_manager import (
    _filter_firefox_launch_args,
    _public_gpu_text,
    _public_hardware_concurrency,
    _public_screen_dimension,
)
from .models import (
    ProfileCreate,
    ProfileImportPreviewProfile,
    ProfileImportPreviewResponse,
    ProfileImportPreviewRow,
    TagResponse,
)
from .proxies import normalize_proxy_asset_url, redact_proxy_asset_url


TEMPLATE_FIELDS = (
    "platform",
    "screen_width",
    "screen_height",
    "gpu_vendor",
    "gpu_renderer",
    "hardware_concurrency",
    "color_scheme",
    "humanize",
    "human_preset",
    "launch_args",
    "geoip",
)

SUPPORTED_COLUMNS = {
    "name",
    "proxy",
    "tags",
    "notes",
    "template",
    "platform",
    "locale",
    "timezone",
    "screen_width",
    "screen_height",
    "gpu_vendor",
    "gpu_renderer",
    "hardware_concurrency",
    "color_scheme",
    "humanize",
    "human_preset",
    "launch_args",
    "geoip",
}

PLATFORMS = {"windows", "macos", "linux"}
COLOR_SCHEMES = {"light", "dark", "no-preference"}
HUMAN_PRESETS = {"default", "careful"}
SAFE_PROXY_ERROR_DETAILS = (
    ("Invalid proxy scheme", "Invalid proxy scheme"),
    ("Invalid proxy URL", "Invalid proxy URL"),
    ("Proxy URL missing hostname", "Proxy URL missing hostname"),
    ("Proxy URL invalid port", "Proxy URL invalid port"),
    ("Proxy URL missing port", "Proxy URL missing port"),
)
_SENSITIVE_TEMPLATE_ARG_RE = re.compile(
    r"(?:https?://|[?&#]|\bauthorization\b|\bbearer\b|\btoken=|\bpassword=|\bsecret=|\bcookie=)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ParsedProfileImportRow:
    line_number: int
    source: dict[str, str]
    errors: list[str]
    create_data: dict[str, Any] | None


class ProfileImportHeaderError(ValueError):
    """Raised when pasted CSV does not contain a usable profile header."""


class ProfileTemplateNotFoundError(ValueError):
    """Raised when a template id used by profile creation is missing."""


def apply_profile_template_fields(data: dict[str, Any], explicit_fields: set[str]) -> dict[str, Any]:
    """Apply copied template fingerprint fields while preserving explicit profile fields."""
    template_id = data.get("template_id")
    if not template_id:
        return data

    template = db.get_profile_template(str(template_id))
    if not template:
        raise ProfileTemplateNotFoundError("Profile template not found")

    for field in TEMPLATE_FIELDS:
        if field not in explicit_fields:
            safe_value, should_copy = _safe_template_field(field, template.get(field))
            if should_copy:
                data[field] = safe_value
    return data


def _safe_template_field(field: str, value: Any) -> tuple[Any, bool]:
    if field == "platform":
        return value, isinstance(value, str) and value in PLATFORMS
    if field in {"screen_width", "screen_height"}:
        dimension = _public_screen_dimension(value)
        return dimension, dimension is not None
    if field in {"gpu_vendor", "gpu_renderer"}:
        if value is None:
            return None, True
        text = _public_gpu_text(value)
        return text, bool(text)
    if field == "hardware_concurrency":
        concurrency = _public_hardware_concurrency(value)
        return concurrency, concurrency is not None
    if field == "color_scheme":
        if value is None:
            return None, True
        return value, isinstance(value, str) and value in COLOR_SCHEMES
    if field == "human_preset":
        return value, isinstance(value, str) and value in HUMAN_PRESETS
    if field in {"humanize", "geoip"}:
        if isinstance(value, bool):
            return value, True
        if isinstance(value, int) and value in {0, 1}:
            return bool(value), True
        return None, False
    if field == "launch_args":
        return _safe_template_launch_args(value), True
    return value, True


def _safe_template_launch_args(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    candidates = []
    for arg in value:
        if not isinstance(arg, str):
            continue
        text = arg.strip()
        if not text or _SENSITIVE_TEMPLATE_ARG_RE.search(text):
            continue
        candidates.append(text)
    return _filter_firefox_launch_args(candidates)


def preview_profile_csv_import(csv_text: str) -> ProfileImportPreviewResponse:
    parsed_rows = parse_profile_csv_import(csv_text)
    rows = [_preview_from_parsed(row) for row in parsed_rows]
    valid = sum(1 for row in rows if row.ok)
    return ProfileImportPreviewResponse(
        total=len(rows),
        valid=valid,
        invalid=len(rows) - valid,
        rows=rows,
    )


def parse_profile_csv_import(csv_text: str) -> list[ParsedProfileImportRow]:
    reader = csv.DictReader(io.StringIO(csv_text))
    headers = [_normalize_header(header) for header in (reader.fieldnames or [])]
    if not headers or not any(header in SUPPORTED_COLUMNS for header in headers):
        raise ProfileImportHeaderError("CSV header with profile columns is required")

    rows: list[ParsedProfileImportRow] = []
    for raw_row in reader:
        line_number = reader.line_num
        row = _normalize_row(raw_row)
        rows.append(_parse_row(line_number, row))
    return rows


def profile_create_data_for_import(row: ParsedProfileImportRow) -> dict[str, Any]:
    if row.create_data is None:
        raise ValueError("Cannot create profile from an invalid CSV import row")
    data = dict(row.create_data)
    data.pop("template_id", None)
    return data


def _preview_from_parsed(row: ParsedProfileImportRow) -> ProfileImportPreviewRow:
    if row.errors or row.create_data is None:
        return ProfileImportPreviewRow(
            line_number=row.line_number,
            ok=False,
            errors=row.errors,
            source=row.source,
            profile=None,
        )

    profile_data = dict(row.create_data)
    profile_data["proxy"] = _redact_optional_proxy(profile_data.get("proxy"))
    profile_data["tags"] = [TagResponse(**tag) for tag in profile_data.get("tags") or []]
    profile = ProfileImportPreviewProfile(**profile_data)
    return ProfileImportPreviewRow(
        line_number=row.line_number,
        ok=True,
        errors=[],
        source=row.source,
        profile=profile,
    )


def _parse_row(line_number: int, row: dict[str, str]) -> ParsedProfileImportRow:
    errors: list[str] = []
    source = _redacted_source(row)

    unknown_columns = [column for column in row if column and column not in SUPPORTED_COLUMNS]
    if unknown_columns:
        errors.append("Unsupported column")

    data: dict[str, Any] = {}
    explicit_fields: set[str] = set()

    name = row.get("name", "").strip()
    if name:
        data["name"] = name
        explicit_fields.add("name")
    else:
        errors.append("name is required")

    template_ref = row.get("template", "").strip()
    if template_ref:
        template = _resolve_template(template_ref)
        if template:
            data["template_id"] = template["id"]
            explicit_fields.add("template_id")
        else:
            errors.append("Template not found")

    _set_optional_text(row, data, explicit_fields, "locale")
    _set_optional_text(row, data, explicit_fields, "timezone")
    _set_optional_text(row, data, explicit_fields, "notes")
    _set_optional_text(row, data, explicit_fields, "gpu_vendor")
    _set_optional_text(row, data, explicit_fields, "gpu_renderer")

    proxy = row.get("proxy", "").strip()
    if proxy:
        try:
            normalized_proxy = normalize_proxy_asset_url(proxy)
            data["proxy"] = normalized_proxy
            explicit_fields.add("proxy")
        except ValueError as exc:
            errors.append(_safe_proxy_error_detail(str(exc)))

    platform = row.get("platform", "").strip().lower()
    if platform:
        if platform in PLATFORMS:
            data["platform"] = platform
            explicit_fields.add("platform")
        else:
            errors.append("platform must be one of: windows, macos, linux")

    color_scheme = row.get("color_scheme", "").strip().lower()
    if color_scheme:
        if color_scheme in COLOR_SCHEMES:
            data["color_scheme"] = color_scheme
            explicit_fields.add("color_scheme")
        else:
            errors.append("color_scheme must be one of: light, dark, no-preference")

    human_preset = row.get("human_preset", "").strip().lower()
    if human_preset:
        if human_preset in HUMAN_PRESETS:
            data["human_preset"] = human_preset
            explicit_fields.add("human_preset")
        else:
            errors.append("human_preset must be one of: default, careful")

    for field in ("screen_width", "screen_height", "hardware_concurrency"):
        _set_optional_int(row, data, explicit_fields, errors, field)

    for field in ("humanize", "geoip"):
        _set_optional_bool(row, data, explicit_fields, errors, field)

    tags = _parse_tags(row.get("tags", ""))
    if tags:
        data["tags"] = tags
        explicit_fields.add("tags")

    launch_args = _parse_list(row.get("launch_args", ""))
    if launch_args:
        data["launch_args"] = launch_args
        explicit_fields.add("launch_args")

    if not errors and data.get("template_id"):
        try:
            data = apply_profile_template_fields(data, explicit_fields)
        except ProfileTemplateNotFoundError as exc:
            errors.append(str(exc))

    if errors:
        return ParsedProfileImportRow(
            line_number=line_number,
            errors=errors,
            source=source,
            create_data=None,
        )

    try:
        profile_create = ProfileCreate(**data)
    except ValidationError as exc:
        return ParsedProfileImportRow(
            line_number=line_number,
            errors=_validation_errors(exc),
            source=source,
            create_data=None,
        )

    return ParsedProfileImportRow(
        line_number=line_number,
        errors=[],
        source=source,
        create_data=profile_create.model_dump(),
    )


def _normalize_header(header: str | None) -> str:
    return (header or "").strip().lower()


def _normalize_row(raw_row: dict[str | None, Any]) -> dict[str, str]:
    row: dict[str, str] = {}
    for key, value in raw_row.items():
        if key is None:
            extra_values = value if isinstance(value, list) else [str(value)]
            row["extra_values"] = ",".join(item for item in extra_values if item)
            continue
        row[_normalize_header(key)] = (value or "").strip()
    return row


def _set_optional_text(
    row: dict[str, str],
    data: dict[str, Any],
    explicit_fields: set[str],
    field: str,
) -> None:
    value = row.get(field, "").strip()
    if value:
        data[field] = value
        explicit_fields.add(field)


def _set_optional_int(
    row: dict[str, str],
    data: dict[str, Any],
    explicit_fields: set[str],
    errors: list[str],
    field: str,
) -> None:
    value = row.get(field, "").strip()
    if not value:
        return
    try:
        data[field] = int(value)
        explicit_fields.add(field)
    except ValueError:
        errors.append(f"{field} must be an integer")


def _set_optional_bool(
    row: dict[str, str],
    data: dict[str, Any],
    explicit_fields: set[str],
    errors: list[str],
    field: str,
) -> None:
    value = row.get(field, "").strip().lower()
    if not value:
        return
    if value in {"1", "true", "yes", "y"}:
        data[field] = True
        explicit_fields.add(field)
    elif value in {"0", "false", "no", "n"}:
        data[field] = False
        explicit_fields.add(field)
    else:
        errors.append(f"{field} must be a boolean")


def _parse_tags(raw: str) -> list[dict[str, str | None]]:
    return [{"tag": item, "color": None} for item in _parse_list(raw)]


def _parse_list(raw: str) -> list[str]:
    return [item.strip() for item in raw.split("|") if item.strip()]


def _resolve_template(template_ref: str) -> dict[str, Any] | None:
    by_id = db.get_profile_template(template_ref)
    if by_id:
        return by_id

    matches = [
        template
        for template in db.list_profile_templates()
        if template["name"].casefold() == template_ref.casefold()
    ]
    return matches[0] if len(matches) == 1 else None


def _redacted_source(row: dict[str, str]) -> dict[str, str]:
    source: dict[str, str] = {}
    unsupported_count = 0
    for field, value in row.items():
        if field not in SUPPORTED_COLUMNS:
            unsupported_count += 1
            continue
        if field == "proxy":
            source[field] = redact_proxy_asset_url(value) if value else value
        elif field == "template":
            source[field] = _redact_csv_source_text(value)
        else:
            source[field] = _redact_csv_source_text(value)
    if unsupported_count:
        source["unsupported_column_count"] = str(unsupported_count)
    return source


def _safe_proxy_error_detail(message: str) -> str:
    for prefix, detail in SAFE_PROXY_ERROR_DETAILS:
        if message.startswith(prefix):
            return detail
    return "Invalid proxy URL"


def _redact_optional_proxy(proxy: object) -> str | None:
    return redact_proxy_asset_url(str(proxy)) if proxy else None


def _redact_csv_source_text(value: str) -> str:
    lowered = value.casefold()
    if (
        "://" in value
        or "/" in value
        or "\\" in value
        or "@" in value
        or "?" in value
        or "#" in value
        or "token" in lowered
        or "secret" in lowered
        or "password" in lowered
        or "cookie" in lowered
        or "authorization" in lowered
        or "bearer" in lowered
    ):
        return "[redacted]"
    return value


def _validation_errors(exc: ValidationError) -> list[str]:
    errors = []
    for error in exc.errors():
        loc = ".".join(str(item) for item in error.get("loc", ()))
        message = str(error.get("msg", "Invalid value"))
        errors.append(f"{loc}: {message}" if loc else message)
    return errors
