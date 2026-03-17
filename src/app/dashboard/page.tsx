"use client";

import { useState, useEffect, useCallback } from "react";
import { AppShell } from "@/components/app-shell";
import { useAuth } from "@/lib/auth-context";
import { supabase } from "@/lib/supabase";
import { TimeEntry, Project } from "@/lib/types";
import { Plus, Minus, Save, Pencil, Trash2, ChevronLeft, ChevronRight } from "lucide-react";
import { format, addDays, subDays } from "date-fns";
import { sv } from "date-fns/locale";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

function DashboardContent() {
  const { user } = useAuth();
  const searchParams = useSearchParams();
  const initialDate = searchParams.get("date") || format(new Date(), "yyyy-MM-dd");
  const [date, setDate] = useState(initialDate);
  const [projects, setProjects] = useState<Project[]>([]);
  const [entries, setEntries] = useState<TimeEntry[]>([]);
  const [loading, setLoading] = useState(true);

  // Form state
  const [projectId, setProjectId] = useState("");
  const [hours, setHours] = useState(8);
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    if (!user) return;
    setLoading(true);

    const [projectsRes, entriesRes] = await Promise.all([
      supabase.from("projects").select("*").eq("status", "active").order("name"),
      supabase
        .from("time_entries")
        .select("*, project:projects(*)")
        .eq("user_id", user.id)
        .eq("date", date)
        .order("created_at", { ascending: false }),
    ]);

    if (projectsRes.data) setProjects(projectsRes.data);
    if (entriesRes.data) setEntries(entriesRes.data as TimeEntry[]);
    setLoading(false);
  }, [user, date]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  async function handleSave() {
    if (!user) return;
    setSaving(true);

    const entry = {
      user_id: user.id,
      project_id: projectId || null,
      date,
      hours,
      description: description || null,
    };

    if (editingId) {
      await supabase.from("time_entries").update(entry).eq("id", editingId);
      setEditingId(null);
    } else {
      await supabase.from("time_entries").insert(entry);
    }

    setProjectId("");
    setHours(8);
    setDescription("");
    setSaving(false);
    fetchData();
  }

  async function handleDelete(id: string) {
    await supabase.from("time_entries").delete().eq("id", id);
    fetchData();
  }

  function startEdit(entry: TimeEntry) {
    setEditingId(entry.id);
    setProjectId(entry.project_id || "");
    setHours(entry.hours);
    setDescription(entry.description || "");
  }

  function cancelEdit() {
    setEditingId(null);
    setProjectId("");
    setHours(8);
    setDescription("");
  }

  const totalHours = entries.reduce((sum, e) => sum + Number(e.hours), 0);
  const dateObj = new Date(date + "T12:00:00");
  const displayDate = format(dateObj, "EEEE d MMMM", { locale: sv });

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Date selector */}
        <div className="flex items-center justify-between">
          <button
            onClick={() => setDate(format(subDays(dateObj, 1), "yyyy-MM-dd"))}
            className="p-2 rounded-lg hover:bg-slate-200 transition-colors"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <div className="text-center">
            <h2 className="text-lg font-semibold text-slate-900 capitalize">{displayDate}</h2>
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className="text-xs text-blue-600 bg-transparent border-none cursor-pointer"
            />
          </div>
          <button
            onClick={() => setDate(format(addDays(dateObj, 1), "yyyy-MM-dd"))}
            className="p-2 rounded-lg hover:bg-slate-200 transition-colors"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>

        {/* Entry form */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-5 space-y-4">
          <h3 className="font-semibold text-slate-900">
            {editingId ? "Redigera post" : "Ny tidsrapport"}
          </h3>

          {/* Project selector */}
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">Projekt / Adress</label>
            <select
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
              className="w-full px-4 py-3 rounded-xl border border-slate-300 text-slate-900 bg-white focus:ring-2 focus:ring-blue-500 outline-none text-base"
            >
              <option value="">-- Inget projekt --</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>

          {/* Hours with stepper */}
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">Timmar</label>
            <div className="flex items-center gap-3">
              <button
                onClick={() => setHours(Math.max(0.5, hours - 0.5))}
                className="w-12 h-12 rounded-xl bg-slate-100 hover:bg-slate-200 flex items-center justify-center transition-colors"
              >
                <Minus className="w-5 h-5" />
              </button>
              <input
                type="number"
                min="0.5"
                max="24"
                step="0.5"
                value={hours}
                onChange={(e) => setHours(Number(e.target.value))}
                className="flex-1 text-center text-2xl font-bold px-4 py-2 rounded-xl border border-slate-300 focus:ring-2 focus:ring-blue-500 outline-none"
              />
              <button
                onClick={() => setHours(Math.min(24, hours + 0.5))}
                className="w-12 h-12 rounded-xl bg-slate-100 hover:bg-slate-200 flex items-center justify-center transition-colors"
              >
                <Plus className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">Beskrivning</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              placeholder="Beskrivning av utfört arbete..."
              className="w-full px-4 py-3 rounded-xl border border-slate-300 text-slate-900 placeholder:text-slate-400 focus:ring-2 focus:ring-blue-500 outline-none resize-none text-base"
            />
          </div>

          {/* Save / Cancel */}
          <div className="flex gap-3">
            <button
              onClick={handleSave}
              disabled={saving || hours <= 0}
              className="flex-1 flex items-center justify-center gap-2 bg-green-600 hover:bg-green-700 disabled:bg-green-400 text-white font-semibold py-3.5 rounded-xl transition-colors text-base"
            >
              <Save className="w-5 h-5" />
              {saving ? "Sparar..." : editingId ? "Uppdatera" : "Spara"}
            </button>
            {editingId && (
              <button
                onClick={cancelEdit}
                className="px-6 py-3.5 rounded-xl border border-slate-300 text-slate-600 font-medium hover:bg-slate-50 transition-colors"
              >
                Avbryt
              </button>
            )}
          </div>
        </div>

        {/* Today's entries */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-slate-900">Dagens poster</h3>
            <span className="text-sm font-medium text-slate-500">
              Totalt: <span className="text-slate-900">{totalHours}h</span>
            </span>
          </div>

          {loading ? (
            <div className="text-center py-8 text-slate-400">Laddar...</div>
          ) : entries.length === 0 ? (
            <div className="text-center py-8 text-slate-400 bg-white rounded-2xl border border-slate-200">
              Inga poster för detta datum
            </div>
          ) : (
            <div className="space-y-3">
              {entries.map((entry) => (
                <div
                  key={entry.id}
                  className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-lg font-bold text-slate-900">{Number(entry.hours)}h</span>
                        {entry.project && (
                          <span className="text-sm text-blue-600 font-medium truncate">
                            {entry.project.name}
                          </span>
                        )}
                      </div>
                      {entry.description && (
                        <p className="text-sm text-slate-500 mt-1 line-clamp-2">{entry.description}</p>
                      )}
                    </div>
                    <div className="flex gap-1 ml-3">
                      <button
                        onClick={() => startEdit(entry)}
                        className="p-2 rounded-lg text-slate-400 hover:text-blue-600 hover:bg-blue-50 transition-colors"
                      >
                        <Pencil className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleDelete(entry.id)}
                        className="p-2 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}

export default function DashboardPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center"><div className="animate-spin w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full" /></div>}>
      <DashboardContent />
    </Suspense>
  );
}
