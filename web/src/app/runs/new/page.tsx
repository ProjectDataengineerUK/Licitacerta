import { SubmitForm } from "@/components/SubmitForm";
import { FileText } from "lucide-react";

export const metadata = {
  title: "Nova Análise — LicitaCerta",
};

export default function NovaAnalise() {
  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-blue-600 flex items-center justify-center">
          <FileText className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-zinc-100">Nova Análise</h1>
          <p className="text-xs text-zinc-500">Cole o edital e informe o CNPJ para iniciar</p>
        </div>
      </div>

      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6">
        <SubmitForm />
      </div>
    </div>
  );
}
