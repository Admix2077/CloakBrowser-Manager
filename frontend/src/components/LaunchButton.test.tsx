import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { LaunchButton } from "./LaunchButton";

describe("LaunchButton", () => {
  it("does not render or log raw launch failure details", async () => {
    const leakMarker = "launch-token-super-secret";
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const onLaunch = vi
      .fn()
      .mockRejectedValue(
        new Error(`launch failed token=${leakMarker} /data/profile-secret`),
      );

    try {
      render(
        <LaunchButton
          status="stopped"
          onLaunch={onLaunch}
          onStop={vi.fn()}
        />,
      );

      fireEvent.click(screen.getByRole("button", { name: "Launch" }));

      await waitFor(() => {
        expect(screen.getByText("Action failed")).toBeTruthy();
      });

      expect(document.body.textContent).not.toContain(leakMarker);
      expect(document.body.textContent).not.toContain("token=");
      expect(document.body.textContent).not.toContain("/data/profile-secret");

      const consoleCalls = JSON.stringify(consoleError.mock.calls);
      expect(consoleCalls).not.toContain(leakMarker);
      expect(consoleCalls).not.toContain("token=");
      expect(consoleCalls).not.toContain("/data/profile-secret");
    } finally {
      consoleError.mockRestore();
    }
  });
});
