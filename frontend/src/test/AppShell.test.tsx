import { fireEvent, render, screen, within } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import App from "@/App"

const SECTIONS = ["Documents", "Search", "Chat"]

beforeEach(() => {
  // Never settles: the shell must not depend on the backend answering.
  vi.stubGlobal(
    "fetch",
    vi.fn(() => new Promise<Response>(() => {})),
  )
})

afterEach(() => {
  vi.unstubAllGlobals()
})

function navigation() {
  return within(screen.getByRole("navigation"))
}

describe("AppShell", () => {
  it("shows the Documents, Search and Chat entries", () => {
    render(<App />)

    const entries = navigation().getAllByRole("button")
    expect(entries.map((entry) => entry.textContent)).toEqual(SECTIONS)
  })

  it("selects Documents by default", () => {
    render(<App />)

    expect(navigation().getByRole("button", { name: "Documents" })).toHaveAttribute(
      "aria-current",
      "page",
    )
    expect(screen.getByRole("heading", { level: 1, name: "Documents" })).toBeVisible()
  })

  it.each(SECTIONS)("shows the %s placeholder when its entry is clicked", (name) => {
    render(<App />)

    fireEvent.click(navigation().getByRole("button", { name }))

    expect(screen.getByRole("heading", { level: 1, name })).toBeVisible()
    expect(screen.getByText(/not available yet/)).toBeVisible()
    expect(navigation().getByRole("button", { name })).toHaveAttribute(
      "aria-current",
      "page",
    )
    for (const other of SECTIONS.filter((section) => section !== name)) {
      expect(navigation().getByRole("button", { name: other })).not.toHaveAttribute(
        "aria-current",
      )
    }
  })

  it("renders the health badge", () => {
    render(<App />)

    expect(screen.getByText("Backend: checking…")).toBeInTheDocument()
  })
})
