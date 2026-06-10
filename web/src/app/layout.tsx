import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/providers";
import { Sidebar } from "@/components/Sidebar";
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
      <body className={`${inter.className} bg-zinc-950 text-zinc-100`}>
        <Providers>
          <ActivationGuard>
            <div className="flex h-screen overflow-hidden">
              <Sidebar />
              <div className="flex-1 overflow-y-auto">
                <main className="px-8 py-8 min-h-full">{children}</main>
              </div>
            </div>
            <CoachOverlay />
            <ConsentGate />
          </ActivationGuard>
        </Providers>
      </body>
    </html>
  );
}
