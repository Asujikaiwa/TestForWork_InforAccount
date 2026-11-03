"use client";

import { useEffect, useState } from "react";

type State<T> = { scope: string; version: number; data?: T; error?: unknown };

/**
 * Minimal data-fetching hook.
 *
 * - `scope` identifies *what* is loaded (e.g. "alice|group-1"). When it
 *   changes, old data is hidden immediately so we never show group 1's
 *   balances under group 2's name.
 * - `version` is bumped to refetch the same scope (after a create/delete);
 *   the previous data stays on screen until the fresh data arrives.
 * - Requests are aborted when the scope changes, so a slow old response can
 *   never overwrite a newer one.
 * - Pass `scope = null` to skip fetching.
 *
 * `fetcher` must be stable (wrap it in useCallback).
 */
export function useApi<T>(
  scope: string | null,
  version: number,
  fetcher: (signal: AbortSignal) => Promise<T>,
) {
  const [state, setState] = useState<State<T> | null>(null);

  useEffect(() => {
    if (scope === null) return;
    const controller = new AbortController();
    fetcher(controller.signal).then(
      (data) => setState({ scope, version, data }),
      (error: unknown) => {
        if (!controller.signal.aborted) setState({ scope, version, error });
      },
    );
    return () => controller.abort();
  }, [scope, version, fetcher]);

  const sameScope = scope !== null && state?.scope === scope;
  return {
    data: sameScope ? state.data : undefined,
    error: sameScope && state.version === version ? state.error : undefined,
    loading: scope !== null && (!sameScope || state.version !== version),
  };
}
