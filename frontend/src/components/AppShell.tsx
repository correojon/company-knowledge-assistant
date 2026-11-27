import { FileText, MessageSquare, Search, type LucideIcon } from "lucide-react"
import { useState } from "react"

import { HealthBadge } from "@/components/HealthBadge"
import { Placeholder } from "@/components/Placeholder"
import { Button } from "@/components/ui/button"

type Section = "Documents" | "Search" | "Chat"

const SECTIONS: { name: Section; icon: LucideIcon }[] = [
  { name: "Documents", icon: FileText },
  { name: "Search", icon: Search },
  { name: "Chat", icon: MessageSquare },
]

/** Sidebar navigation and the selected section. State only: no router yet. */
export function AppShell() {
  const [current, setCurrent] = useState<Section>("Documents")

  return (
    <div className="flex min-h-svh">
      <aside className="flex w-56 shrink-0 flex-col gap-6 border-r bg-muted/30 p-4">
        <p className="px-2 text-sm font-semibold">Knowledge Assistant</p>
        <nav aria-label="Main" className="flex flex-col gap-1">
          {SECTIONS.map(({ name, icon: Icon }) => (
            <Button
              key={name}
              variant={current === name ? "secondary" : "ghost"}
              className="justify-start"
              aria-current={current === name ? "page" : undefined}
              onClick={() => setCurrent(name)}
            >
              <Icon aria-hidden="true" />
              {name}
            </Button>
          ))}
        </nav>
        <div className="mt-auto px-2">
          <HealthBadge />
        </div>
      </aside>
      <main className="flex-1 p-8">
        <Placeholder title={current} />
      </main>
    </div>
  )
}
