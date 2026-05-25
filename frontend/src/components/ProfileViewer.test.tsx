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
