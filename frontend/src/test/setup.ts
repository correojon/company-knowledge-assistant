// Adds DOM matchers such as toBeInTheDocument() to Vitest's expect.
import "@testing-library/jest-dom/vitest"
import { cleanup } from "@testing-library/react"
import { afterEach } from "vitest"

// Testing Library unmounts after each test only when Vitest globals are on; they are off.
afterEach(() => {
  cleanup()
})
