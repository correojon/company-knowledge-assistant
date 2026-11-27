import type { components } from "./schema"

export type HealthReport = components["schemas"]["HealthReport"]

// With the 5 s poll, a hanging request still shows "unreachable" within 10 s (R9).
export const HEALTH_TIMEOUT_MS = 4000

/** Fetch the backend health report; rejects on network error, timeout, non-2xx or bad JSON. */
export async function getHealth(signal?: AbortSignal): Promise<HealthReport> {
  const controller = new AbortController()
  const timer = setTimeout(
    () => controller.abort(new DOMException("Health check timed out", "TimeoutError")),
    HEALTH_TIMEOUT_MS,
  )
  const forwardAbort = () => controller.abort(signal?.reason)
  if (signal?.aborted) forwardAbort()
  signal?.addEventListener("abort", forwardAbort)

  try {
    const response = await fetch("/api/health", { signal: controller.signal })
    if (!response.ok) {
      throw new Error(`Health check failed with HTTP ${response.status}`)
    }
    return (await response.json()) as HealthReport
  } finally {
    clearTimeout(timer)
    signal?.removeEventListener("abort", forwardAbort)
  }
}
