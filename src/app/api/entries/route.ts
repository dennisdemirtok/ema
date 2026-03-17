import { NextRequest, NextResponse } from "next/server";
import { createServerSupabase } from "@/lib/supabase-server";

export async function GET(request: NextRequest) {
  const { supabase, accessToken } = await createServerSupabase();
  if (!accessToken) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const params = request.nextUrl.searchParams;
  const userId = params.get("user_id");
  const date = params.get("date");
  const dateFrom = params.get("date_from");
  const dateTo = params.get("date_to");
  const fieldsOnly = params.get("fields"); // e.g. "user_id,hours,date" for lightweight queries

  let selectStr = "*, project:tr_projects(*)";
  if (fieldsOnly) selectStr = fieldsOnly;

  let query = supabase.from("tr_time_entries").select(selectStr);

  if (userId) query = query.eq("user_id", userId);
  if (date) query = query.eq("date", date);
  if (dateFrom) query = query.gte("date", dateFrom);
  if (dateTo) query = query.lte("date", dateTo);

  const order = params.get("order") || "date";
  const ascending = params.get("ascending") !== "false";
  query = query.order(order, { ascending });

  const { data, error } = await query;
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });

  return NextResponse.json({ entries: data });
}

export async function POST(request: NextRequest) {
  const { supabase, accessToken } = await createServerSupabase();
  if (!accessToken) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const body = await request.json();
  const { data, error } = await supabase.from("tr_time_entries").insert({
    user_id: body.user_id,
    project_id: body.project_id || null,
    date: body.date,
    hours: body.hours,
    description: body.description || null,
  }).select().single();

  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return NextResponse.json({ entry: data });
}

export async function PATCH(request: NextRequest) {
  const { supabase, accessToken } = await createServerSupabase();
  if (!accessToken) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const body = await request.json();
  const { id, ...updates } = body;

  const { data, error } = await supabase.from("tr_time_entries").update(updates).eq("id", id).select().single();
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });

  return NextResponse.json({ entry: data });
}

export async function DELETE(request: NextRequest) {
  const { supabase, accessToken } = await createServerSupabase();
  if (!accessToken) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const id = request.nextUrl.searchParams.get("id");
  if (!id) return NextResponse.json({ error: "Missing id" }, { status: 400 });

  const { error } = await supabase.from("tr_time_entries").delete().eq("id", id);
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });

  return NextResponse.json({ ok: true });
}
