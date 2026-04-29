import { TradingWorkspace } from '../components/TradingWorkspace';

export default function HomePage() {
  return (
    <main className="workspace-shell">
      <section className="hero-card">
        <p className="eyebrow">Next.js Bootstrap Slice</p>
        <h1>ATrade Frontend Home</h1>
        <p className="hero-copy">Aspire AppHost Frontend Contract</p>
        <p>
          Trading workspace MVP for trending stocks and ETFs, backend-saved watchlists, symbol navigation, and the
          upcoming interactive paper-trading chart view.
        </p>
      </section>

      <TradingWorkspace />
    </main>
  );
}
