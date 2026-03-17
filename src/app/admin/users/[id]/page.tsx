"use client";

import { useState, useEffect, useCallback } from "react";
import { AppShell } from "@/components/app-shell";
import { useAuth } from "@/lib/auth-context";
import { User, TimeEntry } from "@/lib/types";
import { ArrowLeft, Download } from "lucide-react";
import { format, subDays } from "date-fns";
import { sv } from "date-fns/locale";
import Link from "next/link";
import { useParams } from "next/navigation";

export default function UserDetailPage() {
  const { user: admin } = useAuth();
  const params = useParams();
  const userId = params.id as string;

  const [worker, setWorker] = useState<User | null>(null);
  const [entries, setEntries] = useState<TimeEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [from, setFrom] = useState(format(subDays(new Date(), 30), "yyyy-MM-dd"));
  const [to, setTo] = useState(format(new Date(), "yyyy-MM-dd"));

  const fetchData = useCallback(async () => {
    setLoading(true);

    try {
      const [userRes, entriesRes] = await Promise.all([
        fetch(`/api/admin/users?id=${userId}`),
        fetch(`/api/entries?user_id=${userId}&date_from=${from}&date_to=${to}&order=date&ascending=false`),
      ]);

      const userData = await userRes.json();
      const entriesData = await entriesRes.json();

      if (userData.user) setWorker(userData.user as User);
      if (entriesData.entries) setEntries(entriesData.entries as TimeEntry[]);
    } catch {
      // Handle error
    }
    setLoading(false);
  }, [userId, from, to]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const totalHours = entries.reduce((sum, e) => sum + Number(e.hours), 0);

  if (admin?.role !== "admin") {
    return (
      <AppShell>
        <div className="text-center py-12 text-slate-500">Ingen behörighet.</div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center gap-3">
          <Link
            href="/admin"
            className="p-2 rounded-lg hover:bg-slate-200 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h2 className="text-xl font-bold text-slate-900">
              {worker?.name || "Laddar..."}
            </h2>
            <p className="text-sm text-slate-500">{worker?.email}</p>
          </div>
        </div>

        {/* Date filter */}
        <div className="flex gap-3 items-end">
          <div className="flex-1">
            <label className="block text-xs font-medium text-slate-500 mb-1">Från</label>
            <input
              type="date"
              value={from}
              onChange={(e) => setFrom(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm"
            />
          </div>
          <div className="flex-1">
            <label className="block text-xs font-medium text-slate-500 mb-1">Till</label>
            <input
              type="date"
              value={to}
              onChange={(e) => setTo(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm"
            />
          </div>
          <a
            href={`/api/admin/export?user=${userId}&from=${from}&to=${to}`}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-slate-900 text-white text-sm font-medium hover:bg-slate-800 transition-colors whitespace-nowrap"
          >
            <Download className="w-4 h-4" />
            CSV
          </a>
        </div>

        {/* Summary */}
        <div className="bg-slate-900 text-white rounded-xl p-4 flex items-center justify-between">
          <span className="text-sm text-slate-300">Total tid</span>
          <span className="text-2xl font-bold">{totalHours}h</span>
        </div>

        {/* Entries table */}
        {loading ? (
          <div className="text-center py-8 text-slate-400">Laddar...</div>
        ) : entries.length === 0 ? (
          <div className="text-center py-8 text-slate-400 bg-white rounded-xl border border-slate-200">
            Inga poster för vald period
          </div>
        ) : (
          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50">
                    <th className="text-left p-3 font-medium text-slate-600">Datum</th>
                    <th className="text-left p-3 font-medium text-slate-600">Projekt</th>
                    <th className="text-right p-3 font-medium text-slate-600">Timmar</th>
                    <th className="text-left p-3 font-medium text-slate-600">Beskrivning</th>
                  </tr>
                </thead>
                <tbody>
                  {entries.map((entry) => (
                    <tr key={entry.id} className="border-b border-slate-100 last:border-0">
                      <td className="p-3 text-slate-900 whitespace-nowrap">
                        {format(new Date(entry.date + "T12:00:00"), "d MMM", { locale: sv })}
                      </td>
                      <td className="p-3 text-blue-600">
                        {entry.project?.name || "–"}
                      </td>
                      <td className="p-3 text-right font-semibold text-slate-900">
                        {Number(entry.hours)}h
                      </td>
                      <td className="p-3 text-slate-500 max-w-[200px] truncate">
                        {entry.description || "–"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
