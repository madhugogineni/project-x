export function validatePhone(phone: string): string | null {
  const digits = phone.replace(/\D/g, "");
  if (digits.length !== 10) return "Phone number must be 10 digits";
  if (!/^[6-9]/.test(digits)) return "Enter a valid Indian mobile number";
  return null;
}

export function validateEmail(email: string): string | null {
  if (!email.trim()) return "Email is required";
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email.trim())) return "Enter a valid email address";
  return null;
}

export function validatePan(pan: string): string | null {
  if (!pan.trim()) return "PAN is required";
  if (!/^[A-Z]{5}[0-9]{4}[A-Z]$/.test(pan.trim().toUpperCase())) {
    return "PAN must be in format AAAAA9999A";
  }
  return null;
}

export function validatePincode(pincode: string): string | null {
  const digits = pincode.replace(/\D/g, "");
  if (digits.length !== 6) return "Pincode must be 6 digits";
  return null;
}

export function validateRequired(value: string, fieldName: string): string | null {
  if (!value.trim()) return `${fieldName} is required`;
  return null;
}

export function validateDateOfBirth(dob: string): string | null {
  if (!dob) return "Date of birth is required";
  const date = new Date(dob);
  if (isNaN(date.getTime())) return "Enter a valid date";
  if (date >= new Date()) return "Date of birth must be in the past";
  return null;
}

export function normalizePhone(phone: string): string {
  return phone.replace(/\D/g, "").slice(-10);
}

export function normalizeEmail(email: string): string {
  return email.trim().toLowerCase();
}

export function normalizePan(pan: string): string {
  return pan.trim().toUpperCase();
}
