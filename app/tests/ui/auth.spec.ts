import { expect, test } from "@playwright/test";

const productName = process.env.NEXT_PUBLIC_PRODUCT_NAME ?? "Project X";

test("login page renders the configured product name", async ({ page }) => {
  await page.goto("/login");

  await expect(page.getByRole("heading", { name: "Log in" })).toBeVisible();
  await expect(page.getByText(`Welcome back to ${productName}`)).toBeVisible();
  await expect(page.getByRole("link", { name: "Sign up" })).toBeVisible();
});

test("signup page exposes the primary onboarding fields", async ({ page }) => {
  await page.goto("/signup");

  await expect(page.getByRole("heading", { name: "Sign up" })).toBeVisible();
  await expect(page.getByText(`Create your ${productName} account`)).toBeVisible();
  await expect(page.getByLabel("Phone number")).toBeVisible();
  await expect(page.getByRole("link", { name: "Log in" })).toBeVisible();
});
