import { ConfigSidebar } from "@/components/ConfigSidebar";

export default function ConfigLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex gap-8 max-w-5xl mx-auto py-8 px-4">
      <ConfigSidebar />
      <main className="flex-1 min-w-0">{children}</main>
    </div>
  );
}
