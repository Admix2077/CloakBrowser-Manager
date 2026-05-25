import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { ProfileViewer } from "./ProfileViewer";

vi.mock("@novnc/novnc/core/rfb.js", () => ({
  default: class MockRFB {
    scaleViewport = false;
    resizeSession = false;
    showDotCursor = false;
    addEventListener = vi.fn();
    removeEventListener = vi.fn();
    disconnect = vi.fn();
    sendKey = vi.fn();
  },
}));

vi.mock("../lib/api", () => ({
  api: {
    getClipboard: vi.fn(),
    setClipboard: vi.fn(),
  },
}));

beforeEach(() => {
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: {
      readText: vi.fn(),
      writeText: vi.fn().mockResolvedValue(undefined),
    },
  });
});

describe("ProfileViewer CDP toolbar action", () => {
  it("keeps the CDP action visible but disabled when invisible_playwright has no CDP URL", () => {
    render(
      <ProfileViewer
        profileId="profile-1"
        cdpUrl={null}
        clipboardSync={false}
        onDisconnect={vi.fn()}
      />,
    );

    const button = screen.getByRole("button", {
      name: "CDP unavailable for invisible_playwright Firefox profiles",
    }) as HTMLButtonElement;

    expect(button.disabled).toBe(true);
    expect(button.title).toBe("CDP is not available for invisible_playwright Firefox profiles");
  });

  it("copies the CDP endpoint when a future backend exposes one", async () => {
    const writeText = vi.mocked(navigator.clipboard.writeText);

    render(
      <ProfileViewer
        profileId="profile-1"
        cdpUrl="/api/profiles/profile-1/cdp"
        clipboardSync={false}
        onDisconnect={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Copy CDP endpoint URL" }));

    await waitFor(() => {
      expect(writeText).toHaveBeenCalledWith(
        `${window.location.protocol}//${window.location.host}/api/profiles/profile-1/cdp`,
      );
    });
  });
});
