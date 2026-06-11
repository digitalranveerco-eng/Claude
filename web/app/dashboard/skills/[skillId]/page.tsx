// Server Component: reads the deep-routing params (?section=<uuid>), fetches the
// skill + the caller's progress, and renders the static body plus the client-side
// interactive island.

import { SectionRenderer } from './section-renderer';
import { InteractiveModule } from './interactive-module';
import { api } from '@/lib/api';

export default async function SkillPage({
  params,
  searchParams,
}: {
  params: { skillId: string };
  searchParams: { section?: string; tab?: string };
}) {
  const sectionId = searchParams.section ?? null;
  const [skill, progress] = await Promise.all([
    api.skills.get(params.skillId),
    api.progress.forSkill(params.skillId),
  ]);

  const active = sectionId
    ? skill.sections.find((s) => s.id === sectionId)
    : skill.sections[0];

  if (!active) return <p className="p-8">Section not found.</p>;

  return (
    <div className="flex gap-8 p-8">
      <aside className="w-64 shrink-0">
        <nav className="space-y-1">
          {skill.sections.map((s) => (
            <a
              key={s.id}
              href={`?section=${s.id}`}
              className={s.id === active.id ? 'font-semibold' : 'text-muted-foreground'}
            >
              {s.title}
              {progress[s.id]?.status === 'COMPLETED' ? ' ✓' : ''}
            </a>
          ))}
        </nav>
      </aside>

      <main className="min-w-0 flex-1">
        <SectionRenderer section={active} />
        {active.kind === 'INTERACTIVE' && (
          <InteractiveModule sectionId={active.id} skillId={params.skillId} />
        )}
      </main>
    </div>
  );
}
