"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/button";
import { Input } from "@/components/input";
import { Select } from "@/components/select";
import { Alert } from "@/components/alert";
import { useToast } from "@/components/toast";
import { useAuth } from "@/lib/auth-context";
import { apiClient, ApiClientError } from "@/lib/api-client";
import type {
  Nominee,
  NomineeCreateRequest,
  NomineeUpdateRequest,
  NomineeRelationship,
  PaginatedResponse,
} from "@/lib/types";

/* ─── Constants ────────────────────────────────────────────────────── */

const RELATIONSHIP_OPTIONS: { value: NomineeRelationship; label: string }[] = [
  { value: "SPOUSE", label: "Spouse" },
  { value: "MOTHER", label: "Mother" },
  { value: "FATHER", label: "Father" },
  { value: "SON", label: "Son" },
  { value: "DAUGHTER", label: "Daughter" },
  { value: "BROTHER", label: "Brother" },
  { value: "SISTER", label: "Sister" },
  { value: "OTHER", label: "Other" },
];

const RELATIONSHIP_LABELS = new Map(
  RELATIONSHIP_OPTIONS.map((option) => [option.value, option.label])
);

const STATUS_STYLES: Record<string, string> = {
  PENDING: "bg-warning-subtle text-warning",
  INVITED: "bg-info-subtle text-info",
  LINKED: "bg-success-subtle text-success",
  REMOVED: "bg-bg-secondary text-text-tertiary",
};

const STATUS_LABELS: Record<string, string> = {
  PENDING: "Pending",
  INVITED: "Invited",
  LINKED: "Linked",
  REMOVED: "Removed",
};

const EDITABLE_STATUSES = new Set(["PENDING", "INVITED"]);

/* ─── Form types & validation ──────────────────────────────────────── */

type FormData = {
  full_name: string;
  relationship: string;
  custom_relationship: string;
  phone: string;
  email: string;
};

const EMPTY_FORM: FormData = {
  full_name: "",
  relationship: "",
  custom_relationship: "",
  phone: "",
  email: "",
};

type FormErrors = Partial<Record<keyof FormData | "_form", string>>;

function normalizePhoneForCompare(value: string): string {
  const digits = value.replace(/\D/g, "");
  return digits.slice(-10);
}

function validateForm(
  data: FormData,
  primaryContact?: { phone?: string | null; email?: string | null }
): FormErrors {
  const errors: FormErrors = {};
  if (!data.full_name.trim()) errors.full_name = "Full name is required";
  if (!data.relationship) errors.relationship = "Relationship is required";
  if (data.relationship === "OTHER" && !data.custom_relationship.trim()) {
    errors.custom_relationship = "Enter the relationship";
  }

  const hasPhone = !!data.phone.trim();
  const hasEmail = !!data.email.trim();

  if (!hasPhone) errors.phone = "Phone number is required";
  if (!hasEmail) errors.email = "Email is required";

  if (hasPhone) {
    const digits = data.phone.replace(/\D/g, "");
    if (digits.length !== 10) errors.phone = "Phone number must be 10 digits";
    else if (!/^[6-9]/.test(digits))
      errors.phone = "Enter a valid Indian mobile number";
    else if (
      primaryContact?.phone &&
      normalizePhoneForCompare(data.phone) ===
        normalizePhoneForCompare(primaryContact.phone)
    ) {
      errors.phone = "Nominee phone number cannot be your phone number";
    }
  }

  if (hasEmail) {
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(data.email.trim())) {
      errors.email = "Enter a valid email address";
    } else if (
      primaryContact?.email &&
      data.email.trim().toLowerCase() === primaryContact.email.trim().toLowerCase()
    ) {
      errors.email = "Nominee email cannot be your email";
    }
  }

  return errors;
}

