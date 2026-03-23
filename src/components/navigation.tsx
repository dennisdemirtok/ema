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
  Ruler,
  FileStack,
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
  Ruler,
  FileStack,
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
      {/* Top header */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-white text-gray-900 h-14 flex items-center px-4 shadow-sm border-b border-gray-200">
        {/* Hamburger - only on mobile */}
        <button
          onClick={() => setOpen(!open)}
          className="p-2 -ml-2 rounded-lg hover:bg-gray-100 transition-colors md:hidden"
          aria-label="Meny"
        >
          {open ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>
        <div className="ml-3 md:ml-0 md:pl-72 flex items-center gap-2">
          <span className="material-symbols-outlined text-[#2b6cee]" style={{ fontSize: 24 }}>
            schedule
          </span>
          <h1 className="font-semibold text-lg text-gray-900">Tidrapport</h1>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <span className="text-sm text-gray-500 hidden sm:inline">{user.name}</span>
          <div className="w-8 h-8 rounded-full bg-[#2b6cee] flex items-center justify-center text-xs font-bold text-white">
            {initials}
          </div>
        </div>
      </header>

      {/* Mobile overlay */}
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/40 md:hidden"
          onClick={() => setOpen(false)}
        />
      )}

      {/* Sidebar */}
      <nav
        className={`fixed top-14 left-0 bottom-0 z-40 w-72 bg-white border-r border-gray-200 text-gray-900 transform transition-transform duration-200 ease-in-out overflow-y-auto ${
          open ? "translate-x-0" : "-translate-x-full"
        } md:translate-x-0`}
      >
        <div className="p-4 space-y-1">
          {sections.map((section, sectionIdx) => (
            <div key={section.id}>
              {sectionIdx > 0 && (
                <div className="my-3 border-t border-gray-100" />
              )}
              <h2 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2 px-3">
                {section.title}
              </h2>
              <ul className="space-y-0.5">
                {section.items.map((item) => {
                  const Icon = iconMap[item.icon] || ChevronRight;
                  const isActive = pathname === item.href;
                  return (
                    <li key={item.id}>
                      <Link
                        href={item.href}
                        onClick={() => setOpen(false)}
                        className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 ${
                          isActive
                            ? "bg-[#2b6cee]/10 text-[#2b6cee]"
                            : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
                        }`}
                      >
                        <Icon className={`w-5 h-5 flex-shrink-0 ${isActive ? "text-[#2b6cee]" : "text-gray-400"}`} />
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
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-100 bg-white">
          <div className="flex items-center gap-3 mb-3 px-3">
            <div className="w-9 h-9 rounded-full bg-[#2b6cee] flex items-center justify-center text-xs font-bold text-white flex-shrink-0">
              {initials}
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-sm font-medium text-gray-900 truncate">{user.name}</div>
              <span className={`inline-block text-[10px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded-md ${
                user.role === "admin"
                  ? "bg-amber-100 text-amber-700"
                  : "bg-[#2b6cee]/10 text-[#2b6cee]"
              }`}>
                {user.role === "admin" ? "Admin" : "Montör"}
              </span>
            </div>
          </div>
          <button
            onClick={signOut}
            className="flex items-center gap-3 w-full px-3 py-2.5 rounded-xl text-sm font-medium text-gray-400 hover:bg-red-50 hover:text-red-500 transition-all duration-150"
          >
            <LogOut className="w-5 h-5" />
            Logga ut
          </button>
        </div>
      </nav>
    </>
  );
}
