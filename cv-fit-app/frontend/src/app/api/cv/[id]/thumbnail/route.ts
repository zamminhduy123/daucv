import { NextResponse } from "next/server";
import { getServerSession } from "next-auth/next";
import { authOptions } from "@/app/api/auth/[...nextauth]/route";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

interface RouteContext {
  params: Promise<{ id: string }> | { id: string };
}

export async function GET(req: Request, context: RouteContext) {
  try {
    const session = (await getServerSession(authOptions)) as {
      accessToken?: string;
    } | null;

    if (!session?.accessToken) {
      return new NextResponse("Unauthorized", { status: 401 });
    }

    const { id } = await Promise.resolve(context.params);
    if (!id) {
      return new NextResponse("Missing CV ID", { status: 400 });
    }

    const url = new URL(req.url);
    const v = url.searchParams.get("v");
    const query = v ? `?v=${encodeURIComponent(v)}` : "";

    const backendRes = await fetch(`${API_URL}/api/user/cv/${id}/thumbnail${query}`, {
      headers: {
        Authorization: `Bearer ${session.accessToken}`,
      },
      signal: AbortSignal.timeout(15_000),
    });

    if (!backendRes.ok) {
      return new NextResponse(null, { status: backendRes.status });
    }

    const imageBuffer = await backendRes.arrayBuffer();
    const contentType = backendRes.headers.get("content-type") || "image/webp";
    return new NextResponse(imageBuffer, {
      status: 200,
      headers: {
        "Content-Type": contentType,
        "Cache-Control": "private, max-age=86400, stale-while-revalidate=604800",
      },
    });
  } catch (error) {
    console.error("Failed to proxy CV thumbnail:", error);
    return new NextResponse(null, { status: 500 });
  }
}
