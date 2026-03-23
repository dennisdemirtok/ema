"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Navigation } from "./navigation";

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.push("/login");
    }
  }, [user, loading, router]);

  if (loading) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-[#f6f6f8] gap-4">
        <div className="w-12 h-12 rounded-2xl bg-[#2b6cee] flex items-center justify-center shadow-lg shadow-blue-500/20">
          <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
        </div>
        <span className="text-sm text-gray-400 font-medium">Laddar Tidrapport...</span>
      </div>
    );
  }

  if (!user) return null;

  return (
    <div className="min-h-screen bg-[#f6f6f8]">
      <Navigation />
      <main className="pt-14 md:pl-72">
        <div className="p-4 md:p-6 max-w-3xl mx-auto">{children}</div>
      </main>
    </div>
  );
}
