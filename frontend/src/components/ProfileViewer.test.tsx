import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { ProfileViewer } from "./ProfileViewer";

const { MockRFB, rfbInstances } = vi.hoisted(() => {
  const rfbInstances: Array<{
    constructorArgs: unknown[];
    scaleViewport: boolean;
    resizeSession: boolean;
    showDotCursor: boolean;
    listeners: Record<string, (event?: unknown) => void>;
    addEventListener: ReturnType<typeof vi.fn>;
    removeEventListener: ReturnType<typeof vi.fn>;
    disconnect: ReturnType<typeof vi.fn>;
    sendKey: ReturnType<typeof vi.fn>;
  }> = [];

  const MockRFB = vi.fn(function MockRFB(this: unknown, ...args: unknown[]) {
    const listeners: Record<string, (event?: unknown) => void> = {};
    const instance = {
      constructorArgs: args,
      scaleViewport: false,
      resizeSession: true,
      showDotCursor: false,
      listeners,
      addEventListener: vi.fn((event: string, handler: (event?: unknown) => void) => {
        listeners[event] = handler;
      }),
      removeEventListener: vi.fn((event: string) => {
        delete listeners[event];
      }),
      disconnect: vi.fn(),
      sendKey: vi.fn(),
    };

    rfbInstances.push(instance);
    return instance;
  });

  return { MockRFB, rfbInstances };
});

vi.mock("@novnc/novnc/core/rfb.js", () => ({
  default: MockRFB,
}));

vi.mock("../lib/api", () => ({
  api: {
    getClipboard: vi.fn(),
    setClipboard: vi.fn(),
  },
}));

beforeEach(() => {
  MockRFB.mockClear();
  rfbInstances.length = 0;
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: {
      readText: vi.fn(),
      writeText: vi.fn().mockResolvedValue(undefined),
    },
  });
});

describe("ProfileViewer VNC connection", () => {
  it("connects noVNC to the selected profile VNC websocket", async () => {
    render(
      <ProfileViewer
        profileId="profile-1"
        automationUrl={null}
        clipboardSync={false}
        onDisconnect={vi.fn()}
      />,
    );

    await waitFor(() => expect(MockRFB).toHaveBeenCalledTimes(1));

    const [container, wsUrl, options] = MockRFB.mock.calls[0];
    expect(container).toBeInstanceOf(HTMLElement);
    expect(wsUrl).toBe(`ws://${window.location.host}/api/profiles/profile-1/vnc`);
    expect(options).toEqual({ wsProtocols: ["binary"] });
    expect(rfbInstances[0].scaleViewport).toBe(true);
    expect(rfbInstances[0].resizeSession).toBe(false);
    expect(rfbInstances[0].showDotCursor).toBe(true);
  });

  it("notifies the operations console when noVNC disconnects", async () => {
    const onDisconnect = vi.fn();
    render(
      <ProfileViewer
        profileId="profile-1"
        automationUrl={null}
        clipboardSync={false}
        onDisconnect={onDisconnect}
      />,
    );

    await waitFor(() => expect(rfbInstances[0]?.listeners.disconnect).toBeTruthy());

    act(() => {
      rfbInstances[0].listeners.disconnect();
    });

    await waitFor(() => expect(onDisconnect).toHaveBeenCalledTimes(1));
  });

  it("redacts regular profile viewer security failures instead of rendering raw reasons", async () => {
    const onDisconnect = vi.fn();
    const rawReason =
      "unexpected server detail for /api/profiles/profile-1/vnc?internal_ticket=secret-ticket";

    render(
      <ProfileViewer
        profileId="profile-1"
        automationUrl={null}
        clipboardSync={false}
        onDisconnect={onDisconnect}
      />,
    );

    await waitFor(() => expect(rfbInstances[0]?.listeners.securityfailure).toBeTruthy());

    act(() => {
      rfbInstances[0].listeners.securityfailure({
        detail: { reason: rawReason },
      });
    });

    expect(await screen.findByText("Connection failed")).toBeTruthy();
    expect(
      screen.getByText(
        "Viewer access expired or unavailable. Request a fresh viewer session from Project Mileage and try again.",
      ),
    ).toBeTruthy();
    expect(onDisconnect).not.toHaveBeenCalled();
    expect(document.body.textContent).not.toContain("internal_ticket=secret-ticket");
    expect(document.body.textContent).not.toContain(rawReason);
  });

  it("redacts regular profile viewer initialization errors instead of rendering token-bearing messages", async () => {
    const onDisconnect = vi.fn();
    const rawMessage =
      `failed to initialize /api/profiles/profile-1/vnc?internal_ticket=secret-ticket`;

    MockRFB.mockImplementationOnce(function MockRFBProfileInitFailure() {
      throw new Error(rawMessage);
    });

    render(
      <ProfileViewer
        profileId="profile-1"
        automationUrl={null}
        clipboardSync={false}
        onDisconnect={onDisconnect}
      />,
    );

    expect(await screen.findByText("Connection failed")).toBeTruthy();
    expect(
      screen.getByText(
        "Viewer access expired or unavailable. Request a fresh viewer session from Project Mileage and try again.",
      ),
    ).toBeTruthy();
    expect(onDisconnect).not.toHaveBeenCalled();
    expect(document.body.textContent).not.toContain("internal_ticket=secret-ticket");
    expect(document.body.textContent).not.toContain(rawMessage);
  });
});

