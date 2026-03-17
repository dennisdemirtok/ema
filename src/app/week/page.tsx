"use client";

import { useState, useEffect, useCallback } from "react";
import { AppShell } from "@/components/app-shell";
import { useAuth } from "@/lib/auth-context";
import { supabase } from "@/lib/supabase";
import { TimeEntry } from "@/lib/types";
import { ChevronLeft, ChevronRight, CalendarX2 } from "lucide-react";
import { format, startOfWeek, endOfWeek, addWeeks, subWeeks, eachDayOfInterval, isSameDay } from "date-fns";
import { sv } from "date-fns/locale";
import { useRouter } from "next/navigation";

export default function WeekPage() {
  const { user } = useAuth();
  const router = useRouter();
  const [weekStart, setWeekStart] = useState(() =>
    startOfWeek(new Date(), { weekStartsOn: 1 })
  );
  const [entries, setEntries] = useState<TimeEntry[]>([]);
  const [loading, setLoading] = useState(true);

  const weekEnd = endOfWeek(weekStart, { weekStartsOn: 1 });
  const days = eachDayOfInterval({ start: weekStart, end: weekEnd });

  const fetchEntries = useCallback(async () => {
    if (!user) return;
    setLoading(true);

    const { data } = await supabase
      .from("time_entries")
      .select("*, project:projects(*)")
      .eq("user_id", user.id)
      .gte("date", format(weekStart, "yyyy-MM-dd"))
      .lte("date", format(weekEnd, "yyyy-MM-dd"))
      .order("date");

    if (data) setEntries(data as TimeEntry[]);
    setLoading(false);
  }, [user, weekStart, weekEnd]);

  useEffect(() => {
    fetchEntries();
  }, [fetchEntries]);

  function getEntriesForDay(day: Date) {
    return entries.filter((e) => isSameDay(new Date(e.date + "T12:00:00"), day));
  }

  function getHoursForDay(day: Date) {
    return getEntriesForDay(day).reduce((sum, e) => sum + Number(e.hours), 0);
  }

  const totalWeek = entries.reduce((sum, e) => sum + Number(e.hours), 0);
  const isToday = (day: Date) => isSameDay(day, new Date());
  const TARGET_HOURS = 8;

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Week navigator */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-3 flex items-center justify-between">
          <button
            onClick={() => setWeekStart(subWeeks(weekStart, 1))}
            className="p-2 rounded-lg hover:bg-slate-100 transition-colors"
          >
            <ChevronLeft className="w-5 h-5 text-slate-600" />
          </button>
          <div className="text-center">
            <div className="flex items-center justify-center gap-2">
              <span className="text-2xl font-bold text-slate-900">
                {format(weekStart, "w", { locale: sv })}
              </span>
              <span className="text-sm font-medium text-slate-500 uppercase tracking-wide">vecka</span>
            </div>
            <p className="text-sm text-slate-500">
              {format(weekStart, "d MMM", { locale: sv })} – {format(weekEnd, "d MMM yyyy", { locale: sv })}
            </p>
          </div>
          <button
            onClick={() => setWeekStart(addWeeks(weekStart, 1))}
            className="p-2 rounded-lg hover:bg-slate-100 transition-colors"
          >
            <ChevronRight className="w-5 h-5 text-slate-600" />
          </button>
        </div>

        {/* Day cards */}
        {loading ? (
          <div className="text-center py-8 text-slate-400">Laddar...</div>
        ) : (
          <div className="space-y-2">
            {days.map((day) => {
              const dayHours = getHoursForDay(day);
              const dayEntries = getEntriesForDay(day);
              const dayStr = format(day, "yyyy-MM-dd");
              const progress = Math.min((dayHours / TARGET_HOURS) * 100, 100);
              const isTodayDay = isToday(day);

              return (
                <button
                  key={dayStr}
                  onClick={() => router.push(`/dashboard?date=${dayStr}`)}
                  className={`w-full text-left bg-white rounded-xl border p-4 shadow-sm transition-all duration-150 hover:shadow-md ${
                    isTodayDay
                      ? "border-blue-400 ring-2 ring-blue-100 border-l-4 border-l-blue-500 bg-blue-50/30"
                      : "border-slate-200 hover:border-blue-300"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {dayHours === 0 && (
                        <CalendarX2 className="w-4 h-4 text-slate-300" />
                      )}
                      <span className="font-semibold text-slate-900 capitalize">
                        {format(day, "EEEE", { locale: sv })}
                      </span>
                      <span className="text-sm text-slate-500">
                        {format(day, "d/M")}
                      </span>
                    </div>
                    <span
                      className={`text-lg font-bold ${
                        dayHours >= TARGET_HOURS
                          ? "text-green-600"
                          : dayHours > 0
                          ? "text-amber-600"
                          : "text-slate-300"
                      }`}
                    >
                      {dayHours > 0 ? `${dayHours}h` : "–"}
                    </span>
                  </div>

                  {/* Progress bar */}
                  <div className="mt-2 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-300 ${
                        dayHours >= TARGET_HOURS
                          ? "bg-gradient-to-r from-green-500 to-emerald-500"
                          : dayHours > 0
                          ? "bg-gradient-to-r from-amber-400 to-amber-500"
                          : "bg-slate-100"
                      }`}
                      style={{ width: `${progress}%` }}
                    />
                  </div>

                  {dayEntries.length > 0 && (
                    <div className="mt-2 space-y-1">
                      {dayEntries.map((e) => (
                        <div key={e.id} className="text-sm text-slate-500 flex gap-2">
                          <span className="font-medium text-slate-600">{Number(e.hours)}h</span>
                          {e.project && <span className="text-blue-500">{e.project.name}</span>}
                          {e.description && (
                            <span className="truncate">{e.description}</span>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        )}

        {/* Week total */}
        <div className="bg-gradient-to-r from-slate-800 to-slate-900 text-white rounded-2xl p-5 text-center shadow-lg">
          <span className="text-sm text-slate-400 font-medium uppercase tracking-wide">Veckans total</span>
          <div className="text-4xl font-bold mt-1">{totalWeek}h</div>
        </div>
      </div>
    </AppShell>
  );
}
