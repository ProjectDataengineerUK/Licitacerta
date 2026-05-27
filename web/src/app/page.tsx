import { SubmitForm } from "@/components/SubmitForm";

export default function HomePage() {
  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Analisar Edital</h1>
        <p className="text-gray-500 mt-1 text-sm">
          Cole o texto do edital e o CNPJ da sua empresa para iniciar a análise.
        </p>
      </div>
      <div className="bg-white rounded-xl border p-6 shadow-sm">
        <SubmitForm />
      </div>
    </div>
  );
}
