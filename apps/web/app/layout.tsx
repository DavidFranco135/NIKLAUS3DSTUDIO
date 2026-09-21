import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "3D AI Studio",
  description: "Copiloto de produção 3D",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR">
      <body className="bg-neutral-950 text-neutral-100">{children}</body>
    </html>
  );
}
