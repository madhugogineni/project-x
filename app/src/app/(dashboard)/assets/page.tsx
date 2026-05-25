"use client";

import Image from "next/image";
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { Button } from "@/components/button";
import { Input } from "@/components/input";
import { Select } from "@/components/select";
import { Alert } from "@/components/alert";
import { useToast } from "@/components/toast";
import { apiClient, ApiClientError } from "@/lib/api-client";
import { useProfile } from "@/lib/profile-context";
import type {
  Asset,
  AssetBlueprintResponse,
  AssetDocumentSummary,
  AssetFieldBlueprint,
  AssetListItem,
  AssetTypeBlueprint,
  DocumentUploadInitiateResponse,
  Nominee,
  NomineeScopeResponse,
  PaginatedResponse,
} from "@/lib/types";

/* ─── Constants ─────────────────────────────────────────────────────── */

const CONTAINER_TYPE_LABELS: Record<string, string> = {
  BANK_RELATIONSHIP: "Bank account",
  DEMAT_ACCOUNT: "Demat account",
  MUTUAL_FUND_FOLIO: "Mutual fund",
  RETIREMENT_ACCOUNT: "Retirement account",
  INSURANCE_POLICY: "Insurance policy",
  REAL_ESTATE: "Real estate",
  LOAN_ACCOUNT: "Loan account",
  BUSINESS_OWNERSHIP: "Business",
  GOVERNMENT_SAVINGS_SCHEME: "Government savings",
  CRYPTO_ACCOUNT: "Crypto account",
  RECEIVABLE_CLAIM: "Receivable claim",
};

const NOMINEE_RELATIONSHIP_LABELS: Record<string, string> = {
  SPOUSE: "Spouse",
  MOTHER: "Mother",
  FATHER: "Father",
  SON: "Son",
  DAUGHTER: "Daughter",
  BROTHER: "Brother",
  SISTER: "Sister",
  OTHER: "Other",
};

function formatNomineeRelationship(value: string): string {
  return (
    NOMINEE_RELATIONSHIP_LABELS[value] ??
    value
      .replace(/_/g, " ")
      .toLowerCase()
      .replace(/\b\w/g, (char) => char.toUpperCase())
  );
}

const CONTAINER_TYPE_ICONS: Record<string, ReactNode> = {
  BANK_RELATIONSHIP: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <line x1="3" y1="22" x2="21" y2="22" /><line x1="6" y1="18" x2="6" y2="11" />
      <line x1="10" y1="18" x2="10" y2="11" /><line x1="14" y1="18" x2="14" y2="11" />
      <line x1="18" y1="18" x2="18" y2="11" /><polygon points="12 2 20 7 4 7" />
    </svg>
  ),
  DEMAT_ACCOUNT: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="22 7 13.5 15.5 8.5 10.5 2 17" /><polyline points="16 7 22 7 22 13" />
    </svg>
  ),
  MUTUAL_FUND_FOLIO: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="20" x2="18" y2="10" /><line x1="12" y1="20" x2="12" y2="4" />
      <line x1="6" y1="20" x2="6" y2="14" /><line x1="2" y1="20" x2="22" y2="20" />
    </svg>
  ),
  RETIREMENT_ACCOUNT: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" />
    </svg>
  ),
  INSURANCE_POLICY: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    </svg>
  ),
  REAL_ESTATE: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
      <polyline points="9 22 9 12 15 12 15 22" />
    </svg>
  ),
  LOAN_ACCOUNT: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <rect x="1" y="4" width="22" height="16" rx="2" ry="2" /><line x1="1" y1="10" x2="23" y2="10" />
    </svg>
  ),
  BUSINESS_OWNERSHIP: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="7" width="20" height="14" rx="2" ry="2" />
      <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
    </svg>
  ),
  GOVERNMENT_SAVINGS_SCHEME: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z" /><line x1="4" y1="22" x2="4" y2="15" />
    </svg>
  ),
  CRYPTO_ACCOUNT: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="12 2 19.07 6 19.07 18 12 22 4.93 18 4.93 6" />
      <polyline points="12 2 12 22" /><line x1="4.93" y1="6" x2="19.07" y2="6" />
      <line x1="4.93" y1="18" x2="19.07" y2="18" />
    </svg>
  ),
  RECEIVABLE_CLAIM: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" /><polyline points="10 9 9 9 8 9" />
    </svg>
  ),
};

/* ─── Institution catalog ────────────────────────────────────────────── */

type InstitutionEntry = { name: string; abbr: string; bg: string; text: string; logoUrl?: string };

