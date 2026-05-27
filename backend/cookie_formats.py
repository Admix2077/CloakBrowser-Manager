"""Cookie import/export format helpers."""

from __future__ import annotations

from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, model_validator


COOKIE_JSON_FORMAT = "cloakbrowser.cookie-json.v1"


class CookieJsonCookie(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    name: str = Field(min_length=1, max_length=4096)
    value: str = Field(default="", max_length=1_048_576, repr=False)
    domain: str | None = Field(default=None, min_length=1, max_length=4096)
    url: str | None = Field(default=None, min_length=1, max_length=8192)
    path: str = Field(default="/", min_length=1, max_length=4096)
    expires: int | float | None = None
    secure: bool = False
    http_only: bool = Field(default=False, alias="httpOnly")
    same_site: Literal["Strict", "Lax", "None"] | None = Field(default=None, alias="sameSite")

    @model_validator(mode="after")
    def validate_cookie_scope(self):
        if not self.domain and not self.url:
            raise ValueError("Cookie must provide domain or url")
        return self

    def to_playwright_cookie(self) -> dict:
        return self.model_dump(mode="json", by_alias=True, exclude_none=True)


class CookieJsonDocument(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    format: Literal["cloakbrowser.cookie-json.v1"] = COOKIE_JSON_FORMAT
    schema_version: Literal[1] = 1
    profile_id: str | None = Field(default=None, min_length=1, max_length=4096)
    exported_at: str | None = Field(default=None, min_length=1, max_length=128)
    cookies: list[CookieJsonCookie] = Field(default_factory=list, max_length=10_000)


def build_cookie_json_export(
    cookies: list[dict],
    *,
    profile_id: str | None = None,
    exported_at: str | None = None,
) -> CookieJsonDocument:
    return CookieJsonDocument(
        profile_id=profile_id,
        exported_at=exported_at,
        cookies=[CookieJsonCookie.model_validate(cookie) for cookie in cookies],
    )


def cookies_for_playwright(document: CookieJsonDocument) -> list[dict]:
    return [cookie.to_playwright_cookie() for cookie in document.cookies]


def cookie_json_audit_summary(document: CookieJsonDocument) -> dict:
    same_site_counts = {"Strict": 0, "Lax": 0, "None": 0, "unset": 0}
    session_cookie_count = 0
    persistent_cookie_count = 0

    for cookie in document.cookies:
        same_site_counts[cookie.same_site or "unset"] += 1
        if cookie.expires is None or cookie.expires < 0:
            session_cookie_count += 1
        else:
            persistent_cookie_count += 1

    return {
        "format": document.format,
        "schema_version": document.schema_version,
        "cookie_count": len(document.cookies),
        "domain_scoped_count": sum(1 for cookie in document.cookies if cookie.domain),
        "url_scoped_count": sum(1 for cookie in document.cookies if cookie.url),
        "secure_count": sum(1 for cookie in document.cookies if cookie.secure),
        "http_only_count": sum(1 for cookie in document.cookies if cookie.http_only),
        "session_cookie_count": session_cookie_count,
        "persistent_cookie_count": persistent_cookie_count,
        "same_site_counts": same_site_counts,
    }


def parse_netscape_cookies(
    text: str,
    *,
    profile_id: str | None = None,
    exported_at: str | None = None,
) -> CookieJsonDocument:
    cookies = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or (line.startswith("#") and not line.startswith("#HttpOnly_")):
            continue

        http_only = line.startswith("#HttpOnly_")
        if http_only:
            line = line.removeprefix("#HttpOnly_")

        parts = line.split("\t")
        if len(parts) != 7:
            raise ValueError(f"Invalid Netscape cookie line {line_number}")

        domain, _include_subdomains, path, secure, expires, name, value = parts
        try:
            expires_value = int(expires)
        except ValueError as exc:
            raise ValueError(f"Invalid Netscape cookie line {line_number}") from exc

        cookies.append(
            CookieJsonCookie(
                name=name,
                value=value,
                domain=domain,
                path=path or "/",
                expires=expires_value,
                secure=secure.upper() == "TRUE",
                httpOnly=http_only,
            )
        )

    return CookieJsonDocument(
        profile_id=profile_id,
        exported_at=exported_at,
        cookies=cookies,
    )


def build_netscape_cookie_export(document: CookieJsonDocument) -> str:
    lines = ["# Netscape HTTP Cookie File"]
    for cookie in document.cookies:
        domain = cookie.domain
        if not domain and cookie.url:
            parsed = urlparse(cookie.url)
            domain = parsed.hostname
        if not domain:
            continue

        include_subdomains = "TRUE" if domain.startswith(".") else "FALSE"
        prefix = "#HttpOnly_" if cookie.http_only else ""
        expires = int(cookie.expires) if cookie.expires is not None else 0
        lines.append(
            "\t".join(
                [
                    f"{prefix}{domain}",
                    include_subdomains,
                    cookie.path or "/",
                    "TRUE" if cookie.secure else "FALSE",
                    str(expires),
                    cookie.name,
                    cookie.value,
                ]
            )
        )
    return "\n".join(lines)


def netscape_cookie_audit_summary(document: CookieJsonDocument) -> dict:
    session_cookie_count = 0
    persistent_cookie_count = 0
    for cookie in document.cookies:
        if cookie.expires is None or cookie.expires <= 0:
            session_cookie_count += 1
        else:
            persistent_cookie_count += 1

    return {
        "format": "netscape-cookie-file",
        "cookie_count": len(document.cookies),
        "secure_count": sum(1 for cookie in document.cookies if cookie.secure),
        "session_cookie_count": session_cookie_count,
        "persistent_cookie_count": persistent_cookie_count,
        "http_only_count": sum(1 for cookie in document.cookies if cookie.http_only),
    }
