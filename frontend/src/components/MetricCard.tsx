interface MetricCardProps {
  description: string;
  details?: string[];
  direction: string;
  name: string;
  unit?: string;
  value: string;
}

export function MetricCard({
  description,
  details,
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
      {details && (
        <div className="mt-4 space-y-1 text-xs font-semibold text-muted">
          {details.map((detail) => <p key={detail}>{detail}</p>)}
        </div>
      )}
      <p className="mt-auto pt-4 text-xs font-semibold text-accent-strong">
        {direction}
      </p>
    </article>
  );
}
