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

  return (
    <>
      {/* Mobile header */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-slate-900 text-white h-14 flex items-center px-4 shadow-lg">
        <button
          onClick={() => setOpen(!open)}
          className="p-2 -ml-2 rounded-lg hover:bg-slate-800 transition-colors"
          aria-label="Meny"
        >
          {open ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>
        <h1 className="ml-3 font-semibold text-lg">Tidrapport</h1>
        <div className="ml-auto text-sm text-slate-300">{user.name}</div>
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
        <div className="p-4 space-y-6">
          {sections.map((section) => (
            <div key={section.id}>
              <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2 px-3">
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
                        className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                          isActive
                            ? "bg-blue-600 text-white"
                            : "text-slate-300 hover:bg-slate-800 hover:text-white"
                        }`}
                      >
                        <Icon className="w-5 h-5 flex-shrink-0" />
                        {item.label}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>

        {/* Sign out */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-slate-800">
          <button
            onClick={signOut}
            className="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm font-medium text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
          >
            <LogOut className="w-5 h-5" />
            Logga ut
          </button>
        </div>
      </nav>
    </>
  );
}
