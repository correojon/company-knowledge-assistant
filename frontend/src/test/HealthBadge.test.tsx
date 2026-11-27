import { act, render, screen } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import type { HealthReport } from "@/api/client"
import { HealthBadge } from "@/components/HealthBadge"
import { HEALTH_POLL_MS } from "@/hooks/useHealth"

const report: HealthReport = {
  status: "ok",
  version: "0.1.0",
  database: {
    status: "ok",
    schema_revision: "0001",
    vector_search: "ok",
    vector_search_version: "v0.1.9",
  },
  llm: {
    provider: "fake",
    model: "fake-model",
    status: "available",
    reason: null,
    checked_at: "2026-11-27T10:00:00Z",
  },
}

const fetchMock = vi.fn<typeof fetch>()

/** A fetch that never settles unless its signal aborts. */
function hangingFetch(_input: RequestInfo | URL, init?: RequestInit) {
  return new Promise<Response>((_resolve, reject) => {
    init?.signal?.addEventListener("abort", () => reject(init.signal?.reason))
  })
}

async function advance(ms: number) {
  await act(() => vi.advanceTimersByTimeAsync(ms))
}

beforeEach(() => {
  vi.useFakeTimers()
  fetchMock.mockReset()
  vi.stubGlobal("fetch", fetchMock)
})

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

describe("HealthBadge", () => {
  it("shows checking before the first response", () => {
    fetchMock.mockImplementation(hangingFetch)

    render(<HealthBadge />)

    expect(screen.getByText("Backend: checking…")).toBeInTheDocument()
  })

  it("shows healthy on an ok response", async () => {
    fetchMock.mockResolvedValue(Response.json(report))

    render(<HealthBadge />)
    await advance(0)

    expect(screen.getByText("Backend: healthy")).toBeInTheDocument()
  })

  it("shows unreachable when fetch rejects", async () => {
    fetchMock.mockRejectedValue(new TypeError("Failed to fetch"))

    render(<HealthBadge />)
    await advance(0)

    expect(screen.getByText("Backend: unreachable")).toBeInTheDocument()
  })

  it("shows unreachable on a 500 response", async () => {
    fetchMock.mockResolvedValue(new Response("boom", { status: 500 }))

    render(<HealthBadge />)
    await advance(0)

    expect(screen.getByText("Backend: unreachable")).toBeInTheDocument()
  })

  it("shows unreachable within 10 s when the request hangs", async () => {
    fetchMock.mockImplementation(hangingFetch)

    render(<HealthBadge />)
    await advance(10_000)

    expect(screen.getByText("Backend: unreachable")).toBeInTheDocument()
  })

  it("turns unreachable after a healthy backend goes down", async () => {
    fetchMock.mockResolvedValueOnce(Response.json(report))
    fetchMock.mockImplementation(hangingFetch)

    render(<HealthBadge />)
    await advance(0)
    expect(screen.getByText("Backend: healthy")).toBeInTheDocument()
    await advance(10_000)

    expect(screen.getByText("Backend: unreachable")).toBeInTheDocument()
  })

  it("shows healthy again on the next poll after recovery", async () => {
    fetchMock.mockRejectedValueOnce(new TypeError("Failed to fetch"))
    fetchMock.mockImplementation(() => Promise.resolve(Response.json(report)))

    render(<HealthBadge />)
    await advance(0)
    expect(screen.getByText("Backend: unreachable")).toBeInTheDocument()
    await advance(HEALTH_POLL_MS)

    expect(screen.getByText("Backend: healthy")).toBeInTheDocument()
  })

  it("polls every 5 s without overlapping requests", async () => {
    let inFlight = 0
    let maxInFlight = 0
    fetchMock.mockImplementation((input, init) => {
      inFlight += 1
      maxInFlight = Math.max(maxInFlight, inFlight)
      return hangingFetch(input, init).finally(() => {
        inFlight -= 1
      })
    })

    render(<HealthBadge />)
    await advance(3 * HEALTH_POLL_MS)

    expect(HEALTH_POLL_MS).toBe(5000)
    expect(fetchMock).toHaveBeenCalledTimes(4)
    expect(maxInFlight).toBe(1)
  })

  it("stops polling on unmount", async () => {
    fetchMock.mockImplementation(() => Promise.resolve(Response.json(report)))

    const { unmount } = render(<HealthBadge />)
    await advance(0)
    unmount()
    const calls = fetchMock.mock.calls.length
    await advance(3 * HEALTH_POLL_MS)

    expect(fetchMock).toHaveBeenCalledTimes(calls)
  })

  it("aborts the request in flight on unmount", async () => {
    fetchMock.mockImplementation(hangingFetch)

    const { unmount } = render(<HealthBadge />)
    unmount()

    const signal = fetchMock.mock.calls[0][1]?.signal
    expect(signal?.aborted).toBe(true)
  })
})
