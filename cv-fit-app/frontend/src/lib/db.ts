import { Pool } from "pg";

const connectionString = process.env.DATABASE_URL;

if (!connectionString) {
  console.warn(
    "WARNING: DATABASE_URL is not set. NextAuth database operations will fail."
  );
}

export const pool = new Pool({
  connectionString,
  ssl:
    connectionString &&
    (connectionString.includes("supabase.co") ||
      connectionString.includes("neon.tech"))
      ? { rejectUnauthorized: false }
      : undefined,
});

export async function query(text: string, params?: any[]) {
  const start = Date.now();
  const res = await pool.query(text, params);
  const duration = Date.now() - start;
  console.log("Executed query", { text, duration, rows: res.rowCount });
  return res;
}