function formatRelationship(value: string): string {
  const knownLabel = RELATIONSHIP_LABELS.get(value);
  if (knownLabel) return knownLabel;

  return value
    .replace(/_/g, " ")
    .toLowerCase()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function toRelationshipFormData(nominee: Nominee): FormData {
  const isKnownRelationship = RELATIONSHIP_OPTIONS.some(
    (option) => option.value === nominee.relationship
  );

  return {
    full_name: nominee.full_name,
    relationship: isKnownRelationship ? nominee.relationship : "OTHER",
    custom_relationship: isKnownRelationship
      ? ""
      : formatRelationship(nominee.relationship),
    phone: nominee.phone ?? "",
    email: nominee.email ?? "",
  };
}

function getRelationshipValue(data: FormData): string {
  return data.relationship === "OTHER"
    ? data.custom_relationship.trim()
    : data.relationship;
}

function getInitials(name: string): string {
  return name
    .split(" ")
    .filter(Boolean)
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

/* ─── Modal component ──────────────────────────────────────────────── */

function NomineeFormModal({
  title,
  initialData,
  onSubmit,
  onClose,
  isSubmitting,
  submitLabel,
  serverError,
  primaryContact,
}: {
  title: string;
  initialData: FormData;
  onSubmit: (data: FormData) => void;
  onClose: () => void;
  isSubmitting: boolean;
  submitLabel: string;
  serverError: string | null;
  primaryContact?: { phone?: string | null; email?: string | null };
}) {
  const [form, setForm] = useState<FormData>(initialData);
  const [errors, setErrors] = useState<FormErrors>({});

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const errs = validateForm(form, primaryContact);
    setErrors(errs);
    if (Object.keys(errs).length > 0) return;
    onSubmit({ ...form, relationship: getRelationshipValue(form) });
  };

  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/40 px-4">
      <div className="bg-surface-strong border border-border-light rounded-xl shadow-md w-full max-w-lg overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border-light">
          <h3 className="text-base font-bold text-text-primary">{title}</h3>
          <button
            type="button"
            className="w-8 h-8 flex items-center justify-center rounded-md text-text-tertiary hover:text-text-primary hover:bg-bg-secondary transition-colors"
            onClick={onClose}
            aria-label="Close"
          >
            <svg
              className="w-5 h-5"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <form onSubmit={handleSubmit} className="px-6 py-5">
          {(serverError || errors._form) && (
            <div className="mb-4">
              <Alert variant="error">{serverError || errors._form}</Alert>
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Full name"
              name="nominee-name"
              value={form.full_name}
              onChange={(v) => setForm({ ...form, full_name: v })}
              placeholder="Enter full name"
              error={errors.full_name}
              required
            />
            <Select
              label="Relationship"
              name="nominee-relationship"
              value={form.relationship}
              onChange={(v) =>
                setForm({
                  ...form,
                  relationship: v,
                  custom_relationship:
                    v === "OTHER" ? form.custom_relationship : "",
                })
              }
              options={RELATIONSHIP_OPTIONS}
              placeholder="Select relationship"
              error={errors.relationship}
              required
            />
            {form.relationship === "OTHER" && (
              <Input
                label="Custom relationship"
                name="nominee-custom-relationship"
                value={form.custom_relationship}
                onChange={(v) =>
                  setForm({ ...form, custom_relationship: v })
                }
                placeholder="Enter relationship"
                error={errors.custom_relationship}
                maxLength={50}
                required
              />
            )}
            <Input
              label="Phone number"
              name="nominee-phone"
              type="tel"
              value={form.phone}
              onChange={(v) => setForm({ ...form, phone: v })}
              placeholder="10-digit mobile number"
              error={errors.phone}
              required
            />
            <Input
              label="Email"
              name="nominee-email"
              type="email"
              value={form.email}
              onChange={(v) => setForm({ ...form, email: v })}
              placeholder="nominee@example.com"
              error={errors.email}
              required
            />
          </div>

          {/* Footer */}
          <div className="flex items-center gap-3 mt-6 justify-end">
            <Button type="button" variant="ghost" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" loading={isSubmitting}>
              {submitLabel}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ─── Page ─────────────────────────────────────────────────────────── */

export default function NomineesPage() {
  const toast = useToast();
  const { user } = useAuth();

  // Data
  const [nominees, setNominees] = useState<Nominee[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // Create modal
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // Edit modal
  const [editingNominee, setEditingNominee] = useState<Nominee | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  // Delete
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Fetch nominees
  const fetchNominees = useCallback(async () => {
    try {
      setFetchError(null);
      const data = await apiClient.get<PaginatedResponse<Nominee>>("/nominees");
      setNominees(data.items);
    } catch (err) {
      const message =
        err instanceof ApiClientError ? err.message : "Failed to load nominees";
      setFetchError(message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchNominees();
  }, [fetchNominees]);

  // Create
  const handleCreate = async (data: FormData) => {
    setIsCreating(true);
    setCreateError(null);
    try {
      const payload: NomineeCreateRequest = {
        full_name: data.full_name.trim(),
        relationship: data.relationship as NomineeRelationship,
        phone: data.phone.trim(),
        email: data.email.trim().toLowerCase(),
      };
      const created = await apiClient.post<Nominee>("/nominees", payload);
      setNominees((prev) => [created, ...prev]);
      setShowCreateModal(false);
      toast.show("success", "Nominee added successfully");
    } catch (err) {
      const message =
        err instanceof ApiClientError ? err.message : "Failed to add nominee";
      setCreateError(message);
    } finally {
      setIsCreating(false);
    }
  };

  // Edit
  const handleUpdate = async (data: FormData) => {
    if (!editingNominee) return;
    setIsSaving(true);
    setEditError(null);
    try {
      const payload: NomineeUpdateRequest = {
        full_name: data.full_name.trim(),
        relationship: data.relationship as NomineeRelationship,
        phone: data.phone.trim(),
        email: data.email.trim().toLowerCase(),
      };
      const updated = await apiClient.patch<Nominee>(
        `/nominees/${editingNominee.id}`,
        payload
      );
      setNominees((prev) =>
        prev.map((n) => (n.id === editingNominee.id ? updated : n))
      );
      setEditingNominee(null);
      toast.show("success", "Nominee updated successfully");
    } catch (err) {
      const message =
        err instanceof ApiClientError
          ? err.message
          : "Failed to update nominee";
      setEditError(message);
    } finally {
      setIsSaving(false);
    }
  };

  // Delete
  const handleDelete = async () => {
    if (!deletingId) return;
    setIsDeleting(true);
    try {
      await apiClient.delete<Nominee>(`/nominees/${deletingId}`);
      setNominees((prev) => prev.filter((n) => n.id !== deletingId));
      setDeletingId(null);
      toast.show("success", "Nominee removed");
    } catch (err) {
      const message =
        err instanceof ApiClientError
          ? err.message
          : "Failed to remove nominee";
      toast.show("error", message);
    } finally {
      setIsDeleting(false);
    }
  };

  // Loading
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <span className="w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  // Fetch error
  if (fetchError) {
    return (
      <div className="flex flex-col items-center gap-4 py-16">
        <Alert variant="error">{fetchError}</Alert>
        <Button variant="outline" size="sm" onClick={fetchNominees}>
          Try again
        </Button>
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <p className="text-sm text-text-secondary">
          Manage the people who will receive access to your financial information
          when a release is triggered.
        </p>
        <Button
          type="button"
          variant="primary"
          size="sm"
          onClick={() => {
            setCreateError(null);
            setShowCreateModal(true);
          }}
          className="flex-shrink-0"
        >
          Add nominee
        </Button>
      </div>

      {/* Create modal */}
      {showCreateModal && (
        <NomineeFormModal
          title="Add nominee"
          initialData={EMPTY_FORM}
          onSubmit={handleCreate}
          onClose={() => setShowCreateModal(false)}
          isSubmitting={isCreating}
          submitLabel="Save nominee"
          serverError={createError}
          primaryContact={user ?? undefined}
        />
      )}

      {/* Edit modal */}
      {editingNominee && (
        <NomineeFormModal
          title="Edit nominee"
          initialData={toRelationshipFormData(editingNominee)}
          onSubmit={handleUpdate}
          onClose={() => {
            setEditingNominee(null);
            setEditError(null);
          }}
          isSubmitting={isSaving}
          submitLabel="Save changes"
          serverError={editError}
          primaryContact={user ?? undefined}
        />
      )}

      {/* Delete confirmation */}
      {deletingId && (
        <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/40 px-4">
          <div className="bg-surface-strong border border-border-light rounded-xl shadow-md p-6 w-full max-w-sm">
            <h3 className="text-base font-bold text-text-primary mb-2">
              Remove nominee
            </h3>
            <p className="text-sm text-text-secondary mb-5">
              This will revoke all access permissions for this nominee. This
              action cannot be undone.
            </p>
            <div className="flex items-center gap-3 justify-end">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setDeletingId(null)}
                disabled={isDeleting}
              >
                Cancel
              </Button>
              <Button
                type="button"
                variant="danger"
                size="sm"
                loading={isDeleting}
                onClick={handleDelete}
              >
                Remove
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Empty state */}
      {nominees.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-center bg-surface-strong rounded-xl border border-border-light shadow-sm">
          <div className="w-12 h-12 rounded-full bg-accent-subtle text-accent flex items-center justify-center mb-4">
            <svg
              className="w-6 h-6"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
              <circle cx="9" cy="7" r="4" />
              <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
              <path d="M16 3.13a4 4 0 0 1 0 7.75" />
            </svg>
          </div>
          <h3 className="text-base font-semibold text-text-primary mb-1">
            No nominees yet
          </h3>
          <p className="text-sm text-text-secondary max-w-sm mb-5 px-4">
            Add nominees to designate who should receive access to your financial
            information.
          </p>
          <Button
            type="button"
            variant="primary"
            onClick={() => {
              setCreateError(null);
              setShowCreateModal(true);
            }}
          >
            Add your first nominee
          </Button>
        </div>
      ) : (
        /* ── Table view ── */
        <div className="bg-surface-strong border border-border-light rounded-xl shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left min-w-[600px]">
              <thead>
                <tr className="border-b border-border-light bg-bg-secondary/50">
                  <th className="px-4 py-3 font-semibold text-text-secondary whitespace-nowrap">
                    Name
                  </th>
                  <th className="px-4 py-3 font-semibold text-text-secondary whitespace-nowrap">
                    Relationship
                  </th>
                  <th className="px-4 py-3 font-semibold text-text-secondary whitespace-nowrap">
                    Phone
                  </th>
                  <th className="px-4 py-3 font-semibold text-text-secondary whitespace-nowrap">
                    Email
                  </th>
                  <th className="px-4 py-3 font-semibold text-text-secondary whitespace-nowrap">
                    Status
                  </th>
                  <th className="px-4 py-3 font-semibold text-text-secondary text-right whitespace-nowrap">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {nominees.map((nominee) => {
                  const canEdit = EDITABLE_STATUSES.has(nominee.status);
                  return (
                    <tr
                      key={nominee.id}
                      className="border-b border-border-light last:border-b-0 hover:bg-bg-secondary/30 transition-colors"
                    >
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2.5">
                          <div className="w-8 h-8 rounded-full bg-accent-subtle text-accent text-xs font-bold flex items-center justify-center flex-shrink-0 font-display">
                            {getInitials(nominee.full_name)}
                          </div>
                          <span className="font-semibold text-text-primary truncate max-w-[180px]">
                            {nominee.full_name}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-text-secondary whitespace-nowrap">
                        {formatRelationship(nominee.relationship)}
                      </td>
                      <td className="px-4 py-3 text-text-secondary whitespace-nowrap">
                        {nominee.phone || "—"}
                      </td>
                      <td className="px-4 py-3 text-text-secondary truncate max-w-[200px]">
                        {nominee.email || "—"}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium whitespace-nowrap ${STATUS_STYLES[nominee.status] ?? "bg-bg-secondary text-text-tertiary"}`}
                        >
                          {STATUS_LABELS[nominee.status] ?? nominee.status}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1 justify-end">
                          {canEdit && (
                            <button
                              type="button"
                              className="w-8 h-8 flex items-center justify-center rounded-md text-text-tertiary hover:text-text-primary hover:bg-bg-secondary transition-colors"
                              title="Edit nominee"
                              onClick={() => {
                                setEditError(null);
                                setEditingNominee(nominee);
                              }}
                            >
                              <svg
                                className="w-4 h-4"
                                viewBox="0 0 24 24"
                                fill="none"
                                stroke="currentColor"
                                strokeWidth="2"
                                strokeLinecap="round"
                                strokeLinejoin="round"
                              >
                                <path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z" />
                              </svg>
                            </button>
                          )}
                          <button
                            type="button"
                            className="w-8 h-8 flex items-center justify-center rounded-md text-text-tertiary hover:text-error hover:bg-error-subtle transition-colors"
                            title="Remove nominee"
                            onClick={() => setDeletingId(nominee.id)}
                          >
                            <svg
                              className="w-4 h-4"
                              viewBox="0 0 24 24"
                              fill="none"
                              stroke="currentColor"
                              strokeWidth="2"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                            >
                              <polyline points="3 6 5 6 21 6" />
                              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                            </svg>
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
