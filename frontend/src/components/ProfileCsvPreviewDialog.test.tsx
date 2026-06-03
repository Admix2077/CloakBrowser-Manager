import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
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

  it("redacts preview textarea evidence without changing submitted import CSV", async () => {
    const leakMarker = "profile-csv-textarea-secret";
    const rawCsv = [
      "name,proxy,notes",
      `Imported Authorization=Bearer ${leakMarker} token=${leakMarker} /data/profile-csv.csv 203.0.113.94,http://user:hiddenpass@proxy.example:8080,Notes`,
    ].join("\n");
    mockPreviewProfileImport.mockResolvedValueOnce(validPreview);
    mockImportProfiles.mockResolvedValueOnce({
      total: 1,
      succeeded: 1,
      failed: 0,
      results: [],
    });

    render(<ProfileCsvPreviewDialog onClose={vi.fn()} />);

    const textarea = screen.getByLabelText("Profile CSV content") as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: rawCsv } });
    fireEvent.click(screen.getByRole("button", { name: "Preview CSV" }));

    await waitFor(() => expect(mockPreviewProfileImport).toHaveBeenCalledWith(rawCsv));
    expect(textarea.value).toContain("Imported [redacted] [redacted] [redacted-path] [redacted-ip]");
    for (const leaked of [
      leakMarker,
      "Authorization",
      "Bearer",
      "token=",
      "/data/profile-csv.csv",
      "203.0.113.94",
      "hiddenpass",
    ]) {
      expect(textarea.value).not.toContain(leaked);
    }

    fireEvent.click(await screen.findByRole("button", { name: "Create valid profiles" }));
    await waitFor(() => expect(mockImportProfiles).toHaveBeenCalledWith(rawCsv));
  });

  it("redacts preview row profile metadata from rendered evidence", async () => {
    const leakMarker = "profile-csv-row-secret";
    mockPreviewProfileImport.mockResolvedValueOnce({
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
            ...validPreview.rows[0].profile!,
            name:
              "Imported Authorization=Bearer " +
              `${leakMarker} token=${leakMarker} /data/profile-row-name 203.0.113.95`,
            template_id:
              "template Authorization=Bearer " +
              `${leakMarker} token=${leakMarker} /data/profile-row-template 203.0.113.96`,
            platform:
              "windows Authorization=Bearer " +
              `${leakMarker} token=${leakMarker} /data/profile-row-platform 203.0.113.97`,
            locale:
              "en-US Authorization=Bearer " +
              `${leakMarker} token=${leakMarker} /data/profile-row-locale 203.0.113.98`,
            timezone:
              "America/Los_Angeles Authorization=Bearer " +
              `${leakMarker} token=${leakMarker} /data/profile-row-timezone 203.0.113.99`,
          },
        },
      ],
    });

    render(<ProfileCsvPreviewDialog onClose={vi.fn()} />);

    fireEvent.change(screen.getByLabelText("Profile CSV content"), {
      target: { value: "name,proxy\nImported,http://user:hiddenpass@proxy.example:8080" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Preview CSV" }));

    const table = await screen.findByRole("table", { name: "Profile CSV preview" });
    expect(within(table).getByText("Imported [redacted] [redacted] [redacted-path] [redacted-ip]")).toBeTruthy();
    expect(within(table).getByText("template [redacted] [redacted] [redacted-path] [redacted-ip]")).toBeTruthy();
    expect(within(table).getByText("windows [redacted] [redacted] [redacted-path] [redacted-ip]")).toBeTruthy();
    expect(within(table).getByText("en-US [redacted] [redacted] [redacted-path] [redacted-ip]")).toBeTruthy();
    expect(within(table).getByText("America/Los_Angeles [redacted] [redacted] [redacted-path] [redacted-ip]")).toBeTruthy();

    const titleText = Array.from(table.querySelectorAll("[title]"))
      .map((element) => element.getAttribute("title") ?? "")
      .join(" ");
    const renderedEvidence = `${table.textContent ?? ""} ${titleText}`;

    for (const leaked of [
      leakMarker,
      "Authorization",
      "Bearer",
      "token=",
      "/data/profile-row-name",
      "/data/profile-row-template",
      "/data/profile-row-platform",
      "/data/profile-row-locale",
      "/data/profile-row-timezone",
      "203.0.113.95",
      "203.0.113.96",
      "203.0.113.97",
      "203.0.113.98",
      "203.0.113.99",
      "hiddenpass",
    ]) {
      expect(renderedEvidence).not.toContain(leaked);
    }
  });
});
