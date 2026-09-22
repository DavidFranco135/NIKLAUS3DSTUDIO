"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

export function AppHeader() {
  const { user, organizations, currentOrganizationId, logout } = useAuth();
  const router = useRouter();
  const currentOrg = organizations.find(
    (m) => m.organization.id === currentOrganizationId
  )?.organization;

  async function handleLogout() {
    await logout();
    router.replace("/login");
  }

  return (
    <header className="flex items-center justify-between border-b border-neutral-800 px-6 py-4">
      <Link href="/dashboard" className="font-semibold">
        3D AI Studio
      </Link>
      <div className="flex items-center gap-4 text-sm text-neutral-400">
        {currentOrg && <span>{currentOrg.name}</span>}
        <Link href="/billing" className="text-blue-400 hover:underline">
          Faturamento
        </Link>
        {user && <span>{user.email}</span>}
        <button onClick={handleLogout} className="text-blue-400 hover:underline">
          Sair
        </button>
      </div>
    </header>
  );
}
