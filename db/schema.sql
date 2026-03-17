-- Tidrapporteringsapp Database Schema
-- Run this in Supabase SQL Editor

-- Enums
CREATE TYPE user_role AS ENUM ('admin', 'worker');
CREATE TYPE project_status AS ENUM ('active', 'completed', 'paused');

-- Users table
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) NOT NULL UNIQUE,
  name VARCHAR(100) NOT NULL,
  pin_code VARCHAR(255), -- bcrypt hashed
  role user_role NOT NULL DEFAULT 'worker',
  is_active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Projects table
CREATE TABLE projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(200) NOT NULL,
  description TEXT,
  status project_status NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Time entries table
CREATE TABLE time_entries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
  date DATE NOT NULL,
  hours DECIMAL(4,2) NOT NULL CHECK (hours >= 0.5 AND hours <= 24),
  description TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_time_entries_user_date ON time_entries(user_id, date);
CREATE INDEX idx_time_entries_date ON time_entries(date);
CREATE INDEX idx_time_entries_project ON time_entries(project_id);

-- Row Level Security
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE time_entries ENABLE ROW LEVEL SECURITY;

-- Users: everyone can read active users, admin can manage
CREATE POLICY "Users can view active users" ON users
  FOR SELECT USING (is_active = true);

CREATE POLICY "Admin can manage users" ON users
  FOR ALL USING (
    EXISTS (SELECT 1 FROM users WHERE id = auth.uid() AND role = 'admin')
  );

-- Projects: everyone can read, admin can manage
CREATE POLICY "Everyone can view projects" ON projects
  FOR SELECT USING (true);

CREATE POLICY "Admin can manage projects" ON projects
  FOR ALL USING (
    EXISTS (SELECT 1 FROM users WHERE id = auth.uid() AND role = 'admin')
  );

-- Time entries: workers see own, admin sees all
CREATE POLICY "Workers can view own entries" ON time_entries
  FOR SELECT USING (user_id = auth.uid());

CREATE POLICY "Workers can insert own entries" ON time_entries
  FOR INSERT WITH CHECK (user_id = auth.uid());

CREATE POLICY "Workers can update own entries" ON time_entries
  FOR UPDATE USING (user_id = auth.uid());

CREATE POLICY "Workers can delete own same-day entries" ON time_entries
  FOR DELETE USING (user_id = auth.uid() AND date = CURRENT_DATE);

CREATE POLICY "Admin can view all entries" ON time_entries
  FOR SELECT USING (
    EXISTS (SELECT 1 FROM users WHERE id = auth.uid() AND role = 'admin')
  );

-- Updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER time_entries_updated_at
  BEFORE UPDATE ON time_entries
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Seed data
INSERT INTO projects (name, description, status) VALUES
  ('Storgatan 15', 'Omläggning av tak, tegelpannor', 'active'),
  ('Björkvägen 8', 'Plåttak, nybygge', 'active'),
  ('Industrivägen 22', 'Takrenov och isolering', 'active');
