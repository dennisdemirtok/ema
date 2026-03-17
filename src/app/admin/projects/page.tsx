"use client";

import { useState, useEffect, useCallback } from "react";
import { AppShell } from "@/components/app-shell";
import { useAuth } from "@/lib/auth-context";
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

    try {
      const [projectsRes, hoursRes] = await Promise.all([
        fetch("/api/projects"),
        fetch("/api/entries?fields=project_id,hours"),
      ]);

      const projectsData = await projectsRes.json();
      const hoursData = await hoursRes.json();

      const projectList = projectsData.projects || [];
      const hoursSummary = hoursData.entries || [];

      const hoursMap: Record<string, number> = {};
      hoursSummary.forEach((e: { project_id: string; hours: number }) => {
        if (e.project_id) {
          hoursMap[e.project_id] = (hoursMap[e.project_id] || 0) + Number(e.hours);
        }
      });

      setProjects(
        projectList.map((p: Project) => ({
          ...p,
          total_hours: hoursMap[p.id] || 0,
        }))
      );
    } catch {
      // Handle error
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  async function handleAdd() {
    setSaving(true);
    try {
      await fetch("/api/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newName, description: newDesc || null }),
      });
    } catch {
      // Handle error
    }
    setNewName("");
    setNewDesc("");
    setShowAdd(false);
    setSaving(false);
    fetchProjects();
  }

  async function updateStatus(id: string, status: "active" | "completed" | "paused") {
    try {
      await fetch("/api/projects", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id, status }),
      });
    } catch {
      // Handle error
    }
    fetchProjects();
  }

  const statusConfig = {
    active: {
      icon: <Play className="w-3 h-3" />,
      label: "Aktiv",
      badgeClass: "bg-green-50 text-green-700 border border-green-200",
      borderClass: "border-l-green-500",
    },
    paused: {
      icon: <Pause className="w-3 h-3" />,
      label: "Pausad",
      badgeClass: "bg-amber-50 text-amber-700 border border-amber-200",
      borderClass: "border-l-amber-500",
    },
    completed: {
      icon: <CheckCircle2 className="w-3 h-3" />,
      label: "Klar",
      badgeClass: "bg-slate-50 text-slate-500 border border-slate-200",
      borderClass: "border-l-slate-400",
    },
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
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors shadow-sm"
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
                className="w-full px-4 py-3 rounded-xl border border-slate-300 text-base focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all duration-200"
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
                className="w-full px-4 py-3 rounded-xl border border-slate-300 text-base resize-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all duration-200"
                placeholder="Kort beskrivning av jobbet..."
              />
            </div>
            <button
              onClick={handleAdd}
              disabled={saving || !newName}
              className="w-full bg-green-600 hover:bg-green-700 disabled:bg-green-400 text-white font-semibold py-3 rounded-xl transition-colors shadow-md shadow-green-600/20"
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
            {projects.map((p) => {
              const config = statusConfig[p.status];
              return (
                <div
                  key={p.id}
                  className={`bg-white rounded-xl border border-slate-200 p-4 shadow-sm border-l-4 ${config.borderClass} hover:shadow-md transition-all duration-150 ${
                    p.status === "completed" ? "opacity-60" : ""
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-slate-900">{p.name}</span>
                        <span className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${config.badgeClass}`}>
                          {config.icon}
                          {config.label}
                        </span>
                      </div>
                      {p.description && (
                        <p className="text-sm text-slate-500 mt-1">{p.description}</p>
                      )}
                      <div className="mt-2">
                        <span className="inline-flex items-center text-xs font-semibold bg-slate-100 text-slate-700 px-2.5 py-1 rounded-full">
                          {p.total_hours}h nedlagd tid
                        </span>
                      </div>
                    </div>
                    <select
                      value={p.status}
                      onChange={(e) =>
                        updateStatus(p.id, e.target.value as "active" | "completed" | "paused")
                      }
                      className="text-xs px-2 py-1 rounded-lg border border-slate-200 bg-white ml-3 flex-shrink-0"
                    >
                      <option value="active">Aktiv</option>
                      <option value="paused">Pausad</option>
                      <option value="completed">Klar</option>
                    </select>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </AppShell>
  );
}
