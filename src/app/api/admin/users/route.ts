import { NextRequest, NextResponse } from "next/server";
import { createServerSupabase } from "@/lib/supabase-server";

export async function GET(request: NextRequest) {
  const { supabase, accessToken } = await createServerSupabase();
  if (!accessToken) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const params = request.nextUrl.searchParams;
  const role = params.get("role");
  const isActive = params.get("is_active");
  const id = params.get("id");

  if (id) {
    const { data, error } = await supabase.from("tr_users").select("*").eq("id", id).single();
    if (error) return NextResponse.json({ error: error.message }, { status: 500 });
    return NextResponse.json({ user: data });
  }

  let query = supabase.from("tr_users").select("*");
  if (role) query = query.eq("role", role);
  if (isActive) query = query.eq("is_active", isActive === "true");
  query = query.order("name");

  const { data, error } = await query;
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });

  return NextResponse.json({ users: data });
}

export async function POST(request: NextRequest) {
  const { supabase, accessToken } = await createServerSupabase();
  if (!accessToken) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const body = await request.json();
  const { data, error } = await supabase.from("tr_users").insert({
    name: body.name,
    email: body.email,
    role: body.role || "worker",
  }).select().single();

  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return NextResponse.json({ user: data });
}

export async function PATCH(request: NextRequest) {
  const { supabase, accessToken } = await createServerSupabase();
  if (!accessToken) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const body = await request.json();
  const { id, ...updates } = body;

  const { data, error } = await supabase.from("tr_users").update(updates).eq("id", id).select().single();
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });

  return NextResponse.json({ user: data });
}
