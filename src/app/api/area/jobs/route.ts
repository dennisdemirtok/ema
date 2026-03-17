import { NextRequest, NextResponse } from "next/server";
import { createServerSupabase } from "@/lib/supabase-server";

// List all area jobs
export async function GET() {
  const { supabase, accessToken } = await createServerSupabase();
  if (!accessToken) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const { data, error } = await supabase
    .from("tr_area_jobs")
    .select("*, rooms:tr_area_rooms(*)")
    .order("created_at", { ascending: false });

  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return NextResponse.json({ jobs: data });
}

// Create a new area job (PDF upload)
export async function POST(request: NextRequest) {
  const { supabase, accessToken } = await createServerSupabase();
  if (!accessToken) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const formData = await request.formData();
  const file = formData.get("file") as File;
  const userId = formData.get("user_id") as string;

  if (!file || !userId) {
    return NextResponse.json({ error: "Missing file or user_id" }, { status: 400 });
  }

  if (!file.name.toLowerCase().endsWith(".pdf")) {
    return NextResponse.json({ error: "Only PDF files are supported" }, { status: 400 });
  }

  // 1. Create job record
  const { data: job, error: jobError } = await supabase
    .from("tr_area_jobs")
    .insert({
      user_id: userId,
      filename: file.name,
      status: "uploading",
    })
    .select()
    .single();

  if (jobError) return NextResponse.json({ error: jobError.message }, { status: 500 });

  // 2. Upload PDF to Supabase Storage
  const fileBuffer = Buffer.from(await file.arrayBuffer());
  const storagePath = `originals/${job.id}/${file.name}`;

  const { error: uploadError } = await supabase.storage
    .from("area-pdfs")
    .upload(storagePath, fileBuffer, {
      contentType: "application/pdf",
      upsert: true,
    });

  if (uploadError) {
    // Update job to failed
    await supabase
      .from("tr_area_jobs")
      .update({ status: "failed", error_message: `Upload failed: ${uploadError.message}` })
      .eq("id", job.id);
    return NextResponse.json({ error: uploadError.message }, { status: 500 });
  }

  // 3. Get public URL
  const { data: urlData } = supabase.storage
    .from("area-pdfs")
    .getPublicUrl(storagePath);

  // 4. Update job with URL and set to processing
  await supabase
    .from("tr_area_jobs")
    .update({
      original_url: urlData.publicUrl,
      status: "processing",
    })
    .eq("id", job.id);

  // TODO: Trigger Python processing pipeline here
  // For now, the job stays in "processing" status until a processor picks it up

  return NextResponse.json({
    job: { ...job, original_url: urlData.publicUrl, status: "processing" },
  });
}

// Delete a job
export async function DELETE(request: NextRequest) {
  const { supabase, accessToken } = await createServerSupabase();
  if (!accessToken) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const id = request.nextUrl.searchParams.get("id");
  if (!id) return NextResponse.json({ error: "Missing id" }, { status: 400 });

  // Delete from storage first
  const { data: job } = await supabase
    .from("tr_area_jobs")
    .select("id, filename")
    .eq("id", id)
    .single();

  if (job) {
    await supabase.storage
      .from("area-pdfs")
      .remove([`originals/${job.id}/${job.filename}`, `results/${job.id}/result.pdf`]);
  }

  const { error } = await supabase.from("tr_area_jobs").delete().eq("id", id);
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });

  return NextResponse.json({ ok: true });
}
