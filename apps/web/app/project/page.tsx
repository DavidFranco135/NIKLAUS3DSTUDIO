"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { apiFetch, ApiError } from "@/lib/api-client";
import { inferFileKind } from "@/lib/file-kind";
import type { AIJob, FileAsset, Project, ProjectVersion, RequestUploadResponse } from "@/lib/types";
import { AppShell } from "@/components/AppShell";
import { ModelViewer } from "@/components/ModelViewer";

type VariantStatus = "generating" | "done" | "failed";

type VariantResult = {
  seed: string;
  status: VariantStatus;
  job: AIJob | null;
  previewUrl: string | null;
  fileKind: string | null;
  errorMessage: string | null;
};

function makeSeed(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

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
  const [aiPrompt, setAiPrompt] = useState("");
  const [aiImageFile, setAiImageFile] = useState<File | null>(null);
  const [variantCount, setVariantCount] = useState(1);
  const [variants, setVariants] = useState<VariantResult[]>([]);
  const [isGeneratingAI, setIsGeneratingAI] = useState(false);

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

  async function pollJobUntilDone(jobId: string): Promise<AIJob> {
    const jobPath = `/api/v1/organizations/${currentOrganizationId}/ai/jobs/${jobId}`;
    for (let attempt = 0; attempt < 30; attempt++) {
      const current = await apiFetch<AIJob>(jobPath, { accessToken });
      if (current.status === "COMPLETED" || current.status === "FAILED") return current;
      await new Promise((resolve) => setTimeout(resolve, 1500));
    }
    throw new Error("O job de IA demorou demais para concluir.");
  }

  function updateVariant(seed: string, patch: Partial<VariantResult>) {
    setVariants((current) =>
      current.map((v) => (v.seed === seed ? { ...v, ...patch } : v))
    );
  }

  async function runVariant(seed: string, imageFileId: string | null) {
    try {
      const created = await apiFetch<AIJob>(
        `/api/v1/organizations/${currentOrganizationId}/ai/jobs`,
        {
          method: "POST",
          accessToken,
          body: JSON.stringify({
            prompt: aiPrompt || null,
            image_file_id: imageFileId,
            project_id: projectId,
            variant_seed: seed,
          }),
        }
      );
      const finished =
        created.status === "COMPLETED" || created.status === "FAILED"
          ? created
          : await pollJobUntilDone(created.id);

      if (finished.status !== "COMPLETED") {
        updateVariant(seed, {
          status: "failed",
          job: finished,
          errorMessage: finished.error_message ?? "A geração por IA falhou.",
        });
        return;
      }

      let previewUrl: string | null = null;
      let fileKind: string | null = null;
      if (finished.result_project_version_id) {
        const files = await apiFetch<FileAsset[]>(
          `${orgPath}/versions/${finished.result_project_version_id}/files`,
          { accessToken }
        );
        const resultFile = files.find((f) => f.id === finished.result_file_id) ?? null;
        fileKind = resultFile?.kind ?? null;
        const glbFile = files.find((f) => f.kind === "model_glb");
        if (glbFile) {
          const { download_url } = await apiFetch<{ download_url: string }>(
            `${orgPath}/files/${glbFile.id}/download-url`,
            { accessToken }
          );
          previewUrl = download_url;
        }
      }
      updateVariant(seed, { status: "done", job: finished, previewUrl, fileKind });
    } catch (err) {
      updateVariant(seed, {
        status: "failed",
        errorMessage: err instanceof ApiError ? err.message : "Falha ao criar o job de IA.",
      });
    }
  }

  async function handleGenerateWithAI(event: React.FormEvent) {
    event.preventDefault();
    if (!accessToken) return;
    setIsGeneratingAI(true);
    setError(null);
    setMessage(null);

    try {
      let imageFileId: string | null = null;
      if (aiImageFile) {
        imageFileId = await uploadAndConfirmFile(aiImageFile, "source_image");
      }

      const seeds = Array.from({ length: variantCount }, () => makeSeed());
      setVariants(
        seeds.map((seed) => ({
          seed,
          status: "generating",
          job: null,
          previewUrl: null,
          fileKind: null,
          errorMessage: null,
        }))
      );

      await Promise.all(seeds.map((seed) => runVariant(seed, imageFileId)));
      setMessage(
        variantCount > 1
          ? "Variações geradas — escolha uma para usar no projeto."
          : "Modelo gerado — confira o preview e use ou baixe."
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao gerar com IA.");
    } finally {
      setIsGeneratingAI(false);
    }
  }

  async function handleUseVariant(versionId: string) {
    await handleActivate(versionId);
    setMessage("Versão aplicada ao projeto.");
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

        <div className="rounded-xl border border-neutral-800 bg-neutral-950/50 p-4 sm:p-6">
          <div className="mb-4">
            <h2 className="text-lg font-medium">Gerar com IA</h2>
            <p className="mt-1 text-xs text-neutral-500">
              Com dimensões exatas (ex: &quot;70x35x4mm&quot;), a geometria é gerada de verdade
              (CAD paramétrico real). Sem dimensões exatas ou a partir de uma imagem, o resultado
              ainda é um mock de desenvolvimento (nenhum modelo generativo de IA integrado ainda).
            </p>
          </div>

          <div className="grid gap-6 lg:grid-cols-[minmax(280px,360px)_1fr]">
            <form onSubmit={handleGenerateWithAI} className="space-y-4">
              <textarea
                placeholder='Texto (opcional se enviar imagem). Ex: "Crie um chaveiro de 70x35x4mm com o nome CARLOS, furo de 5mm"'
                value={aiPrompt}
                onChange={(e) => setAiPrompt(e.target.value)}
                rows={3}
                className="w-full rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm"
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
              <div className="space-y-1">
                <label className="block text-xs text-neutral-500">Quantidade de variações</label>
                <div className="flex gap-2">
                  {[1, 2, 3, 4].map((n) => (
                    <button
                      key={n}
                      type="button"
                      onClick={() => setVariantCount(n)}
                      className={`flex-1 rounded-lg border px-3 py-2 text-sm font-medium transition-colors ${
                        variantCount === n
                          ? "border-purple-500 bg-purple-950 text-purple-200"
                          : "border-neutral-700 bg-neutral-900 text-neutral-400 hover:border-neutral-600"
                      }`}
                    >
                      {n}
                    </button>
                  ))}
                </div>
              </div>
              <button
                type="submit"
                disabled={isGeneratingAI || (!aiPrompt.trim() && !aiImageFile)}
                className="w-full rounded-lg bg-purple-600 px-4 py-2.5 font-medium transition-colors hover:bg-purple-500 disabled:opacity-50"
              >
                {isGeneratingAI ? "Gerando…" : "Gerar com IA"}
              </button>
            </form>

            <div className="min-h-[220px]">
              {variants.length === 0 && (
                <div className="flex h-full min-h-[220px] items-center justify-center rounded-lg border border-dashed border-neutral-800 text-sm text-neutral-600">
                  Os resultados aparecem aqui após gerar.
                </div>
              )}
              {variants.length > 0 && (
                <div
                  className={`grid gap-4 ${
                    variants.length === 1 ? "grid-cols-1" : "sm:grid-cols-2"
                  }`}
                >
                  {variants.map((variant, index) => (
                    <div
                      key={variant.seed}
                      className="space-y-2 rounded-lg border border-neutral-800 bg-neutral-900/60 p-3"
                    >
                      <div className="flex items-center justify-between text-xs text-neutral-500">
                        <span>Variação {index + 1}</span>
                        {variant.status === "generating" && (
                          <span className="text-purple-300">Gerando…</span>
                        )}
                        {variant.status === "done" && (
                          <span className="text-green-400">Concluído</span>
                        )}
                        {variant.status === "failed" && (
                          <span className="text-red-400">Falhou</span>
                        )}
                      </div>

                      {variant.status === "generating" && (
                        <div className="flex h-48 items-center justify-center rounded border border-neutral-800 bg-neutral-950">
                          <span className="animate-pulse text-sm text-neutral-500">
                            Processando…
                          </span>
                        </div>
                      )}

                      {variant.status === "failed" && (
                        <p className="rounded bg-red-950 p-2 text-xs text-red-300">
                          {variant.errorMessage}
                        </p>
                      )}

                      {variant.status === "done" && variant.previewUrl && (
                        <ModelViewer src={variant.previewUrl} />
                      )}
                      {variant.status === "done" && !variant.previewUrl && (
                        <div className="flex h-48 items-center justify-center rounded border border-neutral-800 bg-neutral-950 px-2 text-center text-xs text-neutral-500">
                          Sem preview 3D disponível para este formato — use ou baixe para
                          visualizar.
                        </div>
                      )}

                      {variant.status === "done" &&
                        variant.job?.result_metadata?.development_only && (
                          <p className="rounded bg-yellow-950 p-2 text-xs text-yellow-300">
                            MOCK DE DESENVOLVIMENTO — não é uma geração 3D real.{" "}
                            {variant.job.result_metadata.note}
                          </p>
                        )}

                      {variant.status === "done" && variant.job && (
                        <div className="flex gap-2">
                          {variant.job.result_project_version_id && (
                            <button
                              onClick={() => handleUseVariant(variant.job!.result_project_version_id!)}
                              className="flex-1 rounded bg-blue-600 px-3 py-1.5 text-xs font-medium hover:bg-blue-500"
                            >
                              Usar esta versão
                            </button>
                          )}
                          {variant.job.result_file_id && (
                            <button
                              onClick={() => handleDownload(variant.job!.result_file_id!)}
                              className="flex-1 rounded border border-neutral-700 px-3 py-1.5 text-xs font-medium hover:border-neutral-500"
                            >
                              Baixar
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

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
