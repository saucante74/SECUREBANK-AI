export function HomePage() {
  return (
    <div className="flex min-h-screen flex-col bg-[var(--color-surface)] text-[var(--color-ink)]">
      <main className="relative isolate flex flex-1 items-center overflow-hidden px-6 py-16 sm:px-10 lg:px-16">
        <div className="absolute inset-0 -z-10 bg-[radial-gradient(circle_at_top_right,rgba(20,184,166,0.16),transparent_38%)]" />
        <section className="mx-auto w-full max-w-6xl">
          <div className="max-w-3xl">
            <p className="mb-8 inline-flex rounded-full border border-teal-600/25 bg-white/70 px-4 py-2 text-sm font-semibold tracking-wide text-teal-800 shadow-sm backdrop-blur">
              Interface en préparation
            </p>
            <p className="mb-5 text-sm font-bold uppercase tracking-[0.24em] text-teal-700">
              SecureBank-AI
            </p>
            <h1 className="text-balance text-4xl font-semibold leading-tight tracking-tight text-slate-950 sm:text-5xl lg:text-7xl">
              Assistant bancaire intelligent et sécurisé
            </h1>
            <p className="mt-8 max-w-2xl text-lg leading-8 text-slate-600 sm:text-xl">
              Une interface dédiée à l’exploration de connaissances bancaires
              synthétiques, avec des réponses documentées et une attention
              particulière à la confidentialité.
            </p>
          </div>
        </section>
      </main>
      <footer className="border-t border-slate-200/80 px-6 py-6 text-center text-sm text-slate-500 sm:px-10">
        SecureBank-AI — Environnement de démonstration
      </footer>
    </div>
  );
}
