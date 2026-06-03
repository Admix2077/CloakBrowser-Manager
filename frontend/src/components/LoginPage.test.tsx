import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { LoginPage } from "./LoginPage";
import { api } from "../lib/api";

vi.mock("../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/api")>();
  return {
    ...actual,
    api: {
      login: vi.fn(),
    },
  };
});

const mockLogin = api.login as ReturnType<typeof vi.fn>;

beforeEach(() => {
  mockLogin.mockReset();
});

describe("LoginPage", () => {
  it("does not render raw login failure details", async () => {
    const leakMarker = "login-token-super-secret";
    mockLogin.mockRejectedValueOnce(
      new Error(
        `login failed token=${leakMarker} Authorization=Bearer ${leakMarker} /data/auth/${leakMarker}`,
      ),
    );

    render(<LoginPage onSuccess={vi.fn()} />);

    fireEvent.change(screen.getByPlaceholderText("Access token"), {
      target: { value: "user-access-token" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Unlock" }));

    await waitFor(() => {
      expect(screen.getByText("Login failed")).toBeTruthy();
    });

    expect(document.body.textContent).not.toContain(leakMarker);
    expect(document.body.textContent).not.toContain("Authorization");
    expect(document.body.textContent).not.toContain("Bearer");
    expect(document.body.textContent).not.toContain("token=");
    expect(document.body.textContent).not.toContain("/data/auth");
  });
});
