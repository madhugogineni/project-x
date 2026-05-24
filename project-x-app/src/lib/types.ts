export type Gender = "MALE" | "FEMALE" | "OTHER" | "PREFER_NOT_TO_SAY";

export type AddressType = "CURRENT" | "PERMANENT";

export type Address = {
  id?: string;
  address_line_1: string;
  address_line_2?: string;
  landmark?: string;
  city: string;
  district?: string;
  state: string;
  pincode: string;
  country: string;
  address_type: AddressType;
};

export type Account = {
  id: string;
  phone: string;
  email: string;
  full_name: string | null;
  phone_verified: boolean;
  email_verified: boolean;
  status: "ACTIVE" | "SUSPENDED" | "DELETED";
  primary_profile_id: string | null;
};

export type AccountPan = {
  pan_number: string;
  name_on_pan: string;
  is_verified: boolean;
  verification_source?: "SELF_DECLARED" | "THIRD_PARTY_API" | "MANUAL";
};

export type AuthToken = {
  id: string;
  jti: string;
  session_id?: string;
  token_type: "ACCESS" | "REFRESH";
  device_name: string | null;
  ip_address: string | null;
  user_agent: string | null;
  revoked_at: string | null;
  last_used_at: string;
  created_at: string;
};

export type PaginatedResponse<T> = {
  items: T[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
};

export type OtpFlow = "SIGNUP" | "LOGIN";

export type OtpRequestResponse = {
  otp_session_id: string;
  expires_at: string;
  flow: OtpFlow;
  resend_count: number;
  remaining_resends: number;
  attempts_remaining: number;
  cooldown_until: string | null;
};

export type OtpVerifyResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  access_token_expires_at: string;
  refresh_token_expires_at: string;
  account: Account;
};

export type SignupVerifyResponse = {
  verified_signup_token: string;
  expires_at: string;
};

export type SignupCompleteRequest = {
  verified_signup_token: string;
  email: string;
  full_name: string;
  date_of_birth: string;
  gender: Gender;
  pan_number: string;
  name_on_pan: string;
  current_address: Omit<Address, "id" | "address_type">;
  permanent_address: Omit<Address, "id" | "address_type"> | null;
  is_same_as_current: boolean;
};

export type ProfileType = "PRIMARY" | "ADVISOR" | "NOMINEE";

export type Profile = {
  id: string;
  account_id: string;
  profile_type: ProfileType;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type NomineeRelationship =
  | "SPOUSE"
  | "MOTHER"
  | "FATHER"
  | "SON"
  | "DAUGHTER"
  | "BROTHER"
  | "SISTER"
  | "OTHER"
  | (string & {});
export type NomineeStatus = "PENDING" | "INVITED" | "LINKED" | "REMOVED";

export type LinkedAccount = {
  id: string;
  full_name: string | null;
  phone: string;
  email: string;
};

export type Nominee = {
  id: string;
  full_name: string;
  relationship: NomineeRelationship;
  phone: string | null;
  email: string | null;
  status: NomineeStatus;
  linked_account_id: string | null;
  linked_at: string | null;
  linked_account: LinkedAccount | null;
  created_at: string;
  updated_at: string;
};

export type NomineeCreateRequest = {
  full_name: string;
  relationship: NomineeRelationship;
  phone: string;
  email: string;
};

export type NomineeUpdateRequest = {
  full_name?: string;
  relationship?: NomineeRelationship;
  phone?: string;
  email?: string;
};

export type ApiError = {
  detail: string;
  code?: string;
};

/* ─── Asset types ───────────────────────────────────────────────────── */

export type AssetFieldBlueprint = {
  name: string;
  type: string;
  required: boolean;
  enum_options: string[] | null;
  sensitive: boolean;
  masked_on_read: boolean;
};

export type AssetTypeBlueprint = {
  container_type: string;
  base_fields: AssetFieldBlueprint[];
  detail_fields: AssetFieldBlueprint[];
  document_support: boolean;
};

export type AssetBlueprintResponse = {
  types: AssetTypeBlueprint[];
};

export type AssetDocumentSummary = {
  id: string;
  container_id: string;
  document_type: string;
  original_file_name: string | null;
  mime_type: string | null;
  file_size_bytes: number | null;
  upload_status: string;
  is_active: boolean;
  created_at: string;
};

export type AssetListItem = {
  id: string;
  container_type: string;
  institution_name: string;
  nickname: string | null;
  approximate_value: number | null;
  notes: string | null;
  is_active: boolean;
  detail_summary: Record<string, unknown>;
  document_count: number;
  can_edit: boolean;
  can_delete: boolean;
  access_permission: string | null;
  created_at: string;
  updated_at: string;
};

export type Asset = AssetListItem & {
  detail: Record<string, unknown> | null;
  documents: AssetDocumentSummary[];
};

export type DocumentUploadInitiateResponse = {
  document_id: string;
  upload_url: string;
  upload_headers: Record<string, string>;
  expires_at: string;
};

export type NomineeScopeResponse = {
  id: string;
  container_id: string;
  container_type: string;
  institution_name: string;
  permission: string;
  is_active: boolean;
  is_visible: boolean;
  visibility_triggered_at: string | null;
  visibility_trigger_source: string | null;
  created_at: string;
  updated_at: string;
};
