import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "@locales/en.json";
import tr from "@locales/tr.json";

export const LANGUAGES = ["en", "tr"] as const;
export type Language = (typeof LANGUAGES)[number];

const STORAGE_KEY = "opd.language";

function storedLanguage(): Language | null {
  try {
    const value = window.localStorage.getItem(STORAGE_KEY);
    return (LANGUAGES as readonly string[]).includes(value ?? "") ? (value as Language) : null;
  } catch {
    return null;
  }
}

export function rememberLanguage(lng: Language): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, lng);
  } catch {
    // Storage can be unavailable (private mode, sandboxed frames); the choice then lasts for the visit.
  }
}

void i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, tr: { translation: tr } },
  lng: storedLanguage() ?? "en",
  fallbackLng: "en",
  interpolation: { escapeValue: false },
});

i18n.on("languageChanged", (lng) => {
  document.documentElement.lang = lng;
});
document.documentElement.lang = i18n.language;

export default i18n;
