import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { HealthBadge } from "./HealthBadge";
import type { ProfileHealthResponse } from "../lib/api";

function health(status: ProfileHealthResponse["status"], warnings: ProfileHealthResponse["warnings"] = []): ProfileHealthResponse {
  return {
    profile_id: "profile-1",
    status,
    geoip: null,
    manual_overrides: { timezone: false, locale: false },
    runtime: { status: "stopped", vnc_ws_port: null, automation_url: null },
    warnings,
    checked_at: "2026-05-25T01:00:00Z",
  };
}

describe("HealthBadge", () => {
  it("renders an accessible good status label", () => {
    render(<HealthBadge health={health("good")} />);

    expect(screen.getByText("可继续")).toBeTruthy();
    expect(screen.getByLabelText("健康检查通过，可继续启动或使用")).toBeTruthy();
  });

  it("renders warning status with warning summary", () => {
    render(
      <HealthBadge
        health={health("warning", [
          {
            code: "manual_locale_mismatch",
            message: "手动 locale 为 en-US，当前出口建议为 ja-JP。",
            severity: "warning",
            action: "确认是否需要保留手动覆盖。",
          },
        ])}
      />,
    );

    expect(screen.getByText("需关注")).toBeTruthy();
    expect(screen.getByText("手动 locale 为 en-US，当前出口建议为 ja-JP。")).toBeTruthy();
    expect(screen.getByLabelText(/存在需关注项/)).toBeTruthy();
  });

  it("renders error status as unavailable", () => {
    render(<HealthBadge health={health("error")} />);

    expect(screen.getByText("不可用")).toBeTruthy();
    expect(screen.getByLabelText("健康检查失败，当前不可用")).toBeTruthy();
  });

  it("renders unknown when health has not loaded", () => {
    render(<HealthBadge health={undefined} />);

    expect(screen.getByText("未检测")).toBeTruthy();
    expect(screen.getByLabelText("尚未完成健康检测")).toBeTruthy();
  });
});
