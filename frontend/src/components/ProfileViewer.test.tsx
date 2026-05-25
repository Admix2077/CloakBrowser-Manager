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
});

describe("ProfileViewer Automation API toolbar action", () => {
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
