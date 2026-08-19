"use client";

import { useEffect, useState } from "react";

type Theme = "light" | "dark";

const storageKey = "ilaios-theme";

function systemTheme(): Theme {
  return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

function applyTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme;
  document.documentElement.style.colorScheme = theme;
}

export default function ThemeToggle({ locale }: { locale: "en" | "tr" }) {
  const [theme, setTheme] = useState<Theme>("dark");

  useEffect(() => {
    const stored = window.localStorage.getItem(storageKey);
    const resolved: Theme = stored === "light" || stored === "dark" ? stored : systemTheme();
    setTheme(resolved);
    applyTheme(resolved);
  }, []);

  const next = theme === "dark" ? "light" : "dark";
  const label = locale === "tr"
    ? `${next === "light" ? "Açık" : "Koyu"} temaya geç`
    : `Switch to ${next} theme`;

  return <button
    className="theme-toggle"
    type="button"
    aria-label={label}
    title={label}
    onClick={() => {
      setTheme(next);
      applyTheme(next);
      window.localStorage.setItem(storageKey, next);
    }}
  >
    <span aria-hidden="true" className="theme-toggle-icon">{theme === "dark" ? "☼" : "◐"}</span>
    <span>{locale === "tr" ? (theme === "dark" ? "Açık" : "Koyu") : (theme === "dark" ? "Light" : "Dark")}</span>
  </button>;
}
