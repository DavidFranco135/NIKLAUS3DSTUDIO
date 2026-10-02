"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { Storefront } from "@/components/store/Storefront";

function LojaContent() {
  const params = useSearchParams();
  const slug = params.get("s");

  if (!slug) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-neutral-50 p-6 text-center text-neutral-700">
        <div className="space-y-2">
          <p className="text-2xl font-semibold">Loja não encontrada.</p>
          <p className="text-sm text-neutral-500">Use o link completo da loja que você recebeu.</p>
        </div>
      </div>
    );
  }
  return <Storefront slug={slug} />;
}

export default function LojaPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-neutral-50" />}>
      <LojaContent />
    </Suspense>
  );
}
