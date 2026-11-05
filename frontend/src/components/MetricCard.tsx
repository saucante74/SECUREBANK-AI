interface MetricCardProps {
  description: string;
  details?: string[];
  direction: string;
  progress?: number | null;
  name: string;
  unit?: string;
  value: string;
}

export function MetricCard({
  description,
  details,
  direction,
  progress,
  name,
  unit,
  value,
}: MetricCardProps) {
  const normalizedProgress = progress === undefined || progress === null
    ? undefined
    : Math.min(Math.max(progress, 0), 1);
  const circumference = 2 * Math.PI * 36;
  const offset = normalizedProgress === undefined
    ? circumference
    : circumference * (1 - normalizedProgress);

  return (
    <article className="flex min-h-44 items-center gap-5 rounded-3xl border border-border bg-white p-5 shadow-soft sm:p-6">
      {progress !== undefined ? (
        <div
          className="relative size-24 shrink-0"
          role="img"
          aria-label={`${name}: ${value}${unit ?? ""}`}
        >
          <svg className="size-full -rotate-90" viewBox="0 0 88 88" aria-hidden="true">
            <circle cx="44" cy="44" r="36" fill="none" stroke="currentColor" strokeWidth="8" className="text-surface" />
            <circle
              cx="44"
              cy="44"
              r="36"
              fill="none"
              stroke="currentColor"
              strokeLinecap="round"
              strokeWidth="8"
              strokeDasharray={circumference}
              strokeDashoffset={offset}
              className={normalizedProgress === undefined ? "text-border" : "text-accent-strong"}
            />
          </svg>
          <p className="absolute inset-0 flex items-center justify-center font-display text-lg font-extrabold text-brand-navy">
            {value}{unit}
          </p>
        </div>
      ) : (
        <div className="flex min-w-24 shrink-0 items-baseline justify-center rounded-2xl bg-surface px-3 py-5 text-brand-navy">
          <span className="font-display text-2xl font-extrabold">{value}</span>
          {unit && <span className="ml-1 text-sm font-semibold text-muted">{unit}</span>}
        </div>
      )}
      <div className="min-w-0 self-stretch py-1">
        <h3 className="font-display text-base font-bold text-brand-navy">{name}</h3>
        <p className="mt-2 text-sm leading-5 text-muted">{description}</p>
        {details && (
          <div className="mt-3 space-y-1 text-xs font-semibold text-muted">
            {details.map((detail) => <p key={detail}>{detail}</p>)}
          </div>
        )}
        <p className="mt-3 text-xs font-semibold text-accent-strong">{direction}</p>
      </div>
    </article>
  );
}
