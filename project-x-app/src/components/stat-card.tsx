import { Card } from "@/components/card";

type StatCardProps = {
  label: string;
  value: string;
  detail: string;
};

export function StatCard({ label, value, detail }: StatCardProps) {
  return (
    <Card>
      <article className="flex flex-col gap-1">
        <span className="text-xs font-semibold text-text-secondary tracking-wide">{label}</span>
        <strong className="text-2xl font-bold text-text-primary font-display">{value}</strong>
        <p className="text-sm text-text-tertiary mt-1">{detail}</p>
      </article>
    </Card>
  );
}