describe("ProfileViewer Automation API toolbar action", () => {
  it("renders a responsive viewer environment strip with runtime and integration status", async () => {
    render(
      <ProfileViewer
        profileId="profile-1234567890"
        automationUrl="/api/profiles/profile-1234567890/automation"
        clipboardSync={true}
        onDisconnect={vi.fn()}
      />,
    );

    const strip = screen.getByRole("region", { name: "Viewer environment" });
    expect(strip).toBeTruthy();
    const profileChip = screen.getByText("Profile profile-...7890");
    expect(profileChip).toBeTruthy();
    expect(profileChip.getAttribute("title")).toBe("profile-1234567890");
    expect(screen.getByText("Connecting")).toBeTruthy();
    expect(screen.getByText("Automation ready")).toBeTruthy();
    expect(screen.getByText("Clipboard sync on")).toBeTruthy();
    expect(screen.getByRole("toolbar", { name: "Viewer actions" })).toBeTruthy();

    await waitFor(() => expect(rfbInstances[0]?.listeners.connect).toBeTruthy());

    act(() => {
      rfbInstances[0].listeners.connect();
    });

    expect(await screen.findByText("Connected")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Copy Automation API endpoint URL" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Disable clipboard sync" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Fullscreen" })).toBeTruthy();
  });

  it("shows a redacted business session identifier when provided", () => {
    render(
      <ProfileViewer
        profileId="runtime-profile-1234567890"
        externalSessionId="pm-remote-session-1234567890"
        automationUrl={null}
        clipboardSync={false}
        onDisconnect={vi.fn()}
      />,
    );

    const sessionChip = screen.getByText("Session pm-remot...7890");
    expect(sessionChip).toBeTruthy();
    expect(sessionChip.getAttribute("title")).toBe("pm-remote-session-1234567890");
  });

  it("omits the business session chip for regular profile viewers", () => {
    render(
      <ProfileViewer
        profileId="profile-1"
        automationUrl={null}
        clipboardSync={false}
        onDisconnect={vi.fn()}
      />,
    );

    expect(screen.queryByText(/^Session /)).toBeNull();
  });

  it("connects noVNC to a supplied runtime viewer URL without rendering its token", async () => {
    const runtimeViewerUrl =
      "/api/runtime/sessions/runtime-session-1/vnc?viewer_token=secret-viewer-token";

    render(
      <ProfileViewer
        profileId="runtime-profile-1"
        externalSessionId="pm-session-runtime-viewer"
        vncUrl={runtimeViewerUrl}
        automationUrl={null}
        clipboardSync={false}
        onDisconnect={vi.fn()}
      />,
    );

    await waitFor(() => expect(MockRFB).toHaveBeenCalledTimes(1));

    const [, wsUrl, options] = MockRFB.mock.calls[0];
    expect(wsUrl).toBe(runtimeViewerUrl);
    expect(options).toEqual({ wsProtocols: ["binary"] });
    expect(document.body.textContent).not.toContain("secret-viewer-token");
    expect(document.body.textContent).not.toContain(runtimeViewerUrl);
  });

  it("redacts runtime viewer security failures instead of rendering token-bearing reasons", async () => {
    const runtimeViewerUrl =
      "/api/runtime/sessions/runtime-session-1/vnc?viewer_token=secret-viewer-token";
    const rawReason =
      "viewer_token=secret-viewer-token rejected for /api/runtime/sessions/runtime-session-1/vnc?viewer_token=secret-viewer-token";

    render(
      <ProfileViewer
        profileId="runtime-profile-1"
        externalSessionId="pm-session-runtime-viewer"
        vncUrl={runtimeViewerUrl}
        automationUrl={null}
        clipboardSync={false}
        onDisconnect={vi.fn()}
      />,
    );

    await waitFor(() => expect(rfbInstances[0]?.listeners.securityfailure).toBeTruthy());

    act(() => {
      rfbInstances[0].listeners.securityfailure({
        detail: { reason: rawReason },
      });
    });

    expect(await screen.findByText("Connection failed")).toBeTruthy();
    expect(
      screen.getByText(
        "Viewer access expired or unavailable. Request a fresh viewer session from Project Mileage and try again.",
      ),
    ).toBeTruthy();
    expect(document.body.textContent).not.toContain("secret-viewer-token");
    expect(document.body.textContent).not.toContain(runtimeViewerUrl);
    expect(document.body.textContent).not.toContain(rawReason);
  });

  it("shows a redacted runtime viewer access hint when noVNC disconnects before connecting", async () => {
    const onDisconnect = vi.fn();
    const runtimeViewerUrl =
      "/api/runtime/sessions/runtime-session-1/vnc?viewer_token=secret-viewer-token";

    render(
      <ProfileViewer
        profileId="runtime-profile-1"
        externalSessionId="pm-session-runtime-viewer"
        vncUrl={runtimeViewerUrl}
        automationUrl={null}
        clipboardSync={false}
        onDisconnect={onDisconnect}
      />,
    );

    await waitFor(() => expect(rfbInstances[0]?.listeners.disconnect).toBeTruthy());

    act(() => {
      rfbInstances[0].listeners.disconnect({
        detail: { reason: `closed ${runtimeViewerUrl}` },
      });
    });

    expect(await screen.findByText("Connection failed")).toBeTruthy();
    expect(
      screen.getByText(
        "Viewer access expired or unavailable. Request a fresh viewer session from Project Mileage and try again.",
      ),
    ).toBeTruthy();
    expect(onDisconnect).not.toHaveBeenCalled();
    expect(document.body.textContent).not.toContain("secret-viewer-token");
    expect(document.body.textContent).not.toContain(runtimeViewerUrl);
  });

  it("redacts runtime viewer initialization errors instead of rendering token-bearing messages", async () => {
    const runtimeViewerUrl =
      "/api/runtime/sessions/runtime-session-1/vnc?viewer_token=secret-viewer-token";
    const rawMessage = `failed to initialize ${runtimeViewerUrl}`;

    MockRFB.mockImplementationOnce(function MockRFBInitFailure() {
      throw new Error(rawMessage);
    });

    render(
      <ProfileViewer
        profileId="runtime-profile-1"
        externalSessionId="pm-session-runtime-viewer"
        vncUrl={runtimeViewerUrl}
        automationUrl={null}
        clipboardSync={false}
        onDisconnect={vi.fn()}
      />,
    );

    expect(await screen.findByText("Connection failed")).toBeTruthy();
    expect(
      screen.getByText(
        "Viewer access expired or unavailable. Request a fresh viewer session from Project Mileage and try again.",
      ),
    ).toBeTruthy();
    expect(document.body.textContent).not.toContain("secret-viewer-token");
    expect(document.body.textContent).not.toContain(runtimeViewerUrl);
    expect(document.body.textContent).not.toContain(rawMessage);
  });

  it("keeps runtime viewer disconnects after a successful connection on the normal disconnect path", async () => {
    const onDisconnect = vi.fn();
    const runtimeViewerUrl =
      "/api/runtime/sessions/runtime-session-1/vnc?viewer_token=secret-viewer-token";

    render(
      <ProfileViewer
        profileId="runtime-profile-1"
        externalSessionId="pm-session-runtime-viewer"
        vncUrl={runtimeViewerUrl}
        automationUrl={null}
        clipboardSync={false}
        onDisconnect={onDisconnect}
      />,
    );

    await waitFor(() => expect(rfbInstances[0]?.listeners.connect).toBeTruthy());

    act(() => {
      rfbInstances[0].listeners.connect();
      rfbInstances[0].listeners.disconnect();
    });

    await waitFor(() => expect(onDisconnect).toHaveBeenCalledTimes(1));
    expect(screen.queryByText("Connection failed")).toBeNull();
  });

  it("keeps viewer actions compact and fullscreens the whole viewer frame", async () => {
    const requestFullscreen = vi.fn(function requestFullscreen(this: HTMLElement) {
      Object.defineProperty(document, "fullscreenElement", {
        configurable: true,
        value: this,
      });
      document.dispatchEvent(new Event("fullscreenchange"));
      return Promise.resolve();
    });
    Object.defineProperty(HTMLElement.prototype, "requestFullscreen", {
      configurable: true,
      value: requestFullscreen,
    });
    Object.defineProperty(document, "exitFullscreen", {
      configurable: true,
      value: vi.fn().mockResolvedValue(undefined),
    });

    render(
      <div style={{ width: 360, height: 520 }}>
        <ProfileViewer
          profileId="viewer-fullscreen-check"
          automationUrl="/api/profiles/viewer-fullscreen-check/automation"
          clipboardSync={false}
          onDisconnect={vi.fn()}
        />
      </div>,
    );

    const strip = screen.getByRole("region", { name: "Viewer environment" });
    const toolbar = screen.getByRole("toolbar", { name: "Viewer actions" });

    expect(strip.className).toContain("flex-nowrap");
    expect(toolbar.className).toContain("flex-nowrap");

    fireEvent.click(screen.getByRole("button", { name: "Fullscreen" }));

    await waitFor(() => expect(requestFullscreen).toHaveBeenCalledTimes(1));
    const fullscreenTarget = requestFullscreen.mock.instances[0] as HTMLElement;
    expect(fullscreenTarget.contains(strip)).toBe(true);
    expect(fullscreenTarget.contains(toolbar)).toBe(true);
  });

  it("keeps the automation action visible but disabled when a running profile has no Automation API URL", () => {
    render(
      <ProfileViewer
        profileId="profile-1"
        automationUrl={null}
        clipboardSync={false}
        onDisconnect={vi.fn()}
      />,
    );

    const button = screen.getByRole("button", {
      name: "Automation API unavailable until profile is running",
    }) as HTMLButtonElement;

    expect(button.disabled).toBe(true);
    expect(button.title).toBe(
      "Launch the profile to expose its Automation API endpoint.",
    );
  });

  it("copies the Automation API endpoint when the backend exposes one", async () => {
    const writeText = vi.mocked(navigator.clipboard.writeText);

    render(
      <ProfileViewer
        profileId="profile-1"
        automationUrl="/api/profiles/profile-1/automation"
        clipboardSync={false}
        onDisconnect={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Copy Automation API endpoint URL" }));

    await waitFor(() => {
      expect(writeText).toHaveBeenCalledWith(
        `${window.location.protocol}//${window.location.host}/api/profiles/profile-1/automation`,
      );
    });

    await screen.findByRole("button", { name: "Automation API endpoint copied" });
    expect(
      screen.getByRole("button", { name: "Automation API endpoint copied" }).getAttribute("title"),
    ).toBe("Automation API endpoint copied");
  });
});
