# ORCIA Frontend & SDK Layer Rules (`apps/web`, `packages/ui`, `packages/api-client`)

Load before editing frontend routes, `@orcia/ui` primitives, i18n dictionaries, or the generated API SDK.

- **[R-CORE-05]** Never hand-edit `packages/api-client/src/generated/` or write untyped `fetch()` in `apps/web`; regenerate the OpenAPI 3.1 SDK (`0-diff` gate).
- **[R-CORE-10]** UI & Bilingual policy: keep Direction C tokens (`tokens.css`) and components in `@orcia/ui` (no router/API imports, `#6D28D9` reserved for `HumanLedAnchorCard`); zero internal jargon, `< 2 s` labels, systematic `ⓘ` contextual help; keep all chat, docs, commits, and code comments in **English** while keeping the web app and RFC 9457 errors 100% bilingual `fr`/`en` via typed `i18n` dicts (never inline `locale === "fr"` ternaries).
