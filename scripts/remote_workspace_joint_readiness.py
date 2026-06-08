from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import argparse
import re
import sys


EvidenceStatus = str


@dataclass(frozen=True)
class EvidenceDefinition:
    key: str
    relative_path: str
    required_markers: tuple[str, ...]
    required_value_markers: tuple[str, ...] = ()
    not_verified_paths: tuple[str, ...] = ()
    not_verified_markers: tuple[str, ...] = ()


@dataclass(frozen=True)
class JointReadinessReport:
    ready: bool
    lines: list[str]


EVIDENCE_DEFINITIONS = (
    EvidenceDefinition(
        key="RUNTIME_LIVE_WORKSPACE_EVIDENCE",
        relative_path="cloakbrowser-invisible-manager/test-reports/{date}-runtime-live/REPORT.md",
        required_markers=(
            "RUNTIME_LIVE_WORKSPACE_E2E_READY: PASS",
            "RUNTIME_LIVE_WORKSPACE_PREFLIGHT=PASS",
            "RUNTIME_LIVE_WORKSPACE_RUNTIME_SESSION=PASS",
            "RUNTIME_LIVE_WORKSPACE_VIEWER_TOKEN=PASS",
            "RUNTIME_LIVE_WORKSPACE_VNC_WEBSOCKET=PASS",
            "RUNTIME_LIVE_WORKSPACE_TERMINATE=PASS",
            "websocket_frame_prefix=RFB",
        ),
        required_value_markers=(
            "session_id=",
            "external_session_id=",
            "profile_id=",
            "viewer_expires_at=",
        ),
        not_verified_paths=(
            "cloakbrowser-invisible-manager/test-reports/{date}-runtime-live-preflight/REPORT.md",
        ),
        not_verified_markers=("RUNTIME_LIVE_WORKSPACE_E2E_READY: NOT VERIFIED",),
    ),
    EvidenceDefinition(
        key="REMOTE_WORKSPACE_BROKER_EVIDENCE",
        relative_path="project-mileage-v3-payload/test-reports/{date}-remote-workspace-broker-live/REPORT.md",
        required_markers=(
            "REMOTE_WORKSPACE_BROKER_E2E_READY: PASS",
            "REMOTE_WORKSPACE_BROKER_CREATE_OR_REUSE=PASS",
            "REMOTE_WORKSPACE_BROKER_DETAIL=PASS",
            "REMOTE_WORKSPACE_BROKER_LIST=PASS",
            "REMOTE_WORKSPACE_BROKER_LOCAL_SESSION=PASS",
            "viewer_available=true",
            "viewer_reason_code=null",
        ),
        required_value_markers=(
            "session_id=",
            "remote_account_id=",
            "runtime_status=",
            "viewer_expires_at=",
            "local_session_count=",
        ),
        not_verified_paths=(
            "project-mileage-v3-payload/test-reports/{date}-remote-workspace-live-preflight/REPORT.md",
        ),
        not_verified_markers=(
            "REMOTE_WORKSPACE_BROWSER_E2E_READY: NOT VERIFIED",
            "REMOTE_WORKSPACE_JOINT_E2E_READY: NOT VERIFIED",
        ),
    ),
    EvidenceDefinition(
        key="REMOTE_WORKSPACE_ADAPTER_EVIDENCE",
        relative_path=(
            "project-mileage-v3-app/doc/tasks-browser-test-v1/runs/"
            "{date}-remote-workspace-adapter-live/REPORT.md"
        ),
        required_markers=(
            "REMOTE_WORKSPACE_ADAPTER_E2E_READY: PASS",
            "REMOTE_WORKSPACE_ADAPTER_CREATE_OR_REUSE=PASS",
            "REMOTE_WORKSPACE_ADAPTER_DETAIL=PASS",
            "REMOTE_WORKSPACE_ADAPTER_LIST=PASS",
            "REMOTE_WORKSPACE_ADAPTER_VIEWER=PASS",
            "viewer.available：true",
            "viewer.reasonCode：null",
        ),
        required_value_markers=(
            "目标订单号：",
            "目标 remoteAccountId：",
            "创建/复用 session id：",
            "详情 session id：",
            "列表 session 数量：",
            "expiresAt：",
        ),
        not_verified_paths=(
            "project-mileage-v3-app/doc/tasks-browser-test-v1/runs/"
            "{date}-remote-workspace-live-preflight/REPORT.md",
        ),
        not_verified_markers=("REMOTE_WORKSPACE_BROWSER_E2E_READY: NOT VERIFIED",),
    ),
    EvidenceDefinition(
        key="REMOTE_WORKSPACE_BROWSER_EVIDENCE",
        relative_path=(
            "project-mileage-v3-app/doc/tasks-browser-test-v1/runs/"
            "{date}-remote-workspace-browser-live/REPORT.md"
        ),
        required_markers=(
            "REMOTE_WORKSPACE_BROWSER_E2E_READY: PASS",
            "viewer.available：true",
            "viewer.reasonCode：null",
            "noVNC canvas 已绘制像素",
            "noVNC canvas 点击与低敏键盘输入后仍有像素",
            "交互后页面正文和地址栏无敏感连接信息",
        ),
        required_value_markers=(
            "目标订单号：",
            "目标 remoteAccountId：",
            "Payload 可启动订单数量：",
            "Payload broker session id：",
            "App VNC pathname：",
        ),
        not_verified_paths=(
            "project-mileage-v3-app/doc/tasks-browser-test-v1/runs/"
            "{date}-remote-workspace-browser-live-not-verified/REPORT.md",
            "project-mileage-v3-app/doc/tasks-browser-test-v1/runs/"
            "{date}-remote-workspace-live-preflight/REPORT.md",
        ),
        not_verified_markers=("REMOTE_WORKSPACE_BROWSER_E2E_READY: NOT VERIFIED",),
    ),
)

