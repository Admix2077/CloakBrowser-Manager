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
    expect(screen.getByLabelText("健康检查通过，可尝试启动或使用")).toBeTruthy();
    expect(screen.getByText("可继续").closest("[data-badge-type]")?.getAttribute("data-badge-type")).toBe("health");
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

  it("redacts sensitive warning summary text", () => {
    const leakMarker = "health-warning-token-super-secret";
    render(
      <HealthBadge
        health={health("warning", [
          {
            code: "proxy_check_failed",
            message: `proxy warning Authorization=Bearer ${leakMarker} token=${leakMarker} /data/profiles/profile-1`,
            severity: "warning",
            action: "检查代理。",
          },
        ])}
      />,
    );

    const rendered = document.body.textContent ?? "";
    expect(rendered).toContain("proxy warning");
    expect(rendered).not.toContain(leakMarker);
    expect(rendered).not.toContain("Authorization");
    expect(rendered).not.toContain("Bearer");
    expect(rendered).not.toContain("token=");
    expect(rendered).not.toContain("/data/profiles/profile-1");
  });

  it("folds marker-bearing warning summaries before rendering evidence", () => {
    render(
      <HealthBadge
        health={health("warning", [
          {
            code: "proxy_check_failed",
            message: "api_key-health-warning-marker client_secret-health-warning-marker private_key-health-warning-marker",
            severity: "warning",
            action: "检查代理。",
          },
        ])}
      />,
    );

    expect(screen.getAllByText("unknown").length).toBeGreaterThan(0);

    const renderedEvidence = [
      document.body.textContent,
      ...Array.from(document.querySelectorAll("[title]")).map((element) => element.getAttribute("title") ?? ""),
    ].join(" ");

    for (const leaked of [
      "api_key",
      "client_secret",
      "private_key",
    ]) {
      expect(renderedEvidence).not.toContain(leaked);
    }
  });

  it("folds underscore runtime service token warning markers before rendering evidence", () => {
    render(
      <HealthBadge
        health={health("warning", [
          {
            code: "proxy_check_failed",
            message: "runtime_service_token_health_warning_marker service_token_health_warning_marker",
            severity: "warning",
            action: "检查代理。",
          },
        ])}
      />,
    );

    expect(screen.getAllByText("unknown").length).toBeGreaterThan(0);

    const renderedEvidence = [
      document.body.textContent,
      ...Array.from(document.querySelectorAll("[title]")).map((element) => element.getAttribute("title") ?? ""),
    ].join(" ");

    for (const leaked of [
      "runtime_service_token",
      "service_token",
    ]) {
      expect(renderedEvidence).not.toContain(leaked);
    }
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

  it("keeps compact mode limited to the status badge", () => {
    render(
      <HealthBadge
        compact
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
    expect(screen.queryByText("手动 locale 为 en-US，当前出口建议为 ja-JP。")).toBeNull();
  });
});