const INSTITUTION_CATALOG: Record<string, InstitutionEntry[]> = {
  BANK_RELATIONSHIP: [
    { name: "HDFC Bank", abbr: "HD", bg: "#004C8F", text: "#fff", logoUrl: "https://logo.clearbit.com/hdfcbank.com" },
    { name: "ICICI Bank", abbr: "IC", bg: "#F37428", text: "#fff", logoUrl: "https://logo.clearbit.com/icicibank.com" },
    { name: "State Bank of India", abbr: "SB", bg: "#2D5FA0", text: "#fff", logoUrl: "https://logo.clearbit.com/sbi.co.in" },
    { name: "Axis Bank", abbr: "AX", bg: "#97144D", text: "#fff", logoUrl: "https://logo.clearbit.com/axisbank.com" },
    { name: "Kotak Mahindra Bank", abbr: "KO", bg: "#ED1C24", text: "#fff", logoUrl: "https://logo.clearbit.com/kotak.com" },
    { name: "Punjab National Bank", abbr: "PN", bg: "#1A2E6C", text: "#fff", logoUrl: "https://logo.clearbit.com/pnbindia.in" },
    { name: "Bank of Baroda", abbr: "BB", bg: "#F7941E", text: "#fff", logoUrl: "https://logo.clearbit.com/bankofbaroda.in" },
    { name: "Canara Bank", abbr: "CA", bg: "#00529B", text: "#fff", logoUrl: "https://logo.clearbit.com/canarabank.com" },
    { name: "IndusInd Bank", abbr: "IN", bg: "#005B9A", text: "#fff", logoUrl: "https://logo.clearbit.com/indusind.com" },
    { name: "Yes Bank", abbr: "YB", bg: "#00355F", text: "#fff", logoUrl: "https://logo.clearbit.com/yesbank.in" },
    { name: "IDFC First Bank", abbr: "ID", bg: "#E2231A", text: "#fff", logoUrl: "https://logo.clearbit.com/idfcfirstbank.com" },
    { name: "Federal Bank", abbr: "FB", bg: "#00A3E0", text: "#fff", logoUrl: "https://logo.clearbit.com/federalbank.co.in" },
  ],
  DEMAT_ACCOUNT: [
    { name: "Zerodha", abbr: "ZE", bg: "#387ED1", text: "#fff", logoUrl: "https://logo.clearbit.com/zerodha.com" },
    { name: "Upstox", abbr: "UP", bg: "#7B2FBE", text: "#fff", logoUrl: "https://logo.clearbit.com/upstox.com" },
    { name: "Groww", abbr: "GR", bg: "#5367FF", text: "#fff", logoUrl: "https://logo.clearbit.com/groww.in" },
    { name: "Angel One", abbr: "AN", bg: "#D43F22", text: "#fff", logoUrl: "https://logo.clearbit.com/angelone.in" },
    { name: "HDFC Securities", abbr: "HS", bg: "#004C8F", text: "#fff", logoUrl: "https://logo.clearbit.com/hdfcsec.com" },
    { name: "ICICI Direct", abbr: "IC", bg: "#F37428", text: "#fff", logoUrl: "https://logo.clearbit.com/icicidirect.com" },
    { name: "Sharekhan", abbr: "SK", bg: "#009444", text: "#fff", logoUrl: "https://logo.clearbit.com/sharekhan.com" },
    { name: "Motilal Oswal", abbr: "MO", bg: "#C41230", text: "#fff", logoUrl: "https://logo.clearbit.com/motilaloswal.com" },
    { name: "5paisa", abbr: "5P", bg: "#00C2A8", text: "#fff", logoUrl: "https://logo.clearbit.com/5paisa.com" },
    { name: "Kotak Securities", abbr: "KS", bg: "#ED1C24", text: "#fff", logoUrl: "https://logo.clearbit.com/kotaksecurities.com" },
  ],
  MUTUAL_FUND_FOLIO: [
    { name: "SBI Mutual Fund", abbr: "SB", bg: "#2D5FA0", text: "#fff", logoUrl: "https://logo.clearbit.com/sbimf.com" },
    { name: "HDFC Mutual Fund", abbr: "HD", bg: "#004C8F", text: "#fff", logoUrl: "https://logo.clearbit.com/hdfcfund.com" },
    { name: "ICICI Prudential", abbr: "IC", bg: "#F37428", text: "#fff", logoUrl: "https://logo.clearbit.com/iciciprulife.com" },
    { name: "Axis Mutual Fund", abbr: "AX", bg: "#97144D", text: "#fff", logoUrl: "https://logo.clearbit.com/axismf.com" },
    { name: "Kotak Mutual Fund", abbr: "KO", bg: "#ED1C24", text: "#fff", logoUrl: "https://logo.clearbit.com/kotakmf.com" },
    { name: "Mirae Asset", abbr: "MA", bg: "#003087", text: "#fff", logoUrl: "https://logo.clearbit.com/miraeassetmf.co.in" },
    { name: "Nippon India", abbr: "NI", bg: "#E60012", text: "#fff", logoUrl: "https://logo.clearbit.com/nipponindiamf.com" },
    { name: "DSP Mutual Fund", abbr: "DS", bg: "#00A19A", text: "#fff", logoUrl: "https://logo.clearbit.com/dspim.com" },
    { name: "Aditya Birla Sun Life", abbr: "AB", bg: "#E2231A", text: "#fff", logoUrl: "https://logo.clearbit.com/adityabirlacapital.com" },
    { name: "Parag Parikh", abbr: "PP", bg: "#1E3A5F", text: "#fff", logoUrl: "https://logo.clearbit.com/ppfas.com" },
  ],
  RETIREMENT_ACCOUNT: [
    { name: "EPFO", abbr: "EP", bg: "#1A6B3C", text: "#fff", logoUrl: "https://logo.clearbit.com/epfindia.gov.in" },
    { name: "NPS Trust", abbr: "NP", bg: "#00529B", text: "#fff", logoUrl: "https://logo.clearbit.com/npstrust.org.in" },
    { name: "India Post", abbr: "IP", bg: "#CC0000", text: "#fff", logoUrl: "https://logo.clearbit.com/indiapost.gov.in" },
    { name: "SBI Pension Fund", abbr: "SB", bg: "#2D5FA0", text: "#fff", logoUrl: "https://logo.clearbit.com/sbipensionsfund.com" },
    { name: "LIC Pension Fund", abbr: "LI", bg: "#00539B", text: "#fff", logoUrl: "https://logo.clearbit.com/licindia.in" },
  ],
  INSURANCE_POLICY: [
    { name: "LIC", abbr: "LI", bg: "#00539B", text: "#fff", logoUrl: "https://logo.clearbit.com/licindia.in" },
    { name: "HDFC Life", abbr: "HD", bg: "#004C8F", text: "#fff", logoUrl: "https://logo.clearbit.com/hdfclife.com" },
    { name: "ICICI Prudential Life", abbr: "IC", bg: "#F37428", text: "#fff", logoUrl: "https://logo.clearbit.com/iciciprulife.com" },
    { name: "SBI Life", abbr: "SB", bg: "#2D5FA0", text: "#fff", logoUrl: "https://logo.clearbit.com/sbilife.co.in" },
    { name: "Bajaj Allianz", abbr: "BA", bg: "#003087", text: "#fff", logoUrl: "https://logo.clearbit.com/bajajallianz.com" },
    { name: "Max Life", abbr: "MX", bg: "#E31837", text: "#fff", logoUrl: "https://logo.clearbit.com/maxlifeinsurance.com" },
    { name: "Tata AIA", abbr: "TA", bg: "#003399", text: "#fff", logoUrl: "https://logo.clearbit.com/tataaia.com" },
    { name: "Kotak Life", abbr: "KO", bg: "#ED1C24", text: "#fff", logoUrl: "https://logo.clearbit.com/kotaklife.com" },
    { name: "Aditya Birla Health", abbr: "AB", bg: "#E2231A", text: "#fff", logoUrl: "https://logo.clearbit.com/adityabirlacapital.com" },
    { name: "Star Health", abbr: "ST", bg: "#C8102E", text: "#fff", logoUrl: "https://logo.clearbit.com/starhealth.in" },
    { name: "Niva Bupa", abbr: "NB", bg: "#005EB8", text: "#fff", logoUrl: "https://logo.clearbit.com/nivabupa.com" },
  ],
  REAL_ESTATE: [
    { name: "DDA", abbr: "DD", bg: "#1A4B8C", text: "#fff" },
    { name: "MHADA", abbr: "MH", bg: "#006A4E", text: "#fff" },
    { name: "CIDCO", abbr: "CI", bg: "#003087", text: "#fff" },
    { name: "HUDCO", abbr: "HU", bg: "#C8102E", text: "#fff" },
  ],
  LOAN_ACCOUNT: [
    { name: "HDFC Bank", abbr: "HD", bg: "#004C8F", text: "#fff", logoUrl: "https://logo.clearbit.com/hdfcbank.com" },
    { name: "SBI", abbr: "SB", bg: "#2D5FA0", text: "#fff", logoUrl: "https://logo.clearbit.com/sbi.co.in" },
    { name: "ICICI Bank", abbr: "IC", bg: "#F37428", text: "#fff", logoUrl: "https://logo.clearbit.com/icicibank.com" },
    { name: "Axis Bank", abbr: "AX", bg: "#97144D", text: "#fff", logoUrl: "https://logo.clearbit.com/axisbank.com" },
    { name: "Bajaj Finance", abbr: "BF", bg: "#003087", text: "#fff", logoUrl: "https://logo.clearbit.com/bajajfinserv.in" },
    { name: "LIC Housing Finance", abbr: "LH", bg: "#00539B", text: "#fff", logoUrl: "https://logo.clearbit.com/lichfl.com" },
    { name: "PNB Housing Finance", abbr: "PH", bg: "#1A2E6C", text: "#fff", logoUrl: "https://logo.clearbit.com/pnbhousing.com" },
    { name: "Tata Capital", abbr: "TC", bg: "#003399", text: "#fff", logoUrl: "https://logo.clearbit.com/tatacapital.com" },
    { name: "Kotak Mahindra Bank", abbr: "KO", bg: "#ED1C24", text: "#fff", logoUrl: "https://logo.clearbit.com/kotak.com" },
  ],
  BUSINESS_OWNERSHIP: [],
  GOVERNMENT_SAVINGS_SCHEME: [
    { name: "India Post", abbr: "IP", bg: "#CC0000", text: "#fff", logoUrl: "https://logo.clearbit.com/indiapost.gov.in" },
    { name: "SBI", abbr: "SB", bg: "#2D5FA0", text: "#fff", logoUrl: "https://logo.clearbit.com/sbi.co.in" },
    { name: "Bank of Baroda", abbr: "BB", bg: "#F7941E", text: "#fff", logoUrl: "https://logo.clearbit.com/bankofbaroda.in" },
  ],
  CRYPTO_ACCOUNT: [
    { name: "CoinDCX", abbr: "CD", bg: "#1A3FBE", text: "#fff", logoUrl: "https://logo.clearbit.com/coindcx.com" },
    { name: "CoinSwitch", abbr: "CS", bg: "#6C3CE1", text: "#fff", logoUrl: "https://logo.clearbit.com/coinswitch.co" },
    { name: "WazirX", abbr: "WX", bg: "#0B0E11", text: "#fff", logoUrl: "https://logo.clearbit.com/wazirx.com" },
    { name: "Mudrex", abbr: "MU", bg: "#7C4DFF", text: "#fff", logoUrl: "https://logo.clearbit.com/mudrex.com" },
    { name: "Binance", abbr: "BI", bg: "#F3BA2F", text: "#000", logoUrl: "https://logo.clearbit.com/binance.com" },
    { name: "Kraken", abbr: "KR", bg: "#5741D9", text: "#fff", logoUrl: "https://logo.clearbit.com/kraken.com" },
    { name: "Coinbase", abbr: "CB", bg: "#0052FF", text: "#fff", logoUrl: "https://logo.clearbit.com/coinbase.com" },
  ],
  RECEIVABLE_CLAIM: [],
};

function getInstitutionEntry(containerType: string, institutionName: string): InstitutionEntry | null {
  const entries = INSTITUTION_CATALOG[containerType] ?? [];
  return entries.find((e) => e.name.toLowerCase() === institutionName.toLowerCase()) ?? null;
}

