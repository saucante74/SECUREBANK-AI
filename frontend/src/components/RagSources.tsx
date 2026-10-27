import type { RagCitation, RagSource } from "../api/types";

interface RagSourcesProps {
  citations: RagCitation[];
  sources: RagSource[];
}

function matchingSourceIndex(
  citation: RagCitation,
  sources: RagSource[],
): number {
  return sources.findIndex(
    (source) =>
      source.document_id === citation.document_id &&
      source.id === citation.chunk_id,
  );
}

export function RagSources({ citations, sources }: RagSourcesProps) {
  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(16rem,0.55fr)]">
      <section aria-labelledby="sources-title">
        <h3 id="sources-title" className="text-lg font-semibold text-brand-navy">
          Sources
        </h3>
        {sources.length === 0 ? (
          <p className="mt-3 text-sm text-muted">Aucune source disponible.</p>
        ) : (
          <ol className="mt-4 space-y-4">
            {sources.map((source, index) => (
              <li
                id={`rag-source-${String(index + 1)}`}
                key={`${source.document_id}-${source.id}`}
                className="rounded-xl border border-border bg-surface p-4"
              >
                <p className="text-sm font-semibold text-brand-navy">
                  {source.title}
                </p>
                <p className="mt-1 break-all text-xs font-medium text-muted">
                  {source.source}
                </p>
                <p className="mt-3 line-clamp-4 whitespace-pre-wrap text-sm leading-6 text-ink">
                  {source.content}
                </p>
              </li>
            ))}
          </ol>
        )}
      </section>

      <section aria-labelledby="citations-title">
        <h3 id="citations-title" className="text-lg font-semibold text-brand-navy">
          Citations
        </h3>
        {citations.length === 0 ? (
          <p className="mt-3 text-sm text-muted">Aucune citation disponible.</p>
        ) : (
          <ol className="mt-4 space-y-3">
            {citations.map((citation) => {
              const sourceIndex = matchingSourceIndex(citation, sources);
              const citationLabel = `Référence ${String(citation.reference)}`;

              return (
                <li
                  key={`${String(citation.reference)}-${citation.document_id}-${citation.chunk_id}`}
                  className="rounded-xl border border-border bg-white p-4 text-sm"
                >
                  {sourceIndex >= 0 ? (
                    <a
                      className="font-semibold text-accent-strong underline decoration-accent/35 underline-offset-4"
                      href={`#rag-source-${String(sourceIndex + 1)}`}
                    >
                      {citationLabel}
                    </a>
                  ) : (
                    <span className="font-semibold text-brand-navy">
                      {citationLabel}
                    </span>
                  )}
                  <p className="mt-2 break-all text-xs leading-5 text-muted">
                    Document : {citation.document_id}
                  </p>
                  {sourceIndex < 0 && (
                    <p className="mt-2 text-xs text-muted">
                      Source associée non disponible.
                    </p>
                  )}
                </li>
              );
            })}
          </ol>
        )}
      </section>
    </div>
  );
}
