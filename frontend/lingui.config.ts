import { formatter } from "@lingui/format-po";

/** @type {import('@lingui/conf').LinguiConfig} */
export default {
  locales: [
    "de",
    "en",
    "es",
    "fr",
    "it",
    "ja",
    "ru",
    "zh_Hans",
    "zh_Hant",
    "pseudo-LOCALE",
  ],
  sourceLocale: "en",
  fallbackLocales: {
    default: "en",
    "pseudo-LOCALE": "en",
  },
  catalogs: [
    {
      path: "src/locales/{locale}/messages",
      include: ["src"],
      exclude: ["**/node_modules/**", "./dist/**"],
    },
  ],
  format: formatter({ lineNumbers: false }),
  orderBy: "origin",
};
