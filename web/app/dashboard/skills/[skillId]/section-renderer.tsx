// Renders a section's static markdown body. Swap the naive renderer for your
// markdown pipeline of choice (e.g. react-markdown + remark-gfm).

export function SectionRenderer({
  section,
}: {
  section: { title: string; body?: string | null };
}) {
  return (
    <article className="prose max-w-none">
      <h1>{section.title}</h1>
      {section.body ? (
        <div className="whitespace-pre-wrap">{section.body}</div>
      ) : (
        <p className="text-muted-foreground">No content yet.</p>
      )}
    </article>
  );
}
