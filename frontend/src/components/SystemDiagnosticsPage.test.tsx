import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SystemDiagnosticsPage } from "./SystemDiagnosticsPage";
import { api, type SystemDiagnostics } from "../lib/api";

vi.mock("../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/api")>();
  return {
    ...actual,
    api: {
      getDiagnostics: vi.fn(),
    },
  };
});

const mockGetDiagnostics = api.getDiagnostics as ReturnType<typeof vi.fn>;

function diagnostics(overrides: Partial<SystemDiagnostics> = {}): SystemDiagnostics {
  return {
    status: "ok",
    binary_version: "invisible-playwright",
    storage: {
      data_dir_exists: true,
      db_exists: true,
    },
    counts: {
      running: 2,
      launching: 1,
      profiles_total: 12,
      proxy_count: 4,
      queued_tasks: 5,
      failed_tasks: 3,
      automation_task_counts: {
        queued: 5,
        running: 1,
        failed: 3,
      },
    },
    runtime: {
      active_displays: [100, 101],
      active_vnc_ws_ports: [6100, 6101],
      max_running_profiles: 6,
      managed_user_agent_version: "149.0",
      invisible_playwright_version: "0.1.8",
      firefox_binary_version: "150.0.1",
      firefox_binary_build_id: "20260521160037",
    },
    automation_worker: {
      enabled: true,
      lease_seconds: 60,
      idle_sleep_seconds: 1,
      shutdown_timeout_seconds: 5,
    },
    ...overrides,
  };
}

beforeEach(() => {
  mockGetDiagnostics.mockReset();
});

describe("SystemDiagnosticsPage", () => {
  it("renders a read-only low-sensitive diagnostics snapshot", async () => {
    mockGetDiagnostics.mockResolvedValueOnce(diagnostics());

    render(<SystemDiagnosticsPage />);

    const page = await screen.findByRole("region", { name: "System diagnostics" });
    expect(within(page).getByRole("heading", { name: "System diagnostics" })).toBeTruthy();
    expect(within(page).getByRole("group", { name: "Status: ok" })).toBeTruthy();
    expect(within(page).getByRole("group", { name: "Binary: invisible-playwright" })).toBeTruthy();
    expect(within(page).getByRole("group", { name: "Profiles: 12" })).toBeTruthy();
    expect(within(page).getByRole("group", { name: "Running: 2" })).toBeTruthy();
    expect(within(page).getByRole("group", { name: "Launching: 1" })).toBeTruthy();
    expect(within(page).getByRole("group", { name: "Failed tasks: 3" })).toBeTruthy();
    expect(within(page).getByRole("group", { name: "Proxies: 4" })).toBeTruthy();
    expect(within(page).getByRole("group", { name: "Queued tasks: 5" })).toBeTruthy();
    expect(within(page).getByRole("group", { name: "Active displays: :100, :101" })).toBeTruthy();
    expect(within(page).getByRole("group", { name: "Active VNC ports: 6100, 6101" })).toBeTruthy();
    expect(within(page).getByRole("group", { name: "Max running: 6" })).toBeTruthy();
    expect(within(page).getByRole("group", { name: "Managed UA: Firefox 149.0" })).toBeTruthy();
    expect(within(page).getByRole("group", { name: "Engine package: invisible_playwright 0.1.8" })).toBeTruthy();
    expect(within(page).getByRole("group", { name: "Firefox binary: 150.0.1" })).toBeTruthy();
    expect(within(page).getByRole("group", { name: "Firefox BuildID: 20260521160037" })).toBeTruthy();
    expect(within(page).getByRole("group", { name: "State: enabled" })).toBeTruthy();
    expect(within(page).getByRole("group", { name: "Lease: 60s" })).toBeTruthy();
    expect(within(page).getByRole("group", { name: "Idle sleep: 1s" })).toBeTruthy();
    expect(within(page).getByRole("group", { name: "Shutdown wait: 5s" })).toBeTruthy();

    expect(page.textContent).not.toContain("/data");
    expect(page.textContent).not.toContain("secret");
    expect(page.textContent).not.toContain("token");
    expect(page.textContent).not.toContain("proxy.example");
    expect(page.textContent).not.toContain("http://");
    expect(page.textContent).not.toContain("profile-");
    expect(page.textContent).not.toContain("selector");
  });

  it("refreshes diagnostics on demand", async () => {
    mockGetDiagnostics
      .mockResolvedValueOnce(diagnostics({ counts: { ...diagnostics().counts, running: 1 } }))
      .mockResolvedValueOnce(diagnostics({ counts: { ...diagnostics().counts, running: 3 } }));

    render(<SystemDiagnosticsPage />);

    const page = await screen.findByRole("region", { name: "System diagnostics" });
    expect(within(page).getByRole("group", { name: "Running: 1" })).toBeTruthy();
    fireEvent.click(within(page).getByRole("button", { name: "Refresh diagnostics" }));

    await waitFor(() => expect(mockGetDiagnostics).toHaveBeenCalledTimes(2));
    expect(within(page).getByRole("group", { name: "Running: 3" })).toBeTruthy();
  });

  it("uses a fixed error message without rendering backend details", async () => {
    mockGetDiagnostics.mockRejectedValueOnce(new Error("secret token at /data/profiles/profile-1"));

    render(<SystemDiagnosticsPage />);

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toBe("Unable to load diagnostics");
    expect(document.body.textContent).not.toContain("secret token");
    expect(document.body.textContent).not.toContain("/data/profiles");
    expect(document.body.textContent).not.toContain("profile-1");
  });
});
