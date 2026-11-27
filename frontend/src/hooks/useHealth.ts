import { useEffect, useState } from "react"

import { getHealth, type HealthReport } from "@/api/client"

// With the 4 s request timeout, an outage shows within 10 s (R9).
export const HEALTH_POLL_MS = 5000

export type BackendHealth =
  | { status: "checking" }
  | { status: "healthy"; report: HealthReport }
  | { status: "unreachable" }

/** Poll the backend every 5 s, one request at a time, until unmount. */
export function useHealth(): BackendHealth {
  const [health, setHealth] = useState<BackendHealth>({ status: "checking" })

  useEffect(() => {
    const controller = new AbortController()
    let timer: ReturnType<typeof setTimeout> | undefined

    async function poll() {
      const startedAt = Date.now()
      try {
        const report = await getHealth(controller.signal)
        if (controller.signal.aborted) return
        setHealth(
          report.status === "ok"
            ? { status: "healthy", report }
            : { status: "unreachable" },
        )
      } catch {
        if (controller.signal.aborted) return
        setHealth({ status: "unreachable" })
      }
      // The next request starts only after this one settled, keeping a 5 s cadence.
      const wait = Math.max(0, HEALTH_POLL_MS - (Date.now() - startedAt))
      timer = setTimeout(poll, wait)
    }

    void poll()
    return () => {
      controller.abort()
      clearTimeout(timer)
    }
  }, [])

  return health
}
