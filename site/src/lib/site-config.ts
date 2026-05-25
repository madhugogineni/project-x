const productName = process.env.NEXT_PUBLIC_PRODUCT_NAME ?? "Project X";

export const siteConfig = {
  name: productName,
  tagline: "Financial continuity for the people left behind.",
  description:
    `${productName} helps families organize financial records, documents, and nominee instructions before they are urgently needed.`,
  links: {
    app: process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3021",
    site: process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3020"
  },
  pillars: [
    {
      title: "Asset clarity",
      description:
        "Organize bank accounts, insurance policies, investments, and property records into one structured registry."
    },
    {
      title: "Encrypted documents",
      description:
        "Store supporting files with privacy-first handling so families can locate what matters without exposure to secrets."
    },
    {
      title: "Guided release",
      description:
        "Use inactivity and nominee workflows to decide when information should become available."
    }
  ],
  highlights: [
    "No password storage",
    "No bank integrations",
    "No transaction execution",
    "Clear nominee guidance"
  ]
} as const;
