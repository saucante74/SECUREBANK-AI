import type { RagAskResponse } from "../api/types";
import { RagSources } from "./RagSources";

interface RagResponsePanelProps {
  response?: RagAskResponse;
}

export function RagResponsePanel({ response }: RagResponsePanelProps) {
  if (response === undefined) {
    return (
      <section
        className="flex min-h-64 items-center justify-center rounded-2xl border border-dashed border-border bg-white/65 p-8 text-center"
        aria-labelledby="empty-conversation-title"
      >
        <div className="max-w-md">
          <h2
            id="empty-conversation-title"
            className="text-xl font-semibold text-brand-navy"
          >
            Conversation vide
          </h2>
          <p className="mt-3 leading-7 text-muted">
            Les réponses documentaires apparaîtront dans cet espace lorsque
            l’envoi sera disponible.
          </p>
        </div>
      </section>
    );
  }

  return (
    <article className="space-y-6 rounded-2xl border border-border bg-white p-6 shadow-soft sm:p-8">
      <div
        className={
          response.abstained
            ? "rounded-xl border border-amber-300 bg-amber-50 p-4 text-amber-950"
            : "rounded-xl border border-accent/25 bg-accent-soft p-4 text-brand-navy"
        }
        role="status"
      >
        <p className="text-sm font-semibold">
          {response.abstained
            ? "Réponse avec abstention"
            : "Réponse documentaire"}
        </p>
        {response.abstained && (
          <p className="mt-1 text-sm leading-6">
            Les éléments disponibles ne permettent pas de fournir une réponse
            suffisamment étayée.
          </p>
        )}
      </div>

      <section aria-labelledby="answer-title">
        <h2 id="answer-title" className="text-xl font-semibold text-brand-navy">
          Réponse
        </h2>
        <p className="mt-4 whitespace-pre-wrap leading-7 text-ink">
          {response.answer}
        </p>
      </section>

      <RagSources citations={response.citations} sources={response.sources} />
    </article>
  );
}
