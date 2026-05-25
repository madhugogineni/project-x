"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { apiClient, ApiClientError } from "@/lib/api-client";
import type { OtpFlow, OtpRequestResponse } from "@/lib/types";
import { normalizePhone, validatePhone } from "@/lib/validators";

type OtpStep = "phone" | "otp";

type UseOtpFlowOptions = {
  flow: OtpFlow;
  onVerified: (response: unknown) => void;
};

const OTP_LENGTH = 6;

function getSecondsUntil(target: string | null) {
  if (!target) {
    return 0;
  }

  const milliseconds = new Date(target).getTime() - Date.now();
  return milliseconds > 0 ? Math.ceil(milliseconds / 1000) : 0;
}

export function useOtpFlow({ flow, onVerified }: UseOtpFlowOptions) {
  const [step, setStep] = useState<OtpStep>("phone");
  const [phone, setPhone] = useState("");
  const [otp, setOtp] = useState("");
  const [otpSessionId, setOtpSessionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [phoneError, setPhoneError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(0);
  const [remainingResends, setRemainingResends] = useState<number | null>(null);
  const [isMaxAttemptsReached, setIsMaxAttemptsReached] = useState(false);
  const cooldownRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => {
      if (cooldownRef.current) {
        clearInterval(cooldownRef.current);
      }
    };
  }, []);

  const startCooldown = useCallback((durationSeconds: number) => {
    const nextCooldown = Math.max(0, durationSeconds);
    setResendCooldown(nextCooldown);

    if (cooldownRef.current) {
      clearInterval(cooldownRef.current);
    }

    if (nextCooldown <= 0) {
      return;
    }

    cooldownRef.current = setInterval(() => {
      setResendCooldown((previous) => {
        if (previous <= 1) {
          if (cooldownRef.current) {
            clearInterval(cooldownRef.current);
          }
          return 0;
        }

        return previous - 1;
      });
    }, 1000);
  }, []);

  const syncOtpState = useCallback(
    (response: OtpRequestResponse) => {
      setOtpSessionId(response.otp_session_id);
      setRemainingResends(response.remaining_resends);
      setStep("otp");
      setOtp("");
      startCooldown(getSecondsUntil(response.cooldown_until));
    },
    [startCooldown]
  );

  const requestOtp = useCallback(async () => {
    const normalizedPhone = normalizePhone(phone);
    const validationError = validatePhone(normalizedPhone);

    if (validationError) {
      setPhoneError(validationError);
      return;
    }

    setPhoneError(null);
    setError(null);
    setIsLoading(true);
    setIsMaxAttemptsReached(false);

    try {
      const response = await apiClient.post<OtpRequestResponse>(
        "/auth/otp/request",
        { phone: normalizedPhone, flow },
        { skipAuth: true }
      );

      syncOtpState(response);
    } catch (err) {
      if (err instanceof ApiClientError) {
        if (err.status === 429) {
          const wait = err.retryAfterSeconds ?? 0;
          startCooldown(wait);
          setError(
            wait > 0
              ? `A code was already sent. Please wait ${wait} second${wait !== 1 ? "s" : ""} before trying again.`
              : "A code was already sent. Please wait a moment before trying again."
          );
        } else {
          setError(err.message);
        }
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setIsLoading(false);
    }
  }, [flow, phone, startCooldown, syncOtpState]);

  const verifyOtp = useCallback(async () => {
    if (!otpSessionId) {
      setError("Request a code first.");
      return;
    }

    if (otp.length !== OTP_LENGTH) {
      setError(`Enter the ${OTP_LENGTH}-digit code`);
      return;
    }

    setError(null);
    setIsLoading(true);

    try {
      const response = await apiClient.post("/auth/otp/verify", {
        otp_session_id: otpSessionId,
        phone: normalizePhone(phone),
        otp,
        flow,
      }, { skipAuth: true });

      onVerified(response);
    } catch (err) {
      if (err instanceof ApiClientError) {
        if (
          err.code === "OTP_ATTEMPTS_EXHAUSTED" ||
          err.code === "OTP_MAX_ATTEMPTS" ||
          err.message.toLowerCase().includes("maximum attempts") ||
          err.message.toLowerCase().includes("attempt limit exceeded")
        ) {
          setIsMaxAttemptsReached(true);
          setError("Maximum attempts reached. Please request a new code.");
        } else {
          setError(err.message);
        }
      } else {
        setError("Verification failed. Please try again.");
      }
    } finally {
      setIsLoading(false);
    }
  }, [flow, onVerified, otp, otpSessionId, phone]);

  const resendOtp = useCallback(async () => {
    if (resendCooldown > 0) {
      return;
    }

    setError(null);
    setIsLoading(true);
    setIsMaxAttemptsReached(false);
    setOtp("");

    try {
      const response = await apiClient.post<OtpRequestResponse>(
        "/auth/otp/request",
        { phone: normalizePhone(phone), flow },
        { skipAuth: true }
      );

      syncOtpState(response);
    } catch (err) {
      if (err instanceof ApiClientError) {
        if (err.status === 429) {
          const wait = err.retryAfterSeconds ?? 0;
          startCooldown(wait);
          setError(
            wait > 0
              ? `A code was already sent. Please wait ${wait} second${wait !== 1 ? "s" : ""} before trying again.`
              : "A code was already sent. Please wait a moment before trying again."
          );
        } else {
          setError(err.message);
        }
      } else {
        setError("Could not resend code. Please try again.");
      }
    } finally {
      setIsLoading(false);
    }
  }, [flow, phone, resendCooldown, startCooldown, syncOtpState]);

  const goBackToPhone = useCallback(() => {
    setStep("phone");
    setOtp("");
    setError(null);
    setOtpSessionId(null);
    setRemainingResends(null);
    setIsMaxAttemptsReached(false);

    if (cooldownRef.current) {
      clearInterval(cooldownRef.current);
    }

    setResendCooldown(0);
  }, []);

  return {
    step,
    phone,
    setPhone,
    otp,
    setOtp,
    otpLength: OTP_LENGTH,
    otpSessionId,
    error,
    phoneError,
    isLoading,
    resendCooldown,
    remainingResends,
    isMaxAttemptsReached,
    requestOtp,
    verifyOtp,
    resendOtp,
    goBackToPhone,
  };
}
