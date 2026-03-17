"""
Main processor: polls Supabase for pending jobs, processes PDFs,
and uploads results.
"""

import os
import sys
import time
import tempfile
import traceback
from supabase import create_client
from config import SUPABASE_URL, SUPABASE_SERVICE_KEY, STORAGE_BUCKET
from pdf_parser import extract_pdf_data
from room_detector import detect_rooms
from pdf_generator import generate_result_pdf


def get_supabase():
    """Create Supabase client with service role key."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        sys.exit(1)
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def process_job(supabase, job: dict):
    """Process a single area calculation job."""
    job_id = job["id"]
    filename = job["filename"]
    print(f"\n{'='*60}")
    print(f"Processing job: {job_id}")
    print(f"File: {filename}")
    print(f"{'='*60}")

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # 1. Download original PDF
            print("  [1/5] Downloading PDF...")
            storage_path = f"originals/{job_id}/{filename}"
            pdf_bytes = supabase.storage.from_(STORAGE_BUCKET).download(storage_path)

            input_path = os.path.join(tmpdir, filename)
            with open(input_path, "wb") as f:
                f.write(pdf_bytes)
            print(f"  Downloaded: {len(pdf_bytes)} bytes")

            # 2. Extract vector data
            print("  [2/5] Extracting vector data...")
            pdf_data = extract_pdf_data(input_path)
            print(f"  Found {len(pdf_data.lines)} lines, "
                  f"{len(pdf_data.wall_lines)} walls, "
                  f"{len(pdf_data.text_blocks)} text blocks")
            print(f"  Detected scale: 1:{pdf_data.scale}")

            # 3. Detect rooms
            print("  [3/5] Detecting rooms...")
            rooms = detect_rooms(pdf_data)
            print(f"  Found {len(rooms)} rooms")

            for i, room in enumerate(rooms):
                name = room.name or "(unnamed)"
                print(f"    Room {i+1}: {name} = {room.area_m2:.2f} m²"
                      f" (confidence: {room.confidence:.0%})")

            # 4. Generate result PDF
            print("  [4/5] Generating result PDF...")
            output_path = os.path.join(tmpdir, "result.pdf")
            generate_result_pdf(input_path, output_path, rooms)

            # 5. Upload result and update database
            print("  [5/5] Uploading results...")
            result_storage_path = f"results/{job_id}/result.pdf"

            with open(output_path, "rb") as f:
                result_bytes = f.read()

            supabase.storage.from_(STORAGE_BUCKET).upload(
                result_storage_path, result_bytes,
                file_options={"content-type": "application/pdf", "upsert": "true"}
            )

            # Get public URL
            result_url = supabase.storage.from_(STORAGE_BUCKET).get_public_url(
                result_storage_path
            )

            # Calculate totals
            total_area = sum(r.area_m2 for r in rooms)

            # Insert rooms into database
            for room in rooms:
                supabase.table("tr_area_rooms").insert({
                    "job_id": job_id,
                    "name": room.name,
                    "area_m2": room.area_m2,
                    "confidence": room.confidence,
                    "polygon_pts": [list(p) for p in room.polygon_pts],
                    "source": room.source,
                    "verified": False,
                }).execute()

            # Update job status
            supabase.table("tr_area_jobs").update({
                "status": "completed",
                "result_url": result_url,
                "scale": f"1:{pdf_data.scale}",
                "total_rooms": len(rooms),
                "total_area_m2": round(total_area, 2),
                "error_message": None,
            }).eq("id", job_id).execute()

            print(f"\n  ✅ Done! {len(rooms)} rooms, {total_area:.2f} m² total")

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        print(f"\n  ❌ Error: {error_msg}")
        traceback.print_exc()

        # Update job as failed
        try:
            supabase.table("tr_area_jobs").update({
                "status": "failed",
                "error_message": error_msg[:500],
            }).eq("id", job_id).execute()
        except Exception:
            pass


def poll_jobs(supabase, once: bool = False):
    """Poll for pending jobs and process them."""
    print("Area Processor started. Polling for jobs...")

    while True:
        try:
            # Find jobs with status 'processing'
            result = supabase.table("tr_area_jobs") \
                .select("*") \
                .eq("status", "processing") \
                .order("created_at") \
                .limit(1) \
                .execute()

            if result.data:
                job = result.data[0]
                process_job(supabase, job)
            else:
                if once:
                    print("No pending jobs.")
                    return
                # Wait before next poll
                time.sleep(5)

        except KeyboardInterrupt:
            print("\nShutting down...")
            break
        except Exception as e:
            print(f"Poll error: {e}")
            if once:
                return
            time.sleep(10)


def process_single(job_id: str):
    """Process a specific job by ID."""
    supabase = get_supabase()

    result = supabase.table("tr_area_jobs") \
        .select("*") \
        .eq("id", job_id) \
        .single() \
        .execute()

    if not result.data:
        print(f"Job {job_id} not found")
        return

    process_job(supabase, result.data)


if __name__ == "__main__":
    supabase = get_supabase()

    if len(sys.argv) > 1:
        if sys.argv[1] == "--once":
            poll_jobs(supabase, once=True)
        else:
            # Process specific job ID
            process_single(sys.argv[1])
    else:
        # Continuous polling
        poll_jobs(supabase)
