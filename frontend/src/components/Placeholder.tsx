/** Stand-in for a section that a later feature builds. */
export function Placeholder({ title }: { title: string }) {
  return (
    <section className="flex flex-col gap-2">
      <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
      <p className="text-muted-foreground">{title} is not available yet.</p>
    </section>
  )
}
