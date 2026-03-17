"use client";

import { useState, useEffect, useCallback } from "react";
import { AppShell } from "@/components/app-shell";
import { useAuth } from "@/lib/auth-context";
import { User } from "@/lib/types";
import { AlertCircle, CheckCircle2, Download, Clock, CalendarDays } from "lucide-react";
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

    try {
      const [usersRes, weekRes, monthRes] = await Promise.all([
        fetch("/api/admin/users?role=worker&is_active=true"),
        fetch(`/api/entries?date_from=${weekStart}&date_to=${weekEnd}&fields=user_id,hours,date`),
        fetch(`/api/entries?date_from=${monthStart}&date_to=${monthEnd}&fields=user_id,hours`),
      ]);

      const usersData = await usersRes.json();
      const weekData = await weekRes.json();
      const monthData = await monthRes.json();

      const users = usersData.users || [];
      const weekEntries = weekData.entries || [];
      const monthEntries = monthData.entries || [];

      const summaries: WorkerSummary[] = users.map((u: User) => ({
        user: u,
        weekHours: weekEntries
          .filter((e: { user_id: string }) => e.user_id === u.id)
          .reduce((sum: number, e: { hours: number }) => sum + Number(e.hours), 0),
        monthHours: monthEntries
          .filter((e: { user_id: string }) => e.user_id === u.id)
          .reduce((sum: number, e: { hours: number }) => sum + Number(e.hours), 0),
        reportedToday: weekEntries.some(
          (e: { user_id: string; date: string }) => e.user_id === u.id && e.date === today
        ),
      }));

      setWorkers(summaries);
    } catch {
      // Handle error
    }
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
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-900 text-white text-sm font-medium hover:bg-slate-800 transition-colors shadow-sm"
          >
            <Download className="w-4 h-4" />
            Exportera CSV
          </a>
        </div>

        {/* Summary cards */}
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm overflow-hidden relative">
            <div className="absolute top-0 left-0 right-0 h-[3px] bg-gradient-to-r from-blue-500 to-blue-400" />
            <div className="flex items-center gap-2 mb-1">
              <Clock className="w-4 h-4 text-blue-500" />
              <span className="text-sm text-slate-500">Denna vecka</span>
            </div>
            <div className="text-2xl font-bold text-slate-900">{totalWeekHours}h</div>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm overflow-hidden relative">
            <div className="absolute top-0 left-0 right-0 h-[3px] bg-gradient-to-r from-indigo-500 to-purple-400" />
            <div className="flex items-center gap-2 mb-1">
              <CalendarDays className="w-4 h-4 text-indigo-500" />
              <span className="text-sm text-slate-500">Denna månad</span>
            </div>
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
              {workers.map((w) => {
                const initials = w.user.name
                  ? w.user.name.split(" ").map((n) => n[0]).join("").toUpperCase().slice(0, 2)
                  : "?";
                return (
                  <Link
                    key={w.user.id}
                    href={`/admin/users/${w.user.id}`}
                    className="block bg-white rounded-xl border border-slate-200 p-4 shadow-sm hover:shadow-md hover:border-blue-300 transition-all duration-150"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-indigo-500 flex items-center justify-center text-sm font-bold text-white flex-shrink-0">
                          {initials}
                        </div>
                        <div>
                          <div className="font-semibold text-slate-900">{w.user.name}</div>
                          <div className="text-sm text-slate-500">{w.user.email}</div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-lg font-bold text-slate-900">{w.weekHours}h</div>
                        <div className="text-xs text-slate-400">denna vecka</div>
                      </div>
                    </div>
                    <div className="mt-2 flex items-center gap-2">
                      {w.reportedToday ? (
                        <span className="inline-flex items-center gap-1 text-xs font-medium bg-green-50 text-green-700 px-2 py-1 rounded-full">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          Rapporterat idag
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-xs font-medium bg-amber-50 text-amber-700 px-2 py-1 rounded-full">
                          <AlertCircle className="w-3.5 h-3.5" />
                          Ej rapporterat idag
                        </span>
                      )}
                      <span className="text-xs text-slate-400 ml-auto">
                        {w.monthHours}h denna månad
                      </span>
                    </div>
                  </Link>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
