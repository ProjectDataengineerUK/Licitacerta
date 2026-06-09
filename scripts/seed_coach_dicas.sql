-- Seed: Coach Dicas — conteúdo inicial do onboarding

INSERT INTO coach_dicas (id, titulo, descricao, categoria, rota_sugerida, ordem)
VALUES
  ('d01_upload',
   'Faça upload do seu primeiro edital',
   'Carregue um edital em PDF. Nossa IA extrai todos os requisitos automaticamente.',
   'inicio', '/runs/new', 1),

  ('d02_resultado',
   'Entenda o resultado da análise',
   'Após a análise, veja o Bid/No-Bid score e os principais riscos identificados.',
   'analise', NULL, 2),

  ('d03_cashflow',
   'Verifique o fluxo de caixa',
   'O agente de cashflow projeta quando você precisará de capital durante o contrato.',
   'financeiro', NULL, 3),

  ('d04_portfolio',
   'Otimize seu portfólio de licitações',
   'Com mais de uma licitação em análise, use a otimização para maximizar retorno.',
   'decisao', '/portfolio', 4),

  ('d05_recebiveis',
   'Antecipe recebíveis em contratos críticos',
   'Se o cashflow tiver risco crítico, simule a antecipação para garantir capital de giro.',
   'financeiro', '/recebiveis', 5),

  ('d06_mentor',
   'Tire dúvidas com o Mentor IA',
   'O Mentor responde perguntas jurídicas, financeiras e operacionais sobre o edital.',
   'analise', NULL, 6),

  ('d07_impugnacao',
   'Saiba quando impugnar um edital',
   'Cláusulas restritivas podem ser impugnadas. O agente de compliance sinaliza esses casos.',
   'proposta', NULL, 7),

  ('d08_proposta',
   'Gere a proposta comercial',
   'Após aprovar a análise, gere a proposta formatada para o portal de compras.',
   'proposta', NULL, 8)

ON CONFLICT (id) DO NOTHING;
