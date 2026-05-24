type FeatureCardProps = {
  title: string;
  description: string;
};

export function FeatureCard({ title, description }: FeatureCardProps) {
  return (
    <article className="feature-card">
      <p className="feature-card__eyebrow">Module</p>
      <h3>{title}</h3>
      <p>{description}</p>
    </article>
  );
}
