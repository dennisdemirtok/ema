"use client";

import { useState, useRef } from "react";
import { AppShell } from "@/components/app-shell";
import { useAuth } from "@/lib/auth-context";
import { useRouter } from "next/navigation";
import { Upload, FileText, AlertCircle, CheckCircle2, Loader2, Ruler } from "lucide-react";

export default function AreaUploadPage() {
  const { user } = useAuth();
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  if (user?.role !== "admin") {
    return (
      <AppShell>
        <div className="text-center py-12 text-slate-500">
          Du har inte behörighet att använda denna funktion.
        </div>
      </AppShell>
    );
  }

  function handleFileSelect(selectedFile: File) {
    setError(null);
    if (!selectedFile.name.toLowerCase().endsWith(".pdf")) {
      setError("Endast PDF-filer stöds. Ladda upp en arkitektritning i PDF-format.");
      return;
    }
    if (selectedFile.size > 100 * 1024 * 1024) {
      setError("Filen är för stor. Max 100 MB.");
      return;
    }
    setFile(selectedFile);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) handleFileSelect(droppedFile);
  }

  async function handleUpload() {
    if (!file || !user) return;
    setUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("user_id", user.id);

      const res = await fetch("/api/area/jobs", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.error || "Något gick fel vid uppladdning.");
        setUploading(false);
        return;
      }

      // Redirect to jobs page
      router.push("/area/jobs");
    } catch {
      setError("Kunde inte ladda upp filen. Försök igen.");
      setUploading(false);
    }
  }

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h2 className="text-xl font-bold text-slate-900">Ny rumsyta-beräkning</h2>
          <p className="text-sm text-slate-500 mt-1">
            Ladda upp en arkitektritning i PDF-format för automatisk beräkning av rumsytor
          </p>
        </div>

        {/* Info card */}
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
          <div className="flex gap-3">
            <Ruler className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-blue-800">
              <p className="font-semibold mb-1">Så fungerar det</p>
              <ul className="space-y-1 text-blue-700">
                <li>1. Ladda upp en planritning i PDF-format (vektorbaserad)</li>
                <li>2. Systemet identifierar rum och beräknar ytor automatiskt</li>
                <li>3. Ladda ner resultat-PDF med färgkodade rum och kvm-etiketter</li>
              </ul>
              <p className="mt-2 text-xs text-blue-600">
                Stödjer skalor 1:50, 1:100, 1:200. Bäst resultat med vektorbaserade ritningar från AutoCAD, Revit eller ArchiCAD.
              </p>
            </div>
          </div>
        </div>

        {/* Upload area */}
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all duration-200 ${
            dragOver
              ? "border-blue-500 bg-blue-50"
              : file
              ? "border-green-400 bg-green-50/50"
              : "border-slate-300 bg-white hover:border-blue-400 hover:bg-blue-50/30"
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) handleFileSelect(f);
            }}
            className="hidden"
          />

          {file ? (
            <div className="space-y-3">
              <div className="w-14 h-14 rounded-2xl bg-green-100 flex items-center justify-center mx-auto">
                <CheckCircle2 className="w-7 h-7 text-green-600" />
              </div>
              <div>
                <p className="font-semibold text-slate-900">{file.name}</p>
                <p className="text-sm text-slate-500 mt-1">
                  {(file.size / (1024 * 1024)).toFixed(1)} MB
                </p>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setFile(null);
                }}
                className="text-sm text-slate-500 hover:text-red-600 transition-colors"
              >
                Byt fil
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="w-14 h-14 rounded-2xl bg-slate-100 flex items-center justify-center mx-auto">
                <Upload className="w-7 h-7 text-slate-400" />
              </div>
              <div>
                <p className="font-semibold text-slate-700">
                  Dra och släpp PDF här
                </p>
                <p className="text-sm text-slate-500 mt-1">
                  eller klicka för att välja fil
                </p>
              </div>
              <div className="flex items-center justify-center gap-2 text-xs text-slate-400">
                <FileText className="w-3.5 h-3.5" />
                <span>PDF-filer, max 100 MB</span>
              </div>
            </div>
          )}
        </div>

        {/* Error */}
        {error && (
          <div className="flex items-start gap-3 bg-red-50 border border-red-200 rounded-xl p-4">
            <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {/* Upload button */}
        <button
          onClick={handleUpload}
          disabled={!file || uploading}
          className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-semibold py-4 rounded-xl transition-all duration-150 text-base shadow-md shadow-blue-600/20"
        >
          {uploading ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Laddar upp och analyserar...
            </>
          ) : (
            <>
              <Upload className="w-5 h-5" />
              Starta beräkning
            </>
          )}
        </button>
      </div>
    </AppShell>
  );
}
