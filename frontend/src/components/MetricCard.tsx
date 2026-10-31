interface MetricCardProps {
  description: string;
  direction: string;
  name: string;
  unit?: string;
  value: string;
}

export function MetricCard({
  description,
  direction,
  name,
  unit,
  value,
}: MetricCardProps) {
  return (
    <article className="flex min-h-52 flex-col rounded-2xl border border-border bg-white p-5 shadow-soft">
      <h3 className="text-sm font-bold text-brand-navy">{name}</h3>
      <p className="mt-4 text-3xl font-extrabold tracking-tight text-brand-navy">
        {value}
        {unit && <span className="ml-1 text-base font-semibold text-muted">{unit}</span>}
      </p>
      <p className="mt-4 text-sm leading-5 text-muted">{description}</p>
      <p className="mt-auto pt-4 text-xs font-semibold text-accent-strong">
        {direction}
      </p>
    </article>
  );
}
