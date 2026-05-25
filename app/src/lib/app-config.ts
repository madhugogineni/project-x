const productName = process.env.NEXT_PUBLIC_PRODUCT_NAME ?? "Project X";

export const appConfig = {
  name: productName,
  description:
    `${productName} is the operational interface for profile-aware asset management, encrypted documents, and nominee release workflows.`,
  navigation: [
    {
      href: "/",
      label: "Overview",
      description: "Dashboard and summary"
    },
    {
      href: "/nominees",
      label: "Nominees",
      description: "Manage nominees and access rules"
    },
    {
      href: "/assets",
      label: "Assets",
      description: "Accounts, holdings, and containers"
    },
    {
      href: "/documents",
      label: "Documents",
      description: "Encrypted vault and uploads"
    },
    {
      href: "/profiles",
      label: "Profiles",
      description: "Primary, advisor, and nominee contexts"
    },
    {
      href: "/sessions",
      label: "Sessions",
      description: "Active login sessions"
    },
    {
      href: "/devices",
      label: "Devices",
      description: "Recognized devices"
    }
  ],
  summaryCards: [
    {
      label: "Asset containers",
      value: "06",
      detail: "Banking, brokerage, retirement, property, and insurance groups"
    },
    {
      label: "Encrypted documents",
      value: "14",
      detail: "Files queued for secure storage and structured retrieval"
    },
    {
      label: "Nominee readiness",
      value: "81%",
      detail: "Release workflow coverage across registered asset records"
    }
  ]
} as const;
