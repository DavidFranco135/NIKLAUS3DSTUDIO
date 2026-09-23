"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

type NavItem = {
  href: string;
  label: string;
  icon: (props: { className?: string }) => React.ReactElement;
};

function IconHome({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" className={className}>
      <path d="M3 11.5 12 4l9 7.5" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M5 10v9a1 1 0 0 0 1 1h4v-6h4v6h4a1 1 0 0 0 1-1v-9" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function IconBox({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" className={className}>
      <path d="M3.5 7.5 12 3l8.5 4.5v9L12 21l-8.5-4.5z" strokeLinejoin="round" />
      <path d="M3.5 7.5 12 12l8.5-4.5M12 12v9" strokeLinejoin="round" />
    </svg>
  );
}

function IconClipboard({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" className={className}>
      <rect x="5" y="4" width="14" height="17" rx="2" />
      <path d="M9 4V3a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v1" strokeLinecap="round" />
      <path d="M8 10h8M8 14h8M8 18h5" strokeLinecap="round" />
    </svg>
  );
}

function IconUsers({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" className={className}>
      <circle cx="9" cy="8" r="3" />
      <path d="M2.5 20a6.5 6.5 0 0 1 13 0" strokeLinecap="round" />
      <path d="M16 4.5a3 3 0 0 1 0 6M18.5 20a6 6 0 0 0-3.5-5.5" strokeLinecap="round" />
    </svg>
  );
}

function IconArchive({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" className={className}>
      <rect x="3" y="3.5" width="18" height="4.5" rx="1" />
      <path d="M4.5 8v10.5a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2V8" />
      <path d="M10 12.5h4" strokeLinecap="round" />
    </svg>
  );
}

function IconDollar({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" className={className}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 6.5v11M15 9.2c0-1.2-1.3-2-3-2s-3 .9-3 2.1c0 2.9 6 1.3 6 4.2 0 1.3-1.3 2.2-3 2.2s-3-.8-3-2" strokeLinecap="round" />
    </svg>
  );
}

function IconCalculator({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" className={className}>
      <rect x="5" y="2.5" width="14" height="19" rx="2" />
      <path d="M8 6.5h8" strokeLinecap="round" />
      <circle cx="8.3" cy="11" r="0.9" fill="currentColor" stroke="none" />
      <circle cx="12" cy="11" r="0.9" fill="currentColor" stroke="none" />
      <circle cx="15.7" cy="11" r="0.9" fill="currentColor" stroke="none" />
      <circle cx="8.3" cy="14.5" r="0.9" fill="currentColor" stroke="none" />
      <circle cx="12" cy="14.5" r="0.9" fill="currentColor" stroke="none" />
      <circle cx="15.7" cy="14.5" r="0.9" fill="currentColor" stroke="none" />
      <circle cx="8.3" cy="18" r="0.9" fill="currentColor" stroke="none" />
      <circle cx="12" cy="18" r="0.9" fill="currentColor" stroke="none" />
      <circle cx="15.7" cy="18" r="0.9" fill="currentColor" stroke="none" />
    </svg>
  );
}

function IconCpu({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" className={className}>
      <rect x="6" y="6" width="12" height="12" rx="1.5" />
      <rect x="9.5" y="9.5" width="5" height="5" rx="0.5" />
      <path d="M9 2.5v3M15 2.5v3M9 18.5v3M15 18.5v3M2.5 9h3M2.5 15h3M18.5 9h3M18.5 15h3" strokeLinecap="round" />
    </svg>
  );
}

function IconLayers({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" className={className}>
      <path d="M12 3 3 8l9 5 9-5z" strokeLinejoin="round" />
      <path d="M3 12l9 5 9-5M3 16l9 5 9-5" strokeLinejoin="round" />
    </svg>
  );
}

function IconTag({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" className={className}>
      <path d="M11.5 3H5a2 2 0 0 0-2 2v6.5a2 2 0 0 0 .59 1.41l8.5 8.5a2 2 0 0 0 2.82 0l6.5-6.5a2 2 0 0 0 0-2.82l-8.5-8.5A2 2 0 0 0 11.5 3Z" strokeLinejoin="round" />
      <circle cx="8" cy="8" r="1.4" fill="currentColor" stroke="none" />
    </svg>
  );
}