function institutionAbbr(name: string): string {
  const words = name.trim().split(/\s+/);
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return (words[0][0] + (words[1]?.[0] ?? "")).toUpperCase();
}

function InstitutionAvatar({
  containerType,
  name,
  size = "md",
}: {
  containerType: string;
  name: string;
  size?: "sm" | "md";
}) {
  const entry = getInstitutionEntry(containerType, name);
  const bg = entry?.bg ?? "#64748B";
  const text = entry?.text ?? "#fff";
  const abbr = entry?.abbr ?? institutionAbbr(name);
  const dim = size === "sm" ? "w-6 h-6 text-[0.6rem]" : "w-8 h-8 text-xs";
  const [imgFailed, setImgFailed] = useState(false);

  if (entry?.logoUrl && !imgFailed) {
    return (
      <span
        className={`${dim} rounded-lg flex items-center justify-center flex-shrink-0 overflow-hidden bg-white`}
      >
        <Image
          src={entry.logoUrl}
          alt={name}
          width={size === "sm" ? 24 : 32}
          height={size === "sm" ? 24 : 32}
          className="w-full h-full object-contain p-0.5"
          onError={() => setImgFailed(true)}
        />
      </span>
    );
  }

  return (
    <span
      className={`${dim} rounded-lg flex items-center justify-center font-bold flex-shrink-0 select-none`}
      style={{ backgroundColor: bg, color: text }}
    >
      {abbr}
    </span>
  );
}


function buildInstitutionOptions(containerType: string) {
  const entries = INSTITUTION_CATALOG[containerType] ?? [];
  return [...entries.map((e) => ({ value: e.name, label: e.name })), { value: "__other__", label: "Other" }];
}

function InstitutionOptionLabel({
  option,
  containerType,
}: {
  option: { value: string; label: string };
  containerType: string;
}) {
  if (option.value === "__other__") {
    return <span>{option.label}</span>;
  }
  return (
    <span className="flex items-center gap-2">
      <InstitutionAvatar containerType={containerType} name={option.value} size="sm" />
      {option.label}
    </span>
  );
}

const PERMISSION_OPTIONS = [
  { value: "VIEW_SUMMARY", label: "View summary" },
  { value: "VIEW_FULL", label: "View full details" },
  { value: "VIEW_WITH_DOCUMENTS", label: "View with documents" },
];

const DOCUMENT_TYPE_OPTIONS = [
  { value: "POLICY_DOCUMENT", label: "Policy document" },
  { value: "PROPERTY_PAPER", label: "Property paper" },
  { value: "INVESTMENT_STATEMENT", label: "Investment statement" },
  { value: "LEGAL_AGREEMENT", label: "Legal agreement" },
  { value: "ACCOUNT_STATEMENT", label: "Account statement" },
  { value: "OTHER", label: "Other" },
];

const FIELD_LABEL_OVERRIDES: Record<string, string> = {
  ifsc_code: "IFSC code",
};

const INSTITUTION_FIELD_LABELS: Record<string, string> = {
  DEMAT_ACCOUNT: "Broker",
};

const OPTION_LABEL_OVERRIDES: Record<string, string> = {
  FD: "Fixed deposit (FD)",
  RD: "Recurring deposit (RD)",
};

const BANK_DEPOSIT_ACCOUNT_TYPES = new Set(["FD", "RD"]);

/* ─── Helpers ───────────────────────────────────────────────────────── */

function formatFieldName(name: string): string {
  if (FIELD_LABEL_OVERRIDES[name]) return FIELD_LABEL_OVERRIDES[name];
  return name
    .split("_")
    .map((w, i) => (i === 0 ? w.charAt(0).toUpperCase() + w.slice(1) : w))
    .join(" ");
}

function formatOptionName(name: string): string {
  if (OPTION_LABEL_OVERRIDES[name]) return OPTION_LABEL_OVERRIDES[name];
  if (name.includes(" ")) return name;
  return name
    .split("_")
    .map((w) => (w.length <= 3 ? w.toUpperCase() : w.charAt(0) + w.slice(1).toLowerCase()))
    .join(" ");
}

function getOtherOptionValue(options: string[] | null): string | null {
  return options?.find((option) => option.trim().toLowerCase() === "other") ?? null;
}

function formatCurrency(value: number | null): string {
  if (value == null) return "—";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value);
}

