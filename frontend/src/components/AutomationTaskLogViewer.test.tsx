import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { AutomationTaskLogViewer } from "./AutomationTaskLogViewer";
import { api, type AutomationTask } from "../lib/api";

vi.mock("../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/api")>();
  return {
    ...actual,
    api: {
      listAutomationTasks: vi.fn(),
    },
  };
});

const mockListAutomationTasks = api.listAutomationTasks as ReturnType<typeof vi.fn>;

function task(overrides: Partial<AutomationTask>): AutomationTask {
  return {
    id: "task-1234567890",
    profile_id: "profile-1234567890",
    status: "queued",
    steps: [{ type: "wait", ms: 1000 }],
    result: null,
    error: null,
    created_at: "2026-05-27T00:00:00Z",
    started_at: null,
    finished_at: null,
    ...overrides,
  };
}

beforeEach(() => {
  mockListAutomationTasks.mockReset();
});

describe("AutomationTaskLogViewer", () => {
  it("renders a read-only task log with redacted step and result summaries", async () => {
    mockListAutomationTasks.mockResolvedValueOnce({
      tasks: [
        task({
          id: "task-open-url-123456",
          profile_id: "profile-alpha-123456",
          status: "failed",
          steps: [
            {
              type: "open_url",
              page_ref: "0",
              wait_until: "load",
              timeout_ms: 30000,
              url: "https://example.com/account?token=super-secret#private",
              token: "super-secret",
            },
            {
              type: "fill",
              page_ref: "0",
              timeout_ms: 30000,
              selector: "#password",
              value: "input-secret",
            },
            {
              type: "evaluate",
              page_ref: "0",
              expression: "document.cookie",
            },
            {
              type: "screenshot",
              page_ref: "0",
              full_page: false,
              base64: "screenshot-secret",
            },
          ] as AutomationTask["steps"],
          result: {
            steps: [
              {
                index: 0,
                type: "open_url",
                status: "succeeded",
                raw_url: "https://example.com/account?token=result-secret",
              },
              {
                index: 1,
                type: "fill",
                status: "failed",
                value: "result-value-secret",
              },
            ] as AutomationTask["result"]["steps"],
          },
          error: "Fill step failed",
        }),
      ],
    });

    render(<AutomationTaskLogViewer />);

    const page = await screen.findByRole("region", { name: "Automation tasks" });
    expect(within(page).getByRole("heading", { name: "Automation tasks" })).toBeTruthy();
    expect(within(page).getByRole("table", { name: "Automation task log" })).toBeTruthy();
    expect(within(page).getByText("task-ope...")).toBeTruthy();
    expect(within(page).getByText("profile-...")).toBeTruthy();
    expect(within(page).getByText("failed")).toBeTruthy();
    expect(within(page).getByText("open_url")).toBeTruthy();
    expect(within(page).getByText("wait_until load")).toBeTruthy();
    expect(within(page).getAllByText("timeout 30000ms").length).toBeGreaterThan(0);
    expect(within(page).getByText("0 open_url succeeded")).toBeTruthy();
    expect(within(page).getByText("1 fill failed")).toBeTruthy();

    expect(page.textContent).not.toContain("https://example.com/account");
    expect(page.textContent).not.toContain("token");
    expect(page.textContent).not.toContain("super-secret");
    expect(page.textContent).not.toContain("#password");
    expect(page.textContent).not.toContain("input-secret");
    expect(page.textContent).not.toContain("document.cookie");
    expect(page.textContent).not.toContain("screenshot-secret");
    expect(page.textContent).not.toContain("result-secret");
    expect(page.textContent).not.toContain("result-value-secret");
    expect(within(page).queryByRole("button", { name: /run/i })).toBeNull();
    expect(within(page).queryByRole("button", { name: /cancel/i })).toBeNull();
    expect(within(page).queryByRole("button", { name: /retry/i })).toBeNull();
  });

  it("refreshes the read-only task list on demand", async () => {
    mockListAutomationTasks
      .mockResolvedValueOnce({ tasks: [task({ id: "task-first-123456" })] })
      .mockResolvedValueOnce({ tasks: [task({ id: "task-second-123456", status: "succeeded" })] });

    render(<AutomationTaskLogViewer />);

    expect(await screen.findByText("task-fir...")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Refresh automation tasks" }));

    await waitFor(() => expect(mockListAutomationTasks).toHaveBeenCalledTimes(2));
    expect(await screen.findByText("task-sec...")).toBeTruthy();
    expect(mockListAutomationTasks).toHaveBeenLastCalledWith({ limit: 50 });
  });

  it("opens a read-only task detail drawer without rendering sensitive payloads", async () => {
    mockListAutomationTasks.mockResolvedValueOnce({
      tasks: [
        task({
          id: "task-detail-123456",
          profile_id: "profile-detail-123456",
          status: "cancelled",
          steps: [
            { type: "wait", ms: 1000 },
            {
              type: "open_url",
              page_ref: "0",
              wait_until: "domcontentloaded",
              timeout_ms: 5000,
              url: "https://example.com/app?token=super-secret#frag",
            },
            {
              type: "click",
              page_ref: "0",
              timeout_ms: 30000,
              selector: "#danger",
            },
            {
              type: "keyboard_type",
              page_ref: "0",
              delay_ms: 5,
              text: "typed-secret",
            },
            {
              type: "scroll",
              page_ref: "0",
              delta_x: 0,
              delta_y: 600,
              note: "do-not-render",
            },
          ] as AutomationTask["steps"],
          result: {
            steps: [
              { index: 0, type: "wait", status: "succeeded" },
              {
                index: 1,
                type: "open_url",
                status: "succeeded",
                raw_url: "https://example.com/app?token=result-secret",
              },
              {
                index: 2,
                type: "click",
                status: "cancelled",
                selector: "#danger",
              },
              { index: 3, type: "keyboard_type", status: "succeeded", text: "result-typed-secret" },
              { index: 4, type: "scroll", status: "succeeded", note: "result-do-not-render" },
            ] as AutomationTask["result"]["steps"],
            raw_url: "https://example.com/result?token=result-secret",
          },
          error: "Open URL step failed",
          started_at: "2026-05-27T00:00:01Z",
          finished_at: "2026-05-27T00:00:02Z",
        }),
      ],
    });

    render(<AutomationTaskLogViewer />);

    const page = await screen.findByRole("region", { name: "Automation tasks" });
    expect(within(page).getByText("+1 more steps")).toBeTruthy();
    expect(within(page).getByText("+1 more results")).toBeTruthy();

    fireEvent.click(within(page).getByRole("button", { name: "View task details for task-detail-123456" }));

    const drawer = await screen.findByRole("dialog", { name: "Automation task details" });
    expect(within(drawer).getAllByText("task-det...").length).toBeGreaterThan(0);
    expect(within(drawer).getByText("profile-...")).toBeTruthy();
    expect(within(drawer).getByText("cancelled")).toBeTruthy();
    expect(within(drawer).getByText("wait")).toBeTruthy();
    expect(within(drawer).getByText("open_url")).toBeTruthy();
    expect(within(drawer).getByText("click")).toBeTruthy();
    expect(within(drawer).getByText("keyboard_type")).toBeTruthy();
    expect(within(drawer).getByText("scroll")).toBeTruthy();
    expect(within(drawer).getByText("2 click cancelled")).toBeTruthy();
    expect(within(drawer).getByText("4 scroll succeeded")).toBeTruthy();
    expect(within(drawer).getByText("Open URL step failed")).toBeTruthy();
    expect(within(drawer).queryByText("+1 more steps")).toBeNull();
    expect(within(drawer).queryByText("+1 more results")).toBeNull();

    expect(drawer.textContent).not.toContain("https://example.com");
    expect(drawer.textContent).not.toContain("token");
    expect(drawer.textContent).not.toContain("super-secret");
    expect(drawer.textContent).not.toContain("result-secret");
    expect(drawer.textContent).not.toContain("#danger");
    expect(drawer.textContent).not.toContain("typed-secret");
    expect(drawer.textContent).not.toContain("do-not-render");
    expect(drawer.textContent).not.toContain("result-typed-secret");
    expect(drawer.textContent).not.toContain("result-do-not-render");
    expect(within(drawer).queryByRole("button", { name: /run/i })).toBeNull();
    expect(within(drawer).queryByRole("button", { name: /cancel/i })).toBeNull();
    expect(within(drawer).queryByRole("button", { name: /retry/i })).toBeNull();

    fireEvent.click(within(drawer).getByRole("button", { name: "Close task details" }));
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Automation task details" })).toBeNull());
  });

  it("shows a low-risk empty state when no tasks exist", async () => {
    mockListAutomationTasks.mockResolvedValueOnce({ tasks: [] });

    render(<AutomationTaskLogViewer />);

    expect(await screen.findByRole("status", { name: "No automation tasks yet" })).toBeTruthy();
    expect(screen.getByText("Queued scripts will appear here after they are created through the trusted management API.")).toBeTruthy();
  });
});
