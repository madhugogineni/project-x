"use client";

import { useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { Button } from "@/components/button";
import { Input } from "@/components/input";
import { OtpInput } from "@/components/otp-input";
import { Alert } from "@/components/alert";
import { useAuth } from "@/lib/auth-context";
import { useOtpFlow } from "@/lib/use-otp-flow";
import type { OtpVerifyResponse } from "@/lib/types";
import { appConfig } from "@/lib/app-config";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();

  const onVerified = useCallback(
    (response: unknown) => {
      const data = response as OtpVerifyResponse;
      login(data.access_token, data.refresh_token, data.account);
      router.replace("/");
    },
    [login, router]
  );

  const otp = useOtpFlow({
    flow: "LOGIN",
    onVerified,
  });

  return (
    <div className="w-full max-w-[440px] my-auto mx-auto bg-surface-strong rounded-xl border border-border-light shadow-md p-8 sm:p-10">
      {/* Heading */}
      <div className="text-center mb-8">
        <h1 className="text-2xl font-bold font-display text-text-primary">Log in</h1>
        <p className="text-sm text-text-tertiary mt-1">Welcome back to {appConfig.name}</p>
      </div>

      {otp.step === "phone" && (
        <>
          <form
            className="flex flex-col gap-5"
            onSubmit={(e) => {
              e.preventDefault();
              otp.requestOtp();
            }}
          >
            <Input
              label="Phone number"
              name="phone"
              type="tel"
              value={otp.phone}
              onChange={otp.setPhone}
              placeholder="10-digit mobile number"
              error={otp.phoneError ?? undefined}
              required
              autoFocus
            />

            {otp.error && (
              <Alert variant="error">
                <p>{otp.error}</p>
              </Alert>
            )}

            <Button
              type="submit"
              variant="primary"
              fullWidth
              loading={otp.isLoading}
              disabled={otp.resendCooldown > 0}
            >
              {otp.resendCooldown > 0 ? `Wait ${otp.resendCooldown}s` : "Continue"}
            </Button>
          </form>

          <div className="flex items-center justify-center gap-1.5 mt-7 text-sm text-text-secondary">
            <span>Don&apos;t have an account?</span>
            <Link href="/signup" className="text-accent font-medium hover:text-accent-hover">
              Sign up
            </Link>
          </div>
        </>
      )}

      {otp.step === "otp" && (
        <>
          <div className="mb-5">
            <h3 className="text-base font-semibold text-text-primary">Enter verification code</h3>
            <div className="flex items-center gap-2 text-sm text-text-secondary mt-0.5">
              <span>Sent to {otp.phone.slice(0, -4).replace(/\d/g, "*") + otp.phone.slice(-4)}</span>
              <button
                type="button"
                className="text-accent text-xs font-medium hover:text-accent-hover bg-transparent border-none p-0 cursor-pointer"
                onClick={otp.goBackToPhone}
              >
                Change
              </button>
            </div>
          </div>

          <form
            className="flex flex-col gap-5"
            onSubmit={(e) => {
              e.preventDefault();
              otp.verifyOtp();
            }}
          >
            <OtpInput
              length={otp.otpLength}
              value={otp.otp}
              onChange={otp.setOtp}
              onComplete={() => otp.verifyOtp()}
              error={otp.error ?? undefined}
              disabled={otp.isMaxAttemptsReached}
            />

            <Button
              type="submit"
              variant="primary"
              fullWidth
              loading={otp.isLoading}
              disabled={otp.otp.length !== otp.otpLength || otp.isMaxAttemptsReached}
            >
              Verify
            </Button>

            <div className="flex items-center justify-between text-sm text-text-tertiary">
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  className="text-accent font-medium hover:text-accent-hover disabled:opacity-50 disabled:cursor-not-allowed bg-transparent border-none p-0 cursor-pointer"
                  onClick={otp.resendOtp}
                  disabled={otp.resendCooldown > 0 || otp.isLoading}
                >
                  Resend code
                </button>
                {otp.resendCooldown > 0 && (
                  <span>in {otp.resendCooldown}s</span>
                )}
              </div>
              {typeof otp.remainingResends === "number" && (
                <span>
                  {otp.remainingResends} resend{otp.remainingResends === 1 ? "" : "s"} left
                </span>
              )}
            </div>
          </form>
        </>
      )}
    </div>
  );
}
