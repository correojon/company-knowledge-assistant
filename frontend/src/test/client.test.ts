import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { getHealth, HEALTH_TIMEOUT_MS, type HealthReport } from "@/api/client"

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

beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal("fetch", fetchMock)
})

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

describe("getHealth", () => {
  it("resolves to the parsed body on 200", async () => {
    fetchMock.mockResolvedValue(Response.json(report))

    await expect(getHealth()).resolves.toEqual(report)
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/health",
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    )
  })

  it("rejects on a non-2xx status", async () => {
    fetchMock.mockResolvedValue(Response.json(report, { status: 503 }))

    await expect(getHealth()).rejects.toThrow("503")
  })

  it("rejects when fetch rejects", async () => {
    fetchMock.mockRejectedValue(new TypeError("Failed to fetch"))

    await expect(getHealth()).rejects.toThrow("Failed to fetch")
  })

  it("rejects on invalid JSON", async () => {
    fetchMock.mockResolvedValue(new Response("not json", { status: 200 }))

    await expect(getHealth()).rejects.toThrow()
  })

  it("aborts and rejects after the timeout when fetch never settles", async () => {
    vi.useFakeTimers()
    let seenSignal: AbortSignal | undefined
    fetchMock.mockImplementation(
      (_input, init) =>
        new Promise<Response>((_resolve, reject) => {
          seenSignal = init?.signal ?? undefined
          seenSignal?.addEventListener("abort", () => reject(seenSignal?.reason))
        }),
    )

    const result = getHealth()
    const settled = expect(result).rejects.toThrow()
    await vi.advanceTimersByTimeAsync(HEALTH_TIMEOUT_MS - 1)
    expect(seenSignal?.aborted).toBe(false)
    await vi.advanceTimersByTimeAsync(1)

    await settled
    expect(seenSignal?.aborted).toBe(true)
    expect(HEALTH_TIMEOUT_MS).toBe(4000)
  })

  it("aborts when the caller's signal aborts", async () => {
    fetchMock.mockImplementation(
      (_input, init) =>
        new Promise<Response>((_resolve, reject) => {
          init?.signal?.addEventListener("abort", () => reject(init.signal?.reason))
        }),
    )
    const caller = new AbortController()

    const result = getHealth(caller.signal)
    caller.abort()

    await expect(result).rejects.toThrow()
  })
})
