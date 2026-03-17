"use client";

import { useState, useEffect, useCallback } from "react";
import { AppShell } from "@/components/app-shell";
import { useAuth } from "@/lib/auth-context";
import { User } from "@/lib/types";
import { UserPlus, Shield, Wrench } from "lucide-react";
import Link from "next/link";

export default function UsersPage() {
  const { user: admin } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [newName, setNewName] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [newRole, setNewRole] = useState<"worker" | "admin">("worker");
  const [saving, setSaving] = useState(false);

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/admin/users");
      const data = await res.json();
      if (data.users) setUsers(data.users as User[]);
    } catch {
      // Handle error
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  async function handleAdd() {
    setSaving(true);
    try {
      await fetch("/api/admin/users", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newName, email: newEmail, role: newRole }),
      });
    } catch {
      // Handle error
    }
    setNewName("");
    setNewEmail("");
    setNewRole("worker");
    setShowAdd(false);
    setSaving(false);
    fetchUsers();
  }

  async function toggleActive(u: User) {
    try {
      await fetch("/api/admin/users", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: u.id, is_active: !u.is_active }),
      });
    } catch {
      // Handle error
    }
    fetchUsers();
  }

  if (admin?.role !== "admin") {
    return (
      <AppShell>
        <div className="text-center py-12 text-slate-500">Ingen behörighet.</div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-slate-900">Personal</h2>
          <button
            onClick={() => setShowAdd(!showAdd)}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors shadow-sm"
          >
            <UserPlus className="w-4 h-4" />
            Lägg till
          </button>
        </div>

        {/* Add form */}
        {showAdd && (
          <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-4 shadow-sm">
            <h3 className="font-semibold text-slate-900">Ny anställd</h3>
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1">Namn</label>
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                className="w-full px-4 py-3 rounded-xl border border-slate-300 text-base focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all duration-200"
                placeholder="Förnamn Efternamn"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1">E-post</label>
              <input
                type="email"
                value={newEmail}
                onChange={(e) => setNewEmail(e.target.value)}
                className="w-full px-4 py-3 rounded-xl border border-slate-300 text-base focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all duration-200"
                placeholder="namn@email.se"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1">Roll</label>
              <select
                value={newRole}
                onChange={(e) => setNewRole(e.target.value as "worker" | "admin")}
                className="w-full px-4 py-3 rounded-xl border border-slate-300 bg-white text-base focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all duration-200"
              >
                <option value="worker">Montör</option>
                <option value="admin">Admin</option>
              </select>
            </div>
            <button
              onClick={handleAdd}
              disabled={saving || !newName || !newEmail}
              className="w-full bg-green-600 hover:bg-green-700 disabled:bg-green-400 text-white font-semibold py-3 rounded-xl transition-colors shadow-md shadow-green-600/20"
            >
              {saving ? "Sparar..." : "Lägg till"}
            </button>
          </div>
        )}

        {/* User list */}
        {loading ? (
          <div className="text-center py-8 text-slate-400">Laddar...</div>
        ) : (
          <div className="space-y-3">
            {users.map((u) => {
              const initials = u.name
                ? u.name.split(" ").map((n) => n[0]).join("").toUpperCase().slice(0, 2)
                : "?";
              const isAdmin = u.role === "admin";
              return (
                <div
                  key={u.id}
                  className={`bg-white rounded-xl border p-4 shadow-sm hover:shadow-md transition-all duration-150 ${
                    u.is_active ? "border-slate-200" : "border-slate-200 opacity-50"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <Link href={`/admin/users/${u.id}`} className="flex items-center gap-3 flex-1 min-w-0">
                      <div className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold text-white flex-shrink-0 ${
                        isAdmin
                          ? "bg-gradient-to-br from-amber-400 to-amber-600"
                          : "bg-gradient-to-br from-blue-500 to-indigo-500"
                      }`}>
                        {initials}
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-slate-900">{u.name}</span>
                          <span className={`inline-flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded ${
                            isAdmin
                              ? "bg-amber-50 text-amber-700"
                              : "bg-blue-50 text-blue-700"
                          }`}>
                            {isAdmin ? (
                              <><Shield className="w-2.5 h-2.5" /> Admin</>
                            ) : (
                              <><Wrench className="w-2.5 h-2.5" /> Montör</>
                            )}
                          </span>
                        </div>
                        <div className="text-sm text-slate-500 mt-0.5 truncate">{u.email}</div>
                      </div>
                    </Link>
                    <button
                      onClick={() => toggleActive(u)}
                      className={`text-xs px-3 py-1.5 rounded-full font-semibold transition-colors flex-shrink-0 ml-3 ${
                        u.is_active
                          ? "bg-green-50 text-green-700 hover:bg-green-100 border border-green-200"
                          : "bg-slate-100 text-slate-500 hover:bg-slate-200 border border-slate-200"
                      }`}
                    >
                      {u.is_active ? "Aktiv" : "Inaktiv"}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </AppShell>
  );
}
