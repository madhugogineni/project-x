import type { ReactNode, TdHTMLAttributes, ThHTMLAttributes } from "react";

// ── Wrapper ───────────────────────────────────────────────────────────────────

type TableProps = {
  children: ReactNode;
  className?: string;
};

export function Table({ children, className = "" }: TableProps) {
  return (
    <div className="w-full overflow-x-auto rounded-lg border border-border-light">
      <table className={`w-full text-sm text-left ${className}`}>{children}</table>
    </div>
  );
}

// ── Head / Body ───────────────────────────────────────────────────────────────

export function Thead({ children }: { children: ReactNode }) {
  return (
    <thead className="bg-surface-sunken border-b border-border-light">
      {children}
    </thead>
  );
}

export function Tbody({ children }: { children: ReactNode }) {
  return (
    <tbody className="divide-y divide-border-light bg-surface-strong">
      {children}
    </tbody>
  );
}

// ── Row ───────────────────────────────────────────────────────────────────────

type TrProps = {
  children: ReactNode;
  onClick?: () => void;
  className?: string;
};

export function Tr({ children, onClick, className = "" }: TrProps) {
  const interactive = !!onClick;
  return (
    <tr
      onClick={onClick}
      className={[
        "transition-colors duration-[180ms]",
        interactive ? "cursor-pointer hover:bg-surface-base" : "",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {children}
    </tr>
  );
}

// ── Header cell ───────────────────────────────────────────────────────────────

type ThProps = ThHTMLAttributes<HTMLTableCellElement> & {
  children?: ReactNode;
};

export function Th({ children, className = "", ...props }: ThProps) {
  return (
    <th
      className={`px-4 py-3 text-xs font-semibold text-text-tertiary whitespace-nowrap ${className}`}
      {...props}
    >
      {children}
    </th>
  );
}

// ── Data cell ─────────────────────────────────────────────────────────────────

type TdProps = TdHTMLAttributes<HTMLTableCellElement> & {
  children?: ReactNode;
  muted?: boolean;
};

export function Td({ children, muted = false, className = "", ...props }: TdProps) {
  return (
    <td
      className={[
        "px-4 py-3",
        muted ? "text-text-tertiary" : "text-text-primary",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
      {...props}
    >
      {children}
    </td>
  );
}
