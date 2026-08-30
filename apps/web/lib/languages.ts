export interface Language {
  code: string
  translationKey: string
  nativeName: string
}

// Prabodh ships English only (Frontend Track §7.3). Trimmed from LearnHouse's
// 22-language list to just English — the other 21 locale JSON files under
// apps/web/locales/ are intentionally left in place (unreachable, harmless,
// and avoid a needless conflict with future upstream merges). Restore
// entries here if multi-language support is ever required again.
export const AVAILABLE_LANGUAGES: Language[] = [
  { code: 'en', translationKey: 'common.english', nativeName: 'English' },
]

export const getLanguageByCode = (code: string): Language | undefined => {
  return AVAILABLE_LANGUAGES.find(lang => lang.code === code)
}

export const getCurrentLanguageNativeName = (currentLang: string): string => {
  const language = getLanguageByCode(currentLang)
  return language?.nativeName || 'English'
}
