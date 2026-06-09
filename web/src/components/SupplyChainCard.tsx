"use client";

interface APICheck {
  api: string;
  status: "aprovado" | "reprovado" | "nao_verificado" | "pendente_regularizacao";
  numero_registro?: string | null;
  valido_ate?: string | null;
  nota?: string | null;
}

interface SupplyChainData {
  produto_descricao: string;
  fabricante_nome: string;
  fabricante_cnpj: string;
  categoria: string;
  checks: APICheck[];
  status_geral: "aprovado" | "reprovado" | "nao_verificado" | "pendente_regularizacao";
  bloqueante: boolean;
  fundamentacao?: string | null;
}

const STATUS_CONFIG = {
  aprovado:              { label: "Aprovado",              color: "text-emerald-700 bg-emerald-50 border-emerald-200" },
  reprovado:             { label: "Reprovado",             color: "text-red-700 bg-red-50 border-red-200" },
  nao_verificado:        { label: "Não verificado",        color: "text-gray-500 bg-gray-50 border-gray-200" },
  pendente_regularizacao:{ label: "Pendente regularização",color: "text-amber-700 bg-amber-50 border-amber-200" },
} as const;

function StatusBadge({ status }: { status: keyof typeof STATUS_CONFIG }) {
  const { label, color } = STATUS_CONFIG[status] ?? STATUS_CONFIG.nao_verificado;
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded border ${color}`}>
      {label}
    </span>
  );
}

export function SupplyChainCard({ data }: { data: SupplyChainData }) {
  return (
    <div className={`rounded-xl border shadow-sm overflow-hidden ${data.bloqueante ? "border-red-300" : "border-gray-200"}`}>
      <div className={`px-5 py-4 border-b flex items-center justify-between ${data.bloqueante ? "bg-red-50" : "bg-white"}`}>
        <div className="flex items-center gap-2">
          <span className="text-lg">🏭</span>
          <h2 className="font-semibold text-gray-800 text-sm">Conformidade de Fornecimento</h2>
          {data.bloqueante && (
            <span className="text-xs font-bold text-red-700 bg-red-100 border border-red-300 px-2 py-0.5 rounded">
              BLOQUEANTE
            </span>
          )}
        </div>
        <StatusBadge status={data.status_geral} />
      </div>

      <div className="px-5 py-4 space-y-4 bg-white">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Produto</p>
            <p className="text-gray-700 font-medium truncate">{data.produto_descricao}</p>
          </div>
          <div>
            <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Fabricante</p>
            <p className="text-gray-700 font-medium">{data.fabricante_nome}</p>
            <p className="text-gray-400 text-xs font-mono">{data.fabricante_cnpj}</p>
          </div>
          <div>
            <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Categoria</p>
            <p className="text-gray-700 font-medium capitalize">{data.categoria.replace(/_/g, " ")}</p>
          </div>
        </div>

        <div>
          <p className="text-xs text-gray-400 uppercase tracking-wide mb-2">Verificações por API</p>
          <div className="space-y-2">
            {data.checks.map((c) => (
              <div key={c.api} className="flex items-start justify-between text-sm border rounded-lg px-3 py-2">
                <div>
                  <span className="font-mono font-medium text-gray-700 uppercase text-xs">{c.api}</span>
                  {c.numero_registro && (
                    <span className="text-gray-400 text-xs ml-2">Reg. {c.numero_registro}</span>
                  )}
                  {c.valido_ate && (
                    <span className="text-gray-400 text-xs ml-2">válido até {c.valido_ate}</span>
                  )}
                  {c.nota && (
                    <p className="text-xs text-gray-400 mt-0.5">{c.nota}</p>
                  )}
                </div>
                <StatusBadge status={c.status} />
              </div>
            ))}
          </div>
        </div>

        {data.fundamentacao && (
          <div className="text-xs text-gray-500 bg-gray-50 rounded-lg px-3 py-2 border">
            {data.fundamentacao}
          </div>
        )}
      </div>
    </div>
  );
}
