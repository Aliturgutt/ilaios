"use client";

type Locale = "en" | "tr";
type Theme = "dark" | "light";

function currentTheme(): Theme {
  return document.documentElement.dataset.theme === "light" ? "light" : "dark";
}

export default function ThemeToggle({ locale }: { locale: Locale }) {
  const label = locale === "tr" ? "Temayı değiştir" : "Toggle theme";

  const toggle = () => {
    const next: Theme = currentTheme() === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    document.documentElement.style.colorScheme = next;
  };

  return <button className="theme-toggle" type="button" onClick={toggle} aria-label={label} title={label}>
    <span aria-hidden="true">◐</span>
    <strong>{locale === "tr" ? "Tema" : "Theme"}</strong>
  </button>;
}
