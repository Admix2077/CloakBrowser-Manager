import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useProfiles } from "./useProfiles";

// Mock the api module
vi.mock("../lib/api", () => ({
  api: {
    listProfiles: vi.fn(),
    createProfile: vi.fn(),
    updateProfile: vi.fn(),
    deleteProfile: vi.fn(),
    launchProfile: vi.fn(),
    stopProfile: vi.fn(),
    getProfileHealth: vi.fn(),
    checkProfileHealth: vi.fn(),
  },
}));

import { api } from "../lib/api";

const mockApi = api as {
  listProfiles: ReturnType<typeof vi.fn>;
  createProfile: ReturnType<typeof vi.fn>;
  updateProfile: ReturnType<typeof vi.fn>;
  deleteProfile: ReturnType<typeof vi.fn>;
  launchProfile: ReturnType<typeof vi.fn>;
  stopProfile: ReturnType<typeof vi.fn>;
  getProfileHealth: ReturnType<typeof vi.fn>;
  checkProfileHealth: ReturnType<typeof vi.fn>;
};

const fakeProfile = {
  id: "abc-123",
  name: "Test",
  fingerprint_seed: 12345,
  proxy: null,
  timezone: null,
  locale: null,
  platform: "windows",
  user_agent: null,
  screen_width: 1920,
  screen_height: 1080,
  gpu_vendor: null,
  gpu_renderer: null,
  hardware_concurrency: null,
  humanize: false,
  human_preset: "default",
  headless: false,
  geoip: false,
  clipboard_sync: true,
  color_scheme: null,
  notes: null,
  user_data_dir: "/data/profiles/abc-123",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  tags: [],
  status: "stopped" as const,
  vnc_ws_port: null,
  automation_url: null,
};

const fakeHealth = {
  profile_id: "abc-123",
  status: "good" as const,
  geoip: null,
  manual_overrides: { timezone: false, locale: false },
  runtime: { status: "stopped", vnc_ws_port: null, automation_url: null },
  warnings: [],
  checked_at: "2026-05-25T01:00:00Z",
};

