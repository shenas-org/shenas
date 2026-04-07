import tseslint from "typescript-eslint";
import litPlugin from "eslint-plugin-lit";
import prettierConfig from "eslint-config-prettier";

export default tseslint.config(
  {
    ignores: [
      "**/node_modules/**",
      "**/dist/**",
      "**/static/**",
      "**/shenas_frontends/**",
      "**/.venv/**",
      "**/__pycache__/**",
      "**/*.config.js",
      "**/*.config.ts",
    ],
  },
  ...tseslint.configs.recommended,
  {
    files: ["**/*.ts"],
    plugins: {
      lit: litPlugin,
    },
    rules: {
      ...litPlugin.configs.recommended.rules,
      "@typescript-eslint/no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
      "@typescript-eslint/no-explicit-any": "warn",
      "prefer-const": "error",
      "no-var": "error",
      eqeqeq: ["error", "always", { null: "ignore" }],
    },
  },
  prettierConfig,
);
