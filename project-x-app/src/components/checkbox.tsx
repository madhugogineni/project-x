"use client";

type CheckboxProps = {
  label: string;
  name?: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
};

export function Checkbox({ label, name, checked, onChange, disabled }: CheckboxProps) {
  const id = name || label.toLowerCase().replace(/\s+/g, "-");

  return (
    <label className="inline-flex items-center gap-2 cursor-pointer text-sm text-text-primary" htmlFor={id}>
      <input
        id={id}
        name={name}
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        disabled={disabled}
        className="w-4 h-4 accent-accent cursor-pointer"
      />
      <span>{label}</span>
    </label>
  );
}
