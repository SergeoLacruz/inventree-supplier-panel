import type { LocaleLoader } from '@inventreedb/ui';

// Necessary callback function to dynamically load the locale messages for the plugin
export const loadLocale: LocaleLoader = async (locale: string) =>
  import(`./locales/${locale}/messages.ts`).catch(() => null);
