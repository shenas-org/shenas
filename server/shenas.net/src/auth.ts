import { betterAuth } from "better-auth";
import { Pool } from "pg";

// Load .env for CLI usage (Astro loads it automatically via Vite)
try { await import("dotenv/config"); } catch { /* running inside Astro */ }

const e = (key: string) =>
  (typeof import.meta !== "undefined" && import.meta.env?.[key]) || process.env[key];

export const auth = betterAuth({
  baseURL: e("BETTER_AUTH_URL") || "http://localhost:4321",
  secret: e("BETTER_AUTH_SECRET"),
  database: new Pool({
    connectionString: e("DATABASE_URL"),
  }),
  socialProviders: {
    google: {
      clientId: e("GOOGLE_CLIENT_ID") as string,
      clientSecret: e("GOOGLE_CLIENT_SECRET") as string,
    },
  },
});
