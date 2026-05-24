"use client";

import { useCallback, useEffect, useRef, type KeyboardEvent, type ClipboardEvent } from "react";

type OtpInputProps = {
  length?: number;
  value: string;
  onChange: (value: string) => void;
  onComplete?: (value: string) => void;
  error?: string;
  disabled?: boolean;
};

export function OtpInput({
  length = 6,
  value,
  onChange,
  onComplete,
  error,
  disabled,
}: OtpInputProps) {
  const inputsRef = useRef<(HTMLInputElement | null)[]>([]);

  useEffect(() => {
    if (value === "" && inputsRef.current[0]) {
      inputsRef.current[0].focus();
    }
  }, [value]);

  const focusInput = useCallback((index: number) => {
    const input = inputsRef.current[index];
    if (input) {
      input.focus();
      input.select();
    }
  }, []);

  const handleChange = useCallback(
    (index: number, char: string) => {
      if (!/^\d$/.test(char)) return;

      const chars = value.split("");
      while (chars.length < length) chars.push("");
      chars[index] = char;
      const newValue = chars.join("").slice(0, length);
      onChange(newValue);

      if (index < length - 1) {
        focusInput(index + 1);
      }

      if (newValue.length === length && !newValue.includes("")) {
        onComplete?.(newValue);
      }
    },
    [value, length, onChange, onComplete, focusInput]
  );

  const handleKeyDown = useCallback(
    (index: number, e: KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Backspace") {
        e.preventDefault();
        const chars = value.split("");
        if (chars[index]) {
          chars[index] = "";
          onChange(chars.join(""));
        } else if (index > 0) {
          chars[index - 1] = "";
          onChange(chars.join(""));
          focusInput(index - 1);
        }
      } else if (e.key === "ArrowLeft" && index > 0) {
        focusInput(index - 1);
      } else if (e.key === "ArrowRight" && index < length - 1) {
        focusInput(index + 1);
      }
    },
    [value, onChange, focusInput, length]
  );

  const handlePaste = useCallback(
    (e: ClipboardEvent<HTMLInputElement>) => {
      e.preventDefault();
      const pasted = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, length);
      if (pasted.length > 0) {
        onChange(pasted);
        const focusIdx = Math.min(pasted.length, length - 1);
        focusInput(focusIdx);
        if (pasted.length === length) {
          onComplete?.(pasted);
        }
      }
    },
    [length, onChange, onComplete, focusInput]
  );

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="flex items-center gap-2 max-[400px]:gap-1.5" role="group" aria-label="Verification code">
        {Array.from({ length }, (_, i) => (
          <input
            key={i}
            ref={(el) => {
              inputsRef.current[i] = el;
            }}
            type="text"
            inputMode="numeric"
            maxLength={1}
            value={value[i] || ""}
            onChange={(e) => {
              const char = e.target.value.slice(-1);
              if (char) handleChange(i, char);
            }}
            onKeyDown={(e) => handleKeyDown(i, e)}
            onPaste={handlePaste}
            onFocus={(e) => e.target.select()}
            disabled={disabled}
            className={[
              "w-11 h-13 text-center text-xl font-semibold border-[1.5px] rounded-md bg-surface-base text-text-primary",
              "focus:outline-none focus:shadow-[0_0_0_3px_var(--accent-primary-subtle)] transition-all duration-[180ms]",
              "max-[400px]:w-9 max-[400px]:h-11 max-[400px]:text-lg",
              error
                ? "border-error"
                : value[i]
                  ? "border-accent bg-accent-subtle"
                  : "border-border-default focus:border-accent",
            ]
              .filter(Boolean)
              .join(" ")}
            aria-label={`Digit ${i + 1}`}
            autoComplete={i === 0 ? "one-time-code" : "off"}
          />
        ))}
      </div>
      {error && (
        <p className="text-xs text-error text-center" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
