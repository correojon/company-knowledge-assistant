import { cn } from "cn"

import { useHealth, type BackendHealth } from "@/hooks/useHealth"

const LABELS: Record<BackendHealth["status"], string> = {
  checking: "Backend: checking…",
  healthy: "Backend: healthy",
  unreachable: "Backend: unreachable",
}

const DOT_COLORS: Record<BackendHealth["status"], string> = {
  checking: "bg-muted-foreground",
  healthy: "bg-emerald-500",
  unreachable: "bg-destructive",
}

/** Live backend status, refreshed by polling ``GET /api/health``. */
export function HealthBadge() {
  const { status } = useHealth()

  return (
    <div role="status" aria-live="polite" className="flex items-center gap-2 text-sm">
      <span
        aria-hidden="true"
        className={cn("size-2 rounded-full", DOT_COLORS[status])}
      />
      <span>{LABELS[status]}</span>
    </div>
  )
}
