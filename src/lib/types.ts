export type UserRole = "admin" | "worker";
export type ProjectStatus = "active" | "completed" | "paused";

export interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface Project {
  id: string;
  name: string;
  description: string | null;
  status: ProjectStatus;
  created_at: string;
}

export interface TimeEntry {
  id: string;
  user_id: string;
  project_id: string | null;
  date: string;
  hours: number;
  description: string | null;
  created_at: string;
  updated_at: string;
  // Joined fields
  user?: User;
  project?: Project;
}

// Area calculation types
export type AreaJobStatus = "uploading" | "processing" | "completed" | "failed";

export interface AreaJob {
  id: string;
  user_id: string;
  filename: string;
  original_url: string | null;
  result_url: string | null;
  status: AreaJobStatus;
  scale: string | null;
  total_rooms: number;
  total_area_m2: number | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  rooms?: AreaRoom[];
}

export interface AreaRoom {
  id: string;
  job_id: string;
  name: string | null;
  area_m2: number;
  confidence: number;
  polygon_pts: number[][] | null;
  source: "auto" | "manual";
  verified: boolean;
  created_at: string;
}

export interface MenuItem {
  id: string;
  label: string;
  href: string;
  icon: string;
  roles: UserRole[];
  badge?: number;
}
