"""Deployment configuration and documentation guardrails."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_compose_exposes_local_admin_and_runtime_service_tokens():
    compose = (ROOT / "docker-compose.yml").read_text()

    assert "127.0.0.1:8080:8080" in compose
    assert "~/.invisible-browser-manager:/data" in compose
    assert "AUTH_TOKEN=${AUTH_TOKEN:-}" in compose
    assert "RUNTIME_SERVICE_TOKEN=${RUNTIME_SERVICE_TOKEN:-}" in compose


def test_readme_documents_runtime_service_token_boundary():
    readme = (ROOT / "README.md").read_text()

    assert "AUTH_TOKEN" in readme
    assert "RUNTIME_SERVICE_TOKEN" in readme
    assert "X-Runtime-Service-Token" in readme
    assert "Project Mileage App 不能直连 CloakBrowser runtime API" in readme
    assert "不要把 RUNTIME_SERVICE_TOKEN 放进前端环境变量" in readme
