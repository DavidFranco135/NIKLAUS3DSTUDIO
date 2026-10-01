"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { apiFetch, ApiError } from "@/lib/api-client";
import { inferFileKind } from "@/lib/file-kind";
import type { FileAsset, Project, ProjectVersion, RequestUploadResponse } from "@/lib/types";
import { AppShell } from "@/components/AppShell";
import { ModelViewer } from "@/components/ModelViewer";

export default function ProjectDetailPage() {
  return (
    <Suspense
      fallback={
        <main className="flex min-h-screen items-center justify-center">
          <p className="text-neutral-400">Carregando…</p>
        </main>
      }
    >
      <ProjectDetailPageInner />
    </Suspense>
  );
}

function ProjectDetailPageInner() {
  const { status, accessToken, currentOrganizationId } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const projectId = searchParams.get("id") ?? "";

  const [project, setProject] = useState<Project | null>(null);
  const [versions, setVersions] = useState<ProjectVersion[]>([]);
  const [activeVersionFiles, setActiveVersionFiles] = useState<FileAsset[]>([]);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [label, setLabel] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  const orgPath = `/api/v1/organizations/${currentOrganizationId}/projects/${projectId}`;

  const loadAll = useCallback(async () => {
    if (!accessToken || !currentOrganizationId || !projectId) return;
    try {
      const [projectData, versionsData] = await Promise.all([
        apiFetch<Project>(orgPath, { accessToken }),
        apiFetch<ProjectVersion[]>(`${orgPath}/versions`, { accessToken }),
      ]);
      setProject(projectData);
      setVersions(versionsData);

      if (projectData.active_version_id) {
        const files = await apiFetch<FileAsset[]>(
          `${orgPath}/versions/${projectData.active_version_id}/files`,
          { accessToken }
        );
        setActiveVersionFiles(files);
        const glbFile = files.find((f) => f.kind === "model_glb");
        if (glbFile) {
          const { download_url } = await apiFetch<{ download_url: string }>(
            `${orgPath}/files/${glbFile.id}/download-url`,
            { accessToken }
          );
          setPreviewUrl(download_url);
        } else {
          setPreviewUrl(null);
        }
      } else {
        setActiveVersionFiles([]);
        setPreviewUrl(null);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao carregar projeto.");
    }
  }, [accessToken, currentOrganizationId, orgPath, projectId]);

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/login");
      return;
    }
    if (status !== "authenticated") return;
    if (!projectId) {
      router.replace("/projetos");
      return;
    }
    const timeoutId = setTimeout(loadAll, 0);
    return () => clearTimeout(timeoutId);
  }, [status, router, loadAll, projectId]);

  async function uploadAndConfirmFile(file: File, kind: string): Promise<string> {
    const uploadInfo = await apiFetch<RequestUploadResponse>(`${orgPath}/files/upload-url`, {
      method: "POST",
      accessToken,
      body: JSON.stringify({
        filename: file.name,
        mime_type: file.type || "application/octet-stream",
        kind,
      }),
    });

    const putResponse = await fetch(uploadInfo.upload_url, {
      method: "PUT",
      body: file,
      headers: { "Content-Type": file.type || "application/octet-stream" },
    });
    if (!putResponse.ok) {
      throw new Error(`Falha ao enviar arquivo ao storage (HTTP ${putResponse.status}).`);
    }

    await apiFetch(`${orgPath}/files/${uploadInfo.file_id}/confirm`, { method: "POST", accessToken });
    return uploadInfo.file_id;
  }

  async function handleUpload(event: React.FormEvent) {
    event.preventDefault();
    if (!accessToken || !selectedFile) return;
    setIsUploading(true);
    setError(null);
    setMessage(null);
    try {
      const fileId = await uploadAndConfirmFile(selectedFile, inferFileKind(selectedFile.name));
      await apiFetch(`${orgPath}/versions`, {
        method: "POST",
        accessToken,
        body: JSON.stringify({ file_id: fileId, label: label || null }),
      });

      setSelectedFile(null);
      setLabel("");
      setMessage("Nova versão criada.");
      await loadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao enviar arquivo.");
    } finally {
      setIsUploading(false);
    }
  }

  async function handleActivate(versionId: string) {
    if (!accessToken) return;
    setError(null);
    try {
      await apiFetch(`${orgPath}/versions/${versionId}/activate`, {
        method: "POST",
        accessToken,
      });
      await loadAll();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao ativar versão.");
    }
  }

  async function handleDownload(fileId: string) {
    if (!accessToken) return;
    try {
      const { download_url } = await apiFetch<{ download_url: string }>(
        `${orgPath}/files/${fileId}/download-url`,
        { accessToken }
      );
      window.open(download_url, "_blank");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao gerar link de download.");
    }
  }

  if (status !== "authenticated" || !project) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <p className="text-neutral-400">Carregando…</p>
      </main>
    );
  }

  return (
    <AppShell title={project.name}>
      <div className="mx-auto max-w-5xl space-y-6">
        {project.description && <p className="text-neutral-400">{project.description}</p>}

        {error && <p className="rounded bg-red-950 p-2 text-sm text-red-300">{error}</p>}
        {message && <p className="rounded bg-green-950 p-2 text-sm text-green-300">{message}</p>}

        {previewUrl && (
          <div>
            <h2 className="mb-2 text-lg font-medium">Preview 3D</h2>
            <ModelViewer src={previewUrl} />
          </div>
        )}
        {activeVersionFiles.length > 0 && !previewUrl && (
          <p className="text-sm text-neutral-500">
            Sem preview 3D disponível para este formato ainda — baixe o arquivo para visualizar.
          </p>
        )}

        <form onSubmit={handleUpload} className="space-y-3 rounded border border-neutral-800 p-4">
          <h2 className="text-lg font-medium">Nova versão</h2>
          <input
            type="file"
            required
            onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
            className="block w-full text-sm"
          />
          <input
            placeholder="Rótulo (opcional)"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            className="w-full rounded border border-neutral-700 bg-neutral-900 px-3 py-2"
          />
          <button
            type="submit"
            disabled={isUploading || !selectedFile}
            className="rounded bg-blue-600 px-4 py-2 font-medium disabled:opacity-50"
          >
            {isUploading ? "Enviando…" : "Enviar e criar versão"}
          </button>
        </form>

        <div>
          <h2 className="mb-2 text-lg font-medium">Versões</h2>
          <ul className="divide-y divide-neutral-800 rounded border border-neutral-800">
            {versions.map((version) => (
              <li key={version.id} className="flex items-center justify-between p-4">
                <span>
                  v{version.version_number}
                  {version.label ? ` — ${version.label}` : ""}
                  {project.active_version_id === version.id && (
                    <span className="ml-2 rounded bg-blue-900 px-2 py-0.5 text-xs">ativa</span>
                  )}
                </span>
                {project.active_version_id !== version.id && (
                  <button
                    onClick={() => handleActivate(version.id)}
                    className="text-sm text-blue-400 hover:underline"
                  >
                    Ativar
                  </button>
                )}
              </li>
            ))}
          </ul>
        </div>

        {activeVersionFiles.length > 0 && (
          <div>
            <h2 className="mb-2 text-lg font-medium">Arquivos da versão ativa</h2>
            <ul className="divide-y divide-neutral-800 rounded border border-neutral-800">
              {activeVersionFiles.map((file) => (
                <li key={file.id} className="flex items-center justify-between p-4">
                  <span>
                    {file.kind} — {file.size_bytes ? `${Math.round(file.size_bytes / 1024)} KB` : "—"}
                  </span>
                  <button
                    onClick={() => handleDownload(file.id)}
                    className="text-sm text-blue-400 hover:underline"
                  >
                    Baixar
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </AppShell>
  );
}
