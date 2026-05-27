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


def test_backup_restore_runbook_documents_data_scope_and_quiesce_boundary():
    runbook = (ROOT / "docs/ai-docs/v1/deployment-backup-restore-runbook.md").read_text()

    assert "/data/profiles.db" in runbook
    assert "/data/profiles/" in runbook
    assert "docker compose down" in runbook
    assert "不支持热备" in runbook
    assert "恢复前先备份当前 /data" in runbook
    assert "/api/status" in runbook


def test_backup_restore_runbook_documents_sensitive_and_project_mileage_boundaries():
    runbook = (ROOT / "docs/ai-docs/v1/deployment-backup-restore-runbook.md").read_text()
    readme = (ROOT / "README.md").read_text()

    assert "不要提交备份包" in runbook
    assert ".env" in runbook
    assert "secret" in runbook.lower()
    assert "cookie" in runbook.lower()
    assert "RUNTIME_SERVICE_TOKEN" in runbook
    assert "Project Mileage app/payload" in runbook
    assert "App 不能直连 CloakBrowser" in runbook
    assert "deployment-backup-restore-runbook.md" in readme


def test_backup_restore_progress_marks_runbook_without_claiming_full_restore():
    task_doc = (ROOT / "docs/ai-docs/v1/tasks/12-deployment-observability.md").read_text()
    progress = (ROOT / "docs/ai-docs/v1/tasks/progress.md").read_text()

    assert "- [x] 文档说明 backup/restore。" in task_doc
    assert "- [ ] 备份 SQLite。" in task_doc
    assert "- [ ] 备份 profile dirs。" in task_doc
    assert "- [ ] 恢复后可启动 profile。" in task_doc
    assert "deployment-backup-restore-runbook.md" in progress
