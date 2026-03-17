"use client";

import { useState, useEffect, useCallback } from "react";
import { AppShell } from "@/components/app-shell";
import { useAuth } from "@/lib/auth-context";
import { supabase } from "@/lib/supabase";
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
    const { data } = await supabase.from("users").select("*").order("name");
    if (data) setUsers(data as User[]);
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  async function handleAdd() {
    setSaving(true);
    await supabase.from("users").insert({
      name: newName,
      email: newEmail,
      role: newRole,
    });
    setNewName("");
    setNewEmail("");
    setNewRole("worker");
    setShowAdd(false);
    setSaving(false);
    fetchUsers();
  }

  async function toggleActive(u: User) {
    await supabase.from("users").update({ is_active: !u.is_active }).eq("id", u.id);
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
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors"
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
                className="w-full px-4 py-3 rounded-xl border border-slate-300 text-base"
                placeholder="Förnamn Efternamn"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1">E-post</label>
              <input
                type="email"
                value={newEmail}
                onChange={(e) => setNewEmail(e.target.value)}
                className="w-full px-4 py-3 rounded-xl border border-slate-300 text-base"
                placeholder="namn@email.se"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1">Roll</label>
              <select
                value={newRole}
                onChange={(e) => setNewRole(e.target.value as "worker" | "admin")}
                className="w-full px-4 py-3 rounded-xl border border-slate-300 bg-white text-base"
              >
                <option value="worker">Montör</option>
                <option value="admin">Admin</option>
              </select>
            </div>
            <button
              onClick={handleAdd}
              disabled={saving || !newName || !newEmail}
              className="w-full bg-green-600 hover:bg-green-700 disabled:bg-green-400 text-white font-semibold py-3 rounded-xl transition-colors"
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
            {users.map((u) => (
              <div
                key={u.id}
                className={`bg-white rounded-xl border p-4 shadow-sm ${
                  u.is_active ? "border-slate-200" : "border-slate-200 opacity-50"
                }`}
              >
                <div className="flex items-center justify-between">
                  <Link href={`/admin/users/${u.id}`} className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      {u.role === "admin" ? (
                        <Shield className="w-4 h-4 text-amber-500" />
                      ) : (
                        <Wrench className="w-4 h-4 text-blue-500" />
                      )}
                      <span className="font-semibold text-slate-900">{u.name}</span>
                    </div>
                    <div className="text-sm text-slate-500 mt-0.5">{u.email}</div>
                  </Link>
                  <button
                    onClick={() => toggleActive(u)}
                    className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-colors ${
                      u.is_active
                        ? "bg-green-50 text-green-700 hover:bg-green-100"
                        : "bg-slate-100 text-slate-500 hover:bg-slate-200"
                    }`}
                  >
                    {u.is_active ? "Aktiv" : "Inaktiv"}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
