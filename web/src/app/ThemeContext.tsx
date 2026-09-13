import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

type Theme = "light" | "dark" | "system";
type ResolvedTheme = "light" | "dark";

const ThemeContext = createContext<{
  theme: Theme;
  resolvedTheme: ResolvedTheme;
  toggleTheme: () => void;
} | null>(null);

function initialTheme(): Theme {
  const saved = window.localStorage.getItem("commerce-theme");
  if (saved === "light" || saved === "dark" || saved === "system") return saved;
  return "light";
}

function resolveTheme(theme: Theme): ResolvedTheme {
  if (theme !== "system") return theme;
  return typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-color-scheme: light)").matches
    ? "light"
    : "dark";
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(initialTheme);
  const [resolvedTheme, setResolvedTheme] = useState<ResolvedTheme>(() =>
    resolveTheme(initialTheme()),
  );

  useEffect(() => {
    const media =
      typeof window.matchMedia === "function"
        ? window.matchMedia("(prefers-color-scheme: light)")
        : null;
    const apply = () => {
      const resolved = resolveTheme(theme);
      setResolvedTheme(resolved);
      document.documentElement.dataset.theme = resolved;
    };
    apply();
    window.localStorage.setItem("commerce-theme", theme);
    if (theme === "system") media?.addEventListener("change", apply);
    return () => media?.removeEventListener("change", apply);
  }, [theme]);

  const value = useMemo(
    () => ({
      theme,
      resolvedTheme,
      toggleTheme: () =>
        setTheme((current) =>
          current === "dark"
            ? "light"
            : current === "light"
              ? "system"
              : "dark",
        ),
    }),
    [resolvedTheme, theme],
  );

  return (
    <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
  );
}

export function useTheme() {
  const value = useContext(ThemeContext);
  if (!value) throw new Error("useTheme must be used inside ThemeProvider");
  return value;
}
