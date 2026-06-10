import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/providers";
import { NavBar } from "@/components/NavBar";
import { CoachOverlay } from "@/components/CoachOverlay";
import { ActivationGuard } from "@/components/ActivationGuard";
import { ConsentGate } from "@/components/ConsentGate";

const inter = Inter({ subsets: ["latin"] });

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "LicitaCerta",
  description: "Análise inteligente de editais de licitação",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR">
      <body className={`${inter.className} bg-zinc-950 text-zinc-100 min-h-screen`}>
        <Providers>
          <ActivationGuard>
            <NavBar />
            <main className="max-w-6xl mx-auto px-6 py-8">{children}</main>
            <CoachOverlay />
            <ConsentGate />
          </ActivationGuard>
        </Providers>
      </body>
    </html>
  );
}
