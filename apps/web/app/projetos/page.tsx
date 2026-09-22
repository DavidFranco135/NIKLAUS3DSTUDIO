"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { apiFetch, ApiError } from "@/lib/api-client";
import type { Project } from "@/lib/types";
import { AppShell } from "@/components/AppShell";

export default function ProjetosPage() {
  const { status, accessToken, currentOrganizationId } = useAuth();
  const router = useRouter();
  const [projects, setProjects] = useState<Project[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [newProjectName, setNewProjectName] = useState("");
  const [isCreating, setIsCreating] = useState(false);

  const loadProjects = useCallback(async () => {
    if (!accessToken || !currentOrganizationId) return;
    setIsLoading(true);
    try {
      const data = await apiFetch<Project[]>(
        `/api/v1/organizations/${currentOrganizationId}/projects`,
        { accessToken }
      );
      setProjects(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao carregar projetos.");
    } finally {
      setIsLoading(false);
    }
  }, [accessToken, currentOrganizationId]);

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/login");
      return;
    }
    if (status !== "authenticated") return;
    const timeoutId = setTimeout(loadProjects, 0);
    return () => clearTimeout(timeoutId);
  }, [status, router, loadProjects]);

  async function handleCreateProject(event: React.FormEvent) {
    event.preventDefault();
    if (!accessToken || !currentOrganizationId) return;
    setIsCreating(true);
    setError(null);
    try {
      await apiFetch(`/api/v1/organizations/${currentOrganizationId}/projects`, {
        method: "POST",
        accessToken,
        body: JSON.stringify({ name: newProjectName }),
      });
      setNewProjectName("");
      await loadProjects();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao criar projeto.");
    } finally {
      setIsCreating(false);
    }
  }

  if (status !== "authenticated") {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <p className="text-neutral-400">Carregando…</p>
      </main>
    );
  }

  return (
    <AppShell title="Projetos">
      <div className="mx-auto max-w-4xl space-y-6">
        {error && <p className="rounded bg-red-950 p-2 text-sm text-red-300">{error}</p>}

        <form onSubmit={handleCreateProject} className="flex flex-col gap-2 sm:flex-row">
          <input
            required
            minLength={2}
            placeholder="Nome do novo projeto"
            value={newProjectName}
            onChange={(e) => setNewProjectName(e.target.value)}
            className="flex-1 rounded border border-neutral-700 bg-neutral-900 px-3 py-2"
          />
          <button
            type="submit"
            disabled={isCreating}
            className="rounded bg-blue-600 px-4 py-2 font-medium disabled:opacity-50"
          >
            {isCreating ? "Criando…" : "Criar projeto"}
          </button>
        </form>

        {isLoading ? (
          <p className="text-neutral-400">Carregando projetos…</p>
        ) : projects.length === 0 ? (
          <p className="text-neutral-400">Nenhum projeto ainda.</p>
        ) : (
          <ul className="divide-y divide-neutral-800 rounded border border-neutral-800">
            {projects.map((project) => (
              <li key={project.id} className="p-4 hover:bg-neutral-900">
                <Link href={`/project?id=${project.id}`} className="flex items-center justify-between">
                  <span>{project.name}</span>
                  <span className="text-sm text-neutral-500">{project.status}</span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </AppShell>
  );
}
