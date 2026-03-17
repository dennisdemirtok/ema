import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";

export async function GET(request: NextRequest) {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

  const authHeader = request.headers.get("authorization");
  const cookieHeader = request.headers.get("cookie");

  // Create client with user's auth
  const supabase = createClient(supabaseUrl, supabaseAnonKey, {
    global: {
      headers: {
        ...(authHeader ? { authorization: authHeader } : {}),
        ...(cookieHeader ? { cookie: cookieHeader } : {}),
      },
    },
  });

  const { searchParams } = new URL(request.url);
  const from = searchParams.get("from");
  const to = searchParams.get("to");
  const userId = searchParams.get("user");

  let query = supabase
    .from("time_entries")
    .select("date, hours, description, user:users(name), project:projects(name)")
    .order("date", { ascending: true });

  if (from) query = query.gte("date", from);
  if (to) query = query.lte("date", to);
  if (userId) query = query.eq("user_id", userId);

  const { data, error } = await query;

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  // Build CSV
  const rows = [["Anställd", "Datum", "Projekt", "Timmar", "Beskrivning"]];

  interface EntryRow {
    date: string;
    hours: number;
    description: string | null;
    user: { name: string } | null;
    project: { name: string } | null;
  }

  for (const entry of (data as unknown as EntryRow[]) || []) {
    rows.push([
      entry.user?.name || "",
      entry.date,
      entry.project?.name || "",
      String(entry.hours),
      (entry.description || "").replace(/"/g, '""'),
    ]);
  }

  const csv = rows.map((row) => row.map((cell) => `"${cell}"`).join(",")).join("\n");

  return new NextResponse(csv, {
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "Content-Disposition": `attachment; filename="tidrapport-${from || "alla"}-${to || "alla"}.csv"`,
    },
  });
}
