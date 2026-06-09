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
                "- session_id=rws_live_1",
                "- external_session_id=pm-live-1",
                "- profile_id=profile-live-1",
                "- viewer_expires_at=2099-06-08T00:00:00.000Z",
                "- websocket_frame_prefix=RFB",
            ]
        ),
    )
    _write(
        root / f"project-mileage-v3-payload/test-reports/{REPORT_DATE}-remote-workspace-broker-live/REPORT.md",
        "\n".join(
            [
                "REMOTE_WORKSPACE_BROKER_E2E_READY: PASS",
                "REMOTE_WORKSPACE_BROKER_LIVE=PASS",
                "REMOTE_WORKSPACE_BROKER_CREATE_OR_REUSE=PASS",
                "REMOTE_WORKSPACE_BROKER_DETAIL=PASS",
                "REMOTE_WORKSPACE_BROKER_LIST=PASS",
                "REMOTE_WORKSPACE_BROKER_LOCAL_SESSION=PASS",
                "session_id=rws_broker_1",
                "remote_account_id=account-live-1",
                "runtime_status=active",
                "viewer_available=true",
                "viewer_reason_code=null",
                "viewer_expires_at=2099-06-08T00:00:00.000Z",
                "session_listed=true",
                "local_session_count=1",
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
                "目标订单号：AO-LIVE-1",
                "目标 remoteAccountId：account-live-1",
                "创建/复用 session id：rws_adapter_1",
                "详情 session id：rws_adapter_1",
                "列表 session 数量：1",
                "viewer.available：true",
                "viewer.reasonCode：null",
                "viewer.originAllowed=true",
                "expiresAt：2099-06-08T00:00:00.000Z",
            ]
        ),
    )
    _write(
        root
        / f"project-mileage-v3-app/doc/tasks-browser-test-v1/runs/{REPORT_DATE}-remote-workspace-browser-live/REPORT.md",
        "\n".join(
            [
                "REMOTE_WORKSPACE_BROWSER_E2E_READY: PASS",
                "目标订单号：AO-LIVE-1",
                "目标 remoteAccountId：account-live-1",
                "Payload 可启动订单数量：1",
                "Payload broker session id：rws_browser_1",
                "App VNC pathname：/app/remote-workspace/rws_browser_1/vnc",
                "viewer.available：true",
                "viewer.reasonCode：null",
                "viewer.originAllowed=true",
                "expiresAt：2099-06-08T00:00:00.000Z",
                "真实 App 登录桥建立登录态",
                "页面启动卡片数量与 Payload launchable 订单数量一致",
                "页面启动卡片订单号集合与 Payload launchable 订单集合一致",
                "目标订单卡片唯一匹配",
                "VNC pathname 保持同一 Payload broker session",
                "noVNC canvas 已绘制像素",
                "noVNC canvas 点击与低敏键盘输入后仍有像素",
                "交互后页面无连接失败或已断开状态",
                "交互后页面正文和地址栏无敏感连接信息",
                "交互后 Payload broker 详情与 session 列表复核通过",
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


def test_joint_readiness_report_uses_broker_not_verified_marker(tmp_path: Path) -> None:
    _write_pass_reports(tmp_path)
    (
        tmp_path / f"project-mileage-v3-payload/test-reports/{REPORT_DATE}-remote-workspace-broker-live/REPORT.md"
    ).unlink()
    _write(
        tmp_path / f"project-mileage-v3-payload/test-reports/{REPORT_DATE}-remote-workspace-live-preflight/REPORT.md",
        "\n".join(
            [
                "REMOTE_WORKSPACE_BROWSER_E2E_READY: NOT VERIFIED",
                "REMOTE_WORKSPACE_JOINT_E2E_READY: NOT VERIFIED",
            ]
        ),
    )

    report = build_remote_workspace_joint_readiness_report(tmp_path, REPORT_DATE)

    assert report.ready is False
    assert "REMOTE_WORKSPACE_BROKER_EVIDENCE=NOT_VERIFIED" in report.lines
    assert "REMOTE_WORKSPACE_JOINT_E2E_READY: NOT VERIFIED" in report.lines


def test_joint_readiness_report_uses_payload_preflight_browser_not_verified_marker(tmp_path: Path) -> None:
    _write_pass_reports(tmp_path)
    (
        tmp_path / f"project-mileage-v3-payload/test-reports/{REPORT_DATE}-remote-workspace-broker-live/REPORT.md"
    ).unlink()
    _write(
        tmp_path / f"project-mileage-v3-payload/test-reports/{REPORT_DATE}-remote-workspace-live-preflight/REPORT.md",
        "\n".join(
            [
                "REMOTE_WORKSPACE_BROWSER_E2E_READY: NOT VERIFIED",
                "REMOTE_WORKSPACE_JOINT_E2E_READY: NOT VERIFIED",
                "REMOTE_WORKSPACE_LIVE_PREFLIGHT=FAIL",
            ]
        ),
    )

    report = build_remote_workspace_joint_readiness_report(tmp_path, REPORT_DATE)

    assert report.ready is False
    assert "REMOTE_WORKSPACE_BROKER_EVIDENCE=NOT_VERIFIED" in report.lines
    assert "REMOTE_WORKSPACE_JOINT_E2E_READY: NOT VERIFIED" in report.lines


def test_joint_readiness_report_rejects_runtime_pass_with_unparsable_viewer_expiry_evidence(tmp_path: Path) -> None:
    _write_pass_reports(tmp_path)
    _write(
        tmp_path / f"cloakbrowser-invisible-manager/test-reports/{REPORT_DATE}-runtime-live/REPORT.md",
        "\n".join(
            [
                "RUNTIME_LIVE_WORKSPACE_E2E_READY: PASS",
                "RUNTIME_LIVE_WORKSPACE_PREFLIGHT=PASS",
                "RUNTIME_LIVE_WORKSPACE_RUNTIME_SESSION=PASS",
                "RUNTIME_LIVE_WORKSPACE_VIEWER_TOKEN=PASS",
                "RUNTIME_LIVE_WORKSPACE_VNC_WEBSOCKET=PASS",
                "RUNTIME_LIVE_WORKSPACE_TERMINATE=PASS",
                "- session_id=rws_live_1",
                "- external_session_id=pm-live-1",
                "- profile_id=profile-live-1",
                "- viewer_expires_at=not-a-date",
                "- websocket_frame_prefix=RFB",
            ]
        ),
    )

    report = build_remote_workspace_joint_readiness_report(tmp_path, REPORT_DATE)

    assert report.ready is False
    assert "RUNTIME_LIVE_WORKSPACE_EVIDENCE=FAIL" in report.lines
    assert "REMOTE_WORKSPACE_JOINT_E2E_READY: NOT VERIFIED" in report.lines


def test_joint_readiness_report_rejects_broker_pass_with_unparsable_viewer_expiry_evidence(tmp_path: Path) -> None:
    _write_pass_reports(tmp_path)
    _write(
        tmp_path / f"project-mileage-v3-payload/test-reports/{REPORT_DATE}-remote-workspace-broker-live/REPORT.md",
        "\n".join(
            [
                "REMOTE_WORKSPACE_BROKER_E2E_READY: PASS",
                "REMOTE_WORKSPACE_BROKER_LIVE=PASS",
                "REMOTE_WORKSPACE_BROKER_CREATE_OR_REUSE=PASS",
                "REMOTE_WORKSPACE_BROKER_DETAIL=PASS",
                "REMOTE_WORKSPACE_BROKER_LIST=PASS",
                "REMOTE_WORKSPACE_BROKER_LOCAL_SESSION=PASS",
                "session_id=rws_broker_1",
                "remote_account_id=account-live-1",
                "runtime_status=active",
                "viewer_available=true",
                "viewer_reason_code=null",
                "viewer_expires_at=not-a-date",
                "session_listed=true",
                "local_session_count=1",
            ]
        ),
    )

    report = build_remote_workspace_joint_readiness_report(tmp_path, REPORT_DATE)

    assert report.ready is False
    assert "REMOTE_WORKSPACE_BROKER_EVIDENCE=FAIL" in report.lines
    assert "REMOTE_WORKSPACE_JOINT_E2E_READY: NOT VERIFIED" in report.lines


def test_joint_readiness_report_rejects_adapter_pass_without_viewer_origin_evidence(tmp_path: Path) -> None:
    _write_pass_reports(tmp_path)
    _write(
        tmp_path
        / f"project-mileage-v3-app/doc/tasks-browser-test-v1/runs/{REPORT_DATE}-remote-workspace-adapter-live/REPORT.md",
        "\n".join(
            [
                "REMOTE_WORKSPACE_ADAPTER_E2E_READY: PASS",
                "REMOTE_WORKSPACE_ADAPTER_CREATE_OR_REUSE=PASS",
                "REMOTE_WORKSPACE_ADAPTER_DETAIL=PASS",
                "REMOTE_WORKSPACE_ADAPTER_LIST=PASS",
                "REMOTE_WORKSPACE_ADAPTER_VIEWER=PASS",
                "目标订单号：AO-LIVE-1",
                "目标 remoteAccountId：account-live-1",
                "创建/复用 session id：rws_adapter_1",
                "详情 session id：rws_adapter_1",
                "列表 session 数量：1",
                "viewer.available：true",
                "viewer.reasonCode：null",
                "expiresAt：2099-06-08T00:00:00.000Z",
            ]
        ),
    )

    report = build_remote_workspace_joint_readiness_report(tmp_path, REPORT_DATE)

    assert report.ready is False
    assert "REMOTE_WORKSPACE_ADAPTER_EVIDENCE=FAIL" in report.lines
    assert "REMOTE_WORKSPACE_JOINT_E2E_READY: NOT VERIFIED" in report.lines


def test_joint_readiness_report_rejects_browser_pass_without_viewer_origin_evidence(tmp_path: Path) -> None:
    _write_pass_reports(tmp_path)
    _write(
        tmp_path
        / f"project-mileage-v3-app/doc/tasks-browser-test-v1/runs/{REPORT_DATE}-remote-workspace-browser-live/REPORT.md",
        "\n".join(
            [
                "REMOTE_WORKSPACE_BROWSER_E2E_READY: PASS",
                "目标订单号：AO-LIVE-1",
                "目标 remoteAccountId：account-live-1",
                "Payload 可启动订单数量：1",
                "Payload broker session id：rws_browser_1",
                "App VNC pathname：/app/remote-workspace/rws_browser_1/vnc",
                "viewer.available：true",
                "viewer.reasonCode：null",
                "noVNC canvas 已绘制像素",
                "noVNC canvas 点击与低敏键盘输入后仍有像素",
                "交互后页面正文和地址栏无敏感连接信息",
            ]
        ),
    )

    report = build_remote_workspace_joint_readiness_report(tmp_path, REPORT_DATE)

    assert report.ready is False
    assert "REMOTE_WORKSPACE_BROWSER_EVIDENCE=FAIL" in report.lines
    assert "REMOTE_WORKSPACE_JOINT_E2E_READY: NOT VERIFIED" in report.lines


def test_joint_readiness_report_rejects_browser_pass_missing_app_flow_evidence(tmp_path: Path) -> None:
    _write_pass_reports(tmp_path)
    _write(
        tmp_path
        / f"project-mileage-v3-app/doc/tasks-browser-test-v1/runs/{REPORT_DATE}-remote-workspace-browser-live/REPORT.md",
        "\n".join(
            [
                "REMOTE_WORKSPACE_BROWSER_E2E_READY: PASS",
                "目标订单号：AO-LIVE-1",
                "目标 remoteAccountId：account-live-1",
                "Payload 可启动订单数量：1",
                "Payload broker session id：rws_browser_1",
                "App VNC pathname：/app/remote-workspace/rws_browser_1/vnc",
                "viewer.available：true",
                "viewer.reasonCode：null",
                "viewer.originAllowed=true",
                "noVNC canvas 已绘制像素",
                "noVNC canvas 点击与低敏键盘输入后仍有像素",
                "交互后页面正文和地址栏无敏感连接信息",
            ]
        ),
    )

    report = build_remote_workspace_joint_readiness_report(tmp_path, REPORT_DATE)

    assert report.ready is False
    assert "REMOTE_WORKSPACE_BROWSER_EVIDENCE=FAIL" in report.lines
    assert "REMOTE_WORKSPACE_JOINT_E2E_READY: NOT VERIFIED" in report.lines


def test_joint_readiness_report_rejects_browser_pass_missing_viewer_expiry_evidence(tmp_path: Path) -> None:
    _write_pass_reports(tmp_path)
    _write(
        tmp_path
        / f"project-mileage-v3-app/doc/tasks-browser-test-v1/runs/{REPORT_DATE}-remote-workspace-browser-live/REPORT.md",
        "\n".join(
            [
                "REMOTE_WORKSPACE_BROWSER_E2E_READY: PASS",
                "目标订单号：AO-LIVE-1",
                "目标 remoteAccountId：account-live-1",
                "Payload 可启动订单数量：1",
                "Payload broker session id：rws_browser_1",
                "App VNC pathname：/app/remote-workspace/rws_browser_1/vnc",
                "viewer.available：true",
                "viewer.reasonCode：null",
                "viewer.originAllowed=true",
                "真实 App 登录桥建立登录态",
                "页面启动卡片数量与 Payload launchable 订单数量一致",
                "页面启动卡片订单号集合与 Payload launchable 订单集合一致",
                "目标订单卡片唯一匹配",
                "VNC pathname 保持同一 Payload broker session",
                "noVNC canvas 已绘制像素",
                "noVNC canvas 点击与低敏键盘输入后仍有像素",
                "交互后页面无连接失败或已断开状态",
                "交互后页面正文和地址栏无敏感连接信息",
                "交互后 Payload broker 详情与 session 列表复核通过",
            ]
        ),
    )

    report = build_remote_workspace_joint_readiness_report(tmp_path, REPORT_DATE)

    assert report.ready is False
    assert "REMOTE_WORKSPACE_BROWSER_EVIDENCE=FAIL" in report.lines
    assert "REMOTE_WORKSPACE_JOINT_E2E_READY: NOT VERIFIED" in report.lines


def test_joint_readiness_report_rejects_browser_pass_with_unparsable_viewer_expiry_evidence(tmp_path: Path) -> None:
    _write_pass_reports(tmp_path)
    _write(
        tmp_path
        / f"project-mileage-v3-app/doc/tasks-browser-test-v1/runs/{REPORT_DATE}-remote-workspace-browser-live/REPORT.md",
        "\n".join(
            [
                "REMOTE_WORKSPACE_BROWSER_E2E_READY: PASS",
                "目标订单号：AO-LIVE-1",
                "目标 remoteAccountId：account-live-1",
                "Payload 可启动订单数量：1",
                "Payload broker session id：rws_browser_1",
                "App VNC pathname：/app/remote-workspace/rws_browser_1/vnc",
                "viewer.available：true",
                "viewer.reasonCode：null",
                "viewer.originAllowed=true",
                "expiresAt：not-a-date",
                "真实 App 登录桥建立登录态",
                "页面启动卡片数量与 Payload launchable 订单数量一致",
                "页面启动卡片订单号集合与 Payload launchable 订单集合一致",
                "目标订单卡片唯一匹配",
                "VNC pathname 保持同一 Payload broker session",
                "noVNC canvas 已绘制像素",
                "noVNC canvas 点击与低敏键盘输入后仍有像素",
                "交互后页面无连接失败或已断开状态",
                "交互后页面正文和地址栏无敏感连接信息",
                "交互后 Payload broker 详情与 session 列表复核通过",
            ]
        ),
    )

    report = build_remote_workspace_joint_readiness_report(tmp_path, REPORT_DATE)

    assert report.ready is False
    assert "REMOTE_WORKSPACE_BROWSER_EVIDENCE=FAIL" in report.lines
    assert "REMOTE_WORKSPACE_JOINT_E2E_READY: NOT VERIFIED" in report.lines


def test_joint_readiness_report_rejects_browser_pass_with_non_vnc_app_pathname(tmp_path: Path) -> None:
    _write_pass_reports(tmp_path)
    _write(
        tmp_path
        / f"project-mileage-v3-app/doc/tasks-browser-test-v1/runs/{REPORT_DATE}-remote-workspace-browser-live/REPORT.md",
        "\n".join(
            [
                "REMOTE_WORKSPACE_BROWSER_E2E_READY: PASS",
                "目标订单号：AO-LIVE-1",
                "目标 remoteAccountId：account-live-1",
                "Payload 可启动订单数量：1",
                "Payload broker session id：rws_browser_1",
                "App VNC pathname：/app/remote-workspace/rws_browser_1",
                "viewer.available：true",
                "viewer.reasonCode：null",
                "viewer.originAllowed=true",
                "真实 App 登录桥建立登录态",
                "页面启动卡片数量与 Payload launchable 订单数量一致",
                "页面启动卡片订单号集合与 Payload launchable 订单集合一致",
                "目标订单卡片唯一匹配",
                "VNC pathname 保持同一 Payload broker session",
                "noVNC canvas 已绘制像素",
                "noVNC canvas 点击与低敏键盘输入后仍有像素",
                "交互后页面无连接失败或已断开状态",
                "交互后页面正文和地址栏无敏感连接信息",
                "交互后 Payload broker 详情与 session 列表复核通过",
            ]
        ),
    )

    report = build_remote_workspace_joint_readiness_report(tmp_path, REPORT_DATE)

    assert report.ready is False
    assert "REMOTE_WORKSPACE_BROWSER_EVIDENCE=FAIL" in report.lines
    assert "REMOTE_WORKSPACE_JOINT_E2E_READY: NOT VERIFIED" in report.lines


def test_joint_readiness_report_validates_vnc_suffix_on_app_pathname_field(tmp_path: Path) -> None:
    _write_pass_reports(tmp_path)
    _write(
        tmp_path
        / f"project-mileage-v3-app/doc/tasks-browser-test-v1/runs/{REPORT_DATE}-remote-workspace-browser-live/REPORT.md",
        "\n".join(
            [
                "REMOTE_WORKSPACE_BROWSER_E2E_READY: PASS",
                "目标订单号：AO-LIVE-1",
                "目标 remoteAccountId：account-live-1",
                "Payload 可启动订单数量：1",
                "Payload broker session id：rws_browser_1",
                "App VNC pathname：/app/remote-workspace/rws_browser_1",
                "viewer.available：true",
                "viewer.reasonCode：null",
                "viewer.originAllowed=true",
                "真实 App 登录桥建立登录态",
                "页面启动卡片数量与 Payload launchable 订单数量一致",
                "页面启动卡片订单号集合与 Payload launchable 订单集合一致",
                "目标订单卡片唯一匹配",
                "VNC pathname 保持同一 Payload broker session",
                "noVNC canvas 已绘制像素",
                "noVNC canvas 点击与低敏键盘输入后仍有像素",
                "交互后页面无连接失败或已断开状态",
                "交互后页面正文和地址栏无敏感连接信息",
                "交互后 Payload broker 详情与 session 列表复核通过",
                "readiness marker: /vnc",
            ]
        ),
    )

    report = build_remote_workspace_joint_readiness_report(tmp_path, REPORT_DATE)

    assert report.ready is False
    assert "REMOTE_WORKSPACE_BROWSER_EVIDENCE=FAIL" in report.lines
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


def test_joint_readiness_report_rejects_full_runtime_viewer_urls(tmp_path: Path) -> None:
    _write_pass_reports(tmp_path)
    _write(
        tmp_path
        / f"project-mileage-v3-app/doc/tasks-browser-test-v1/runs/{REPORT_DATE}-remote-workspace-browser-live/REPORT.md",
        "\n".join(
            [
                "REMOTE_WORKSPACE_BROWSER_E2E_READY: PASS",
                "目标订单号：AO-LIVE-1",
                "目标 remoteAccountId：account-live-1",
                "Payload 可启动订单数量：1",
                "Payload broker session id：rws_browser_1",
                "App VNC pathname：/app/remote-workspace/rws_browser_1/vnc",
                "viewer.available：true",
                "viewer.reasonCode：null",
                "noVNC canvas 已绘制像素",
                "noVNC canvas 点击与低敏键盘输入后仍有像素",
                "交互后页面正文和地址栏无敏感连接信息",
                "wss://runtime.example.test/api/runtime/sessions/runtime-session-1/vnc?viewer_token=secret",
            ]
        ),
    )

    report = build_remote_workspace_joint_readiness_report(tmp_path, REPORT_DATE)

    assert report.ready is False
    assert "REMOTE_WORKSPACE_BROWSER_EVIDENCE=SENSITIVE" in report.lines
    assert "REMOTE_WORKSPACE_JOINT_E2E_READY: NOT VERIFIED" in report.lines


def test_joint_readiness_report_rejects_natural_language_viewer_token_leaks(tmp_path: Path) -> None:
    _write_pass_reports(tmp_path)
    _write(
        tmp_path
        / f"project-mileage-v3-app/doc/tasks-browser-test-v1/runs/{REPORT_DATE}-remote-workspace-browser-live/REPORT.md",
        "\n".join(
            [
                "REMOTE_WORKSPACE_BROWSER_E2E_READY: PASS",
                "目标订单号：AO-LIVE-1",
                "目标 remoteAccountId：account-live-1",
                "Payload 可启动订单数量：1",
                "Payload broker session id：rws_browser_1",
                "App VNC pathname：/app/remote-workspace/rws_browser_1/vnc",
                "viewer.available：true",
                "viewer.reasonCode：null",
                "noVNC canvas 已绘制像素",
                "noVNC canvas 点击与低敏键盘输入后仍有像素",
                "交互后页面正文和地址栏无敏感连接信息",
                "viewer token: short-lived-secret",
            ]
        ),
    )

    report = build_remote_workspace_joint_readiness_report(tmp_path, REPORT_DATE)

    assert report.ready is False
    assert "REMOTE_WORKSPACE_BROWSER_EVIDENCE=SENSITIVE" in report.lines
    assert "REMOTE_WORKSPACE_JOINT_E2E_READY: NOT VERIFIED" in report.lines


def test_joint_readiness_report_rejects_empty_required_evidence_values(tmp_path: Path) -> None:
    _write_pass_reports(tmp_path)
    _write(
        tmp_path / f"cloakbrowser-invisible-manager/test-reports/{REPORT_DATE}-runtime-live/REPORT.md",
        "\n".join(
            [
                "RUNTIME_LIVE_WORKSPACE_E2E_READY: PASS",
                "RUNTIME_LIVE_WORKSPACE_PREFLIGHT=PASS",
                "RUNTIME_LIVE_WORKSPACE_RUNTIME_SESSION=PASS",
                "RUNTIME_LIVE_WORKSPACE_VIEWER_TOKEN=PASS",
                "RUNTIME_LIVE_WORKSPACE_VNC_WEBSOCKET=PASS",
                "RUNTIME_LIVE_WORKSPACE_TERMINATE=PASS",
                "- session_id=",
                "- external_session_id=pm-live-1",
                "- profile_id=profile-live-1",
                "- viewer_expires_at=2099-06-08T00:00:00.000Z",
                "- websocket_frame_prefix=RFB",
            ]
        ),
    )

    report = build_remote_workspace_joint_readiness_report(tmp_path, REPORT_DATE)

    assert report.ready is False
    assert "RUNTIME_LIVE_WORKSPACE_EVIDENCE=FAIL" in report.lines
    assert "REMOTE_WORKSPACE_JOINT_E2E_READY: NOT VERIFIED" in report.lines


def test_joint_readiness_report_rejects_broker_pass_missing_live_marker(tmp_path: Path) -> None:
    _write_pass_reports(tmp_path)
    _write(
        tmp_path / f"project-mileage-v3-payload/test-reports/{REPORT_DATE}-remote-workspace-broker-live/REPORT.md",
        "\n".join(
            [
                "REMOTE_WORKSPACE_BROKER_E2E_READY: PASS",
                "REMOTE_WORKSPACE_BROKER_CREATE_OR_REUSE=PASS",
                "REMOTE_WORKSPACE_BROKER_DETAIL=PASS",
                "REMOTE_WORKSPACE_BROKER_LIST=PASS",
                "REMOTE_WORKSPACE_BROKER_LOCAL_SESSION=PASS",
                "session_id=rws_broker_1",
                "remote_account_id=account-live-1",
                "runtime_status=active",
                "viewer_available=true",
                "viewer_reason_code=null",
                "viewer_expires_at=2099-06-08T00:00:00.000Z",
                "session_listed=true",
                "local_session_count=1",
            ]
        ),
    )

    report = build_remote_workspace_joint_readiness_report(tmp_path, REPORT_DATE)

    assert report.ready is False
    assert "REMOTE_WORKSPACE_BROKER_EVIDENCE=FAIL" in report.lines
    assert "REMOTE_WORKSPACE_JOINT_E2E_READY: NOT VERIFIED" in report.lines


def test_joint_readiness_report_rejects_broker_pass_missing_session_listed_evidence(tmp_path: Path) -> None:
    _write_pass_reports(tmp_path)
    _write(
        tmp_path / f"project-mileage-v3-payload/test-reports/{REPORT_DATE}-remote-workspace-broker-live/REPORT.md",
        "\n".join(
            [
                "REMOTE_WORKSPACE_BROKER_E2E_READY: PASS",
                "REMOTE_WORKSPACE_BROKER_LIVE=PASS",
                "REMOTE_WORKSPACE_BROKER_CREATE_OR_REUSE=PASS",
                "REMOTE_WORKSPACE_BROKER_DETAIL=PASS",
                "REMOTE_WORKSPACE_BROKER_LIST=PASS",
                "REMOTE_WORKSPACE_BROKER_LOCAL_SESSION=PASS",
                "session_id=rws_broker_1",
                "remote_account_id=account-live-1",
                "runtime_status=active",
                "viewer_available=true",
                "viewer_reason_code=null",
                "viewer_expires_at=2099-06-08T00:00:00.000Z",
                "local_session_count=1",
            ]
        ),
    )

    report = build_remote_workspace_joint_readiness_report(tmp_path, REPORT_DATE)

    assert report.ready is False
    assert "REMOTE_WORKSPACE_BROKER_EVIDENCE=FAIL" in report.lines
    assert "REMOTE_WORKSPACE_JOINT_E2E_READY: NOT VERIFIED" in report.lines


def test_joint_readiness_report_rejects_token_and_api_key_aliases(tmp_path: Path) -> None:
    _write_pass_reports(tmp_path)
    _write(
        tmp_path / f"project-mileage-v3-payload/test-reports/{REPORT_DATE}-remote-workspace-broker-live/REPORT.md",
        "\n".join(
            [
                "REMOTE_WORKSPACE_BROKER_E2E_READY: PASS",
                "REMOTE_WORKSPACE_BROKER_LIVE=PASS",
                "REMOTE_WORKSPACE_BROKER_CREATE_OR_REUSE=PASS",
                "REMOTE_WORKSPACE_BROKER_DETAIL=PASS",
                "REMOTE_WORKSPACE_BROKER_LIST=PASS",
                "REMOTE_WORKSPACE_BROKER_LOCAL_SESSION=PASS",
                "session_id=rws_broker_1",
                "remote_account_id=account-live-1",
                "runtime_status=active",
                "viewer_available=true",
                "viewer_reason_code=null",
                "viewer_expires_at=2099-06-08T00:00:00.000Z",
                "session_listed=true",
                "local_session_count=1",
                "access.token=access-secret",
                "auth.token=auth-secret",
                "refresh.token=refresh-secret",
                "api.key=api-key-secret",
                "x.api.key=x-api-key-secret",
            ]
        ),
    )

    report = build_remote_workspace_joint_readiness_report(tmp_path, REPORT_DATE)
    text = "\n".join(report.lines)

    assert report.ready is False
    assert "REMOTE_WORKSPACE_BROKER_EVIDENCE=SENSITIVE" in report.lines
    assert "REMOTE_WORKSPACE_JOINT_E2E_READY: NOT VERIFIED" in report.lines
    assert "access-secret" not in text
    assert "api-key-secret" not in text


def test_joint_readiness_report_rejects_jwt_identity_material(tmp_path: Path) -> None:
    _write_pass_reports(tmp_path)
    _write(
        tmp_path / f"project-mileage-v3-payload/test-reports/{REPORT_DATE}-remote-workspace-broker-live/REPORT.md",
        "\n".join(
            [
                "REMOTE_WORKSPACE_BROKER_E2E_READY: PASS",
                "REMOTE_WORKSPACE_BROKER_LIVE=PASS",
                "REMOTE_WORKSPACE_BROKER_CREATE_OR_REUSE=PASS",
                "REMOTE_WORKSPACE_BROKER_DETAIL=PASS",
                "REMOTE_WORKSPACE_BROKER_LIST=PASS",
                "REMOTE_WORKSPACE_BROKER_LOCAL_SESSION=PASS",
                "session_id=rws_broker_1",
                "remote_account_id=account-live-1",
                "runtime_status=active",
                "viewer_available=true",
                "viewer_reason_code=null",
                "viewer_expires_at=2099-06-08T00:00:00.000Z",
                "session_listed=true",
                "local_session_count=1",
                "jwt:eyJhbGciOiJIUzI1NiJ9.payload.signature",
            ]
        ),
    )

    report = build_remote_workspace_joint_readiness_report(tmp_path, REPORT_DATE)
    text = "\n".join(report.lines)

    assert report.ready is False
    assert "REMOTE_WORKSPACE_BROKER_EVIDENCE=SENSITIVE" in report.lines
    assert "REMOTE_WORKSPACE_JOINT_E2E_READY: NOT VERIFIED" in report.lines
    assert "eyJhbGciOiJIUzI1NiJ9" not in text


def test_joint_readiness_report_rejects_conflicting_not_verified_marker_in_pass_report(tmp_path: Path) -> None:
    _write_pass_reports(tmp_path)
    _write(
        tmp_path
        / f"project-mileage-v3-app/doc/tasks-browser-test-v1/runs/{REPORT_DATE}-remote-workspace-browser-live/REPORT.md",
        "\n".join(
            [
                "REMOTE_WORKSPACE_BROWSER_E2E_READY: PASS",
                "REMOTE_WORKSPACE_BROWSER_E2E_READY: NOT VERIFIED",
                "目标订单号：AO-LIVE-1",
                "目标 remoteAccountId：account-live-1",
                "Payload 可启动订单数量：1",
                "Payload broker session id：rws_browser_1",
                "App VNC pathname：/app/remote-workspace/rws_browser_1/vnc",
                "viewer.available：true",
                "viewer.reasonCode：null",
                "noVNC canvas 已绘制像素",
                "noVNC canvas 点击与低敏键盘输入后仍有像素",
                "交互后页面正文和地址栏无敏感连接信息",
            ]
        ),
    )

    report = build_remote_workspace_joint_readiness_report(tmp_path, REPORT_DATE)

    assert report.ready is False
    assert "REMOTE_WORKSPACE_BROWSER_EVIDENCE=FAIL" in report.lines
    assert "REMOTE_WORKSPACE_JOINT_E2E_READY: NOT VERIFIED" in report.lines