SENSITIVE_REPORT_MARKERS = (
    "runtime_service_token",
    "runtime-service-token",
    "service_token",
    "service-token",
    "viewer_token",
    "viewer-token",
    "viewerToken",
    "proxy_password",
    "proxy-password",
    "account_password",
    "account-password",
    "Authorization",
    "Bearer ",
    "client_secret",
    "client-secret",
    "private_key",
    "private-key",
    "cookie",
)


def _default_workspace_root() -> Path:
    return Path.cwd().parent


def _default_report_date() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _assert_report_date(value: str) -> None:
    parts = value.split("-")
    if len(parts) != 3 or any(not part.isdigit() for part in parts):
        raise ValueError("Invalid remote workspace readiness report date")
    if len(parts[0]) != 4 or len(parts[1]) != 2 or len(parts[2]) != 2:
        raise ValueError("Invalid remote workspace readiness report date")


def _report_path(workspace_root: Path, relative_path: str, report_date: str) -> Path:
    return workspace_root / relative_path.format(date=report_date)


def _contains_sensitive_text(text: str) -> bool:
    low_sensitive_status_text = re.sub(
        r"^\s*-?\s*[A-Z0-9_]+=(?:SET|EMPTY|INVALID|PASS|FAIL)\s*$",
        "",
        text,
        flags=re.MULTILINE,
    )
    lowered = low_sensitive_status_text.lower()
    return any(marker.lower() in lowered for marker in SENSITIVE_REPORT_MARKERS)


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def _has_required_value(text: str, marker: str) -> bool:
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("- "):
            line = line[2:].strip()
        if line.startswith(marker) and line[len(marker):].strip():
            return True
    return False


def _status_for_pass_report(workspace_root: Path, report_date: str, evidence: EvidenceDefinition) -> EvidenceStatus:
    text = _read_text(_report_path(workspace_root, evidence.relative_path, report_date))
    if text is None:
        return "MISSING"
    if _contains_sensitive_text(text):
        return "SENSITIVE"
    if any(marker in text for marker in evidence.not_verified_markers):
        return "FAIL"
    if all(marker in text for marker in evidence.required_markers) and all(
        _has_required_value(text, marker) for marker in evidence.required_value_markers
    ):
        return "PASS"
    return "FAIL"


def _status_for_not_verified_report(
    workspace_root: Path,
    report_date: str,
    evidence: EvidenceDefinition,
) -> EvidenceStatus:
    for relative_path in evidence.not_verified_paths:
        text = _read_text(_report_path(workspace_root, relative_path, report_date))
        if text is None:
            continue
        if _contains_sensitive_text(text):
            return "SENSITIVE"
        if all(marker in text for marker in evidence.not_verified_markers):
            return "NOT_VERIFIED"
    return "MISSING"


def _evidence_status(workspace_root: Path, report_date: str, evidence: EvidenceDefinition) -> EvidenceStatus:
    status = _status_for_pass_report(workspace_root, report_date, evidence)
    if status != "MISSING":
        return status
    return _status_for_not_verified_report(workspace_root, report_date, evidence)


def build_remote_workspace_joint_readiness_report(
    workspace_root: Path | str | None = None,
    report_date: str | None = None,
) -> JointReadinessReport:
    root = Path(workspace_root) if workspace_root is not None else _default_workspace_root()
    date = report_date or _default_report_date()
    _assert_report_date(date)

    lines = [
        f"{evidence.key}={_evidence_status(root, date, evidence)}"
        for evidence in EVIDENCE_DEFINITIONS
    ]
    ready = all(line.endswith("=PASS") for line in lines)
    lines.append(f"REMOTE_WORKSPACE_JOINT_E2E_READY: {'PASS' if ready else 'NOT VERIFIED'}")
    return JointReadinessReport(ready=ready, lines=lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Summarize Project Mileage remote workspace joint readiness evidence.")
    parser.add_argument("--workspace-root", default=None)
    parser.add_argument("--date", default=None)
    args = parser.parse_args(argv)

    report = build_remote_workspace_joint_readiness_report(args.workspace_root, args.date)
    for line in report.lines:
        print(line)
    return 0 if report.ready else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
