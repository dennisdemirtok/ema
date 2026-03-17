import { NextRequest, NextResponse } from "next/server";
import { createServerSupabase } from "@/lib/supabase-server";
import { exec } from "child_process";
import path from "path";

/**
 * Trigger Python processing for a specific job.
 * POST /api/area/process { job_id: "..." }
 *
 * This runs the Python processor as a child process.
 * Works both locally (python3) and in Docker (venv python).
 */
export async function POST(request: NextRequest) {
  const { supabase, accessToken } = await createServerSupabase();
  if (!accessToken)
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const { job_id } = await request.json();
  if (!job_id)
    return NextResponse.json({ error: "Missing job_id" }, { status: 400 });

  // Verify job exists
  const { data: job, error: jobError } = await supabase
    .from("tr_area_jobs")
    .select("*")
    .eq("id", job_id)
    .single();

  if (jobError || !job)
    return NextResponse.json({ error: "Job not found" }, { status: 404 });

  // Run Python processor in background
  const processorDir = path.resolve(process.cwd(), "area-processor");

  // Try venv python first (Docker), fall back to system python3
  const pythonBin = process.env.NODE_ENV === "production"
    ? "/opt/venv/bin/python"
    : "python3";

  const cmd = `cd "${processorDir}" && ${pythonBin} processor.py "${job_id}"`;

  console.log(`[area-processor] Starting: ${cmd}`);

  exec(cmd, { timeout: 300000 }, (error, stdout, stderr) => {
    if (stdout) console.log("[area-processor stdout]", stdout);
    if (stderr) console.error("[area-processor stderr]", stderr);
    if (error) console.error("[area-processor error]", error.message);
  });

  // Return immediately - processing happens in background
  return NextResponse.json({ ok: true, message: "Processing started" });
}
