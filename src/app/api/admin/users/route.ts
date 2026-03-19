import { NextRequest, NextResponse } from "next/server";
import { createServerSupabase } from "@/lib/supabase-server";
import { createClient } from "@supabase/supabase-js";

// Service role client for creating auth users
function getServiceClient() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL || process.env.SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_KEY!
  );
}

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
  const { name, email, password, role } = body;

  if (!name || !email || !password) {
    return NextResponse.json({ error: "Namn, email och lösenord krävs" }, { status: 400 });
  }

  // Step 1: Create user in Supabase Auth (with service role key)
  const serviceClient = getServiceClient();
  const { data: authData, error: authError } = await serviceClient.auth.admin.createUser({
    email,
    password,
    email_confirm: true, // Auto-confirm email
  });

  if (authError) {
    return NextResponse.json({ error: `Auth: ${authError.message}` }, { status: 500 });
  }

  // Step 2: Create profile in tr_users with SAME ID as auth user
  const { data, error } = await serviceClient.from("tr_users").insert({
    id: authData.user.id, // Link to auth user
    name,
    email,
    role: role || "worker",
  }).select().single();

  if (error) {
    // Cleanup: delete auth user if profile creation fails
    await serviceClient.auth.admin.deleteUser(authData.user.id);
    return NextResponse.json({ error: `Profile: ${error.message}` }, { status: 500 });
  }

  return NextResponse.json({ user: data });
}

export async function DELETE(request: NextRequest) {
  const { accessToken } = await createServerSupabase();
  if (!accessToken) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const id = request.nextUrl.searchParams.get("id");
  if (!id) return NextResponse.json({ error: "ID krävs" }, { status: 400 });

  const serviceClient = getServiceClient();

  // Delete from tr_users first
  const { error: dbError } = await serviceClient.from("tr_users").delete().eq("id", id);
  if (dbError) return NextResponse.json({ error: `DB: ${dbError.message}` }, { status: 500 });

  // Delete from Supabase Auth
  const { error: authError } = await serviceClient.auth.admin.deleteUser(id);
  if (authError) return NextResponse.json({ error: `Auth: ${authError.message}` }, { status: 500 });

  return NextResponse.json({ success: true });
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