beforeEach(() => {
  vi.clearAllMocks();
  mockApi.listProfiles.mockResolvedValue([fakeProfile]);
  mockApi.getProfileHealth.mockResolvedValue(fakeHealth);
  mockApi.checkProfileHealth.mockResolvedValue(fakeHealth);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("useProfiles", () => {
  it("starts with loading state", () => {
    const { result } = renderHook(() => useProfiles());
    expect(result.current.loading).toBe(true);
    expect(result.current.profiles).toEqual([]);
  });

  it("fetches profiles on mount", async () => {
    const { result } = renderHook(() => useProfiles());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.profiles).toEqual([fakeProfile]);
    expect(mockApi.listProfiles).toHaveBeenCalled();
  });

  it("loads cached health snapshots without blocking the profile list", async () => {
    const { result } = renderHook(() => useProfiles());

    await waitFor(() => expect(result.current.loading).toBe(false));
    await waitFor(() => {
      expect(result.current.healthByProfileId["abc-123"]).toEqual(fakeHealth);
    });

    expect(mockApi.getProfileHealth).toHaveBeenCalledWith("abc-123");
  });

  it("keeps profiles usable when a health request fails", async () => {
    mockApi.getProfileHealth.mockRejectedValue(new Error("health failed"));

    const { result } = renderHook(() => useProfiles());

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.profiles).toEqual([fakeProfile]);
    expect(result.current.error).toBe(null);
    expect(result.current.healthByProfileId["abc-123"]).toBeUndefined();
  });

  it("create prepends to list", async () => {
    const newProfile = { ...fakeProfile, id: "new-1", name: "New" };
    mockApi.createProfile.mockResolvedValue(newProfile);

    const { result } = renderHook(() => useProfiles());
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.create({ name: "New" });
    });

    expect(result.current.profiles[0].id).toBe("new-1");
  });

  it("update replaces in list", async () => {
    const updated = { ...fakeProfile, name: "Renamed" };
    mockApi.updateProfile.mockResolvedValue(updated);

    const { result } = renderHook(() => useProfiles());
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.update("abc-123", { name: "Renamed" });
    });

    expect(result.current.profiles[0].name).toBe("Renamed");
  });

  it("remove filters from list", async () => {
    mockApi.deleteProfile.mockResolvedValue({ ok: true });

    const { result } = renderHook(() => useProfiles());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.profiles).toHaveLength(1);

    await act(async () => {
      await result.current.remove("abc-123");
    });

    expect(result.current.profiles).toHaveLength(0);
  });

  it("bulk deletes selected stopped profiles once and removes health snapshots", async () => {
    const secondProfile = { ...fakeProfile, id: "delete-2", name: "Delete 2" };
    mockApi.listProfiles.mockResolvedValue([fakeProfile, secondProfile]);
    mockApi.deleteProfile.mockResolvedValue({ ok: true });

    const { result } = renderHook(() => useProfiles());
    await waitFor(() => expect(result.current.loading).toBe(false));
    await waitFor(() => expect(result.current.healthByProfileId["abc-123"]).toEqual(fakeHealth));

    let deleteResult;
    await act(async () => {
      deleteResult = await result.current.deleteProfiles(["abc-123", "delete-2", "abc-123"]);
    });

    expect(mockApi.deleteProfile).toHaveBeenCalledTimes(2);
    expect(mockApi.deleteProfile).toHaveBeenCalledWith("abc-123");
    expect(mockApi.deleteProfile).toHaveBeenCalledWith("delete-2");
    expect(result.current.profiles).toEqual([]);
    expect(result.current.healthByProfileId["abc-123"]).toBeUndefined();
    expect(deleteResult).toMatchObject({
      requestedCount: 2,
      deletableCount: 2,
      deletedCount: 2,
      skippedRunningCount: 0,
      failedCount: 0,
    });
  });

  it("skips running profiles during bulk delete", async () => {
    const runningProfile = { ...fakeProfile, id: "running-123", name: "Running", status: "running" as const };
    mockApi.listProfiles.mockResolvedValue([fakeProfile, runningProfile]);
    mockApi.deleteProfile.mockResolvedValue({ ok: true });

    const { result } = renderHook(() => useProfiles());
    await waitFor(() => expect(result.current.loading).toBe(false));

    let deleteResult;
    await act(async () => {
      deleteResult = await result.current.deleteProfiles(["running-123", "abc-123"]);
    });

    expect(mockApi.deleteProfile).toHaveBeenCalledTimes(1);
    expect(mockApi.deleteProfile).toHaveBeenCalledWith("abc-123");
    expect(deleteResult).toMatchObject({
      requestedCount: 2,
      deletableCount: 1,
      deletedCount: 1,
      skippedRunningCount: 1,
      failedCount: 0,
    });
    expect(result.current.profiles.map((profile) => profile.id)).toEqual(["running-123"]);
  });

  it("reports partial bulk delete failures while removing successful profiles", async () => {
    const failingProfile = { ...fakeProfile, id: "fail-123", name: "Failing delete" };
    mockApi.listProfiles.mockResolvedValue([fakeProfile, failingProfile]);
    mockApi.deleteProfile.mockImplementation((id: string) => {
      if (id === "abc-123") return Promise.resolve({ ok: true });
      return Promise.reject(new Error("Delete failed for proxy http://user:secret@proxy.example:8080"));
    });

    const { result } = renderHook(() => useProfiles());
    await waitFor(() => expect(result.current.loading).toBe(false));

    let deleteResult;
    await act(async () => {
      deleteResult = await result.current.deleteProfiles(["abc-123", "fail-123"]);
    });

    expect(mockApi.deleteProfile).toHaveBeenCalledTimes(2);
    expect(result.current.profiles.map((profile) => profile.id)).toEqual(["fail-123"]);
    expect(deleteResult).toMatchObject({
      requestedCount: 2,
      deletableCount: 2,
      deletedCount: 1,
      skippedRunningCount: 0,
      failedCount: 1,
    });
    expect(result.current.error).toBe("Failed to delete 1 profile(s): Delete failed for proxy http://proxy.example:8080");
  });

  it("reports selected profile ids that disappear before bulk delete", async () => {
    mockApi.listProfiles.mockResolvedValue([fakeProfile]);

    const { result } = renderHook(() => useProfiles());
    await waitFor(() => expect(result.current.loading).toBe(false));

    let deleteResult;
    await act(async () => {
      deleteResult = await result.current.deleteProfiles(["missing-123"]);
    });

    expect(mockApi.deleteProfile).not.toHaveBeenCalled();
    expect(deleteResult).toMatchObject({
      requestedCount: 1,
      deletableCount: 0,
      deletedCount: 0,
      skippedRunningCount: 0,
      failedCount: 1,
    });
    expect(result.current.error).toBe("Failed to delete 1 profile(s): Profile missing-123 is no longer available");
  });

  it("sets error on fetch failure", async () => {
    mockApi.listProfiles.mockRejectedValue(new Error("Network error"));

    const { result } = renderHook(() => useProfiles());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toBe("Network error");
  });

  it("refreshes health after launching a profile", async () => {
    mockApi.launchProfile.mockResolvedValue({
      profile_id: "abc-123",
      status: "running",
      vnc_ws_port: 6100,
      display: ":100",
      automation_url: "/api/profiles/abc-123/automation",
    });

    const { result } = renderHook(() => useProfiles());
    await waitFor(() => expect(result.current.loading).toBe(false));
    mockApi.getProfileHealth.mockClear();

    await act(async () => {
      await result.current.launch("abc-123");
    });

    expect(mockApi.getProfileHealth).toHaveBeenCalledWith("abc-123");
  });

  it("launches selected profiles once, refreshes once, and reports partial failures", async () => {
    const failingProfile = { ...fakeProfile, id: "fail-123", name: "Fail" };
    mockApi.listProfiles.mockResolvedValue([fakeProfile, failingProfile]);
    mockApi.launchProfile.mockImplementation((id: string) => {
      if (id === "abc-123") {
        return Promise.resolve({
          profile_id: id,
          status: "running",
          vnc_ws_port: 6100,
          display: ":100",
          automation_url: `/api/profiles/${id}/automation`,
        });
      }
      return Promise.reject(new Error("Launch failed"));
    });

    const { result } = renderHook(() => useProfiles());
    await waitFor(() => expect(result.current.loading).toBe(false));
    mockApi.listProfiles.mockClear();
    mockApi.getProfileHealth.mockClear();

    await act(async () => {
      await result.current.launchProfiles(["abc-123", "abc-123", "fail-123"]);
    });

    expect(mockApi.launchProfile).toHaveBeenCalledTimes(2);
    expect(mockApi.launchProfile).toHaveBeenCalledWith("abc-123");
    expect(mockApi.launchProfile).toHaveBeenCalledWith("fail-123");
    expect(mockApi.listProfiles).toHaveBeenCalledTimes(1);
    expect(mockApi.getProfileHealth).toHaveBeenCalledWith("abc-123");
    expect(result.current.error).toBe("Failed to launch 1 profile(s): Launch failed");
  });

  it("keeps bulk launch failures visible across background profile refreshes", async () => {
    mockApi.launchProfile.mockRejectedValue(new Error("Failed to launch browser"));

    const { result } = renderHook(() => useProfiles());
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.launchProfiles(["abc-123"]);
    });

    expect(result.current.error).toBe("Failed to launch 1 profile(s): Failed to launch browser");

    await act(async () => {
      await result.current.refresh();
    });

    expect(result.current.error).toBe("Failed to launch 1 profile(s): Failed to launch browser");
  });

  it("skips running profiles during bulk launch", async () => {
    const runningProfile = { ...fakeProfile, id: "running-123", name: "Running", status: "running" as const };
    mockApi.listProfiles.mockResolvedValue([fakeProfile, runningProfile]);
    mockApi.launchProfile.mockResolvedValue({
      profile_id: "abc-123",
      status: "running",
      vnc_ws_port: 6100,
      display: ":100",
      automation_url: "/api/profiles/abc-123/automation",
    });

    const { result } = renderHook(() => useProfiles());
    await waitFor(() => expect(result.current.loading).toBe(false));

    let launchResult;
    await act(async () => {
      launchResult = await result.current.launchProfiles(["running-123", "abc-123"]);
    });

    expect(mockApi.launchProfile).toHaveBeenCalledTimes(1);
    expect(mockApi.launchProfile).toHaveBeenCalledWith("abc-123");
    expect(launchResult).toMatchObject({
      requestedCount: 2,
      launchableCount: 1,
      launchedCount: 1,
      skippedRunningCount: 1,
      failedCount: 0,
    });
  });

  it("stops selected running profiles once, refreshes once, and reports partial failures", async () => {
    const runningProfile = { ...fakeProfile, id: "run-123", name: "Running", status: "running" as const };
    const failingProfile = { ...fakeProfile, id: "fail-123", name: "Failing", status: "running" as const };
    mockApi.listProfiles.mockResolvedValue([fakeProfile, runningProfile, failingProfile]);
    mockApi.stopProfile.mockImplementation((id: string) => {
      if (id === "run-123") return Promise.resolve({ ok: true });
      return Promise.reject(new Error("Profile is not running"));
    });

    const { result } = renderHook(() => useProfiles());
    await waitFor(() => expect(result.current.loading).toBe(false));
    mockApi.listProfiles.mockClear();
    mockApi.getProfileHealth.mockClear();

    let stopResult;
    await act(async () => {
      stopResult = await result.current.stopProfiles(["abc-123", "run-123", "run-123", "fail-123"]);
    });

    expect(mockApi.stopProfile).toHaveBeenCalledTimes(2);
    expect(mockApi.stopProfile).toHaveBeenCalledWith("run-123");
    expect(mockApi.stopProfile).toHaveBeenCalledWith("fail-123");
    expect(mockApi.listProfiles).toHaveBeenCalledTimes(1);
    expect(mockApi.getProfileHealth).toHaveBeenCalledWith("run-123");
    expect(stopResult).toMatchObject({
      requestedCount: 3,
      stoppableCount: 2,
      stoppedCount: 1,
      skippedStoppedCount: 1,
      failedCount: 1,
    });
    expect(result.current.error).toBe("Failed to stop 1 profile(s): Profile is not running");
  });

  it("skips stopped profiles during bulk stop", async () => {
    const runningProfile = { ...fakeProfile, id: "running-123", name: "Running", status: "running" as const };
    mockApi.listProfiles.mockResolvedValue([fakeProfile, runningProfile]);
    mockApi.stopProfile.mockResolvedValue({ ok: true });

    const { result } = renderHook(() => useProfiles());
    await waitFor(() => expect(result.current.loading).toBe(false));

    let stopResult;
    await act(async () => {
      stopResult = await result.current.stopProfiles(["abc-123", "running-123"]);
    });

    expect(mockApi.stopProfile).toHaveBeenCalledTimes(1);
    expect(mockApi.stopProfile).toHaveBeenCalledWith("running-123");
    expect(stopResult).toMatchObject({
      requestedCount: 2,
      stoppableCount: 1,
      stoppedCount: 1,
      skippedStoppedCount: 1,
      failedCount: 0,
    });
  });

  it("adds a tag to selected profiles without removing existing tags", async () => {
    const taggedProfile = {
      ...fakeProfile,
      id: "tagged-123",
      name: "Tagged",
      tags: [{ tag: "existing", color: "#22c55e" }],
    };
    const plainProfile = { ...fakeProfile, id: "plain-123", name: "Plain" };
    mockApi.listProfiles.mockResolvedValue([taggedProfile, plainProfile]);
    mockApi.updateProfile.mockImplementation((id: string, data: { tags?: { tag: string; color: string | null }[] }) => {
      const source = id === "tagged-123" ? taggedProfile : plainProfile;
      return Promise.resolve({ ...source, tags: data.tags ?? [] });
    });

    const { result } = renderHook(() => useProfiles());
    await waitFor(() => expect(result.current.loading).toBe(false));
    mockApi.listProfiles.mockClear();
    mockApi.getProfileHealth.mockClear();

    let tagResult;
    await act(async () => {
      tagResult = await result.current.addTagsToProfiles(["tagged-123", "plain-123"], [
        { tag: "ops", color: "#6366f1" },
      ]);
    });

    expect(mockApi.updateProfile).toHaveBeenCalledWith("tagged-123", {
      tags: [
        { tag: "existing", color: "#22c55e" },
        { tag: "ops", color: "#6366f1" },
      ],
    });
    expect(mockApi.updateProfile).toHaveBeenCalledWith("plain-123", {
      tags: [{ tag: "ops", color: "#6366f1" }],
    });
    expect(mockApi.listProfiles).toHaveBeenCalledTimes(1);
    expect(mockApi.getProfileHealth).toHaveBeenCalledWith("tagged-123");
    expect(mockApi.getProfileHealth).toHaveBeenCalledWith("plain-123");
    expect(tagResult).toMatchObject({
      requestedCount: 2,
      taggedCount: 2,
      failedCount: 0,
      skippedUnchangedCount: 0,
    });
  });

  it("keeps existing tag color when a bulk tag already exists", async () => {
    const taggedProfile = {
      ...fakeProfile,
      id: "tagged-123",
      name: "Tagged",
      tags: [{ tag: "ops", color: "#22c55e" }],
    };
    mockApi.listProfiles.mockResolvedValue([taggedProfile]);
    mockApi.updateProfile.mockImplementation((id: string, data: { tags?: { tag: string; color: string | null }[] }) => {
      return Promise.resolve({ ...taggedProfile, tags: data.tags ?? [] });
    });

    const { result } = renderHook(() => useProfiles());
    await waitFor(() => expect(result.current.loading).toBe(false));
    mockApi.listProfiles.mockClear();
    mockApi.getProfileHealth.mockClear();

    let tagResult;
    await act(async () => {
      tagResult = await result.current.addTagsToProfiles(["tagged-123"], [
        { tag: "ops", color: "#6366f1" },
        { tag: "qa", color: "#0ea5e9" },
      ]);
    });

    expect(mockApi.updateProfile).toHaveBeenCalledWith("tagged-123", {
      tags: [
        { tag: "ops", color: "#22c55e" },
        { tag: "qa", color: "#0ea5e9" },
      ],
    });
    expect(tagResult).toMatchObject({
      requestedCount: 1,
      taggedCount: 1,
      failedCount: 0,
      skippedUnchangedCount: 0,
    });
  });

  it("skips selected profiles when bulk tags would not change them", async () => {
    const taggedProfile = {
      ...fakeProfile,
      id: "tagged-123",
      name: "Tagged",
      tags: [{ tag: "ops", color: "#22c55e" }],
    };
    mockApi.listProfiles.mockResolvedValue([taggedProfile]);

    const { result } = renderHook(() => useProfiles());
    await waitFor(() => expect(result.current.loading).toBe(false));
    mockApi.listProfiles.mockClear();

    let tagResult;
    await act(async () => {
      tagResult = await result.current.addTagsToProfiles(["tagged-123"], [
        { tag: " ops ", color: "#6366f1" },
      ]);
    });

    expect(mockApi.updateProfile).not.toHaveBeenCalled();
    expect(mockApi.listProfiles).not.toHaveBeenCalled();
    expect(tagResult).toMatchObject({
      requestedCount: 1,
      taggedCount: 0,
      failedCount: 0,
      skippedUnchangedCount: 1,
    });
  });

  it("reports selected profile ids that disappear before bulk tagging", async () => {
    mockApi.listProfiles.mockResolvedValue([fakeProfile]);

    const { result } = renderHook(() => useProfiles());
    await waitFor(() => expect(result.current.loading).toBe(false));
    mockApi.listProfiles.mockClear();

    let tagResult;
    await act(async () => {
      tagResult = await result.current.addTagsToProfiles(["missing-123"], [
        { tag: "ops", color: "#6366f1" },
      ]);
    });

    expect(mockApi.updateProfile).not.toHaveBeenCalled();
    expect(mockApi.listProfiles).not.toHaveBeenCalled();
    expect(tagResult).toMatchObject({
      requestedCount: 1,
      taggedCount: 0,
      failedCount: 1,
      skippedUnchangedCount: 0,
    });
    expect(result.current.error).toBe("Failed to tag 1 profile(s): Profile missing-123 is no longer available");
  });

  it("reports partial bulk tag failures while refreshing successful profiles", async () => {
    const taggedProfile = {
      ...fakeProfile,
      id: "tagged-123",
      name: "Tagged",
    };
    const failingProfile = {
      ...fakeProfile,
      id: "fail-123",
      name: "Failing",
    };
    mockApi.listProfiles.mockResolvedValue([taggedProfile, failingProfile]);
    mockApi.updateProfile.mockImplementation((id: string, data: { tags?: { tag: string; color: string | null }[] }) => {
      if (id === "tagged-123") return Promise.resolve({ ...taggedProfile, tags: data.tags ?? [] });
      return Promise.reject(new Error("Tag failed for proxy http://user:secret@proxy.example:8080"));
    });

    const { result } = renderHook(() => useProfiles());
    await waitFor(() => expect(result.current.loading).toBe(false));
    mockApi.listProfiles.mockClear();
    mockApi.getProfileHealth.mockClear();

    let tagResult;
    await act(async () => {
      tagResult = await result.current.addTagsToProfiles(["tagged-123", "fail-123"], [
        { tag: "ops", color: "#6366f1" },
      ]);
    });

    expect(mockApi.updateProfile).toHaveBeenCalledWith("tagged-123", {
      tags: [{ tag: "ops", color: "#6366f1" }],
    });
    expect(mockApi.updateProfile).toHaveBeenCalledWith("fail-123", {
      tags: [{ tag: "ops", color: "#6366f1" }],
    });
    expect(mockApi.listProfiles).toHaveBeenCalledTimes(1);
    expect(mockApi.getProfileHealth).toHaveBeenCalledTimes(1);
    expect(mockApi.getProfileHealth).toHaveBeenCalledWith("tagged-123");
    expect(tagResult).toMatchObject({
      requestedCount: 2,
      taggedCount: 1,
      failedCount: 1,
      skippedUnchangedCount: 0,
    });
    expect(result.current.error).toBe("Failed to tag 1 profile(s): Tag failed for proxy http://proxy.example:8080");
  });

  it("runs active health checks and writes successful results into the health cache", async () => {
    const checkedHealth = {
      ...fakeHealth,
      status: "warning" as const,
      checked_at: "2026-05-25T02:00:00Z",
      warnings: [{
        code: "geoip_stale" as const,
        message: "最近一次 GeoIP 检测结果已过期。",
        severity: "warning" as const,
        action: "重新运行健康检测刷新出口 IP 指纹。",
      }],
    };
    mockApi.checkProfileHealth.mockResolvedValueOnce(checkedHealth);

    const { result } = renderHook(() => useProfiles());
    await waitFor(() => expect(result.current.loading).toBe(false));

    let checkResult;
    await act(async () => {
      checkResult = await result.current.checkHealth(["abc-123", "abc-123"]);
    });

    expect(mockApi.checkProfileHealth).toHaveBeenCalledTimes(1);
    expect(mockApi.checkProfileHealth).toHaveBeenCalledWith("abc-123");
    expect(result.current.healthByProfileId["abc-123"]).toEqual(checkedHealth);
    expect(checkResult).toEqual({
      requestedCount: 1,
      checkedCount: 1,
      failedCount: 0,
    });
  });

  it("keeps successful bulk health results when another check fails", async () => {
    const checkedHealth = {
      ...fakeHealth,
      status: "warning" as const,
      checked_at: "2026-05-25T02:00:00Z",
    };
    mockApi.checkProfileHealth.mockImplementation((id: string) => {
      if (id === "abc-123") return Promise.resolve(checkedHealth);
      return Promise.reject(new Error("Network error"));
    });

    const { result } = renderHook(() => useProfiles());
    await waitFor(() => expect(result.current.loading).toBe(false));

    let checkResult;
    await act(async () => {
      checkResult = await result.current.checkHealth(["abc-123", "missing"]);
    });

    expect(mockApi.checkProfileHealth).toHaveBeenCalledTimes(2);
    expect(result.current.healthByProfileId["abc-123"]).toEqual(checkedHealth);
    expect(result.current.error).toBe("Failed to check health for 1 profile(s)");
    expect(checkResult).toEqual({
      requestedCount: 2,
      checkedCount: 1,
      failedCount: 1,
    });
  });
});
