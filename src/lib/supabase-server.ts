import { createClient } from "@supabase/supabase-js";
import { cookies } from "next/headers";

/**
 * Creates an authenticated Supabase client for server-side API routes.
 * Reads the access token from httpOnly cookies set during login.
 */
export async function createServerSupabase() {
  const cookieStore = await cookies();
  const accessToken = cookieStore.get("sb-access-token")?.value;

  const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    accessToken
      ? { global: { headers: { Authorization: `Bearer ${accessToken}` } } }
      : undefined
  );

  return { supabase, accessToken };
}
