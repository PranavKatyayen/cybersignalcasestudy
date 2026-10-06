"use client";

import { MoonIcon, SunIcon } from "@/components/icons";

// The theme lives in the data-theme attribute on <html>. The script in layout.tsx sets it before the page paints,
// so there is no flash; this button only flips it and remembers the choice in the browser.
export function ThemeToggle() {
  function toggle() {
    const root = document.documentElement;
    const next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
    root.classList.add("theme-ready"); // enables the short colour transition, only after a deliberate switch
    root.setAttribute("data-theme", next);
    try {
      localStorage.setItem("theme", next);
    } catch {
      // private mode or blocked storage: the theme still changes for this visit
    }
  }

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label="Switch between light and dark theme"
      title="Switch between light and dark theme"
      className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 transition-colors hover:border-slate-300 hover:bg-slate-50 hover:text-slate-900"
    >
      <SunIcon className="theme-icon-sun h-[18px] w-[18px]" />
      <MoonIcon className="theme-icon-moon h-[18px] w-[18px]" />
    </button>
  );
}
