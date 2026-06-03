import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ProfileForm } from "./ProfileForm";
import type { Profile, ProfileTemplate } from "../lib/api";

const humanizedProfile: Profile = {
  id: "profile-1",
  name: "Humanized",
  fingerprint_seed: 12345,
  proxy: null,
  timezone: null,
  locale: null,
  platform: "macos",
  user_agent: "custom",
  screen_width: 1920,
  screen_height: 1080,
  gpu_vendor: null,
  gpu_renderer: null,
  hardware_concurrency: null,
  humanize: true,
  human_preset: "careful",
  headless: false,
  geoip: true,
  clipboard_sync: true,
  auto_launch: false,
  color_scheme: null,
  launch_args: [],
  notes: null,
  user_data_dir: "/data/profiles/profile-1",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  tags: [],
  status: "stopped",
  vnc_ws_port: null,
  automation_url: null,
};

function template(overrides: Partial<ProfileTemplate>): ProfileTemplate {
  return {
    id: "template-1",
    name: "Starter",
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
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

describe("ProfileForm launch arguments", () => {
  it("describes launch args as Firefox browser engine arguments", () => {
    render(
      <ProfileForm
        profile={null}
        onSave={vi.fn()}
        onCancel={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("tab", { name: "Advanced" }));

    expect(screen.getByText("Firefox Launch Args")).toBeTruthy();
    expect(screen.getByText(/Custom Firefox arguments passed to the browser engine/)).toBeTruthy();
    expect(screen.getByText(/Only Firefox-compatible launch arguments are applied/)).toBeTruthy();
    expect(screen.getByPlaceholderText("--private-window")).toBeTruthy();
  });
});

describe("ProfileForm phase-one field boundaries", () => {
  it("does not expose unsupported identity controls as editable settings", () => {
    render(
      <ProfileForm
        profile={null}
        onSave={vi.fn()}
        onCancel={vi.fn()}
      />,
    );

    expect(screen.queryByLabelText("Platform")).toBeNull();
    expect(screen.queryByText(/Auto-detect timezone\/locale from proxy IP/)).toBeNull();
    expect(screen.queryByLabelText("User Agent")).toBeNull();

    ["Network", "Device", "Behavior", "Advanced"].forEach((tab) => {
      fireEvent.click(screen.getByRole("tab", { name: tab }));
      expect(screen.queryByLabelText("Platform")).toBeNull();
      expect(screen.queryByText(/Auto-detect timezone\/locale from proxy IP/)).toBeNull();
      expect(screen.queryByLabelText("User Agent")).toBeNull();
    });
  });

  it("does not expose the ignored human preset even when a stored profile has one", () => {
    render(
      <ProfileForm
        profile={humanizedProfile}
        onSave={vi.fn()}
        onCancel={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("tab", { name: "Behavior" }));

    expect(screen.getByText("Human-like mouse, keyboard, and scroll behavior")).toBeTruthy();
    expect(screen.queryByLabelText("Human Preset")).toBeNull();
  });
});

describe("ProfileForm accessibility and control polish", () => {
  it("renders grouped tabs and defaults to Identity", () => {
    render(
      <ProfileForm
        profile={null}
        onSave={vi.fn()}
        onCancel={vi.fn()}
      />,
    );

    expect(screen.getByRole("tablist", { name: "Profile settings sections" })).toBeTruthy();
    ["Identity", "Network", "Device", "Behavior", "Advanced"].forEach((tab) => {
      expect(screen.getByRole("tab", { name: tab })).toBeTruthy();
    });
    expect(screen.getByRole("tab", { name: "Identity" }).getAttribute("aria-selected")).toBe("true");
    expect(screen.getByRole("tabpanel", { name: "Identity" })).toBeTruthy();
    expect(screen.getByLabelText("Profile Name")).toBeTruthy();
    expect(screen.getByLabelText("Fingerprint Seed")).toBeTruthy();
  });

  it("associates core labels with their form controls", () => {
    render(
      <ProfileForm
        profile={null}
        onSave={vi.fn()}
        onCancel={vi.fn()}
      />,
    );

    expect(screen.getByLabelText("Profile Name")).toBeTruthy();
    expect(screen.getByLabelText("Fingerprint Seed")).toBeTruthy();
    fireEvent.click(screen.getByRole("tab", { name: "Network" }));
    expect(screen.getByLabelText("Proxy")).toBeTruthy();
    expect(screen.getByLabelText("Timezone")).toBeTruthy();
    expect(screen.getByLabelText("Locale")).toBeTruthy();
    fireEvent.click(screen.getByRole("tab", { name: "Device" }));
    expect(screen.getByLabelText("Screen Resolution")).toBeTruthy();
    expect(screen.getByLabelText("Hardware Concurrency")).toBeTruthy();
    expect(screen.getByLabelText("GPU Preset")).toBeTruthy();
    expect(screen.getByLabelText("GPU Vendor")).toBeTruthy();
    expect(screen.getByLabelText("GPU Renderer")).toBeTruthy();
    fireEvent.click(screen.getByRole("tab", { name: "Behavior" }));
    expect(screen.getByLabelText("Color Scheme")).toBeTruthy();
    fireEvent.click(screen.getByRole("tab", { name: "Advanced" }));
    expect(screen.getByLabelText("Notes")).toBeTruthy();
  });

  it("keeps behavior checkboxes accessible and interactive", () => {
    render(
      <ProfileForm
        profile={null}
        onSave={vi.fn()}
        onCancel={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("tab", { name: "Behavior" }));

    const humanize = screen.getByLabelText("Human-like mouse, keyboard, and scroll behavior") as HTMLInputElement;
    const clipboard = screen.getByLabelText("Enable clipboard sync by default in VNC viewer") as HTMLInputElement;
    const autoLaunch = screen.getByLabelText("Launch automatically when container starts") as HTMLInputElement;

    expect(humanize.checked).toBe(false);
    expect(clipboard.checked).toBe(true);
    expect(autoLaunch.checked).toBe(false);

    fireEvent.click(humanize);
    fireEvent.click(clipboard);
    fireEvent.click(autoLaunch);

    expect(humanize.checked).toBe(true);
    expect(clipboard.checked).toBe(false);
    expect(autoLaunch.checked).toBe(true);
  });

  it("labels tag color swatches and removable chips", () => {
    render(
      <ProfileForm
        profile={humanizedProfile}
        onSave={vi.fn()}
        onCancel={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("tab", { name: "Advanced" }));

    expect(screen.getByLabelText("Use tag color #6366f1")).toBeTruthy();

    fireEvent.change(screen.getByLabelText("Tag name"), { target: { value: "ops" } });
    fireEvent.click(screen.getByRole("button", { name: "Add tag" }));

    expect(screen.getByRole("button", { name: "Remove tag ops" })).toBeTruthy();
  });

  it("uses an in-app confirmation dialog before deleting a profile", async () => {
    const onDelete = vi.fn().mockResolvedValue(undefined);
    const nativeConfirm = vi.spyOn(window, "confirm").mockReturnValue(true);

    render(
      <ProfileForm
        profile={humanizedProfile}
        onSave={vi.fn()}
        onDelete={onDelete}
        onCancel={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("tab", { name: "Advanced" }));
    fireEvent.click(screen.getByRole("button", { name: "Delete" }));

    expect(nativeConfirm).not.toHaveBeenCalled();
    const dialog = screen.getByRole("dialog", { name: "Delete profile" });
    expect(dialog).toBeTruthy();
    expect(screen.getByText("Humanized")).toBeTruthy();
    expect(onDelete).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Cancel delete" }));
    expect(screen.queryByRole("dialog", { name: "Delete profile" })).toBeNull();
    expect(onDelete).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    fireEvent.click(screen.getByRole("button", { name: "Confirm delete profile" }));

    await waitFor(() => expect(onDelete).toHaveBeenCalledTimes(1));
    expect(screen.queryByRole("dialog", { name: "Delete profile" })).toBeNull();

    nativeConfirm.mockRestore();
  });

  it("redacts template and delete confirmation names from rendered evidence", () => {
    const leakMarker = "profile-form-name-secret";
    const rawName =
      "Humanized Authorization=Bearer " +
      `${leakMarker} token=${leakMarker} /data/profile-form-name 203.0.113.93`;
    const safeName = "Humanized [redacted] [redacted] [redacted-path] [redacted-ip]";

    const { rerender } = render(
      <ProfileForm
        profile={null}
        templates={[template({ name: rawName })]}
        onSave={vi.fn()}
        onCancel={vi.fn()}
      />,
    );

    expect(screen.getByRole("option", { name: safeName })).toBeTruthy();
    expect(document.body.textContent).not.toContain(leakMarker);
    expect(document.body.textContent).not.toContain("Authorization");
    expect(document.body.textContent).not.toContain("Bearer");
    expect(document.body.textContent).not.toContain("token=");
    expect(document.body.textContent).not.toContain("/data/profile-form-name");
    expect(document.body.textContent).not.toContain("203.0.113.93");

    rerender(
      <ProfileForm
        profile={{ ...humanizedProfile, name: rawName }}
        onSave={vi.fn()}
        onDelete={vi.fn()}
        onCancel={vi.fn()}
      />,
    );

    expect((screen.getByLabelText("Profile Name") as HTMLInputElement).value).toBe(rawName);

    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    const dialog = screen.getByRole("dialog", { name: "Delete profile" });
    expect(dialog.textContent).toContain(safeName);

    const renderedEvidence = [
      dialog.textContent,
      ...Array.from(dialog.querySelectorAll("[title]")).map((element) => element.getAttribute("title") ?? ""),
      ...Array.from(dialog.querySelectorAll("[aria-label]")).map((element) => element.getAttribute("aria-label") ?? ""),
    ].join(" ");

    for (const leaked of [
      leakMarker,
      "Authorization",
      "Bearer",
      "token=",
      "/data/profile-form-name",
      "203.0.113.93",
    ]) {
      expect(renderedEvidence).not.toContain(leaked);
    }
  });

  it("switches sections without losing the save payload", async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);

    render(
      <ProfileForm
        profile={null}
        onSave={onSave}
        onCancel={vi.fn()}
      />,
    );

    fireEvent.change(screen.getByLabelText("Profile Name"), { target: { value: "Ops Profile" } });
    fireEvent.change(screen.getByLabelText("Fingerprint Seed"), { target: { value: "424242" } });

    fireEvent.click(screen.getByRole("tab", { name: "Network" }));
    fireEvent.change(screen.getByLabelText("Proxy"), { target: { value: "http://proxy.example:8080" } });
    fireEvent.change(screen.getByLabelText("Timezone"), { target: { value: "America/New_York" } });
    fireEvent.change(screen.getByLabelText("Locale"), { target: { value: "en-US" } });

    fireEvent.click(screen.getByRole("tab", { name: "Device" }));
    fireEvent.change(screen.getByLabelText("Screen Resolution"), { target: { value: "1366 × 768 (HD)" } });
    fireEvent.change(screen.getByLabelText("Hardware Concurrency"), { target: { value: "8" } });
    fireEvent.change(screen.getByLabelText("GPU Preset"), { target: { value: "Intel UHD 770" } });

    fireEvent.click(screen.getByRole("tab", { name: "Behavior" }));
    fireEvent.click(screen.getByLabelText("Human-like mouse, keyboard, and scroll behavior"));
    fireEvent.click(screen.getByLabelText("Enable clipboard sync by default in VNC viewer"));
    fireEvent.click(screen.getByLabelText("Launch automatically when container starts"));
    fireEvent.change(screen.getByLabelText("Color Scheme"), { target: { value: "dark" } });

    fireEvent.click(screen.getByRole("tab", { name: "Advanced" }));
    fireEvent.change(screen.getByLabelText("Tag name"), { target: { value: "ops" } });
    fireEvent.click(screen.getByRole("button", { name: "Add tag" }));
    fireEvent.change(screen.getByLabelText("Firefox launch argument"), { target: { value: "--private-window" } });
    fireEvent.click(screen.getByRole("button", { name: "Add launch argument" }));
    fireEvent.change(screen.getByLabelText("Notes"), { target: { value: "Ready for operations" } });
    fireEvent.click(screen.getByRole("button", { name: "Create" }));

    await waitFor(() => {
      expect(onSave).toHaveBeenCalledWith(expect.objectContaining({
        name: "Ops Profile",
        fingerprint_seed: 424242,
        proxy: "http://proxy.example:8080",
        timezone: "America/New_York",
        locale: "en-US",
        screen_width: 1366,
        screen_height: 768,
        hardware_concurrency: 8,
        humanize: true,
        clipboard_sync: false,
        auto_launch: true,
        color_scheme: "dark",
        tags: [{ tag: "ops", color: "#6366f1" }],
        launch_args: ["--private-window"],
        notes: "Ready for operations",
      }));
    });
  });
});
