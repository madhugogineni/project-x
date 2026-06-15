const themeScript = `
  (() => {
    const storageKey = "project-x-app-theme";
    const saved = window.localStorage.getItem(storageKey);
    const theme = saved === "light" || saved === "dark"
      ? saved
      : window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";

    document.documentElement.setAttribute("data-theme", theme);
    document.documentElement.style.colorScheme = theme;
  })();
`;

export function ThemeScript() {
  return <script dangerouslySetInnerHTML={{ __html: themeScript }} />;
}
