import { NextRequest, NextResponse } from "next/server";
import { createServerSupabase } from "@/lib/supabase-server";

export async function GET(request: NextRequest) {
  const { supabase, accessToken } = await createServerSupabase();
  if (!accessToken) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const { searchParams } = new URL(request.url);
  const from = searchParams.get("from");
  const to = searchParams.get("to");
  const userId = searchParams.get("user");

  let query = supabase
    .from("tr_time_entries")
    .select("date, hours, description, user:tr_users(name), project:tr_projects(name)")
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
