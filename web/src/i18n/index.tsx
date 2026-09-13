import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { ar } from "./ar";
import { en } from "./en";

type Language = "ar" | "en";
type Messages = typeof ar;

const LanguageContext = createContext<{
  language: Language;
  messages: Messages;
  toggle: () => void;
} | null>(null);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = useState<Language>(() =>
    localStorage.getItem("commerce-language") === "en" ? "en" : "ar",
  );
  useEffect(() => {
    document.documentElement.lang = language;
    document.documentElement.dir = language === "ar" ? "rtl" : "ltr";
    localStorage.setItem("commerce-language", language);
  }, [language]);
  const value = useMemo(
    () => ({
      language,
      messages: language === "ar" ? ar : en,
      toggle: () => setLanguage((current) => (current === "ar" ? "en" : "ar")),
    }),
    [language],
  );
  return (
    <LanguageContext.Provider value={value}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context)
    throw new Error("useLanguage must be used inside LanguageProvider");
  return context;
}
