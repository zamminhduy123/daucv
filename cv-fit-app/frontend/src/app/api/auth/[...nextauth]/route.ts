import NextAuth from "next-auth";
import GoogleProvider from "next-auth/providers/google";
import type { Session } from "next-auth";
import type { JWT } from "next-auth/jwt";
import jwt from "jsonwebtoken";
import { query } from "@/lib/db";

const nextauthSecret = process.env.NEXTAUTH_SECRET;
if (!nextauthSecret) {
  throw new Error("CRITICAL: NEXTAUTH_SECRET is required.");
}
const fallbackSecret = nextauthSecret;
const SESSION_MAX_AGE_SECONDS = 30 * 24 * 60 * 60;

type SessionWithAccessToken = Session & {
  accessToken?: string;
};

type SessionUserWithId = NonNullable<Session["user"]> & {
  id?: string;
};

function signBackendAccessToken(token: JWT) {
  const now = Math.floor(Date.now() / 1000);
  return jwt.sign(
    {
      ...token,
      iat: now,
      exp: now + SESSION_MAX_AGE_SECONDS,
    },
    fallbackSecret,
    { algorithm: "HS256" }
  );
}

const handler = NextAuth({
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID || "mock-google-client-id",
      clientSecret: process.env.GOOGLE_CLIENT_SECRET || "mock-google-client-secret",
    }),
  ],
  session: {
    strategy: "jwt",
    maxAge: SESSION_MAX_AGE_SECONDS,
  },
  secret: fallbackSecret,
  callbacks: {
    async signIn({ user }) {
      if (!user.email) return false;

      try {
        const name = user.name || user.email.split("@")[0];
        const image = user.image || "";

        // Check if user exists in our postgres db
        const checkRes = await query(
          "SELECT id FROM public.users WHERE email = $1",
          [user.email]
        );

        if (checkRes.rows.length === 0) {
          // New user sign up - assign 20 credits
          const insertRes = await query(
            "INSERT INTO public.users (email, name, image, credits) VALUES ($1, $2, $3, 20) RETURNING id",
            [user.email, name, image]
          );
          user.id = insertRes.rows[0].id;

          // Record sign up transaction ledger
          await query(
            "INSERT INTO public.credit_transactions (user_id, amount, type, description) VALUES ($1, $2, $3, $4)",
            [
              user.id,
              20,
              "signup_bonus",
              "Tặng 20 credits khi đăng ký tài khoản mới.",
            ]
          );
        } else {
          user.id = checkRes.rows[0].id;
          // Sync name/avatar if changed
          await query(
            "UPDATE public.users SET name = $1, image = $2, updated_at = now() WHERE id = $3",
            [name, image, user.id]
          );
        }
        return true;
      } catch (err) {
        console.error("Error in NextAuth signIn callback:", err);
        // Fallback: If DB fails (like credentials not set up yet in local dev),
        // we can still let them log in, and we will mock the user in frontend.
        return true;
      }
    },
    async jwt({ token, user }) {
      if (user) {
        token.id = user.id;
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        (session.user as SessionUserWithId).id = typeof token.id === "string" ? token.id : undefined;
        (session as SessionWithAccessToken).accessToken = signBackendAccessToken(token);
      }
      return session;
    },
  },
  jwt: {
    // Override the default encryption (JWE) to use symmetric signing (HS256)
    // with a shared secret key, enabling standard verification in FastAPI.
    async encode({ secret, token }) {
      return jwt.sign(token!, secret, { algorithm: "HS256" });
    },
    async decode({ secret, token }) {
      return jwt.verify(token!, secret, { algorithms: ["HS256"] }) as JWT;
    },
  },
});

export { handler as GET, handler as POST };
