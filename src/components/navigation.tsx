"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { getMenuForRole } from "@/lib/menu-config";
import {
  Clock,
  CalendarDays,
  LayoutDashboard,
  Users,
  FolderOpen,
  Package,
  Menu,
  X,
  LogOut,
  ChevronRight,
} from "lucide-react";

// Map icon names to components
const iconMap: Record<string, React.ComponentType<{ className?: string }>> = {
  Clock,
  CalendarDays,
  LayoutDashboard,
  Users,
  FolderOpen,
  Package,
};

export function Navigation() {
  const { user, signOut } = useAuth();
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  if (!user) return null;

  const sections = getMenuForRole(user.role);
  const initials = user.name
    ? user.name.split(" ").map((n) => n[0]).join("").toUpperCase().slice(0, 2)
    : "?";

  return (
    <>
      {/* Mobile header */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-slate-900 text-white h-14 flex items-center px-4 shadow-lg border-b border-slate-800">
        <button
          onClick={() => setOpen(!open)}
          className="p-2 -ml-2 rounded-lg hover:bg-slate-800 transition-colors"
          aria-label="Meny"
        >
          {open ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>
        <h1 className="ml-3 font-semibold text-lg">Tidrapport</h1>
        <div className="ml-auto flex items-center gap-2">
          <span className="text-sm text-slate-300">{user.name}</span>
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-indigo-500 flex items-center justify-center text-xs font-bold text-white">
            {initials}
          </div>
        </div>
      </header>

      {/* Mobile overlay */}
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={() => setOpen(false)}
        />
      )}

      {/* Sidebar */}
      <nav
        className={`fixed top-14 left-0 bottom-0 z-40 w-72 bg-slate-900 text-white transform transition-transform duration-200 ease-in-out overflow-y-auto ${
          open ? "translate-x-0" : "-translate-x-full"
        } md:translate-x-0`}
      >
        <div className="p-4 space-y-1">
          {sections.map((section, sectionIdx) => (
            <div key={section.id}>
              {sectionIdx > 0 && (
                <div className="my-3 border-t border-slate-800" />
              )}
              <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2 px-3">
                {section.title}
              </h2>
              <ul className="space-y-1">
                {section.items.map((item) => {
                  const Icon = iconMap[item.icon] || ChevronRight;
                  const isActive = pathname === item.href;
                  return (
                    <li key={item.id}>
                      <Link
                        href={item.href}
                        onClick={() => setOpen(false)}
                        className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 ${
                          isActive
                            ? "bg-blue-600/15 text-blue-400 border-l-[3px] border-blue-500 pl-[9px]"
                            : "text-slate-300 hover:bg-slate-800/70 hover:text-white"
                        }`}
                      >
                        <Icon className={`w-5 h-5 flex-shrink-0 ${isActive ? "text-blue-400" : ""}`} />
                        {item.label}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>

        {/* User info + Sign out */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-slate-800">
          <div className="flex items-center gap-3 mb-3 px-3">
            <div className="w-9 h-9 rounded-full bg-gradient-to-br from-blue-500 to-indigo-500 flex items-center justify-center text-xs font-bold text-white flex-shrink-0">
              {initials}
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-sm font-medium text-slate-200 truncate">{user.name}</div>
              <span className={`inline-block text-[10px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded ${
                user.role === "admin"
                  ? "bg-amber-500/20 text-amber-400"
                  : "bg-blue-500/20 text-blue-400"
              }`}>
                {user.role === "admin" ? "Admin" : "Montör"}
              </span>
            </div>
          </div>
          <button
            onClick={signOut}
            className="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm font-medium text-slate-400 hover:bg-red-500/10 hover:text-red-400 transition-all duration-150"
          >
            <LogOut className="w-5 h-5" />
            Logga ut
          </button>
        </div>
      </nav>
    </>
  );
}
