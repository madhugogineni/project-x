import Link from "next/link";

import { FeatureCard } from "@/components/feature-card";
import { siteConfig } from "@/lib/site-config";

export default function HomePage() {
  return (
    <main className="page-shell">
      <section className="hero">
        <div className="hero__content">
          <span className="eyebrow">Digital financial continuity</span>
          <h1>{siteConfig.tagline}</h1>
          <p>{siteConfig.description}</p>
          <div className="hero__actions">
            <Link className="button button--primary" href={siteConfig.links.app}>
              Open the app
            </Link>
            <a className="button button--secondary" href="#pillars">
              Explore the product
            </a>
          </div>
        </div>
        <aside className="hero__panel">
          <p className="hero__panel-label">Designed for difficult moments</p>
          <ul>
            {siteConfig.highlights.map((highlight) => (
              <li key={highlight}>{highlight}</li>
            ))}
          </ul>
        </aside>
      </section>

      <section className="section" id="pillars">
        <div className="section__header">
          <span className="eyebrow">Core modules</span>
          <h2>Built to organize, protect, and release information responsibly.</h2>
        </div>
        <div className="feature-grid">
          {siteConfig.pillars.map((pillar) => (
            <FeatureCard
              key={pillar.title}
              title={pillar.title}
              description={pillar.description}
            />
          ))}
        </div>
      </section>

      <section className="section section--cta">
        <div>
          <span className="eyebrow">What Continuum does not do</span>
          <h2>It never stores passwords, private keys, or performs transactions.</h2>
        </div>
        <p>
          The platform exists to preserve context, records, and document trails so
          families can act with clarity.
        </p>
      </section>
    </main>
  );
}
