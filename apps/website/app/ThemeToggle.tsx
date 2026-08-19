"use client";

import { useEffect, useState } from "react";

type Locale = "en" | "tr";
type Theme = "dark" | "light";

const STORAGE_KEY = "ilaios-theme";

function resolveTheme(): Theme {
  if (typeof window === "undefined") return "dark";
  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (stored === "light" || stored === "dark") return stored;
  return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

export default function ThemeToggle({ locale }: { locale: Locale }) {
  const [theme, setTheme] = useState<Theme>("dark");

  useEffect(() => {
    const resolved = resolveTheme();
    setTheme(resolved);
    document.documentElement.dataset.theme = resolved;
    document.documentElement.style.colorScheme = resolved;
  }, []);

  const toggle = () => {
    const next: Theme = theme === "dark" ? "light" : "dark";
    setTheme(next);
    window.localStorage.setItem(STORAGE_KEY, next);
    document.documentElement.dataset.theme = next;
    document.documentElement.style.colorScheme = next;
  };

  const label = theme === "dark"
    ? (locale === "tr" ? "Açık tema" : "Light theme")
    : (locale === "tr" ? "Koyu tema" : "Dark theme");

  return <button className="theme-toggle" type="button" onClick={toggle} aria-label={label} title={label}>
    <span aria-hidden="true">{theme === "dark" ? "☀" : "◐"}</span>
    <strong>{theme === "dark" ? (locale === "tr" ? "Açık" : "Light") : (locale === "tr" ? "Koyu" : "Dark")}</strong>
  </button>;
}
