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

export interface MenuItem {
  id: string;
  label: string;
  href: string;
  icon: string;
  roles: UserRole[];
  badge?: number;
}
