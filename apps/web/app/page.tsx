"use client";

import { useEffect, useState } from "react";

type ApiStatus = "checking" | "online" | "offline";

export default function HomePage() {
  const [apiStatus, setApiStatus] = useState<ApiStatus>("checking");

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    fetch(`${apiUrl}/api/v1/health`)
      .then((res) => (res.ok ? setApiStatus("online") : setApiStatus("offline")))
      .catch(() => setApiStatus("offline"));
  }, []);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-24">
      <h1 className="text-3xl font-semibold">3D AI Studio</h1>
      <p className="text-neutral-400">Fase 1 — Fundação</p>
      <p>
        API:{" "}
        <span
          className={
            apiStatus === "online"
              ? "text-green-400"
              : apiStatus === "offline"
                ? "text-red-400"
                : "text-neutral-400"
          }
        >
          {apiStatus}
        </span>
      </p>
    </main>
  );
}
