import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { ProfileCsvPreviewDialog } from "./ProfileCsvPreviewDialog";
import { api, type ProfileImportPreviewResponse } from "../lib/api";

vi.mock("../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/api")>();
  return {
    ...actual,
    api: {
      previewProfileImport: vi.fn(),
      importProfiles: vi.fn(),
    },
  };
});

const mockPreviewProfileImport = api.previewProfileImport as ReturnType<typeof vi.fn>;
const mockImportProfiles = api.importProfiles as ReturnType<typeof vi.fn>;

const validPreview: ProfileImportPreviewResponse = {
  total: 1,
  valid: 1,
  invalid: 0,
  rows: [
    {
      line_number: 2,
      ok: true,
      errors: [],
      source: {
        name: "Imported Profile",
        proxy: "http://user:hiddenpass@proxy.example:8080",
      },
      profile: {
        name: "Imported Profile",
        template_id: null,
        proxy: "http://user:hiddenpass@proxy.example:8080",
        timezone: "America/Los_Angeles",
        locale: "en-US",
        platform: "windows",
        screen_width: 1920,
        screen_height: 1080,
        gpu_vendor: null,
        gpu_renderer: null,
        hardware_concurrency: null,
        color_scheme: null,
        humanize: false,
        human_preset: "default",
        launch_args: [],
        geoip: true,
        notes: null,
        tags: [],
      },
    },
  ],
};

beforeEach(() => {
  mockPreviewProfileImport.mockReset();
  mockImportProfiles.mockReset();
});

describe("ProfileCsvPreviewDialog", () => {
  it("redacts sensitive preview errors before rendering alert text", async () => {
    const leakMarker = "profile-preview-token-super-secret";
    mockPreviewProfileImport.mockRejectedValueOnce(
      new Error(
        `preview failed Authorization=Bearer ${leakMarker} token=${leakMarker} /data/profile-import.csv`,
      ),
    );

    render(<ProfileCsvPreviewDialog onClose={vi.fn()} />);

    fireEvent.change(screen.getByLabelText("Profile CSV content"), {
      target: { value: "name,proxy\nImported,http://proxy.example:8080" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Preview CSV" }));

    const alert = await screen.findByRole("alert");
    const text = alert.textContent ?? "";
    expect(text).toContain("preview failed");
    expect(text).not.toContain(leakMarker);
    expect(text).not.toContain("Authorization");
    expect(text).not.toContain("Bearer");
    expect(text).not.toContain("token=");
    expect(text).not.toContain("/data/profile-import.csv");
  });

  it("redacts sensitive import errors after a valid preview", async () => {
    const leakMarker = "profile-import-token-super-secret";
    mockPreviewProfileImport.mockResolvedValueOnce(validPreview);
    mockImportProfiles.mockRejectedValueOnce(
      new Error(
        `import failed Authorization=Bearer ${leakMarker} token=${leakMarker} /data/profile-import.csv`,
      ),
    );

    render(<ProfileCsvPreviewDialog onClose={vi.fn()} />);

    fireEvent.change(screen.getByLabelText("Profile CSV content"), {
      target: { value: "name,proxy\nImported,http://user:hiddenpass@proxy.example:8080" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Preview CSV" }));
    await waitFor(() => expect(mockPreviewProfileImport).toHaveBeenCalledTimes(1));

    fireEvent.click(await screen.findByRole("button", { name: "Create valid profiles" }));

    const alert = await screen.findByRole("alert");
    const text = alert.textContent ?? "";
    expect(text).toContain("import failed");
    expect(text).not.toContain(leakMarker);
    expect(text).not.toContain("Authorization");
    expect(text).not.toContain("Bearer");
    expect(text).not.toContain("token=");
    expect(text).not.toContain("/data/profile-import.csv");
    expect(document.body.textContent).not.toContain("hiddenpass");
  });

  it("redacts sensitive row validation errors in preview results", async () => {
    const leakMarker = "profile-row-token-super-secret";
    mockPreviewProfileImport.mockResolvedValueOnce({
      total: 1,
      valid: 0,
      invalid: 1,
      rows: [
        {
          line_number: 2,
          ok: false,
          errors: [
            `proxy failed Authorization=Bearer ${leakMarker} token=${leakMarker} /data/profile-import.csv`,
          ],
          source: {
            name: "Imported Profile",
            proxy: "http://user:hiddenpass@proxy.example:8080",
          },
          profile: null,
        },
      ],
    });

    render(<ProfileCsvPreviewDialog onClose={vi.fn()} />);

    fireEvent.change(screen.getByLabelText("Profile CSV content"), {
      target: { value: "name,proxy\nImported,http://user:hiddenpass@proxy.example:8080" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Preview CSV" }));

    expect(await screen.findByText(/proxy failed/)).toBeTruthy();
    const rendered = document.body.textContent ?? "";
    expect(rendered).not.toContain(leakMarker);
    expect(rendered).not.toContain("Authorization");
    expect(rendered).not.toContain("Bearer");
    expect(rendered).not.toContain("token=");
    expect(rendered).not.toContain("/data/profile-import.csv");
    expect(rendered).not.toContain("hiddenpass");
  });
});
