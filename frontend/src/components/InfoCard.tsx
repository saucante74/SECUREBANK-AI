interface InfoCardProps {
  description: string;
  eyebrow: string;
  title: string;
}

export function InfoCard({ description, eyebrow, title }: InfoCardProps) {
  return (
    <article className="rounded-3xl border border-border bg-white p-6 shadow-soft sm:p-7">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-accent-strong">
        {eyebrow}
      </p>
      <h2 className="mt-3 text-xl font-bold text-ink">{title}</h2>
      <p className="mt-3 leading-7 text-muted">{description}</p>
    </article>
  );
}
