import { NextResponse } from "next/server";
import { query } from "@/lib/db";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const res = await query(
      "SELECT id, name, avatar, rating, content, created_at FROM public.feedbacks WHERE is_public = TRUE ORDER BY created_at DESC"
    );
    return NextResponse.json(res.rows);
  } catch (err) {
    console.error("Error fetching feedbacks directly from db:", err);
    return NextResponse.json({ error: "Failed to fetch feedbacks" }, { status: 500 });
  }
}