function formatFileSize(bytes: number | null): string {
  if (!bytes) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function initDetailForm(blueprint: AssetTypeBlueprint): Record<string, string> {
  const form: Record<string, string> = {};
  for (const field of blueprint.detail_fields) {
    form[field.name] = field.name === "interest_rate" ? "0" : "";
  }
  return form;
}

function populateDetailForm(
  blueprint: AssetTypeBlueprint,
  detail: Record<string, unknown> | null
): Record<string, string> {
  const form = initDetailForm(blueprint);
  if (!detail) return form;
  for (const field of blueprint.detail_fields) {
    const value = detail[field.name];
    if (value == null) continue;
    // For masked fields on read, don't pre-populate (force re-entry)
    if (field.masked_on_read && typeof value === "string" && value.includes("*")) {
      form[field.name] = "";
    } else {
      form[field.name] = String(value);
    }
  }
  return form;
}

function detailFormToPayload(
  form: Record<string, string>,
  fields: AssetFieldBlueprint[]
): Record<string, unknown> {
  const detail: Record<string, unknown> = {};
  for (const field of fields) {
    const raw = form[field.name];
    if (!raw || raw.trim() === "") continue;
    if (field.type === "decimal" || field.type === "float" || field.type === "number") {
      const n = parseFloat(raw);
      if (!Number.isNaN(n)) detail[field.name] = n;
    } else if (field.type === "boolean") {
      detail[field.name] = raw === "true";
    } else {
      detail[field.name] = raw.trim();
    }
  }
  return detail;
}

function getVisibleDetailFields(
  blueprint: AssetTypeBlueprint,
  form: Record<string, string>
): AssetFieldBlueprint[] {
  if (blueprint.container_type === "DEMAT_ACCOUNT") {
    return blueprint.detail_fields.filter((field) => field.name !== "broker_name");
  }

  if (blueprint.container_type !== "BANK_RELATIONSHIP") {
    return blueprint.detail_fields;
  }

  const isDepositAccount = BANK_DEPOSIT_ACCOUNT_TYPES.has(form.account_type);
  return blueprint.detail_fields.filter((field) => {
    if (field.name === "maturity_date" || field.name === "interest_rate") {
      return isDepositAccount;
    }
    return true;
  });
}

/* ─── DynamicFormField ───────────────────────────────────────────────── */

function DynamicFormField({
  field,
  value,
  onChange,
  error,
}: {
  field: AssetFieldBlueprint;
  value: string;
  onChange: (v: string) => void;
  error?: string;
}) {
  const label = formatFieldName(field.name);
  const fieldId = `detail-${field.name}`;

  if (field.enum_options && field.enum_options.length > 0) {
    const otherOptionValue = getOtherOptionValue(field.enum_options);
    const isCustomOtherValue = !!otherOptionValue && !!value && !field.enum_options.includes(value);
    const selectValue = isCustomOtherValue ? otherOptionValue : value;
    const customValue = isCustomOtherValue || value === otherOptionValue ? (isCustomOtherValue ? value : "") : "";
    const opts = field.enum_options.map((o) => ({
      value: o,
      label: formatOptionName(o),
    }));
    return (
      <div className="flex flex-col gap-3">
        <Select
          label={label}
          name={fieldId}
          value={selectValue}
          onChange={(nextValue) => onChange(nextValue)}
          options={opts}
          placeholder={`Select ${label.toLowerCase()}`}
          error={error && selectValue !== otherOptionValue ? error : undefined}
          required={field.required}
          searchable={field.enum_options.length > 10}
        />
        {otherOptionValue && selectValue === otherOptionValue && (
          <Input
            label={`Custom ${label.toLowerCase()}`}
            name={`${fieldId}-custom`}
            value={customValue}
            onChange={onChange}
            placeholder={`Enter ${label.toLowerCase()}`}
            error={error}
            required={field.required}
          />
        )}
      </div>
    );
  }

  if (field.type === "date") {
    return (
      <Input
        label={label}
        name={fieldId}
        type="date"
        value={value}
        onChange={onChange}
        error={error}
        required={field.required}
      />
    );
  }

  if (field.type === "decimal" || field.type === "float" || field.type === "integer") {
    return (
      <Input
        label={label}
        name={fieldId}
        type="number"
        value={value}
        onChange={onChange}
        placeholder={`Enter ${label.toLowerCase()}`}
        error={error}
        required={field.required}
      />
    );
  }

  if (field.name === "account_number") {
    return (
      <Input
        label={label}
        name={fieldId}
        value={value}
        onChange={(nextValue) => onChange(nextValue.replace(/\D/g, ""))}
        placeholder={`Enter ${label.toLowerCase()}`}
        error={error}
        required={field.required}
        inputMode="numeric"
        pattern="[0-9]*"
        helperText={field.sensitive ? "Sensitive — stored encrypted" : undefined}
      />
    );
  }

  return (
    <Input
      label={label}
      name={fieldId}
      value={value}
      onChange={onChange}
      placeholder={`Enter ${label.toLowerCase()}`}
      error={error}
      required={field.required}
      helperText={field.sensitive ? "Sensitive — stored encrypted" : undefined}
    />
  );
}

/* ─── AssetFormModal ─────────────────────────────────────────────────── */

type AssetFormModalProps = {
  blueprint: AssetBlueprintResponse;
  editingAsset?: Asset | null;
  initialType?: string;
  profileId: string;
  onCreated: (asset: AssetListItem) => void;
  onUpdated: (asset: AssetListItem) => void;
  onClose: () => void;
  serverError: string | null;
};

function AssetFormModal({
  blueprint,
  editingAsset,
  initialType,
  profileId,
  onCreated,
  onUpdated,
  onClose,
  serverError,
}: AssetFormModalProps) {
  const toast = useToast();

  const isEdit = !!editingAsset;
  const [step, setStep] = useState<"type" | "form">(
    isEdit || initialType ? "form" : "type"
  );
  const [selectedType, setSelectedType] = useState<string>(
    editingAsset?.container_type ?? initialType ?? ""
  );

  const typeBp = blueprint.types.find((t) => t.container_type === selectedType) ?? null;

  const initInstitutionName = editingAsset?.institution_name ?? "";
  const initPickerValue = (() => {
    if (!initInstitutionName) return "";
    const entries = INSTITUTION_CATALOG[editingAsset?.container_type ?? ""] ?? [];
    return entries.some((e) => e.name === initInstitutionName)
      ? initInstitutionName
      : "__other__";
  })();
  const [institutionName, setInstitutionName] = useState(initInstitutionName);
  const [institutionPickerValue, setInstitutionPickerValue] = useState(initPickerValue);
  const [nickname, setNickname] = useState(editingAsset?.nickname ?? "");
  const [approxValue, setApproxValue] = useState(
    editingAsset?.approximate_value != null ? String(editingAsset.approximate_value) : ""
  );
  const [notes, setNotes] = useState(editingAsset?.notes ?? "");
  const [detailForm, setDetailForm] = useState<Record<string, string>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const visibleDetailFields = typeBp ? getVisibleDetailFields(typeBp, detailForm) : [];
  const institutionFieldLabel = INSTITUTION_FIELD_LABELS[selectedType] ?? "Institution";
  const institutionFieldName = `${institutionFieldLabel.toLowerCase()} name`;

  // When type is picked (or on edit mount), init detail form
  useEffect(() => {
    if (!typeBp) return;
    if (isEdit && editingAsset?.detail) {
      setDetailForm(populateDetailForm(typeBp, editingAsset.detail));
    } else {
      setDetailForm(initDetailForm(typeBp));
    }
  }, [typeBp, isEdit, editingAsset]);

  function handleDetailChange(field: AssetFieldBlueprint, value: string) {
    setDetailForm((prev) => {
      const next = { ...prev, [field.name]: value };
      if (selectedType === "BANK_RELATIONSHIP" && field.name === "account_type") {
        if (BANK_DEPOSIT_ACCOUNT_TYPES.has(value)) {
          next.interest_rate = next.interest_rate?.trim() ? next.interest_rate : "0";
        } else {
          next.maturity_date = "";
          next.interest_rate = "0";
        }
      }
      return next;
    });
  }

  function validate(): Record<string, string> {
    const errs: Record<string, string> = {};
    if (!institutionName.trim()) errs.institution_name = "Institution name is required";
    if (approxValue && Number.isNaN(parseFloat(approxValue))) {
      errs.approximate_value = "Enter a valid number";
    }
    if (typeBp) {
      for (const field of visibleDetailFields) {
        const value = detailForm[field.name]?.trim() ?? "";
        const otherOptionValue = getOtherOptionValue(field.enum_options);
        if (otherOptionValue && value === otherOptionValue) {
          errs[`detail_${field.name}`] = `Enter custom ${formatFieldName(field.name).toLowerCase()}`;
          continue;
        }
        if (field.required && !value) {
          if (!isEdit || !field.masked_on_read) {
            errs[`detail_${field.name}`] = `${formatFieldName(field.name)} is required`;
          }
        }
      }
    }
    return errs;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const errs = validate();
    setErrors(errs);
    if (Object.keys(errs).length > 0) return;

    setIsSubmitting(true);
    try {
      const detail = typeBp ? detailFormToPayload(detailForm, visibleDetailFields) : {};
      if (selectedType === "DEMAT_ACCOUNT") {
        detail.broker_name = institutionName.trim();
      }
      if (isEdit && editingAsset) {
        const payload: Record<string, unknown> = {
          profile_id: profileId,
          institution_name: institutionName.trim(),
          nickname: nickname.trim() || null,
          approximate_value: approxValue ? parseFloat(approxValue) : null,
          notes: notes.trim() || null,
        };
        if (Object.keys(detail).length > 0) payload.detail = detail;
        const updated = await apiClient.patch<Asset>(`/assets/${editingAsset.id}`, payload);
        onUpdated(updated);
        toast.show("success", "Asset updated");
      } else {
        const payload = {
          profile_id: profileId,
          container_type: selectedType,
          institution_name: institutionName.trim(),
          nickname: nickname.trim() || null,
          approximate_value: approxValue ? parseFloat(approxValue) : null,
          notes: notes.trim() || null,
          detail,
        };
        const created = await apiClient.post<Asset>("/assets", payload);
        onCreated(created);
        toast.show("success", "Asset added");
      }
      onClose();
    } catch (err) {
      const msg = err instanceof ApiClientError ? err.message : "Something went wrong";
      setErrors({ _form: msg });
    } finally {
      setIsSubmitting(false);
    }
  }

  // ── Step 1: Type picker ──
  if (step === "type") {
    return (
      <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/40 px-4">
        <div className="bg-surface-strong border border-border-light rounded-xl shadow-md w-full max-w-2xl overflow-hidden max-h-[90vh] flex flex-col">
          <div className="flex items-center justify-between px-6 py-4 border-b border-border-light flex-shrink-0">
            <h3 className="text-base font-bold text-text-primary">Choose asset type</h3>
            <button
              type="button"
              className="w-8 h-8 flex items-center justify-center rounded-md text-text-tertiary hover:text-text-primary hover:bg-bg-secondary transition-colors"
              onClick={onClose}
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
          <div className="overflow-y-auto p-6">
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {blueprint.types.map((t) => (
                <button
                  key={t.container_type}
                  type="button"
                  className="flex flex-col items-start gap-2 p-4 rounded-xl border border-border-light bg-surface-base hover:bg-accent-subtle hover:border-accent hover:text-accent transition-all duration-[180ms] text-left group"
                  onClick={() => {
                    setSelectedType(t.container_type);
                    setDetailForm(initDetailForm(t));
                    setInstitutionName("");
                    setInstitutionPickerValue("");
                    setStep("form");
                  }}
                >
                  <span className="w-8 h-8 text-text-secondary group-hover:text-accent transition-colors flex-shrink-0">
                    {CONTAINER_TYPE_ICONS[t.container_type] ?? (
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"><circle cx="12" cy="12" r="10" /></svg>
                    )}
                  </span>
                  <span className="text-sm font-semibold text-text-primary group-hover:text-accent leading-snug">
                    {CONTAINER_TYPE_LABELS[t.container_type] ?? t.container_type}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ── Step 2: Form ──
  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/40 px-4">
      <div className="bg-surface-strong border border-border-light rounded-xl shadow-md w-full max-w-2xl overflow-hidden max-h-[92vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border-light flex-shrink-0">
          <div className="flex items-center gap-2">
            <span className="w-5 h-5 text-accent flex-shrink-0">
              {CONTAINER_TYPE_ICONS[selectedType] ?? null}
            </span>
            <h3 className="text-base font-bold text-text-primary">
              {isEdit ? "Edit asset" : `Add ${CONTAINER_TYPE_LABELS[selectedType] ?? selectedType.toLowerCase()}`}
            </h3>
          </div>
          <button
            type="button"
            className="w-8 h-8 flex items-center justify-center rounded-md text-text-tertiary hover:text-text-primary hover:bg-bg-secondary transition-colors"
            onClick={onClose}
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <form onSubmit={handleSubmit} className="flex flex-col overflow-hidden flex-1">
          <div className="overflow-y-auto px-6 py-5 flex-1">
            {(serverError || errors._form) && (
              <div className="mb-4">
                <Alert variant="error">{serverError ?? errors._form}</Alert>
              </div>
            )}

            {/* Base fields */}
            <div className="mb-5">
              <p className="text-xs font-semibold text-text-tertiary mb-3">Basic information</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 items-start">
                <div className="sm:col-span-2">
                  {(INSTITUTION_CATALOG[selectedType] ?? []).length > 0 ? (
                    <div className="flex flex-col gap-3">
                      <Select
                        label={institutionFieldLabel}
                        name="institution-picker"
                        value={institutionPickerValue}
                        onChange={(val) => {
                          setInstitutionPickerValue(val);
                          setInstitutionName(val !== "__other__" ? val : "");
                        }}
                        options={buildInstitutionOptions(selectedType)}
                        placeholder={`Select ${institutionFieldLabel.toLowerCase()}`}
                        error={institutionPickerValue === "" ? errors.institution_name : undefined}
                        required
                        formatOptionLabel={(opt) => (
                          <InstitutionOptionLabel option={opt} containerType={selectedType} />
                        )}
                      />
                      {institutionPickerValue === "__other__" && (
                        <Input
                          label={institutionFieldName}
                          name="institution-name"
                          value={institutionName}
                          onChange={setInstitutionName}
                          placeholder="e.g. HDFC Bank, LIC, etc."
                          error={errors.institution_name}
                          required
                        />
                      )}
                    </div>
                  ) : (
                    <Input
                      label={institutionFieldName}
                      name="institution-name"
                      value={institutionName}
                      onChange={setInstitutionName}
                      placeholder="e.g. HDFC Bank, LIC, etc."
                      error={errors.institution_name}
                      required
                    />
                  )}
                </div>
                <div className="sm:col-span-2">
                  <Input
                    label="Nickname"
                    name="asset-nickname"
                    value={nickname}
                    onChange={setNickname}
                    placeholder="e.g. My salary account, Dad's policy"
                    helperText="Optional — your personal label for this asset"
                  />
                </div>
                <Input
                  label="Approximate value (₹)"
                  name="approximate-value"
                  type="number"
                  value={approxValue}
                  onChange={setApproxValue}
                  placeholder="Optional"
                  error={errors.approximate_value}
                />
                <Input
                  label="Notes"
                  name="asset-notes"
                  value={notes}
                  onChange={setNotes}
                  placeholder="Optional notes"
                />
              </div>
            </div>

            {/* Detail fields */}
            {typeBp && typeBp.detail_fields.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-text-tertiary mb-3">
                  {CONTAINER_TYPE_LABELS[selectedType] ?? "Asset"} details
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 items-start">
                  {visibleDetailFields.map((field) => (
                    <DynamicFormField
                      key={field.name}
                      field={field}
                      value={detailForm[field.name] ?? ""}
                      onChange={(v) => handleDetailChange(field, v)}
                      error={errors[`detail_${field.name}`]}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center gap-3 justify-end px-6 py-4 border-t border-border-light flex-shrink-0">
            <Button type="button" variant="ghost" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" loading={isSubmitting}>
              {isEdit ? "Save changes" : "Save"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ─── NomineesTab ────────────────────────────────────────────────────── */

function NomineesTab({ asset }: { asset: Asset }) {
  const toast = useToast();
  const [nominees, setNominees] = useState<Nominee[]>([]);
  const [scopeMap, setScopeMap] = useState<Record<string, NomineeScopeResponse[]>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const nomineesPage = await apiClient.get<PaginatedResponse<Nominee>>("/nominees");
      const allNominees = nomineesPage.items;
      setNominees(allNominees);
      // Fetch scope for each nominee in parallel
      const scopeResults = await Promise.all(
        allNominees.map((n) =>
          apiClient
            .get<PaginatedResponse<NomineeScopeResponse>>(`/nominees/${n.id}/scope`)
            .then((page) => ({ id: n.id, scopes: page.items }))
            .catch(() => ({ id: n.id, scopes: [] }))
        )
      );
      const map: Record<string, NomineeScopeResponse[]> = {};
      for (const r of scopeResults) map[r.id] = r.scopes;
      setScopeMap(map);
    } catch (err) {
      const msg = err instanceof ApiClientError ? err.message : "Failed to load nominees";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  function getCurrentPermission(nomineeId: string): string {
    const scopes = scopeMap[nomineeId] ?? [];
    const match = scopes.find((s) => s.container_id === asset.id && s.is_active);
    return match?.permission ?? "";
  }

  async function handlePermissionChange(nomineeId: string, newPermission: string) {
    setSavingId(nomineeId);
    try {
      const currentScopes = scopeMap[nomineeId] ?? [];
      let updatedScopes: { container_id: string; permission: string }[];
      if (!newPermission) {
        // Revoke access
        updatedScopes = currentScopes
          .filter((s) => s.container_id !== asset.id)
          .map((s) => ({ container_id: s.container_id, permission: s.permission }));
      } else {
        // Add or update
        const existing = currentScopes.filter((s) => s.container_id !== asset.id);
        updatedScopes = [
          ...existing.map((s) => ({ container_id: s.container_id, permission: s.permission })),
          { container_id: asset.id, permission: newPermission },
        ];
      }
      const updatedPage = await apiClient.put<PaginatedResponse<NomineeScopeResponse>>(`/nominees/${nomineeId}/scope`, {
        scopes: updatedScopes,
      });
      setScopeMap((prev) => ({ ...prev, [nomineeId]: updatedPage.items }));
      toast.show("success", newPermission ? "Access granted" : "Access revoked");
    } catch (err) {
      const msg = err instanceof ApiClientError ? err.message : "Failed to update access";
      toast.show("error", msg);
    } finally {
      setSavingId(null);
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-10">
        <span className="w-5 h-5 border-2 border-accent border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="py-6">
        <Alert variant="error">{error}</Alert>
        <div className="mt-3 flex justify-center">
          <Button variant="outline" size="sm" onClick={loadData}>Try again</Button>
        </div>
      </div>
    );
  }

  if (nominees.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <div className="w-10 h-10 rounded-full bg-bg-secondary text-text-tertiary flex items-center justify-center mb-3">
          <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
            <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" />
            <path d="M22 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" />
          </svg>
        </div>
        <p className="text-sm font-semibold text-text-primary mb-1">No nominees added yet</p>
        <p className="text-xs text-text-tertiary max-w-xs">
          Add nominees from the Nominees page, then assign them access to this asset.
        </p>
      </div>
    );
  }

  return (
    <div>
      <p className="text-xs text-text-secondary mb-4">
        Control what each nominee can see for this asset. Changes take effect immediately.
      </p>
      <div className="space-y-2">
        {nominees.map((nominee) => {
          const currentPermission = getCurrentPermission(nominee.id);
          const isSaving = savingId === nominee.id;
          const initials = nominee.full_name
            .split(" ")
            .filter(Boolean)
            .map((w) => w[0])
            .slice(0, 2)
            .join("")
            .toUpperCase();

          return (
            <div
              key={nominee.id}
              className="flex items-center gap-3 p-3 rounded-lg border border-border-light bg-surface-base"
            >
              <div className="w-8 h-8 rounded-full bg-accent-subtle text-accent text-xs font-bold flex items-center justify-center flex-shrink-0">
                {initials}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-text-primary truncate">{nominee.full_name}</p>
                <p className="text-xs text-text-tertiary">
                  {formatNomineeRelationship(nominee.relationship)}
                </p>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                {isSaving ? (
                  <span className="w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin" />
                ) : (
                  <div className="w-44 sm:w-52">
                    <Select
                      label=""
                      name={`perm-${nominee.id}`}
                      value={currentPermission}
                      onChange={(v) => handlePermissionChange(nominee.id, v)}
                      options={[{ value: "", label: "No access" }, ...PERMISSION_OPTIONS]}
                      placeholder="No access"
                    />
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ─── DocumentsTab ───────────────────────────────────────────────────── */

function DocumentsTab({ asset, profileId }: { asset: Asset; profileId: string }) {
  const toast = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [documents, setDocuments] = useState<AssetDocumentSummary[]>(
    asset.documents.filter((d) => d.is_active && d.upload_status === "UPLOADED")
  );
  const [isUploading, setIsUploading] = useState(false);
  const [uploadDocType, setUploadDocType] = useState("OTHER");
  const [uploadDocCustomType, setUploadDocCustomType] = useState("");
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [deletingDocId, setDeletingDocId] = useState<string | null>(null);
  const [isDeletingDoc, setIsDeletingDoc] = useState(false);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  function handleUploadClick() {
    if (uploadDocType === "OTHER" && !uploadDocCustomType.trim()) {
      setUploadError("Enter custom document type");
      return;
    }
    fileInputRef.current?.click();
  }

  async function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";

    setIsUploading(true);
    setUploadError(null);
    try {
      const documentType = uploadDocType === "OTHER" ? uploadDocCustomType.trim() : uploadDocType;
      // Step 1: Initiate upload
      const initPayload = {
        profile_id: profileId,
        document_type: documentType,
        original_file_name: file.name,
        mime_type: file.type || "application/octet-stream",
        file_size_bytes: file.size,
      };
      const initiated = await apiClient.post<DocumentUploadInitiateResponse>(
        `/assets/${asset.id}/documents/initiate-upload`,
        initPayload
      );

      // Step 2: Upload to S3
      await fetch(initiated.upload_url, {
        method: "PUT",
        headers: initiated.upload_headers,
        body: file,
      });

      // Step 3: Complete upload
      const completed = await apiClient.post<AssetDocumentSummary>(
        `/assets/${asset.id}/documents/complete-upload`,
        { profile_id: profileId, document_id: initiated.document_id }
      );
      setDocuments((prev) => [completed, ...prev]);
      toast.show("success", "Document uploaded");
    } catch (err) {
      const msg = err instanceof ApiClientError ? err.message : "Upload failed";
      setUploadError(msg);
    } finally {
      setIsUploading(false);
    }
  }

  async function handleDownload(doc: AssetDocumentSummary) {
    setDownloadingId(doc.id);
    try {
      const res = await apiClient.post<{ download_url: string; expires_at: string }>(
        `/documents/${doc.id}/download-url`,
        { profile_id: profileId }
      );
      window.open(res.download_url, "_blank", "noopener,noreferrer");
    } catch (err) {
      const msg = err instanceof ApiClientError ? err.message : "Failed to get download link";
      toast.show("error", msg);
    } finally {
      setDownloadingId(null);
    }
  }

  async function handleDelete() {
    if (!deletingDocId) return;
    setIsDeletingDoc(true);
    try {
      await apiClient.delete(`/documents/${deletingDocId}?profile_id=${profileId}`);
      setDocuments((prev) => prev.filter((d) => d.id !== deletingDocId));
      setDeletingDocId(null);
      toast.show("success", "Document removed");
    } catch (err) {
      const msg = err instanceof ApiClientError ? err.message : "Failed to remove document";
      toast.show("error", msg);
    } finally {
      setIsDeletingDoc(false);
    }
  }

  const uploadDocCustomError =
    uploadDocType === "OTHER" && uploadError === "Enter custom document type"
      ? uploadError
      : undefined;
  const docTypeLabel = (type: string) =>
    DOCUMENT_TYPE_OPTIONS.find((o) => o.value === type)?.label ?? formatOptionName(type);

  return (
    <div>
      {/* Upload area */}
      <div className="mb-5 p-4 rounded-xl border border-dashed border-border-default bg-surface-base">
        <div className="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto] gap-3 items-start">
          <div className={uploadDocType === "OTHER" ? "" : "sm:col-span-2"}>
            <Select
              label="Document type"
              name="upload-doc-type"
              value={uploadDocType}
              onChange={(value) => {
                setUploadDocType(value);
                setUploadError(null);
              }}
              options={DOCUMENT_TYPE_OPTIONS}
            />
          </div>
          {uploadDocType === "OTHER" && (
            <div>
              <Input
                label="Custom document type"
                name="upload-doc-custom-type"
                value={uploadDocCustomType}
                onChange={(value) => {
                  setUploadDocCustomType(value);
                  setUploadError(null);
                }}
                placeholder="e.g. Tax receipt"
                error={uploadDocCustomError}
                required
              />
            </div>
          )}
          <div className="sm:pt-[1.625rem]">
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              onChange={handleFileSelect}
              accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
            />
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="min-h-[2.75rem]"
              loading={isUploading}
              onClick={handleUploadClick}
            >
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" /><line x1="12" y1="3" x2="12" y2="15" />
              </svg>
              {isUploading ? "Uploading..." : "Upload file"}
            </Button>
          </div>
        </div>
        {uploadError && uploadError !== uploadDocCustomError && (
          <p className="text-xs text-error mt-2">{uploadError}</p>
        )}
        <p className="text-xs text-text-tertiary mt-2">PDF, JPG, PNG, DOC up to 10 MB</p>
      </div>

      {/* Delete confirmation */}
      {deletingDocId && (
        <div className="fixed inset-0 z-[300] flex items-center justify-center bg-black/40 px-4">
          <div className="bg-surface-strong border border-border-light rounded-xl shadow-md p-6 w-full max-w-sm">
            <h3 className="text-base font-bold text-text-primary mb-2">Remove document</h3>
            <p className="text-sm text-text-secondary mb-5">This will permanently remove the document. This action cannot be undone.</p>
            <div className="flex items-center gap-3 justify-end">
              <Button type="button" variant="ghost" size="sm" onClick={() => setDeletingDocId(null)} disabled={isDeletingDoc}>
                Cancel
              </Button>
              <Button type="button" variant="danger" size="sm" loading={isDeletingDoc} onClick={handleDelete}>
                Remove
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Document list */}
      {documents.length === 0 ? (
        <div className="text-center py-8">
          <p className="text-sm text-text-secondary">No documents uploaded yet.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {documents.map((doc) => (
            <div
              key={doc.id}
              className="flex items-center gap-3 p-3 rounded-lg border border-border-light bg-surface-base"
            >
              <div className="w-8 h-8 rounded-lg bg-accent-subtle text-accent flex items-center justify-center flex-shrink-0">
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                </svg>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-text-primary truncate">
                  {doc.original_file_name ?? "Unnamed file"}
                </p>
                <p className="text-xs text-text-tertiary">
                  {docTypeLabel(doc.document_type)}
                  {doc.file_size_bytes ? ` · ${formatFileSize(doc.file_size_bytes)}` : ""}
                </p>
              </div>
              <div className="flex items-center gap-1 flex-shrink-0">
                <button
                  type="button"
                  className="w-8 h-8 flex items-center justify-center rounded-md text-text-tertiary hover:text-accent hover:bg-accent-subtle transition-colors"
                  title="Download"
                  onClick={() => handleDownload(doc)}
                  disabled={downloadingId === doc.id}
                >
                  {downloadingId === doc.id ? (
                    <span className="w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                      <polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" />
                    </svg>
                  )}
                </button>
                <button
                  type="button"
                  className="w-8 h-8 flex items-center justify-center rounded-md text-text-tertiary hover:text-error hover:bg-error-subtle transition-colors"
                  title="Remove"
                  onClick={() => setDeletingDocId(doc.id)}
                >
                  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="3 6 5 6 21 6" />
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                  </svg>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ─── AssetDetailModal ───────────────────────────────────────────────── */

type DetailTab = "overview" | "nominees" | "documents";

function AssetDetailModal({
  assetItem,
  profileId,
  blueprint,
  onEdit,
  onClose,
}: {
  assetItem: AssetListItem;
  profileId: string;
  blueprint: AssetBlueprintResponse;
  onEdit: (asset: Asset) => void;
  onClose: () => void;
}) {
  const [activeTab, setActiveTab] = useState<DetailTab>("overview");
  const [fullAsset, setFullAsset] = useState<Asset | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const typeBp = blueprint.types.find((t) => t.container_type === assetItem.container_type) ?? null;

  const loadAsset = useCallback(async () => {
    setIsLoading(true);
    setFetchError(null);
    try {
      const data = await apiClient.get<Asset>(
        `/assets/${assetItem.id}?profile_id=${encodeURIComponent(profileId)}`
      );
      setFullAsset(data);
    } catch (err) {
      const msg = err instanceof ApiClientError ? err.message : "Failed to load asset";
      setFetchError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [assetItem.id, profileId]);

  useEffect(() => {
    loadAsset();
  }, [loadAsset]);

  const tabs: { id: DetailTab; label: string }[] = [
    { id: "overview", label: "Overview" },
    { id: "nominees", label: "Nominees" },
    { id: "documents", label: `Documents${assetItem.document_count > 0 ? ` (${assetItem.document_count})` : ""}` },
  ];

  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/40 px-4">
      <div className="bg-surface-strong border border-border-light rounded-xl shadow-md w-full max-w-2xl overflow-hidden max-h-[92vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border-light flex-shrink-0">
          <div className="flex items-center gap-2.5 min-w-0">
            <InstitutionAvatar containerType={assetItem.container_type} name={assetItem.institution_name} size="sm" />
            <div className="min-w-0">
              <h3 className="text-base font-bold text-text-primary truncate">{assetItem.institution_name}</h3>
              <p className="text-xs text-text-tertiary">
                {assetItem.nickname ?? (CONTAINER_TYPE_LABELS[assetItem.container_type] ?? assetItem.container_type)}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0 ml-4">
            {assetItem.can_edit && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => fullAsset && onEdit(fullAsset)}
                disabled={!fullAsset}
              >
                Edit
              </Button>
            )}
            <button
              type="button"
              className="w-8 h-8 flex items-center justify-center rounded-md text-text-tertiary hover:text-text-primary hover:bg-bg-secondary transition-colors"
              onClick={onClose}
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-border-light flex-shrink-0 px-6">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              className={[
                "py-3 px-1 mr-5 text-sm font-semibold border-b-2 transition-colors",
                activeTab === tab.id
                  ? "border-accent text-accent"
                  : "border-transparent text-text-secondary hover:text-text-primary",
              ].join(" ")}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Body */}
        <div className="overflow-y-auto flex-1 p-6">
          {isLoading ? (
            <div className="flex items-center justify-center py-10">
              <span className="w-5 h-5 border-2 border-accent border-t-transparent rounded-full animate-spin" />
            </div>
          ) : fetchError ? (
            <div className="py-4">
              <Alert variant="error">{fetchError}</Alert>
              <div className="mt-3 flex justify-center">
                <Button variant="outline" size="sm" onClick={loadAsset}>Try again</Button>
              </div>
            </div>
          ) : fullAsset ? (
            <>
              {activeTab === "overview" && (
                <OverviewTab asset={fullAsset} typeBp={typeBp} />
              )}
              {activeTab === "nominees" && (
                <NomineesTab asset={fullAsset} />
              )}
              {activeTab === "documents" && (
                <DocumentsTab asset={fullAsset} profileId={profileId} />
              )}
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}

/* ─── OverviewTab ────────────────────────────────────────────────────── */

function OverviewTab({ asset, typeBp }: { asset: Asset; typeBp: AssetTypeBlueprint | null }) {
  const rows: { label: string; value: string }[] = [];

  if (asset.approximate_value != null) {
    rows.push({ label: "Approximate value", value: formatCurrency(asset.approximate_value) });
  }
  if (asset.notes) {
    rows.push({ label: "Notes", value: asset.notes });
  }

  // Detail fields
  if (typeBp && asset.detail) {
    for (const field of typeBp.detail_fields) {
      const val = asset.detail[field.name];
      if (val == null || val === "") continue;
      rows.push({ label: formatFieldName(field.name), value: String(val) });
    }
  }

  if (rows.length === 0) {
    return (
      <p className="text-sm text-text-tertiary text-center py-8">No additional details recorded.</p>
    );
  }

  return (
    <div className="space-y-3">
      {rows.map((row) => (
        <div key={row.label} className="flex flex-col sm:flex-row sm:items-start gap-0.5 sm:gap-4 py-2 border-b border-border-light last:border-b-0">
          <span className="text-xs font-semibold text-text-tertiary sm:w-44 flex-shrink-0">{row.label}</span>
          <span className="text-sm text-text-primary break-all">{row.value}</span>
        </div>
      ))}
    </div>
  );
}

/* ─── TypeSelectorBar ────────────────────────────────────────────────── */

function TypeSelectorBar({
  types,
  selectedType,
  counts,
  onSelect,
}: {
  types: { container_type: string }[];
  selectedType: string;
  counts: Record<string, number>;
  onSelect: (ct: string) => void;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Scroll selected item into view when it changes
  useEffect(() => {
    if (!scrollRef.current) return;
    const active = scrollRef.current.querySelector<HTMLElement>('[data-active="true"]');
    active?.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "nearest" });
  }, [selectedType]);

  return (
    <div
      ref={scrollRef}
      className="flex gap-1 overflow-x-auto pb-1 -mx-1 px-1"
      style={{ scrollbarWidth: "none" }}
    >
      {types.map((t) => {
        const isActive = t.container_type === selectedType;
        const count = counts[t.container_type] ?? 0;
        return (
          <button
            key={t.container_type}
            type="button"
            data-active={isActive}
            className={[
              "flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-semibold flex-shrink-0 whitespace-nowrap transition-all duration-[180ms]",
              isActive
                ? "bg-accent text-white shadow-sm"
                : "text-text-secondary bg-surface-base border border-border-light hover:bg-bg-secondary hover:text-text-primary",
            ].join(" ")}
            onClick={() => onSelect(t.container_type)}
          >
            <span className="w-3.5 h-3.5 flex-shrink-0">
              {CONTAINER_TYPE_ICONS[t.container_type]}
            </span>
            {CONTAINER_TYPE_LABELS[t.container_type] ?? t.container_type}
            {count > 0 && (
              <span
                className={[
                  "inline-flex items-center justify-center min-w-[1.1rem] h-[1.1rem] rounded-full text-[0.65rem] font-bold px-1",
                  isActive ? "bg-white/20 text-white" : "bg-bg-secondary text-text-tertiary",
                ].join(" ")}
              >
                {count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

/* ─── AssetsPage ─────────────────────────────────────────────────────── */

export default function AssetsPage() {
  const toast = useToast();
  const { activeProfile } = useProfile();
  const profileId = activeProfile?.id ?? "";

  // Data
  const [blueprint, setBlueprint] = useState<AssetBlueprintResponse | null>(null);
  const [assets, setAssets] = useState<AssetListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // Selected type in the type selector
  const [selectedType, setSelectedType] = useState<string>("");

  // Create modal
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // Edit
  const [editingAsset, setEditingAsset] = useState<Asset | null>(null);
  const [editError, setEditError] = useState<string | null>(null);

  // Detail / view
  const [viewingAsset, setViewingAsset] = useState<AssetListItem | null>(null);

  // Delete
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const loadData = useCallback(async () => {
    if (!profileId) return;
    try {
      setFetchError(null);
      const [bp, page] = await Promise.all([
        apiClient.get<AssetBlueprintResponse>("/assets/blueprint"),
        apiClient.get<PaginatedResponse<AssetListItem>>(
          `/assets?profile_id=${encodeURIComponent(profileId)}&limit=100`
        ),
      ]);
      setBlueprint(bp);
      setAssets(page.items);
      // Init selected type to first type in blueprint
      setSelectedType((prev) => prev || bp.types[0]?.container_type || "");
    } catch (err) {
      const msg = err instanceof ApiClientError ? err.message : "Failed to load assets";
      setFetchError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [profileId]);

  useEffect(() => {
    if (profileId) loadData();
  }, [profileId, loadData]);

  // Counts per type
  const countsByType = assets.reduce<Record<string, number>>((acc, a) => {
    acc[a.container_type] = (acc[a.container_type] ?? 0) + 1;
    return acc;
  }, {});

  // Assets for the selected type
  const visibleAssets = assets.filter((a) => a.container_type === selectedType);

  const selectedTypeLabel = CONTAINER_TYPE_LABELS[selectedType] ?? selectedType.toLowerCase();

  // Dynamic columns: first 3 non-masked detail fields for the selected type
  const selectedTypeBp = blueprint?.types.find((t) => t.container_type === selectedType) ?? null;
  const tableColumns = selectedTypeBp
    ? selectedTypeBp.detail_fields.filter((f) => !f.masked_on_read).slice(0, 3)
    : [];

  async function handleDelete() {
    if (!deletingId) return;
    setIsDeleting(true);
    try {
      await apiClient.delete(`/assets/${deletingId}?profile_id=${encodeURIComponent(profileId)}`);
      setAssets((prev) => prev.filter((a) => a.id !== deletingId));
      setDeletingId(null);
      toast.show("success", "Asset removed");
    } catch (err) {
      const msg = err instanceof ApiClientError ? err.message : "Failed to remove asset";
      toast.show("error", msg);
    } finally {
      setIsDeleting(false);
    }
  }

  function handleEditFromDetail(asset: Asset) {
    setViewingAsset(null);
    setEditError(null);
    setEditingAsset(asset);
  }

  async function handleEditFromRow(assetItem: AssetListItem) {
    try {
      const full = await apiClient.get<Asset>(
        `/assets/${assetItem.id}?profile_id=${encodeURIComponent(profileId)}`
      );
      setEditError(null);
      setEditingAsset(full);
    } catch (err) {
      const msg = err instanceof ApiClientError ? err.message : "Failed to load asset";
      toast.show("error", msg);
    }
  }

  if (isLoading || !profileId) {
    return (
      <div className="flex items-center justify-center py-16">
        <span className="w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (fetchError) {
    return (
      <div className="flex flex-col items-center gap-4 py-16">
        <Alert variant="error">{fetchError}</Alert>
        <Button variant="outline" size="sm" onClick={loadData}>Try again</Button>
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-5">
        <p className="text-sm text-text-secondary">
          Manage your financial assets and control what nominees can access.
        </p>
        {blueprint && selectedType && (
          <Button
            type="button"
            variant="primary"
            size="sm"
            className="flex-shrink-0"
            onClick={() => {
              setCreateError(null);
              setShowCreateModal(true);
            }}
          >
            Add {selectedTypeLabel}
          </Button>
        )}
      </div>

      {/* Type selector */}
      {blueprint && (
        <div className="mb-6">
          <TypeSelectorBar
            types={blueprint.types}
            selectedType={selectedType}
            counts={countsByType}
            onSelect={setSelectedType}
          />
        </div>
      )}

      {/* Modals */}
      {showCreateModal && blueprint && (
        <AssetFormModal
          blueprint={blueprint}
          initialType={selectedType}
          profileId={profileId}
          onCreated={(asset) => setAssets((prev) => [asset, ...prev])}
          onUpdated={() => {}}
          onClose={() => setShowCreateModal(false)}
          serverError={createError}
        />
      )}

      {editingAsset && blueprint && (
        <AssetFormModal
          blueprint={blueprint}
          editingAsset={editingAsset}
          profileId={profileId}
          onCreated={() => {}}
          onUpdated={(updated) => {
            setAssets((prev) => prev.map((a) => (a.id === updated.id ? updated : a)));
          }}
          onClose={() => { setEditingAsset(null); setEditError(null); }}
          serverError={editError}
        />
      )}

      {viewingAsset && blueprint && (
        <AssetDetailModal
          assetItem={viewingAsset}
          profileId={profileId}
          blueprint={blueprint}
          onEdit={handleEditFromDetail}
          onClose={() => setViewingAsset(null)}
        />
      )}

      {deletingId && (
        <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/40 px-4">
          <div className="bg-surface-strong border border-border-light rounded-xl shadow-md p-6 w-full max-w-sm">
            <h3 className="text-base font-bold text-text-primary mb-2">Remove asset</h3>
            <p className="text-sm text-text-secondary mb-5">
              This will permanently remove this asset and all associated documents. This action cannot be undone.
            </p>
            <div className="flex items-center gap-3 justify-end">
              <Button type="button" variant="ghost" size="sm" onClick={() => setDeletingId(null)} disabled={isDeleting}>Cancel</Button>
              <Button type="button" variant="danger" size="sm" loading={isDeleting} onClick={handleDelete}>Remove</Button>
            </div>
          </div>
        </div>
      )}

      {/* Asset table for selected type */}
      {visibleAssets.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-14 text-center bg-surface-strong rounded-xl border border-border-light">
          <span className="w-10 h-10 flex items-center justify-center rounded-full bg-accent-subtle text-accent mb-3">
            <span className="w-5 h-5">{CONTAINER_TYPE_ICONS[selectedType]}</span>
          </span>
          <p className="text-sm font-semibold text-text-primary mb-1">
            No {selectedTypeLabel.toLowerCase()} added yet
          </p>
          <p className="text-xs text-text-secondary mb-4 max-w-xs">
            Add your first {selectedTypeLabel.toLowerCase()} to track it here.
          </p>
          <Button
            type="button"
            variant="primary"
            size="sm"
            onClick={() => { setCreateError(null); setShowCreateModal(true); }}
          >
            Add {selectedTypeLabel}
          </Button>
        </div>
      ) : (
        <div className="bg-surface-strong border border-border-light rounded-xl shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left min-w-[560px]">
              <thead>
                <tr className="border-b border-border-light bg-bg-secondary/40">
                  <th className="px-4 py-3 font-semibold text-text-secondary whitespace-nowrap">Institution</th>
                  <th className="px-4 py-3 font-semibold text-text-secondary whitespace-nowrap">Nickname</th>
                  <th className="px-4 py-3 font-semibold text-text-secondary whitespace-nowrap">Value</th>
                  {tableColumns.map((col) => (
                    <th key={col.name} className="px-4 py-3 font-semibold text-text-secondary whitespace-nowrap">
                      {formatFieldName(col.name)}
                    </th>
                  ))}
                  <th className="px-4 py-3 font-semibold text-text-secondary whitespace-nowrap text-center">Docs</th>
                  <th className="px-4 py-3 font-semibold text-text-secondary whitespace-nowrap text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {visibleAssets.map((asset) => (
                  <tr
                    key={asset.id}
                    className="border-b border-border-light last:border-b-0 hover:bg-bg-secondary/30 transition-colors cursor-pointer"
                    onClick={() => setViewingAsset(asset)}
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2.5">
                        <InstitutionAvatar containerType={asset.container_type} name={asset.institution_name} />
                        <span className="font-semibold text-text-primary truncate max-w-[160px]">
                          {asset.institution_name}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-text-secondary text-sm max-w-[140px] truncate">
                      {asset.nickname ?? <span className="text-text-tertiary">—</span>}
                    </td>
                    <td className="px-4 py-3 text-text-secondary whitespace-nowrap">
                      {asset.approximate_value != null ? formatCurrency(asset.approximate_value) : "—"}
                    </td>
                    {tableColumns.map((col) => {
                      const raw = asset.detail_summary[col.name];
                      const display = raw != null && raw !== "" ? String(raw) : "—";
                      return (
                        <td key={col.name} className="px-4 py-3 text-text-secondary text-sm max-w-[160px] truncate">
                          {display}
                        </td>
                      );
                    })}
                    <td className="px-4 py-3 text-center">
                      {asset.document_count > 0 ? (
                        <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-accent-subtle text-accent text-xs font-bold">
                          {asset.document_count}
                        </span>
                      ) : (
                        <span className="text-text-tertiary">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div
                        className="flex items-center gap-1 justify-end"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <button
                          type="button"
                          className="w-7 h-7 flex items-center justify-center rounded-md text-text-tertiary hover:text-accent hover:bg-accent-subtle transition-colors"
                          title="View details"
                          onClick={() => setViewingAsset(asset)}
                        >
                          <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <circle cx="12" cy="12" r="10" />
                            <line x1="12" y1="16" x2="12" y2="12" />
                            <line x1="12" y1="8" x2="12.01" y2="8" />
                          </svg>
                        </button>
                        {asset.can_edit && (
                          <button
                            type="button"
                            className="w-7 h-7 flex items-center justify-center rounded-md text-text-tertiary hover:text-text-primary hover:bg-bg-secondary transition-colors"
                            title="Edit"
                            onClick={() => handleEditFromRow(asset)}
                          >
                            <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                              <path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z" />
                            </svg>
                          </button>
                        )}
                        {asset.can_delete && (
                          <button
                            type="button"
                            className="w-7 h-7 flex items-center justify-center rounded-md text-text-tertiary hover:text-error hover:bg-error-subtle transition-colors"
                            title="Delete"
                            onClick={() => setDeletingId(asset.id)}
                          >
                            <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                              <polyline points="3 6 5 6 21 6" />
                              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                            </svg>
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
