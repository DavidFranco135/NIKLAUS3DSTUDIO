"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { apiFetch, ApiError } from "@/lib/api-client";
import { inferFileKind } from "@/lib/file-kind";
import type { AIJob, FileAsset, Project, ProjectVersion, RequestUploadResponse } from "@/lib/types";
import { AppHeader } from "@/components/AppHeader";
import { ModelViewer } from "@/components/ModelViewer";

export default function ProjectDetailPage() {
  const { status, accessToken, currentOrganizationId } = useAuth();
  const router = useRouter();
  const { projectId } = useParams<{ projectId: string }>();

  const [project, setProject] = useState<Project | null>(null);
  const [versions, setVersions] = useState<ProjectVersion[]>([]);
  const [activeVersionFiles, setActiveVersionFiles] = useState<FileAsset[]>([]);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [label, setLabel] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [aiPrompt, setAiPrompt] = useState("");
  const [aiImageFile, setAiImageFile] = useState<File | null>(null);
  const [aiJob, setAiJob] = useState<AIJob | null>(null);
  const [isGeneratingAI, setIsGeneratingAI] = useState(false);

  const orgPath = `/api/v1/organizations/${currentOrganizationId}/projects/${projectId}`;

  const loadAll = useCallback(async () => {
    if (!accessToken || !currentOrganizationId) return;
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
  }, [accessToken, currentOrganizationId, orgPath]);

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/login");
      return;
    }
    if (status !== "authenticated") return;
    const timeoutId = setTimeout(loadAll, 0);
    return () => clearTimeout(timeoutId);
  }, [status, router, loadAll]);

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

  async function pollJobUntilDone(jobId: string): Promise<AIJob> {
    const jobPath = `/api/v1/organizations/${currentOrganizationId}/ai/jobs/${jobId}`;
    for (let attempt = 0; attempt < 30; attempt++) {
      const current = await apiFetch<AIJob>(jobPath, { accessToken });
      if (current.status === "COMPLETED" || current.status === "FAILED") return current;
      await new Promise((resolve) => setTimeout(resolve, 1500));
    }
    throw new Error("O job de IA demorou demais para concluir.");
  }

  async function handleGenerateWithAI(event: React.FormEvent) {
    event.preventDefault();
    if (!accessToken) return;
    setIsGeneratingAI(true);
    setError(null);
    setMessage(null);
    setAiJob(null);
    try {
      let imageFileId: string | null = null;
      if (aiImageFile) {
        imageFileId = await uploadAndConfirmFile(aiImageFile, "source_image");
      }

      const created = await apiFetch<AIJob>(
        `/api/v1/organizations/${currentOrganizationId}/ai/jobs`,
        {
          method: "POST",
          accessToken,
          body: JSON.stringify({
            prompt: aiPrompt || null,
            image_file_id: imageFileId,
            project_id: projectId,
          }),
        }
      );
      const finished =
        created.status === "COMPLETED" || created.status === "FAILED"
          ? created
          : await pollJobUntilDone(created.id);
      setAiJob(finished);
      if (finished.status === "COMPLETED") {
        setAiPrompt("");
        setAiImageFile(null);
        setMessage("Modelo gerado pela IA — nova versão criada.");
        await loadAll();
      } else {
        setError(finished.error_message ?? "A geração por IA falhou.");
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao criar o job de IA.");
    } finally {
      setIsGeneratingAI(false);
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
    <main className="min-h-screen">
      <AppHeader />
      <div className="mx-auto max-w-3xl space-y-6 p-6">
        <div>
          <h1 className="text-2xl font-semibold">{project.name}</h1>
          {project.description && <p className="text-neutral-400">{project.description}</p>}
        </div>

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

        <form onSubmit={handleGenerateWithAI} className="space-y-3 rounded border border-neutral-800 p-4">
          <h2 className="text-lg font-medium">Gerar com IA</h2>
          <p className="text-xs text-neutral-500">
            Com dimensões exatas (ex: &quot;70x35x4mm&quot;), a geometria é gerada de verdade (CAD
            paramétrico real). Sem dimensões exatas ou a partir de uma imagem, o resultado ainda
            é um mock de desenvolvimento (nenhum modelo generativo de IA integrado ainda).
          </p>
          <textarea
            placeholder='Texto (opcional se enviar imagem). Ex: "Crie um chaveiro de 70x35x4mm com o nome CARLOS, furo de 5mm"'
            value={aiPrompt}
            onChange={(e) => setAiPrompt(e.target.value)}
            rows={2}
            className="w-full rounded border border-neutral-700 bg-neutral-900 px-3 py-2"
          />
          <div className="space-y-1">
            <label className="block text-xs text-neutral-500">
              Ou gerar a partir de uma imagem (opcional)
            </label>
            <input
              type="file"
              accept="image/png,image/jpeg,image/webp"
              onChange={(e) => setAiImageFile(e.target.files?.[0] ?? null)}
              className="block w-full text-sm"
            />
          </div>
          <button
            type="submit"
            disabled={isGeneratingAI || (!aiPrompt.trim() && !aiImageFile)}
            className="rounded bg-purple-600 px-4 py-2 font-medium disabled:opacity-50"
          >
            {isGeneratingAI ? "Gerando…" : "Gerar com IA"}
          </button>
          {aiJob && (
            <div className="rounded border border-neutral-800 p-3 text-sm text-neutral-400">
              <p>
                Tarefa classificada como <strong>{aiJob.task_type}</strong> — status:{" "}
                <strong>{aiJob.status}</strong>
              </p>
              {aiJob.result_metadata?.development_only && (
                <p className="mt-1 rounded bg-yellow-950 p-2 text-yellow-300">
                  MOCK DE DESENVOLVIMENTO — não é uma geração 3D real.{" "}
                  {aiJob.result_metadata.note}
                </p>
              )}
              <ul className="mt-1 list-inside list-disc">
                {aiJob.attempts.map((attempt) => (
                  <li key={attempt.attempt_number}>
                    {attempt.provider_name}: {attempt.status}
                    {attempt.error_detail ? ` (${attempt.error_detail})` : ""}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </form>

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
    </main>
  );
}
