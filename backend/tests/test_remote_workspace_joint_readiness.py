from __future__ import annotations

from pathlib import Path

from scripts.remote_workspace_joint_readiness import (
    build_remote_workspace_joint_readiness_report,
)


REPORT_DATE = "2026-06-08"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_pass_reports(root: Path) -> None:
    _write(
        root / f"cloakbrowser-invisible-manager/test-reports/{REPORT_DATE}-runtime-live/REPORT.md",
        "\n".join(
            [
                "RUNTIME_LIVE_WORKSPACE_E2E_READY: PASS",
                "RUNTIME_LIVE_WORKSPACE_PREFLIGHT=PASS",
                "RUNTIME_LIVE_WORKSPACE_RUNTIME_SESSION=PASS",
                "RUNTIME_LIVE_WORKSPACE_VIEWER_TOKEN=PASS",
                "RUNTIME_LIVE_WORKSPACE_VNC_WEBSOCKET=PASS",
                "RUNTIME_LIVE_WORKSPACE_TERMINATE=PASS",
                "- websocket_frame_prefix=RFB",
            ]
        ),
    )
    _write(
        root / f"project-mileage-v3-payload/test-reports/{REPORT_DATE}-remote-workspace-broker-live/REPORT.md",
        "\n".join(
            [
                "REMOTE_WORKSPACE_BROKER_E2E_READY: PASS",
                "REMOTE_WORKSPACE_BROKER_CREATE_OR_REUSE=PASS",
                "REMOTE_WORKSPACE_BROKER_DETAIL=PASS",
                "REMOTE_WORKSPACE_BROKER_LIST=PASS",
                "REMOTE_WORKSPACE_BROKER_LOCAL_SESSION=PASS",
                "viewer_available=true",
                "viewer_reason_code=null",
            ]
        ),
    )
    _write(
        root
        / f"project-mileage-v3-app/doc/tasks-browser-test-v1/runs/{REPORT_DATE}-remote-workspace-adapter-live/REPORT.md",
        "\n".join(
            [
                "REMOTE_WORKSPACE_ADAPTER_E2E_READY: PASS",
                "REMOTE_WORKSPACE_ADAPTER_CREATE_OR_REUSE=PASS",
                "REMOTE_WORKSPACE_ADAPTER_DETAIL=PASS",
                "REMOTE_WORKSPACE_ADAPTER_LIST=PASS",
                "REMOTE_WORKSPACE_ADAPTER_VIEWER=PASS",
                "viewer.available：true",
                "viewer.reasonCode：null",
            ]
        ),
    )
    _write(
        root
        / f"project-mileage-v3-app/doc/tasks-browser-test-v1/runs/{REPORT_DATE}-remote-workspace-browser-live/REPORT.md",
        "\n".join(
            [
                "REMOTE_WORKSPACE_BROWSER_E2E_READY: PASS",
                "viewer.available：true",
                "viewer.reasonCode：null",
                "noVNC canvas 已绘制像素",
                "noVNC canvas 点击与低敏键盘输入后仍有像素",
                "交互后页面正文和地址栏无敏感连接信息",
            ]
        ),
    )


def test_joint_readiness_report_passes_when_all_low_sensitive_reports_pass(tmp_path: Path) -> None:
    _write_pass_reports(tmp_path)

    report = build_remote_workspace_joint_readiness_report(tmp_path, REPORT_DATE)

    assert report.ready is True
    assert report.lines == [
        "RUNTIME_LIVE_WORKSPACE_EVIDENCE=PASS",
        "REMOTE_WORKSPACE_BROKER_EVIDENCE=PASS",
        "REMOTE_WORKSPACE_ADAPTER_EVIDENCE=PASS",
        "REMOTE_WORKSPACE_BROWSER_EVIDENCE=PASS",
        "REMOTE_WORKSPACE_JOINT_E2E_READY: PASS",
    ]


def test_joint_readiness_report_marks_missing_report_not_verified(tmp_path: Path) -> None:
    _write_pass_reports(tmp_path)
    (
        tmp_path
        / f"project-mileage-v3-app/doc/tasks-browser-test-v1/runs/{REPORT_DATE}-remote-workspace-browser-live/REPORT.md"
    ).unlink()

    report = build_remote_workspace_joint_readiness_report(tmp_path, REPORT_DATE)

    assert report.ready is False
    assert "REMOTE_WORKSPACE_BROWSER_EVIDENCE=MISSING" in report.lines
    assert "REMOTE_WORKSPACE_JOINT_E2E_READY: NOT VERIFIED" in report.lines


def test_joint_readiness_report_uses_not_verified_evidence(tmp_path: Path) -> None:
    _write_pass_reports(tmp_path)
    (
        tmp_path
        / f"project-mileage-v3-app/doc/tasks-browser-test-v1/runs/{REPORT_DATE}-remote-workspace-browser-live/REPORT.md"
    ).unlink()
    _write(
        tmp_path
        / (
            "project-mileage-v3-app/doc/tasks-browser-test-v1/runs/"
            f"{REPORT_DATE}-remote-workspace-browser-live-not-verified/REPORT.md"
        ),
        "REMOTE_WORKSPACE_BROWSER_E2E_READY: NOT VERIFIED\n",
    )

    report = build_remote_workspace_joint_readiness_report(tmp_path, REPORT_DATE)

    assert report.ready is False
    assert "REMOTE_WORKSPACE_BROWSER_EVIDENCE=NOT_VERIFIED" in report.lines
    assert "REMOTE_WORKSPACE_JOINT_E2E_READY: NOT VERIFIED" in report.lines


def test_joint_readiness_report_never_echoes_sensitive_report_text(tmp_path: Path) -> None:
    _write_pass_reports(tmp_path)
    _write(
        tmp_path
        / f"cloakbrowser-invisible-manager/test-reports/{REPORT_DATE}-runtime-live/REPORT.md",
        "RUNTIME_LIVE_WORKSPACE_E2E_READY: PASS\nviewer_token=secret\n",
    )

    report = build_remote_workspace_joint_readiness_report(tmp_path, REPORT_DATE)
    text = "\n".join(report.lines)

    assert report.ready is False
    assert "RUNTIME_LIVE_WORKSPACE_EVIDENCE=SENSITIVE" in report.lines
    assert "secret" not in text
    assert "viewer_token=secret" not in text
