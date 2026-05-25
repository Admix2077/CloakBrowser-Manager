import { useCallback, useEffect, useState } from "react";
import {
  api,
  type Profile,
  type ProfileCreateData,
  type ProfileHealthResponse,
} from "../lib/api";
import { redactUrlCredentials } from "../lib/profileDisplay";

const HEALTH_CHECK_CONCURRENCY = 6;
const BULK_LAUNCH_CONCURRENCY = 2;
const BULK_STOP_CONCURRENCY = 2;

export interface BulkLaunchResult {
  requestedCount: number;
  launchableCount: number;
  launchedCount: number;
  skippedRunningCount: number;
  failedCount: number;
}

export interface BulkStopResult {
  requestedCount: number;
  stoppableCount: number;
  stoppedCount: number;
  skippedStoppedCount: number;
  failedCount: number;
}

export function useProfiles() {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [healthByProfileId, setHealthByProfileId] = useState<
    Record<string, ProfileHealthResponse | undefined>
  >({});
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [operationError, setOperationError] = useState<string | null>(null);
  const error = operationError ?? fetchError;

  const refreshHealth = useCallback(
    async (profileIds: string[], options: { prune?: boolean } = {}) => {
      const ids = [...new Set(profileIds.filter(Boolean))];
      if (ids.length === 0) {
        if (options.prune) setHealthByProfileId({});
        return;
      }

      const results = await Promise.allSettled(
        ids.map(async (id) => [id, await api.getProfileHealth(id)] as const),
      );

      setHealthByProfileId((prev) => {
        const next: Record<string, ProfileHealthResponse | undefined> = options.prune
          ? {}
          : { ...prev };

        ids.forEach((id) => {
          if (!(id in next)) next[id] = prev[id];
        });
        results.forEach((result) => {
          if (result.status === "fulfilled") {
            const [id, health] = result.value;
            next[id] = health;
          }
        });
        return next;
      });
    },
    [],
  );

  const checkHealth = useCallback(async (profileIds: string[]) => {
    const ids = [...new Set(profileIds.filter(Boolean))];
    if (ids.length === 0) return;

    const successfulResults: [string, ProfileHealthResponse][] = [];
    let failedCount = 0;
    let cursor = 0;
    const workerCount = Math.min(HEALTH_CHECK_CONCURRENCY, ids.length);

    await Promise.all(
      Array.from({ length: workerCount }, async () => {
        while (cursor < ids.length) {
          const id = ids[cursor];
          cursor += 1;
          if (!id) continue;
          try {
            successfulResults.push([id, await api.checkProfileHealth(id)]);
          } catch {
            failedCount += 1;
          }
        }
      }),
    );

    if (successfulResults.length > 0) {
      setHealthByProfileId((prev) => {
        const next = { ...prev };
        successfulResults.forEach(([id, health]) => {
          next[id] = health;
        });
        return next;
      });
    }

    if (failedCount > 0) {
      setOperationError(`Failed to check health for ${failedCount} profile(s)`);
    } else {
      setOperationError(null);
    }
  }, []);

  const refresh = useCallback(async (): Promise<Profile[] | undefined> => {
    try {
      const data = await api.listProfiles();
      setProfiles(data);
      setFetchError(null);
      return data;
    } catch (err) {
      setFetchError(err instanceof Error ? err.message : "Failed to fetch profiles");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    // Poll for status changes every 3 seconds
    const interval = setInterval(refresh, 3000);
    return () => clearInterval(interval);
  }, [refresh]);

  const profileIdsKey = profiles.map((profile) => profile.id).sort().join("|");

  useEffect(() => {
    void refreshHealth(profileIdsKey ? profileIdsKey.split("|") : [], { prune: true });
  }, [profileIdsKey, refreshHealth]);

  const create = useCallback(
    async (data: ProfileCreateData): Promise<Profile | undefined> => {
      try {
        const profile = await api.createProfile(data);
        setProfiles((prev) => [profile, ...prev]);
        await refreshHealth([profile.id]);
        setOperationError(null);
        return profile;
      } catch (err) {
        setOperationError(err instanceof Error ? err.message : "Failed to create profile");
      }
    },
    [refreshHealth],
  );

  const update = useCallback(
    async (id: string, data: Partial<ProfileCreateData>) => {
      try {
        const profile = await api.updateProfile(id, data);
        setProfiles((prev) => prev.map((p) => (p.id === id ? profile : p)));
        await refreshHealth([id]);
        setOperationError(null);
        return profile;
      } catch (err) {
        setOperationError(err instanceof Error ? err.message : "Failed to update profile");
      }
    },
    [refreshHealth],
  );

  const remove = useCallback(
    async (id: string) => {
      try {
        await api.deleteProfile(id);
        setProfiles((prev) => prev.filter((p) => p.id !== id));
        setHealthByProfileId((prev) => {
          const next = { ...prev };
          delete next[id];
          return next;
        });
        setOperationError(null);
      } catch (err) {
        setOperationError(err instanceof Error ? err.message : "Failed to delete profile");
      }
    },
    [],
  );

  const launch = useCallback(
    async (id: string) => {
      try {
        const result = await api.launchProfile(id);
        await refresh();
        await refreshHealth([id]);
        setOperationError(null);
        return result;
      } catch (err) {
        setOperationError(err instanceof Error ? err.message : "Failed to launch profile");
      }
    },
    [refresh, refreshHealth],
  );

  const launchProfiles = useCallback(
    async (profileIds: string[]): Promise<BulkLaunchResult> => {
      const ids = [...new Set(profileIds.filter(Boolean))];
      const profileById = new Map(profiles.map((profile) => [profile.id, profile]));
      const launchableIds = ids.filter((id) => profileById.get(id)?.status === "stopped");
      const skippedRunningCount = ids.filter((id) => profileById.get(id)?.status === "running").length;
      const successfulIds: string[] = [];
      const failureMessages: string[] = [];
      let failedCount = 0;
      let cursor = 0;

      const result: BulkLaunchResult = {
        requestedCount: ids.length,
        launchableCount: launchableIds.length,
        launchedCount: 0,
        skippedRunningCount,
        failedCount: 0,
      };

      if (launchableIds.length === 0) {
        setOperationError(null);
        return result;
      }

      const workerCount = Math.min(BULK_LAUNCH_CONCURRENCY, launchableIds.length);
      await Promise.all(
        Array.from({ length: workerCount }, async () => {
          while (cursor < launchableIds.length) {
            const id = launchableIds[cursor];
            cursor += 1;
            if (!id) continue;
            try {
              await api.launchProfile(id);
              successfulIds.push(id);
            } catch (err) {
              failedCount += 1;
              failureMessages.push(err instanceof Error ? err.message : "Failed to launch profile");
            }
          }
        }),
      );

      await refresh();
      if (successfulIds.length > 0) {
        await refreshHealth(successfulIds);
      }

      result.launchedCount = successfulIds.length;
      result.failedCount = failedCount;

      if (failedCount > 0) {
        const uniqueReasons = [...new Set(failureMessages.map(redactUrlCredentials).filter(Boolean))].slice(0, 2);
        const reasonSummary = uniqueReasons.length > 0 ? `: ${uniqueReasons.join("; ")}` : "";
        setOperationError(`Failed to launch ${failedCount} profile(s)${reasonSummary}`);
      } else {
        setOperationError(null);
      }

      return result;
    },
    [profiles, refresh, refreshHealth],
  );

  const stop = useCallback(
    async (id: string) => {
      try {
        await api.stopProfile(id);
        await refresh();
        await refreshHealth([id]);
        setOperationError(null);
      } catch (err) {
        setOperationError(err instanceof Error ? err.message : "Failed to stop profile");
      }
    },
    [refresh, refreshHealth],
  );

  const stopProfiles = useCallback(
    async (profileIds: string[]): Promise<BulkStopResult> => {
      const ids = [...new Set(profileIds.filter(Boolean))];
      const profileById = new Map(profiles.map((profile) => [profile.id, profile]));
      const stoppableIds = ids.filter((id) => profileById.get(id)?.status === "running");
      const skippedStoppedCount = ids.filter((id) => profileById.get(id)?.status === "stopped").length;
      const successfulIds: string[] = [];
      const failureMessages: string[] = [];
      let failedCount = 0;
      let cursor = 0;

      const result: BulkStopResult = {
        requestedCount: ids.length,
        stoppableCount: stoppableIds.length,
        stoppedCount: 0,
        skippedStoppedCount,
        failedCount: 0,
      };

      if (stoppableIds.length === 0) {
        setOperationError(null);
        return result;
      }

      const workerCount = Math.min(BULK_STOP_CONCURRENCY, stoppableIds.length);
      await Promise.all(
        Array.from({ length: workerCount }, async () => {
          while (cursor < stoppableIds.length) {
            const id = stoppableIds[cursor];
            cursor += 1;
            if (!id) continue;
            try {
              await api.stopProfile(id);
              successfulIds.push(id);
            } catch (err) {
              failedCount += 1;
              failureMessages.push(err instanceof Error ? err.message : "Failed to stop profile");
            }
          }
        }),
      );

      await refresh();
      if (successfulIds.length > 0) {
        await refreshHealth(successfulIds);
      }

      result.stoppedCount = successfulIds.length;
      result.failedCount = failedCount;

      if (failedCount > 0) {
        const uniqueReasons = [...new Set(failureMessages.map(redactUrlCredentials).filter(Boolean))].slice(0, 2);
        const reasonSummary = uniqueReasons.length > 0 ? `: ${uniqueReasons.join("; ")}` : "";
        setOperationError(`Failed to stop ${failedCount} profile(s)${reasonSummary}`);
      } else {
        setOperationError(null);
      }

      return result;
    },
    [profiles, refresh, refreshHealth],
  );

  return {
    profiles,
    healthByProfileId,
    loading,
    error,
    refresh,
    refreshHealth,
    checkHealth,
    create,
    update,
    remove,
    launch,
    launchProfiles,
    stop,
    stopProfiles,
  };
}
