import { createClient } from "@supabase/supabase-js";
import { cookies } from "next/headers";

/**
 * Creates an authenticated Supabase client for server-side API routes.
 * Reads the access token from httpOnly cookies set during login.
 * Automatically refreshes the token if expired.
 */
export async function createServerSupabase() {
  const cookieStore = await cookies();
  let accessToken = cookieStore.get("sb-access-token")?.value;
  const refreshToken = cookieStore.get("sb-refresh-token")?.value;

  const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );

  // If we have an access token, try to use it
  if (accessToken) {
    const { data: { user }, error } = await supabase.auth.getUser(accessToken);

    // If token expired but we have refresh token, refresh the session
    if (error && refreshToken) {
      const { data: refreshData, error: refreshError } = await supabase.auth.refreshSession({
        refresh_token: refreshToken,
      });

      if (!refreshError && refreshData.session) {
        accessToken = refreshData.session.access_token;

        // Update cookies with new tokens
        cookieStore.set("sb-access-token", refreshData.session.access_token, {
          httpOnly: true,
          secure: false,
          sameSite: "lax",
          path: "/",
          maxAge: 60 * 60 * 24 * 30,
        });
        cookieStore.set("sb-refresh-token", refreshData.session.refresh_token, {
          httpOnly: true,
          secure: false,
          sameSite: "lax",
          path: "/",
          maxAge: 60 * 60 * 24 * 30,
        });
      }
    }
  }

  // Create client with the (possibly refreshed) access token
  const authenticatedSupabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    accessToken
      ? { global: { headers: { Authorization: `Bearer ${accessToken}` } } }
      : undefined
  );

  return { supabase: authenticatedSupabase, accessToken };
}
