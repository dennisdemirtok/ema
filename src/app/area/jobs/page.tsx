"use client";

import { useState, useEffect, useCallback } from "react";
import { AppShell } from "@/components/app-shell";
import { useAuth } from "@/lib/auth-context";
import { AreaJob } from "@/lib/types";
import {
  FileText,
  Download,
  Trash2,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Clock,
  Upload,
  Ruler,
  ExternalLink,
} from "lucide-react";
import { format } from "date-fns";
import { sv } from "date-fns/locale";
import Link from "next/link";

export default function AreaJobsPage() {
  const { user } = useAuth();
  const [jobs, setJobs] = useState<AreaJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState<string | null>(null);

  const fetchJobs = useCallback(async () => {
    try {
      const res = await fetch("/api/area/jobs");
      const data = await res.json();
      if (data.jobs) setJobs(data.jobs);
    } catch {
      // Handle error
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchJobs();
    // Poll for processing jobs
    const interval = setInterval(() => {
      if (jobs.some((j) => j.status === "processing" || j.status === "uploading")) {
        fetchJobs();
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [fetchJobs, jobs]);

  async function handleDelete(id: string) {
    if (!confirm("Är du säker på att du vill ta bort denna beräkning?")) return;
    setDeleting(id);
    try {
      await fetch(`/api/area/jobs?id=${id}`, { method: "DELETE" });
      setJobs(jobs.filter((j) => j.id !== id));
    } catch {
      // Handle error
    }
    setDeleting(null);
  }

  const statusConfig = {
    uploading: {
      icon: <Upload className="w-4 h-4" />,
      label: "Laddar upp...",
      color: "text-blue-600 bg-blue-50 border-blue-200",
      borderColor: "border-l-blue-500",
    },
    processing: {
      icon: <Loader2 className="w-4 h-4 animate-spin" />,
      label: "Bearbetar...",
      color: "text-amber-600 bg-amber-50 border-amber-200",
      borderColor: "border-l-amber-500",
    },
    completed: {
      icon: <CheckCircle2 className="w-4 h-4" />,
      label: "Klar",
      color: "text-green-600 bg-green-50 border-green-200",
      borderColor: "border-l-green-500",
    },
    failed: {
      icon: <AlertCircle className="w-4 h-4" />,
      label: "Misslyckades",
      color: "text-red-600 bg-red-50 border-red-200",
      borderColor: "border-l-red-500",
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
          <h2 className="text-xl font-bold text-slate-900">Beräkningar</h2>
          <Link
            href="/area"
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors shadow-sm"
          >
            <Ruler className="w-4 h-4" />
            Ny beräkning
          </Link>
        </div>

        {loading ? (
          <div className="text-center py-8 text-slate-400">Laddar...</div>
        ) : jobs.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-2xl border border-slate-200">
            <FileText className="w-10 h-10 text-slate-300 mx-auto mb-3" />
            <p className="text-slate-400 font-medium">Inga beräkningar ännu</p>
            <p className="text-slate-400 text-sm mt-1">
              Ladda upp en planritning för att komma igång
            </p>
            <Link
              href="/area"
              className="inline-flex items-center gap-2 mt-4 px-4 py-2 rounded-xl bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors"
            >
              <Upload className="w-4 h-4" />
              Ladda upp PDF
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {jobs.map((job) => {
              const config = statusConfig[job.status];
              return (
                <div
                  key={job.id}
                  className={`bg-white rounded-xl border border-slate-200 p-4 shadow-sm border-l-4 ${config.borderColor} hover:shadow-md transition-all duration-150`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-semibold text-slate-900 truncate">
                          {job.filename}
                        </span>
                        <span
                          className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full border ${config.color}`}
                        >
                          {config.icon}
                          {config.label}
                        </span>
                      </div>

                      <div className="flex items-center gap-4 mt-2 text-sm text-slate-500">
                        <span className="flex items-center gap-1">
                          <Clock className="w-3.5 h-3.5" />
                          {format(new Date(job.created_at), "d MMM yyyy HH:mm", { locale: sv })}
                        </span>
                        {job.scale && (
                          <span className="text-slate-400">Skala {job.scale}</span>
                        )}
                      </div>

                      {/* Results summary */}
                      {job.status === "completed" && (
                        <div className="flex items-center gap-3 mt-3">
                          <span className="inline-flex items-center text-xs font-semibold bg-green-100 text-green-800 px-2.5 py-1 rounded-full">
                            {job.total_rooms} rum
                          </span>
                          {job.total_area_m2 && (
                            <span className="inline-flex items-center text-xs font-semibold bg-slate-100 text-slate-700 px-2.5 py-1 rounded-full">
                              {Number(job.total_area_m2).toFixed(1)} m&sup2; total
                            </span>
                          )}
                        </div>
                      )}

                      {/* Room details */}
                      {job.status === "completed" && job.rooms && job.rooms.length > 0 && (
                        <div className="mt-3 grid grid-cols-2 sm:grid-cols-3 gap-2">
                          {job.rooms.slice(0, 6).map((room) => (
                            <div
                              key={room.id}
                              className="bg-slate-50 rounded-lg px-3 py-2 text-sm"
                            >
                              <div className="font-medium text-slate-700 truncate">
                                {room.name || "Okänt rum"}
                              </div>
                              <div className="text-slate-500 text-xs">
                                {Number(room.area_m2).toFixed(2)} m&sup2;
                              </div>
                            </div>
                          ))}
                          {job.rooms.length > 6 && (
                            <div className="bg-slate-50 rounded-lg px-3 py-2 text-sm flex items-center justify-center text-slate-400">
                              +{job.rooms.length - 6} fler
                            </div>
                          )}
                        </div>
                      )}

                      {/* Error message */}
                      {job.status === "failed" && job.error_message && (
                        <p className="mt-2 text-sm text-red-600">{job.error_message}</p>
                      )}
                    </div>

                    {/* Actions */}
                    <div className="flex gap-1 flex-shrink-0">
                      {job.status === "completed" && job.result_url && (
                        <a
                          href={job.result_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="p-2 rounded-lg text-green-600 hover:bg-green-50 transition-colors"
                          title="Ladda ner resultat"
                        >
                          <Download className="w-5 h-5" />
                        </a>
                      )}
                      {job.original_url && (
                        <a
                          href={job.original_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="p-2 rounded-lg text-slate-400 hover:text-blue-600 hover:bg-blue-50 transition-colors"
                          title="Visa original"
                        >
                          <ExternalLink className="w-5 h-5" />
                        </a>
                      )}
                      <button
                        onClick={() => handleDelete(job.id)}
                        disabled={deleting === job.id}
                        className="p-2 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 transition-colors disabled:opacity-50"
                        title="Ta bort"
                      >
                        {deleting === job.id ? (
                          <Loader2 className="w-5 h-5 animate-spin" />
                        ) : (
                          <Trash2 className="w-5 h-5" />
                        )}
                      </button>
                    </div>
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
