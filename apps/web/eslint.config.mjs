export const FEATURE_DOMAINS = [
  "cockpit",
  "inbox",
  "catalog",
  "ontology",
  "gates",
  "finops",
  "admin",
  "workspaces",
];

export default [
  {
    files: ["src/features/**/*.{ts,tsx}"],
    rules: {
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            {
              group: ["../cockpit*", "../inbox*", "../catalog*", "../ontology*", "../gates*", "../finops*", "../admin*", "../workspaces*"],
              message: "Cross-feature imports between src/features/<domaine_A>/ and src/features/<domaine_B>/ are forbidden (AD-19, M11).",
            },
          ],
        },
      ],
    },
  },
];
