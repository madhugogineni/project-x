import { FeatureCard } from "@/components/feature-card";
import { SiteHeader } from "@/components/site-header";
import { siteConfig } from "@/lib/site-config";

const heroHighlights = [
  {
    title: "Clear records",
    description: "Bring accounts, policies, properties, and supporting details into one readable structure."
  },
  {
    title: "Private documents",
    description: "Keep important files attached to the right records so families are not searching blindly."
  },
  {
    title: "Verified release",
    description: "Access follows reminders, checks, and a hold period instead of appearing all at once."
  },
  {
    title: "Read-only access",
    description: "Nominees see the information they need without turning the product into a control surface."
  }
] as const;

const workflowStages = [
  {
    title: "Organize",
    description:
      "Capture accounts, policies, property records, and supporting documents in a structure your family can understand."
  },
  {
    title: "Monitor",
    description:
      "Use inactivity reminders and staged checks before any nominee escalation path becomes relevant."
  },
  {
    title: "Release read-only context",
    description:
      "After verification and a hold window, nominees can see the information they need without getting execution powers."
  }
] as const;

const safeguards = [
  "Sensitive documents stay protected",
  "No money movement or transaction execution",
  "Read-only nominee access after release",
  "Profile isolation across primary, advisor, and nominee contexts"
] as const;

const whatItDoesPoints = [
  {
    title: "Structured records",
    description:
      "Bring accounts, policies, property records, and liabilities into one organized view."
  },
  {
    title: "Document context",
    description:
      "Keep the right files attached to the right financial records so details do not get lost."
  },
  {
    title: "Nominee guidance",
    description:
      "Make it easier for families to understand who should be informed and what they can see."
  },
  {
    title: "Staged visibility",
    description:
      "Preserve context ahead of time so access later feels deliberate instead of chaotic."
  }
] as const;

export default function HomePage() {
  return (
    <main className="page-shell">
      <SiteHeader />

      <section className="hero">
        <div className="hero__content">
          <span className="eyebrow">Digital financial continuity</span>
          <h1>{siteConfig.tagline}</h1>
          <p>{siteConfig.description}</p>
        </div>

        <div className="hero__highlights">
          <p className="hero__panel-label">Designed for difficult moments</p>
          <div className="hero__highlight-grid">
            {heroHighlights.map((highlight) => (
              <article key={highlight.title} className="hero-highlight">
                <h3>{highlight.title}</h3>
                <p>{highlight.description}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="section" id="pillars">
        <div className="section__header">
          <span className="eyebrow">What it does</span>
          <h2>
            Project X turns scattered financial details into a record your family can
            actually use.
          </h2>
        </div>
        <div className="section__overview">
          <p>
            Most families do not inherit one clean record. They inherit fragments:
            account details in old emails, insurance papers in folders, nominee
            information in memory, and property documents spread across drawers and
            drives. Project X is designed to bring those pieces together before they
            become urgent. It is a continuity product, not a transaction product.
            The goal is to create clarity around what exists, which documents
            matter, who should be informed, and how read-only access should happen
            later.
          </p>
        </div>
        <div className="section__capability-grid">
          {whatItDoesPoints.map((point) => (
            <article key={point.title} className="section__capability-card">
              <span className="section__capability-kicker">Capability</span>
              <h3>{point.title}</h3>
              <p>{point.description}</p>
            </article>
          ))}
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

      <section className="section" id="workflow">
        <div className="section__header">
          <span className="eyebrow">How it works</span>
          <h2>Information stays private until the right checks have happened.</h2>
          <p>
            Access is paced through reminders, verification, and a waiting period
            so nothing is released suddenly or without context.
          </p>
        </div>
        <div className="workflow-grid">
          {workflowStages.map((stage) => (
            <article key={stage.title} className="step-card">
              <h3>{stage.title}</h3>
              <p>{stage.description}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="section" id="safeguards">
        <div className="section__header">
          <span className="eyebrow">Built for safety</span>
          <h2>The product is intentionally limited to reduce risk.</h2>
          <p>
            Project X helps people find information. It does not cross into the
            high-risk areas that would make the product harder to trust.
          </p>
        </div>
        <div className="safeguard-list">
          {safeguards.map((item) => (
            <article key={item} className="safeguard-card">
              <p>{item}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="section section--cta">
        <div className="section__header">
          <span className="eyebrow">{`What ${siteConfig.name} does not do`}</span>
          <h2>It does not move money, trade assets, or act on financial accounts.</h2>
          <p>
            The platform preserves records, documents, and release context. It does
            not process assets, execute transactions, or take operational control of
            financial relationships on a family&apos;s behalf.
          </p>
        </div>
      </section>
    </main>
  );
}
