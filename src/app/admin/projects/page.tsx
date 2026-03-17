"use client";

import { useState, useEffect, useCallback } from "react";
import { AppShell } from "@/components/app-shell";
import { useAuth } from "@/lib/auth-context";
import { supabase } from "@/lib/supabase";
import { Project } from "@/lib/types";
import { Plus, Pause, Play, CheckCircle2 } from "lucide-react";

export default function ProjectsPage() {
  const { user } = useAuth();
  const [projects, setProjects] = useState<(Project & { total_hours: number })[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [saving, setSaving] = useState(false);

  const fetchProjects = useCallback(async () => {
    setLoading(true);

    const { data: projectList } = await supabase
      .from("projects")
      .select("*")
      .order("status")
      .order("name");

    if (!projectList) {
      setLoading(false);
      return;
    }

    // Get total hours per project
    const { data: hoursSummary } = await supabase
      .from("time_entries")
      .select("project_id, hours");

    const hoursMap: Record<string, number> = {};
    (hoursSummary || []).forEach((e) => {
      if (e.project_id) {
        hoursMap[e.project_id] = (hoursMap[e.project_id] || 0) + Number(e.hours);
      }
    });

    setProjects(
      projectList.map((p) => ({
        ...(p as Project),
        total_hours: hoursMap[p.id] || 0,
      }))
    );
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  async function handleAdd() {
    setSaving(true);
    await supabase.from("projects").insert({
      name: newName,
      description: newDesc || null,
    });
    setNewName("");
    setNewDesc("");
    setShowAdd(false);
    setSaving(false);
    fetchProjects();
  }

  async function updateStatus(id: string, status: "active" | "completed" | "paused") {
    await supabase.from("projects").update({ status }).eq("id", id);
    fetchProjects();
  }

  const statusIcon = {
    active: <Play className="w-3.5 h-3.5 text-green-600" />,
    paused: <Pause className="w-3.5 h-3.5 text-amber-600" />,
    completed: <CheckCircle2 className="w-3.5 h-3.5 text-slate-400" />,
  };

  const statusLabel = {
    active: "Aktiv",
    paused: "Pausad",
    completed: "Klar",
  };

  if (user?.role !== "admin") {
    return (
      <AppShell>
        <div className="text-center py-12 text-slate-500">Ingen behörighet.</div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-slate-900">Projekt</h2>
          <button
            onClick={() => setShowAdd(!showAdd)}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors"
          >
            <Plus className="w-4 h-4" />
            Nytt projekt
          </button>
        </div>

        {/* Add form */}
        {showAdd && (
          <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-4 shadow-sm">
            <h3 className="font-semibold text-slate-900">Nytt projekt</h3>
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1">
                Projektnamn / Adress
              </label>
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                className="w-full px-4 py-3 rounded-xl border border-slate-300 text-base"
                placeholder="t.ex. Storgatan 15"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1">
                Beskrivning (valfritt)
              </label>
              <textarea
                value={newDesc}
                onChange={(e) => setNewDesc(e.target.value)}
                rows={2}
                className="w-full px-4 py-3 rounded-xl border border-slate-300 text-base resize-none"
                placeholder="Kort beskrivning av jobbet..."
              />
            </div>
            <button
              onClick={handleAdd}
              disabled={saving || !newName}
              className="w-full bg-green-600 hover:bg-green-700 disabled:bg-green-400 text-white font-semibold py-3 rounded-xl transition-colors"
            >
              {saving ? "Sparar..." : "Skapa"}
            </button>
          </div>
        )}

        {/* Project list */}
        {loading ? (
          <div className="text-center py-8 text-slate-400">Laddar...</div>
        ) : (
          <div className="space-y-3">
            {projects.map((p) => (
              <div
                key={p.id}
                className={`bg-white rounded-xl border border-slate-200 p-4 shadow-sm ${
                  p.status === "completed" ? "opacity-60" : ""
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      {statusIcon[p.status]}
                      <span className="font-semibold text-slate-900">{p.name}</span>
                    </div>
                    {p.description && (
                      <p className="text-sm text-slate-500 mt-1">{p.description}</p>
                    )}
                    <div className="text-sm text-slate-400 mt-1">
                      Nedlagd tid: <span className="font-medium text-slate-600">{p.total_hours}h</span>
                    </div>
                  </div>
                  <select
                    value={p.status}
                    onChange={(e) =>
                      updateStatus(p.id, e.target.value as "active" | "completed" | "paused")
                    }
                    className="text-xs px-2 py-1 rounded-lg border border-slate-200 bg-white"
                  >
                    <option value="active">Aktiv</option>
                    <option value="paused">Pausad</option>
                    <option value="completed">Klar</option>
                  </select>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
