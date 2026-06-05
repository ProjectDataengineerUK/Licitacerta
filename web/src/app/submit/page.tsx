import Link from "next/link";
import { Plus } from "lucide-react";
import { SubmitForm } from "@/components/SubmitForm";

export default function SubmitPage() {
  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <Link href="/" className="text-xs text-zinc-500 hover:text-zinc-300 mb-2 inline-block">
          ← Cockpit
        </Link>
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-blue-600 flex items-center justify-center">
            <Plus className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-zinc-100">Nova análise de edital</h1>
            <p className="text-xs text-zinc-500">Cole o texto do edital e informe o CNPJ da sua empresa</p>
          </div>
        </div>
      </div>

      <div className="bg-zinc-900 rounded-2xl border border-zinc-800 p-6">
        <SubmitForm />
      </div>
    </div>
  );
}
