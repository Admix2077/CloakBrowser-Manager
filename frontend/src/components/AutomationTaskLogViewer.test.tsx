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
    const errorLeakMarker = "task-error-token-secret";
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
          error:
            "Fill step failed " +
            `Authorization=Bearer ${errorLeakMarker} token=${errorLeakMarker} ` +
            `/data/tasks/${errorLeakMarker} from 203.0.113.45`,
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
    expect(within(page).getByText(/Fill step failed/)).toBeTruthy();

    expect(page.textContent).not.toContain("https://example.com/account");
    expect(page.textContent).not.toContain("token");
    expect(page.textContent).not.toContain(errorLeakMarker);
    expect(page.textContent).not.toContain("Authorization");
    expect(page.textContent).not.toContain("Bearer");
    expect(page.textContent).not.toContain("/data/tasks");
    expect(page.textContent).not.toContain("203.0.113.45");
    expect(page.textContent).not.toContain("super-secret");
    expect(page.textContent).not.toContain("#password");
    expect(page.textContent).not.toContain("input-secret");
    expect(page.textContent).not.toContain("document.cookie");
    expect(page.textContent).not.toContain("screenshot-secret");
    expect(page.textContent).not.toContain("result-secret");
    expect(page.textContent).not.toContain("result-value-secret");
    expect(within(page).queryByRole("button", { name: /^run task$/i })).toBeNull();
    expect(within(page).queryByRole("button", { name: /^cancel task$/i })).toBeNull();
    expect(within(page).queryByRole("button", { name: /^retry task$/i })).toBeNull();
  });

  it("folds provider and session marker task labels before rendering", async () => {
    mockListAutomationTasks.mockResolvedValueOnce({
      tasks: [
        task({
          id: "api_key-task-marker",
          profile_id: "session_id-profile-marker",
          status: "queued",
          steps: [
            {
              type: "x-api-key-step-marker",
              page_ref: "private_key-page-marker",
              wait_until: "access_token-wait-marker",
              state: "client_secret-state-marker",
            },
          ] as AutomationTask["steps"],
          result: {
            steps: [
              {
                index: 0,
                type: "refresh_token-result-marker",
                status: "session_id-result-status-marker",
              },
            ] as AutomationTask["result"]["steps"],
          },
        }),
      ],
    });

    render(<AutomationTaskLogViewer />);

    const page = await screen.findByRole("region", { name: "Automation tasks" });
    expect(within(page).getAllByText("unknown").length).toBeGreaterThan(0);
    expect(within(page).getByText("page unknown")).toBeTruthy();
    expect(within(page).getByText("wait_until unknown")).toBeTruthy();
    expect(within(page).getByText("state unknown")).toBeTruthy();
    expect(within(page).getByText("0 unknown unknown")).toBeTruthy();

    fireEvent.click(within(page).getByRole("button", { name: "View task details for unknown" }));
    const drawer = await screen.findByRole("dialog", { name: "Automation task details" });
    expect(within(drawer).getAllByText("unknown").length).toBeGreaterThan(0);
    expect(within(drawer).getByText("page unknown")).toBeTruthy();
    expect(within(drawer).getByText("wait_until unknown")).toBeTruthy();
    expect(within(drawer).getByText("state unknown")).toBeTruthy();
    expect(within(drawer).getByText("0 unknown unknown")).toBeTruthy();

    const renderedText = `${page.textContent ?? ""} ${drawer.textContent ?? ""}`;
    expect(renderedText).not.toContain("api_key");
    expect(renderedText).not.toContain("x-api-key");
    expect(renderedText).not.toContain("access_token");
    expect(renderedText).not.toContain("refresh_token");
    expect(renderedText).not.toContain("session_id");
    expect(renderedText).not.toContain("client_secret");
    expect(renderedText).not.toContain("private_key");
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

  it("does not render raw task load failure details", async () => {
    const leakMarker = "automation-load-token-secret";
    mockListAutomationTasks.mockRejectedValueOnce(
      new Error(
        `load failed token=${leakMarker} Authorization=Bearer ${leakMarker} /data/tasks/${leakMarker}`,
      ),
    );

    render(<AutomationTaskLogViewer />);

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain("Unable to load automation tasks");
    expect(alert.textContent).not.toContain(leakMarker);
    expect(alert.textContent).not.toContain("Authorization");
    expect(alert.textContent).not.toContain("Bearer");
    expect(alert.textContent).not.toContain("token=");
    expect(alert.textContent).not.toContain("/data/tasks");
  });

  it("filters the local read-only task list by status group", async () => {
    mockListAutomationTasks.mockResolvedValueOnce({
      tasks: [
        task({ id: "task-queued-123456", status: "queued" }),
        task({ id: "task-running-123456", status: "running" }),
        task({ id: "task-cancel-requested-123456", status: "cancel_requested" }),
        task({ id: "task-failed-123456", status: "failed" }),
        task({ id: "task-succeeded-123456", status: "succeeded" }),
        task({ id: "task-done-123456", status: "cancelled" }),
      ],
    });

    render(<AutomationTaskLogViewer />);

    const page = await screen.findByRole("region", { name: "Automation tasks" });
    expect(within(page).getByText("task-que...")).toBeTruthy();
    expect(within(page).getByText("task-run...")).toBeTruthy();
    expect(within(page).getByText("task-can...")).toBeTruthy();
    expect(within(page).getByText("task-fai...")).toBeTruthy();
    expect(within(page).getByText("task-suc...")).toBeTruthy();
    expect(within(page).getByText("task-don...")).toBeTruthy();

    fireEvent.click(within(page).getByRole("button", { name: "Show running automation tasks" }));
    expect(within(page).getByText("task-run...")).toBeTruthy();
    expect(within(page).getByText("task-can...")).toBeTruthy();
    expect(within(page).queryByText("task-que...")).toBeNull();
    expect(within(page).queryByText("task-fai...")).toBeNull();
    expect(within(page).queryByText("task-suc...")).toBeNull();

    fireEvent.click(within(page).getByRole("button", { name: "Show failed automation tasks" }));
    expect(within(page).getByText("task-fai...")).toBeTruthy();
    expect(within(page).queryByText("task-run...")).toBeNull();
    expect(within(page).queryByText("task-can...")).toBeNull();

    fireEvent.click(within(page).getByRole("button", { name: "Show finished automation tasks" }));
    expect(within(page).getByText("task-suc...")).toBeTruthy();
    expect(within(page).getByText("task-don...")).toBeTruthy();
    expect(within(page).queryByText("task-fai...")).toBeNull();

    fireEvent.click(within(page).getByRole("button", { name: "Show all automation tasks" }));
    expect(within(page).getByText("task-que...")).toBeTruthy();
    expect(within(page).getByText("task-run...")).toBeTruthy();
    expect(within(page).getByText("task-fai...")).toBeTruthy();
    expect(mockListAutomationTasks).toHaveBeenCalledTimes(1);
  });

  it("folds non-public task statuses to unknown before rendering", async () => {
    const leakMarker = "task-status-token-secret";
    mockListAutomationTasks.mockResolvedValueOnce({
      tasks: [
        task({
          id: "task-status-123456",
          profile_id: "profile-status-123456",
          status: `failed Authorization=Bearer ${leakMarker} token=${leakMarker}`,
        }),
      ],
    });

    render(<AutomationTaskLogViewer />);

    const page = await screen.findByRole("region", { name: "Automation tasks" });
    expect(within(page).getByText("unknown")).toBeTruthy();
    expect(page.textContent).not.toContain(leakMarker);
    expect(page.textContent).not.toContain("Authorization");
    expect(page.textContent).not.toContain("Bearer");
    expect(page.textContent).not.toContain("token=");

    fireEvent.click(within(page).getByRole("button", { name: "View task details for task-status-123456" }));
    const drawer = await screen.findByRole("dialog", { name: "Automation task details" });
    expect(within(drawer).getByText("unknown")).toBeTruthy();
    expect(drawer.textContent).not.toContain(leakMarker);
    expect(drawer.textContent).not.toContain("Authorization");
    expect(drawer.textContent).not.toContain("Bearer");
    expect(drawer.textContent).not.toContain("token=");

    fireEvent.click(within(page).getByRole("button", { name: "Show failed automation tasks" }));
    expect(await screen.findByRole("status", { name: "No automation tasks match the selected filter" })).toBeTruthy();
  });

  it("folds non-public task and profile ids to unknown before rendering or searching", async () => {
    const leakMarker = "task-id-token-secret";
    mockListAutomationTasks.mockResolvedValueOnce({
      tasks: [
        task({
          id: `token=${leakMarker} Authorization=Bearer ${leakMarker}`,
          profile_id: `/data/profiles/${leakMarker}/203.0.113.88`,
          status: "queued",
        }),
      ],
    });

    render(<AutomationTaskLogViewer />);

    const page = await screen.findByRole("region", { name: "Automation tasks" });
    expect(within(page).getAllByText("unknown").length).toBeGreaterThanOrEqual(2);
    expect(page.textContent).not.toContain(leakMarker);
    expect(page.textContent).not.toContain("Authorization");
    expect(page.textContent).not.toContain("Bearer");
    expect(page.textContent).not.toContain("token=");
    expect(page.textContent).not.toContain("/data/profiles");
    expect(page.textContent).not.toContain("203.0.113.88");

    const detailsButton = within(page).getByRole("button", { name: "View task details for unknown" });
    expect(detailsButton.getAttribute("aria-label")).not.toContain(leakMarker);
    fireEvent.click(detailsButton);

    const drawer = await screen.findByRole("dialog", { name: "Automation task details" });
    expect(within(drawer).getAllByText("unknown").length).toBeGreaterThanOrEqual(2);
    expect(drawer.textContent).not.toContain(leakMarker);
    expect(drawer.textContent).not.toContain("Authorization");
    expect(drawer.textContent).not.toContain("Bearer");
    expect(drawer.textContent).not.toContain("token=");
    expect(drawer.textContent).not.toContain("/data/profiles");
    expect(drawer.textContent).not.toContain("203.0.113.88");

    const search = within(page).getByRole("searchbox", { name: "Filter automation tasks by task or profile id" });
    fireEvent.change(search, { target: { value: leakMarker } });
    expect(await screen.findByRole("status", { name: "No automation tasks match the selected filter" })).toBeTruthy();
  });

  it("folds non-public step and result summary labels to unknown before rendering", async () => {
    const leakMarker = "task-step-token-secret";
    mockListAutomationTasks.mockResolvedValueOnce({
      tasks: [
        task({
          id: "task-step-summary-123456",
          profile_id: "profile-step-summary-123456",
          status: "failed",
          steps: [
            {
              type: `open_url Authorization=Bearer ${leakMarker}`,
              page_ref: `https://example.test/private?token=${leakMarker}`,
              wait_until: `load token=${leakMarker}`,
              state: `visible Authorization=Bearer ${leakMarker}`,
              timeout_ms: 30000,
            },
          ] as AutomationTask["steps"],
          result: {
            steps: [
              {
                index: 0,
                type: `evaluate token=${leakMarker}`,
                status: `failed Authorization=Bearer ${leakMarker}`,
              },
            ] as AutomationTask["result"]["steps"],
          },
        }),
      ],
    });

    render(<AutomationTaskLogViewer />);

    const page = await screen.findByRole("region", { name: "Automation tasks" });
    expect(within(page).getByText("unknown")).toBeTruthy();
    expect(within(page).getByText("page unknown")).toBeTruthy();
    expect(within(page).getByText("wait_until unknown")).toBeTruthy();
    expect(within(page).getByText("state unknown")).toBeTruthy();
    expect(within(page).getByText("0 unknown unknown")).toBeTruthy();
    expect(page.textContent).not.toContain(leakMarker);
    expect(page.textContent).not.toContain("Authorization");
    expect(page.textContent).not.toContain("Bearer");
    expect(page.textContent).not.toContain("token");
    expect(page.textContent).not.toContain("https://example.test");

    fireEvent.click(within(page).getByRole("button", { name: "View task details for task-step-summary-123456" }));
    const drawer = await screen.findByRole("dialog", { name: "Automation task details" });
    expect(within(drawer).getByText("page unknown")).toBeTruthy();
    expect(within(drawer).getByText("wait_until unknown")).toBeTruthy();
    expect(within(drawer).getByText("state unknown")).toBeTruthy();
    expect(within(drawer).getByText("0 unknown unknown")).toBeTruthy();
    expect(drawer.textContent).not.toContain(leakMarker);
    expect(drawer.textContent).not.toContain("Authorization");
    expect(drawer.textContent).not.toContain("Bearer");
    expect(drawer.textContent).not.toContain("token");
    expect(drawer.textContent).not.toContain("https://example.test");
  });

  it("folds malformed task step collections before rendering automation evidence", async () => {
    const leakMarker = "task-collection-token-secret";
    mockListAutomationTasks.mockResolvedValueOnce({
      tasks: [
        {
          ...task({
            id: "task-malformed-steps",
            profile_id: "profile-malformed-steps",
            status: "failed",
            error: `failed token=${leakMarker} /data/tasks/${leakMarker} 203.0.113.87`,
          }),
          steps: `open_url token=${leakMarker} /data/tasks/${leakMarker}`,
          result: {
            steps: {
              index: 0,
              type: `evaluate token=${leakMarker}`,
              status: `failed token=${leakMarker}`,
            },
          },
        } as unknown as AutomationTask,
      ],
    });

    render(<AutomationTaskLogViewer />);

    const page = await screen.findByRole("region", { name: "Automation tasks" });
    expect(within(page).getByText("task-mal...")).toBeTruthy();
    expect(within(page).getAllByText("-").length).toBeGreaterThanOrEqual(2);
    expect(within(page).getByText("failed [redacted] [redacted-path] [redacted-ip]")).toBeTruthy();

    fireEvent.click(within(page).getByRole("button", { name: "View task details for task-malformed-steps" }));
    const drawer = await screen.findByRole("dialog", { name: "Automation task details" });
    expect(within(drawer).getAllByText("-").length).toBeGreaterThanOrEqual(2);
    expect(within(drawer).getByText("failed [redacted] [redacted-path] [redacted-ip]")).toBeTruthy();

    const renderedText = `${page.textContent ?? ""} ${drawer.textContent ?? ""}`;
    expect(renderedText).not.toContain(leakMarker);
    expect(renderedText).not.toContain("token=");
    expect(renderedText).not.toContain("/data/tasks");
    expect(renderedText).not.toContain("203.0.113.87");
    expect(renderedText).not.toContain("open_url");
    expect(renderedText).not.toContain("evaluate");
  });

  it("filters the local read-only task list by task or profile id", async () => {
    mockListAutomationTasks.mockResolvedValueOnce({
      tasks: [
        task({ id: "task-alpha-123456", profile_id: "profile-alpha-123456", status: "queued" }),
        task({ id: "task-beta-123456", profile_id: "profile-beta-123456", status: "failed" }),
        task({ id: "task-gamma-123456", profile_id: "profile-shared-123456", status: "succeeded" }),
      ],
    });

    render(<AutomationTaskLogViewer />);

    const page = await screen.findByRole("region", { name: "Automation tasks" });
    const search = within(page).getByRole("searchbox", { name: "Filter automation tasks by task or profile id" });
    expect(within(page).getByText("task-alp...")).toBeTruthy();
    expect(within(page).getByText("task-bet...")).toBeTruthy();
    expect(within(page).getByText("task-gam...")).toBeTruthy();

    fireEvent.change(search, { target: { value: "beta" } });
    expect(within(page).getByText("task-bet...")).toBeTruthy();
    expect(within(page).queryByText("task-alp...")).toBeNull();
    expect(within(page).queryByText("task-gam...")).toBeNull();
    expect(mockListAutomationTasks).toHaveBeenCalledTimes(1);

    fireEvent.change(search, { target: { value: "profile-shared" } });
    expect(within(page).getByText("task-gam...")).toBeTruthy();
    expect(within(page).queryByText("task-bet...")).toBeNull();

    fireEvent.click(within(page).getByRole("button", { name: "Show failed automation tasks" }));
    expect(await screen.findByRole("status", { name: "No automation tasks match the selected filter" })).toBeTruthy();

    fireEvent.change(search, { target: { value: "" } });
    expect(within(page).getByText("task-bet...")).toBeTruthy();
    expect(within(page).queryByText("task-gam...")).toBeNull();
  });

  it("opens a read-only task detail drawer without rendering sensitive payloads", async () => {
    const errorLeakMarker = "drawer-task-error-secret";
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
          error:
            "Open URL step failed " +
            `Authorization=Bearer ${errorLeakMarker} token=${errorLeakMarker} ` +
            `/tmp/tasks/${errorLeakMarker} from [2001:db8::46]:443`,
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
    expect(within(drawer).getByText(/Open URL step failed/)).toBeTruthy();
    expect(within(drawer).queryByText("+1 more steps")).toBeNull();
    expect(within(drawer).queryByText("+1 more results")).toBeNull();

    expect(drawer.textContent).not.toContain("https://example.com");
    expect(drawer.textContent).not.toContain("token");
    expect(drawer.textContent).not.toContain(errorLeakMarker);
    expect(drawer.textContent).not.toContain("Authorization");
    expect(drawer.textContent).not.toContain("Bearer");
    expect(drawer.textContent).not.toContain("/tmp/tasks");
    expect(drawer.textContent).not.toContain("2001:db8::46");
    expect(drawer.textContent).not.toContain("super-secret");
    expect(drawer.textContent).not.toContain("result-secret");
    expect(drawer.textContent).not.toContain("#danger");
    expect(drawer.textContent).not.toContain("typed-secret");
    expect(drawer.textContent).not.toContain("do-not-render");
    expect(drawer.textContent).not.toContain("result-typed-secret");
    expect(drawer.textContent).not.toContain("result-do-not-render");
    expect(within(drawer).queryByRole("button", { name: /^run task$/i })).toBeNull();
    expect(within(drawer).queryByRole("button", { name: /^cancel task$/i })).toBeNull();
    expect(within(drawer).queryByRole("button", { name: /^retry task$/i })).toBeNull();

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