function IconCard({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" className={className}>
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <path d="M3 9.5h18" />
      <path d="M6.5 14.5h4" strokeLinecap="round" />
    </svg>
  );
}

const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard", label: "Painel", icon: IconHome },
  { href: "/produtos", label: "Produtos", icon: IconTag },
  { href: "/projetos", label: "Projetos", icon: IconBox },
  { href: "/pedidos", label: "Pedidos", icon: IconClipboard },
  { href: "/clientes", label: "Clientes", icon: IconUsers },
  { href: "/estoque", label: "Estoque", icon: IconArchive },
  { href: "/financeiro", label: "Financeiro", icon: IconDollar },
  { href: "/calculadora", label: "Calculadora", icon: IconCalculator },
  { href: "/maquinas", label: "Máquinas", icon: IconCpu },
  { href: "/materiais", label: "Materiais", icon: IconLayers },
  { href: "/billing", label: "Faturamento", icon: IconCard },
];

function SidebarContent({ pathname, onNavigate }: { pathname: string; onNavigate?: () => void }) {
  return (
    <nav className="flex flex-1 flex-col gap-1 overflow-y-auto px-3 py-4">
      {NAV_ITEMS.map((item) => {
        const active = pathname === item.href || pathname.startsWith(item.href + "/");
        const Icon = item.icon;
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
              active
                ? "bg-blue-600/15 text-blue-300"
                : "text-neutral-400 hover:bg-neutral-900 hover:text-neutral-100"
            }`}
          >
            <Icon className="h-5 w-5 shrink-0" />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}

export function AppShell({ title, children }: { title?: string; children: React.ReactNode }) {
  const { user, organizations, currentOrganizationId, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  const currentOrg = organizations.find(
    (m) => m.organization.id === currentOrganizationId
  )?.organization;

  async function handleLogout() {
    await logout();
    router.replace("/login");
  }

  return (
    <div className="flex min-h-screen">
      <aside className="hidden w-60 shrink-0 flex-col border-r border-neutral-800 bg-neutral-950 lg:flex">
        <div className="flex items-center gap-2 border-b border-neutral-800 px-5 py-4">
          <span className="font-semibold">3D AI Studio</span>
        </div>
        <SidebarContent pathname={pathname} />
      </aside>

      {mobileNavOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div
            className="absolute inset-0 bg-black/60"
            onClick={() => setMobileNavOpen(false)}
          />
          <aside className="absolute inset-y-0 left-0 flex w-64 flex-col border-r border-neutral-800 bg-neutral-950 shadow-xl transition-transform">
            <div className="flex items-center justify-between border-b border-neutral-800 px-5 py-4">
              <span className="font-semibold">3D AI Studio</span>
              <button
                onClick={() => setMobileNavOpen(false)}
                aria-label="Fechar menu"
                className="rounded p-1 text-neutral-400 hover:bg-neutral-900"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-5 w-5">
                  <path d="M6 6l12 12M18 6 6 18" strokeLinecap="round" />
                </svg>
              </button>
            </div>
            <SidebarContent pathname={pathname} onNavigate={() => setMobileNavOpen(false)} />
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between gap-3 border-b border-neutral-800 px-4 py-3 sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <button
              onClick={() => setMobileNavOpen(true)}
              aria-label="Abrir menu"
              className="rounded p-1.5 text-neutral-400 hover:bg-neutral-900 lg:hidden"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-5 w-5">
                <path d="M4 6h16M4 12h16M4 18h16" strokeLinecap="round" />
              </svg>
            </button>
            <h1 className="truncate text-lg font-semibold">{title}</h1>
          </div>
          <div className="flex shrink-0 items-center gap-3 text-sm text-neutral-400">
            {currentOrg && <span className="hidden sm:inline">{currentOrg.name}</span>}
            {user && <span className="hidden truncate md:inline">{user.email}</span>}
            <button onClick={handleLogout} className="text-blue-400 hover:underline">
              Sair
            </button>
          </div>
        </header>

        <div className="min-w-0 flex-1 p-4 sm:p-6">{children}</div>
      </div>
    </div>
  );
}
