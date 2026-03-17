-- Rumsyta-beräkning tables
-- Run this in Supabase SQL Editor

-- Job status enum
DO $$ BEGIN
  CREATE TYPE tr_area_job_status AS ENUM ('uploading', 'processing', 'completed', 'failed');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Area room source enum
DO $$ BEGIN
  CREATE TYPE tr_area_room_source AS ENUM ('auto', 'manual');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Jobs table
CREATE TABLE IF NOT EXISTS tr_area_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES tr_users(id),
  filename TEXT NOT NULL,
  original_url TEXT,
  result_url TEXT,
  status tr_area_job_status NOT NULL DEFAULT 'uploading',
  scale TEXT,
  total_rooms INTEGER NOT NULL DEFAULT 0,
  total_area_m2 NUMERIC(10, 2),
  error_message TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Rooms table
CREATE TABLE IF NOT EXISTS tr_area_rooms (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id UUID NOT NULL REFERENCES tr_area_jobs(id) ON DELETE CASCADE,
  name TEXT,
  area_m2 NUMERIC(10, 2) NOT NULL,
  confidence NUMERIC(3, 2) NOT NULL DEFAULT 0.00,
  polygon_pts JSONB,
  source tr_area_room_source NOT NULL DEFAULT 'auto',
  verified BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_area_jobs_user ON tr_area_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_area_jobs_status ON tr_area_jobs(status);
CREATE INDEX IF NOT EXISTS idx_area_rooms_job ON tr_area_rooms(job_id);

-- RLS policies
ALTER TABLE tr_area_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE tr_area_rooms ENABLE ROW LEVEL SECURITY;

-- Admin can do everything
CREATE POLICY "admin_all_area_jobs" ON tr_area_jobs
  FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "admin_all_area_rooms" ON tr_area_rooms
  FOR ALL USING (true) WITH CHECK (true);

-- Update trigger for updated_at
CREATE OR REPLACE FUNCTION tr_area_jobs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tr_area_jobs_updated_at_trigger ON tr_area_jobs;
CREATE TRIGGER tr_area_jobs_updated_at_trigger
  BEFORE UPDATE ON tr_area_jobs
  FOR EACH ROW EXECUTE FUNCTION tr_area_jobs_updated_at();

-- Storage bucket for PDFs (run separately if needed)
-- INSERT INTO storage.buckets (id, name, public) VALUES ('area-pdfs', 'area-pdfs', true);
