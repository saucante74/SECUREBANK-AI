import type { RagCitation, RagSource } from "../api/types";
import { useTranslation } from "react-i18next";

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
  const { t } = useTranslation();

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(16rem,0.55fr)]">
      <section aria-labelledby="sources-title">
        <h3 id="sources-title" className="text-lg font-semibold text-brand-navy">
          {t("rag.sourcesTitle")}
        </h3>
        {sources.length === 0 ? (
          <p className="mt-3 text-sm text-muted">{t("rag.noSources")}</p>
        ) : (
          <ol className="mt-4 space-y-4">
            {sources.map((source, index) => (
              <li
                id={`rag-source-${String(index + 1)}`}
                key={`${source.document_id}-${source.id}`}
                className="rounded-2xl border border-border bg-surface p-5"
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
          {t("rag.citationsTitle")}
        </h3>
        {citations.length === 0 ? (
          <p className="mt-3 text-sm text-muted">{t("rag.noCitations")}</p>
        ) : (
          <ol className="mt-4 space-y-3">
            {citations.map((citation) => {
              const sourceIndex = matchingSourceIndex(citation, sources);
              const citationLabel = t("rag.reference", {
                reference: citation.reference,
              });

              return (
                <li
                  key={`${String(citation.reference)}-${citation.document_id}-${citation.chunk_id}`}
                  className="rounded-2xl border border-border bg-white p-5 text-sm shadow-soft"
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
                    {t("rag.document", { documentId: citation.document_id })}
                  </p>
                  {sourceIndex < 0 && (
                    <p className="mt-2 text-xs text-muted">
                      {t("rag.unmatchedSource")}
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
