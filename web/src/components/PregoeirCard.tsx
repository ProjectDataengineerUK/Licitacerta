"use client";

interface EmpresaFrequente {
  cnpj: string;
  nome?: string;
  frequencia: number;
}

interface PregoeiroPerfil {
  nome: string;
  orgao_cnpj: string;
  orgao_nome?: string;
  total_sessoes: number;
  indice_reputacao?: number;
  confianca_pct: number;
  label_confianca: string;
  taxa_aceitacao_impugnacao_pct?: number;
  taxa_desclassificacao_pct?: number;
  tempo_medio_sessao_horas?: number;
  previsibilidade?: number;
  clausulas_frequentes: string[];
  tipos_desclassificacao: string[];
  empresas_frequentes_vencedoras: EmpresaFrequente[];
  alertas: string[];
}

function IndexGauge({ value }: { value: number }) {
  const color =
    value >= 70 ? "text-emerald-600" : value >= 40 ? "text-amber-500" : "text-red-500";
  const bg =
    value >= 70 ? "bg-emerald-100" : value >= 40 ? "bg-amber-100" : "bg-red-100";
  return (
    <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-sm font-semibold ${bg} ${color}`}>
      <span>{value.toFixed(0)}</span>
      <span className="text-xs font-normal">/100</span>
    </div>
  );
}

function StatRow({ label, value, unit }: { label: string; value?: number | null; unit?: string }) {
  if (value == null) return null;
  return (
    <div className="flex justify-between text-sm py-1.5 border-b border-gray-100 last:border-0">
      <span className="text-gray-500">{label}</span>
      <span className="font-medium text-gray-800">
        {value.toFixed(1)}{unit ? ` ${unit}` : ""}
      </span>
    </div>
  );
}

export function PregoeirCard({ perfil }: { perfil: PregoeiroPerfil }) {
  const semDados = perfil.total_sessoes === 0;

  return (
    <div className="border border-gray-200 rounded-xl p-5 space-y-4 bg-white shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="font-semibold text-gray-900">{perfil.nome}</h3>
          {perfil.orgao_nome && (
            <p className="text-xs text-gray-500 mt-0.5">{perfil.orgao_nome}</p>
          )}
        </div>
        <div className="flex flex-col items-end gap-1">
          {perfil.indice_reputacao != null ? (
            <IndexGauge value={perfil.indice_reputacao} />
          ) : (
            <span className="text-xs text-gray-400 italic">Índice indisponível</span>
          )}
          <span className="text-xs text-gray-400">{perfil.label_confianca}</span>
        </div>
      </div>

      {perfil.alertas.length > 0 && (
        <div className="space-y-1.5">
          {perfil.alertas.map((a, i) => (
            <div key={i} className="flex items-start gap-2 text-sm text-amber-700 bg-amber-50 rounded-lg px-3 py-2">
              <span className="mt-0.5 shrink-0">⚠</span>
              <span>{a}</span>
            </div>
          ))}
        </div>
      )}

      {!semDados && (
        <div className="bg-gray-50 rounded-lg px-4 py-3">
          <StatRow label="Aceitação de impugnações" value={perfil.taxa_aceitacao_impugnacao_pct} unit="%" />
          <StatRow label="Taxa de desclassificação" value={perfil.taxa_desclassificacao_pct} unit="%" />
          <StatRow label="Duração média das sessões" value={perfil.tempo_medio_sessao_horas} unit="h" />
          <StatRow
            label="Previsibilidade"
            value={perfil.previsibilidade != null ? perfil.previsibilidade * 100 : null}
            unit="%"
          />
        </div>
      )}

      {semDados && (
        <p className="text-sm text-gray-400 italic text-center py-2">
          Sem dados históricos para este pregoeiro ainda.
        </p>
      )}

      {perfil.empresas_frequentes_vencedoras.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
            Empresas que frequentemente vencem
          </p>
          <ul className="space-y-1">
            {perfil.empresas_frequentes_vencedoras.slice(0, 5).map((e, i) => (
              <li key={i} className="flex justify-between text-sm">
                <span className="text-gray-700 truncate">{e.nome || e.cnpj}</span>
                <span className="text-gray-400 shrink-0 ml-2">{e.frequencia}×</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {perfil.clausulas_frequentes.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
            Cláusulas frequentes
          </p>
          <div className="flex flex-wrap gap-1.5">
            {perfil.clausulas_frequentes.map((c, i) => (
              <span key={i} className="text-xs bg-blue-50 text-blue-700 rounded-full px-2.5 py-0.5">
                {c}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
