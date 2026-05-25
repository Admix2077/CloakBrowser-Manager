import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ProfileForm } from "./ProfileForm";

describe("ProfileForm launch arguments", () => {
  it("describes launch args as invisible_playwright Firefox arguments", () => {
    render(
      <ProfileForm
        profile={null}
        onSave={vi.fn()}
        onCancel={vi.fn()}
      />,
    );

    expect(screen.getByText("Firefox Launch Args")).toBeTruthy();
    expect(screen.getByText(/Custom Firefox arguments passed to invisible_playwright/)).toBeTruthy();
    expect(screen.getByPlaceholderText("--private-window")).toBeTruthy();
  });
});
