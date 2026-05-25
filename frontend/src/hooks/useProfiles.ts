import { useCallback, useEffect, useState } from "react";
import {
  api,
  type Profile,
  type ProfileCreateData,
  type ProfileHealthResponse,
} from "../lib/api";

export function useProfiles() {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [healthByProfileId, setHealthByProfileId] = useState<
    Record<string, ProfileHealthResponse | undefined>
  >({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

  const refresh = useCallback(async (): Promise<Profile[] | undefined> => {
    try {
      const data = await api.listProfiles();
      setProfiles(data);
      setError(null);
      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch profiles");
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
        return profile;
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to create profile");
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
        return profile;
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to update profile");
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
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to delete profile");
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
        return result;
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to launch profile");
      }
    },
    [refresh, refreshHealth],
  );

  const stop = useCallback(
    async (id: string) => {
      try {
        await api.stopProfile(id);
        await refresh();
        await refreshHealth([id]);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to stop profile");
      }
    },
    [refresh, refreshHealth],
  );

  return {
    profiles,
    healthByProfileId,
    loading,
    error,
    refresh,
    refreshHealth,
    create,
    update,
    remove,
    launch,
    stop,
  };
}
