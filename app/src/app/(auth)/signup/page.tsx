"use client";

import { useCallback, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { Button } from "@/components/button";
import { Input } from "@/components/input";
import { Select } from "@/components/select";
import { Checkbox } from "@/components/checkbox";
import { OtpInput } from "@/components/otp-input";
import { Alert } from "@/components/alert";
import { useAuth } from "@/lib/auth-context";
import { useOtpFlow } from "@/lib/use-otp-flow";
import { apiClient, ApiClientError } from "@/lib/api-client";
import type { SignupVerifyResponse, OtpVerifyResponse, Gender } from "@/lib/types";
import { appConfig } from "@/lib/app-config";
import {
  validateEmail,
  validatePan,
  validatePincode,
  validateRequired,
  validateDateOfBirth,
  normalizeEmail,
  normalizePan,
} from "@/lib/validators";

type SignupStep = "phone" | "otp" | "details";

const GENDER_OPTIONS = [
  { value: "MALE", label: "Male" },
  { value: "FEMALE", label: "Female" },
  { value: "OTHER", label: "Other" },
  { value: "PREFER_NOT_TO_SAY", label: "Prefer not to say" },
];

type AddressFields = {
  address_line_1: string;
  address_line_2: string;
  landmark: string;
  city: string;
  district: string;
  state: string;
  pincode: string;
  country: string;
};

const emptyAddress: AddressFields = {
  address_line_1: "",
  address_line_2: "",
  landmark: "",
  city: "",
  district: "",
  state: "",
  pincode: "",
  country: "India",
};

export default function SignupPage() {
  const router = useRouter();
  const { login } = useAuth();

  const [step, setStep] = useState<SignupStep>("phone");
  const [verifiedToken, setVerifiedToken] = useState<string | null>(null);

  // Personal details
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [dateOfBirth, setDateOfBirth] = useState("");
  const [gender, setGender] = useState("");
  const [panNumber, setPanNumber] = useState("");
  const [nameOnPan, setNameOnPan] = useState("");
  const [currentAddress, setCurrentAddress] = useState<AddressFields>({ ...emptyAddress });
  const [permanentAddress, setPermanentAddress] = useState<AddressFields>({ ...emptyAddress });
  const [isSameAsCurrent, setIsSameAsCurrent] = useState(false);
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const onOtpVerified = useCallback((response: unknown) => {
    const data = response as SignupVerifyResponse;
    setVerifiedToken(data.verified_signup_token);
    setStep("details");
  }, []);

  const otp = useOtpFlow({
    flow: "SIGNUP",
    onVerified: onOtpVerified,
  });

  // Sync step state with OTP hook
  const currentStep = step === "details" ? "details" : otp.step;

  const updateCurrentAddress = (field: keyof AddressFields, value: string) => {
    setCurrentAddress((prev) => ({ ...prev, [field]: value }));
  };

  const updatePermanentAddress = (field: keyof AddressFields, value: string) => {
    setPermanentAddress((prev) => ({ ...prev, [field]: value }));
  };

  const validateForm = (): boolean => {
    const errors: Record<string, string> = {};

    const nameErr = validateRequired(fullName, "Full name");
    if (nameErr) errors.fullName = nameErr;

    const emailErr = validateEmail(email);
    if (emailErr) errors.email = emailErr;

    const dobErr = validateDateOfBirth(dateOfBirth);
    if (dobErr) errors.dateOfBirth = dobErr;

    if (!gender) errors.gender = "Gender is required";

    const panErr = validatePan(panNumber);
    if (panErr) errors.panNumber = panErr;

    const panNameErr = validateRequired(nameOnPan, "Name on PAN");
    if (panNameErr) errors.nameOnPan = panNameErr;

    // Current address validation
    const addr1Err = validateRequired(currentAddress.address_line_1, "Address line 1");
    if (addr1Err) errors["current.address_line_1"] = addr1Err;

    const cityErr = validateRequired(currentAddress.city, "City");
    if (cityErr) errors["current.city"] = cityErr;

    const stateErr = validateRequired(currentAddress.state, "State");
    if (stateErr) errors["current.state"] = stateErr;

    const pincodeErr = validatePincode(currentAddress.pincode);
    if (pincodeErr) errors["current.pincode"] = pincodeErr;

    // Permanent address validation (if not same as current)
    if (!isSameAsCurrent) {
      const pAddr1Err = validateRequired(permanentAddress.address_line_1, "Address line 1");
      if (pAddr1Err) errors["permanent.address_line_1"] = pAddr1Err;

      const pCityErr = validateRequired(permanentAddress.city, "City");
      if (pCityErr) errors["permanent.city"] = pCityErr;

      const pStateErr = validateRequired(permanentAddress.state, "State");
      if (pStateErr) errors["permanent.state"] = pStateErr;

      const pPincodeErr = validatePincode(permanentAddress.pincode);
      if (pPincodeErr) errors["permanent.pincode"] = pPincodeErr;
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validateForm() || !verifiedToken) return;

    setIsSubmitting(true);
    setSubmitError(null);

    const addressPayload = (addr: AddressFields) => ({
      address_line_1: addr.address_line_1,
      address_line_2: addr.address_line_2 || undefined,
      landmark: addr.landmark || undefined,
      city: addr.city,
      district: addr.district || undefined,
      state: addr.state,
      pincode: addr.pincode,
      country: addr.country || "India",
    });

    try {
      const data = await apiClient.post<OtpVerifyResponse>(
        "/auth/signup/complete",
        {
          verified_signup_token: verifiedToken,
          email: normalizeEmail(email),
          full_name: fullName.trim(),
          date_of_birth: dateOfBirth,
          gender: gender as Gender,
          pan_number: normalizePan(panNumber),
          name_on_pan: nameOnPan.trim(),
          current_address: addressPayload(currentAddress),
          permanent_address: isSameAsCurrent ? null : addressPayload(permanentAddress),
          is_same_as_current: isSameAsCurrent,
        },
        { skipAuth: true }
      );

      login(data.access_token, data.refresh_token, data.account);
      router.replace("/");
    } catch (err) {
      if (err instanceof ApiClientError) {
        setSubmitError(err.message);
      } else {
        setSubmitError("Registration failed. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      className={`w-full my-auto mx-auto bg-surface-strong rounded-xl border border-border-light shadow-md p-8 sm:p-10 ${
        currentStep === "details" ? "max-w-[560px]" : "max-w-[440px]"
      }`}
    >
      {/* Heading */}
      <div className="text-center mb-8">
        <h1 className="text-2xl font-bold font-display text-text-primary">Sign up</h1>
        <p className="text-sm text-text-tertiary mt-1">Create your {appConfig.name} account</p>
      </div>

      {/* Step 1: Phone */}
      {currentStep === "phone" && (
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
            <span>Already have an account?</span>
            <Link href="/login" className="text-accent font-medium hover:text-accent-hover">
              Log in
            </Link>
          </div>
        </>
      )}

      {/* Step 2: OTP */}
      {currentStep === "otp" && (
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

      {/* Step 3: Personal details */}
      {currentStep === "details" && (
        <form
          className="flex flex-col gap-5"
          onSubmit={(e) => {
            e.preventDefault();
            handleSubmit();
          }}
        >
          {/* Personal Information */}
          <div className="mb-6">
            <h4 className="text-sm font-bold text-text-primary pb-2 mb-4 border-b border-border-light">
              Personal information
            </h4>
            <div className="grid grid-cols-2 gap-4 max-[520px]:grid-cols-1">
              <div className="col-span-2 max-[520px]:col-span-1">
                <Input
                  label="Full name"
                  name="fullName"
                  value={fullName}
                  onChange={setFullName}
                  error={formErrors.fullName}
                  required
                  autoFocus
                />
              </div>
              <Input
                label="Email"
                name="email"
                type="email"
                value={email}
                onChange={setEmail}
                error={formErrors.email}
                placeholder="you@example.com"
                required
              />
              <Input
                label="Date of birth"
                name="dateOfBirth"
                type="date"
                value={dateOfBirth}
                onChange={setDateOfBirth}
                error={formErrors.dateOfBirth}
                required
              />
              <Select
                label="Gender"
                name="gender"
                value={gender}
                onChange={setGender}
                options={GENDER_OPTIONS}
                placeholder="Select gender"
                error={formErrors.gender}
                required
              />
            </div>
          </div>

          {/* PAN Details */}
          <div className="mb-6">
            <h4 className="text-sm font-bold text-text-primary pb-2 mb-4 border-b border-border-light">
              Pan details
            </h4>
            <div className="grid grid-cols-2 gap-4 max-[520px]:grid-cols-1">
              <Input
                label="Pan number"
                name="panNumber"
                value={panNumber}
                onChange={setPanNumber}
                error={formErrors.panNumber}
                placeholder="AAAAA9999A"
                required
              />
              <Input
                label="Name on Pan"
                name="nameOnPan"
                value={nameOnPan}
                onChange={setNameOnPan}
                error={formErrors.nameOnPan}
                required
              />
            </div>
          </div>

          {/* Current Address */}
          <div className="mb-6">
            <h4 className="text-sm font-bold text-text-primary pb-2 mb-4 border-b border-border-light">
              Current address
            </h4>
            <div className="grid grid-cols-2 gap-4 max-[520px]:grid-cols-1">
              <div className="col-span-2 max-[520px]:col-span-1">
                <Input
                  label="Address line 1"
                  name="current-address1"
                  value={currentAddress.address_line_1}
                  onChange={(v) => updateCurrentAddress("address_line_1", v)}
                  error={formErrors["current.address_line_1"]}
                  required
                />
              </div>
              <Input
                label="Address line 2"
                name="current-address2"
                value={currentAddress.address_line_2}
                onChange={(v) => updateCurrentAddress("address_line_2", v)}
              />
              <Input
                label="Landmark"
                name="current-landmark"
                value={currentAddress.landmark}
                onChange={(v) => updateCurrentAddress("landmark", v)}
              />
              <Input
                label="City"
                name="current-city"
                value={currentAddress.city}
                onChange={(v) => updateCurrentAddress("city", v)}
                error={formErrors["current.city"]}
                required
              />
              <Input
                label="District"
                name="current-district"
                value={currentAddress.district}
                onChange={(v) => updateCurrentAddress("district", v)}
              />
              <Input
                label="State"
                name="current-state"
                value={currentAddress.state}
                onChange={(v) => updateCurrentAddress("state", v)}
                error={formErrors["current.state"]}
                required
              />
              <Input
                label="Pincode"
                name="current-pincode"
                value={currentAddress.pincode}
                onChange={(v) => updateCurrentAddress("pincode", v)}
                error={formErrors["current.pincode"]}
                required
              />
            </div>
          </div>

          {/* Permanent Address */}
          <div className="mb-6">
            <h4 className="text-sm font-bold text-text-primary pb-2 mb-4 border-b border-border-light">
              Permanent address
            </h4>
            <Checkbox
              label="Same as current address"
              name="isSameAsCurrent"
              checked={isSameAsCurrent}
              onChange={setIsSameAsCurrent}
            />

            {!isSameAsCurrent && (
              <div className="grid grid-cols-2 gap-4 max-[520px]:grid-cols-1 mt-4">
                <div className="col-span-2 max-[520px]:col-span-1">
                  <Input
                    label="Address line 1"
                    name="permanent-address1"
                    value={permanentAddress.address_line_1}
                    onChange={(v) => updatePermanentAddress("address_line_1", v)}
                    error={formErrors["permanent.address_line_1"]}
                    required
                  />
                </div>
                <Input
                  label="Address line 2"
                  name="permanent-address2"
                  value={permanentAddress.address_line_2}
                  onChange={(v) => updatePermanentAddress("address_line_2", v)}
                />
                <Input
                  label="Landmark"
                  name="permanent-landmark"
                  value={permanentAddress.landmark}
                  onChange={(v) => updatePermanentAddress("landmark", v)}
                />
                <Input
                  label="City"
                  name="permanent-city"
                  value={permanentAddress.city}
                  onChange={(v) => updatePermanentAddress("city", v)}
                  error={formErrors["permanent.city"]}
                  required
                />
                <Input
                  label="District"
                  name="permanent-district"
                  value={permanentAddress.district}
                  onChange={(v) => updatePermanentAddress("district", v)}
                />
                <Input
                  label="State"
                  name="permanent-state"
                  value={permanentAddress.state}
                  onChange={(v) => updatePermanentAddress("state", v)}
                  error={formErrors["permanent.state"]}
                  required
                />
                <Input
                  label="Pincode"
                  name="permanent-pincode"
                  value={permanentAddress.pincode}
                  onChange={(v) => updatePermanentAddress("pincode", v)}
                  error={formErrors["permanent.pincode"]}
                  required
                />
              </div>
            )}
          </div>

          {submitError && (
            <Alert variant="error">
              <p>{submitError}</p>
            </Alert>
          )}

          <Button type="submit" variant="primary" fullWidth loading={isSubmitting}>
            Create account
          </Button>
        </form>
      )}
    </div>
  );
}
