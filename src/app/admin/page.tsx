"use client";

import { useState, useEffect, useCallback } from "react";
import { AppShell } from "@/components/app-shell";
import { useAuth } from "@/lib/auth-context";
import { supabase } from "@/lib/supabase";
import { User } from "@/lib/types";
import { AlertCircle, CheckCircle2, Download } from "lucide-react";
import { format, startOfWeek, endOfWeek, startOfMonth, endOfMonth } from "date-fns";
import { sv } from "date-fns/locale";
import Link from "next/link";

interface WorkerSummary {
  user: User;
  weekHours: number;
  monthHours: number;
  reportedToday: boolean;
}

export default function AdminPage() {
  const { user } = useAuth();
  const [workers, setWorkers] = useState<WorkerSummary[]>([]);
  const [loading, setLoading] = useState(true);

  const now = new Date();
  const weekStart = format(startOfWeek(now, { weekStartsOn: 1 }), "yyyy-MM-dd");
  const weekEnd = format(endOfWeek(now, { weekStartsOn: 1 }), "yyyy-MM-dd");
  const monthStart = format(startOfMonth(now), "yyyy-MM-dd");
  const monthEnd = format(endOfMonth(now), "yyyy-MM-dd");
  const today = format(now, "yyyy-MM-dd");

  const fetchData = useCallback(async () => {
    setLoading(true);

    const { data: users } = await supabase
      .from("users")
      .select("*")
      .eq("is_active", true)
      .eq("role", "worker")
      .order("name");

    if (!users) {
      setLoading(false);
      return;
    }

    const { data: weekEntries } = await supabase
      .from("time_entries")
      .select("user_id, hours, date")
      .gte("date", weekStart)
      .lte("date", weekEnd);

    const { data: monthEntries } = await supabase
      .from("time_entries")
      .select("user_id, hours")
      .gte("date", monthStart)
      .lte("date", monthEnd);

    const summaries: WorkerSummary[] = users.map((u) => ({
      user: u as User,
      weekHours: (weekEntries || [])
        .filter((e) => e.user_id === u.id)
        .reduce((sum, e) => sum + Number(e.hours), 0),
      monthHours: (monthEntries || [])
        .filter((e) => e.user_id === u.id)
        .reduce((sum, e) => sum + Number(e.hours), 0),
      reportedToday: (weekEntries || []).some(
        (e) => e.user_id === u.id && e.date === today
      ),
    }));

    setWorkers(summaries);
    setLoading(false);
  }, [weekStart, weekEnd, monthStart, monthEnd, today]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const totalWeekHours = workers.reduce((sum, w) => sum + w.weekHours, 0);
  const totalMonthHours = workers.reduce((sum, w) => sum + w.monthHours, 0);

  if (user?.role !== "admin") {
    return (
      <AppShell>
        <div className="text-center py-12 text-slate-500">
          Du har inte behörighet att se denna sida.
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-slate-900">Översikt</h2>
          <a
            href={`/api/admin/export?from=${monthStart}&to=${monthEnd}`}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-900 text-white text-sm font-medium hover:bg-slate-800 transition-colors"
          >
            <Download className="w-4 h-4" />
            Exportera CSV
          </a>
        </div>

        {/* Summary cards */}
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
            <div className="text-sm text-slate-500">Denna vecka</div>
            <div className="text-2xl font-bold text-slate-900">{totalWeekHours}h</div>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
            <div className="text-sm text-slate-500">Denna månad</div>
            <div className="text-2xl font-bold text-slate-900">{totalMonthHours}h</div>
          </div>
        </div>

        {/* Workers */}
        <div>
          <h3 className="font-semibold text-slate-900 mb-3">Anställda</h3>
          {loading ? (
            <div className="text-center py-8 text-slate-400">Laddar...</div>
          ) : (
            <div className="space-y-3">
              {workers.map((w) => (
                <Link
                  key={w.user.id}
                  href={`/admin/users/${w.user.id}`}
                  className="block bg-white rounded-xl border border-slate-200 p-4 shadow-sm hover:border-blue-300 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-semibold text-slate-900">{w.user.name}</div>
                      <div className="text-sm text-slate-500">{w.user.email}</div>
                    </div>
                    <div className="text-right">
                      <div className="text-lg font-bold text-slate-900">{w.weekHours}h</div>
                      <div className="text-xs text-slate-400">denna vecka</div>
                    </div>
                  </div>
                  <div className="mt-2 flex items-center gap-2">
                    {w.reportedToday ? (
                      <span className="flex items-center gap-1 text-xs text-green-600">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        Rapporterat idag
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-xs text-amber-600">
                        <AlertCircle className="w-3.5 h-3.5" />
                        Ej rapporterat idag
                      </span>
                    )}
                    <span className="text-xs text-slate-400 ml-auto">
                      {w.monthHours}h denna månad
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
