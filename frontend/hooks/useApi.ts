"use client";

import { useCallback, useEffect, useState } from "react";

import { getStoredAuthToken } from "@/services/auth";

const API_BASE = process.env.NEXT_PUBLIC_INSIGHT_API_BASE ?? "http://127.0.0.1:8013";

type ApiResult<T> = { data: T | null; loading: boolean; error: string | null; refetch: () => Promise<void>; get: (path: string) => Promise<{ data: unknown }> };

export function useApi<T = unknown>(path?: string | null): ApiResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(Boolean(path));
  const [error, setError] = useState<string | null>(null);

  const get = useCallback(async (requestPath: string) => {
    const token = getStoredAuthToken();
    const response = await fetch(`${API_BASE}${requestPath}`, { headers: token ? { Authorization: `Bearer ${token}` } : undefined, cache: 'no-store' });
    if (!response.ok) throw new Error(await response.text() || `Request failed with ${response.status}`);
    return { data: await response.json() };
  }, []);

  const refetch = useCallback(async () => {
    if (!path) { setLoading(false); setData(null); setError(null); return; }
    setLoading(true); setError(null);
    try {
      const result = await get(path);
      setData(result.data as T);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [get, path]);

  useEffect(() => { void refetch(); }, [refetch]);
  return { data, loading, error, refetch, get };
}
