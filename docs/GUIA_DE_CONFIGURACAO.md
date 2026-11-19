# RADAR DE VAGAS — Guia Prático de Configuração

Este guia ensina como personalizar e ajustar cada um dos arquivos presentes no diretório `/config` para atender perfeitamente aos seus objetivos de carreira e localização.

---

## 1. Ajustando seu Perfil (`config/profile.yaml`)

- **`candidata.nome`**: Nome para identificação nos relatórios.
- **`nivel_senioridade_alvo`**: Ajuste a lista para os níveis de seu interesse (ex: `["Pleno", "Sênior"]`).
- **`competencias_tecnicas.avancadas`**: Adicione ou remova tecnologias que você domina (ex: Power BI, SQL, DAX). Quanto mais precisas forem as ferramentas listadas, melhor será o cálculo de pontuação.
- **`areas_de_atuacao_dominio`**: Áreas de negócio onde você possui experiência (ex: BI, Comercial, Logística).

---

## 2. Definindo Cargos, Localidades e Fontes (`config/search_queries.yaml`)

- **`cargos_procurados`**: Pode adicionar novas palavras ou títulos de vagas nos grupos existentes (Dados, Operações, Comercial, Logística) ou criar novos grupos.
- **`localidades.cidade_base_usuario`**: Defina sua cidade principal de residência.
- **`localidades.cidades_prioritarias`**: Lista de municípios da sua região aceitáveis para vagas híbridas/presenciais.
- **`modalidades.ordem_prioridade`**: Define o peso de preferência entre Remoto, Híbrido e Presencial.
- **`fontes_de_vagas`**: Alterne entre `ativo: true` e `ativo: false` para habilitar ou desabilitar plataformas específicas (LinkedIn, Indeed, Glassdoor, Gupy, Google Jobs).

---

## 3. Calibrando Palavras-Chave e Filtros Negativos (`config/keywords.yaml`)

- **`palavras_chave_essenciais`**: Termos que, se presentes na vaga, concedem a pontuação máxima no critério técnico.
- **`sinonimos_e_aliases`**: Ensina o sistema a reconhecer variações (ex: reconhecer que "PBI" é o mesmo que "Power BI").
- **`termos_excludentes_titulo`**: Lista de termos no título que provocam o descarte imediato da vaga (ex: "Estágio", "Vendedor Externo", "Enfermagem").

---

## 4. Ajustando os Pesos do Fit Score (`config/scoring_rules.yaml`)

A pontuação total é calibrada em uma escala de **0 a 100 pontos**:
- **`competencias_tecnicas_max`** (Padrão: 40): Peso das hard skills.
- **`alinhamento_area_e_cargo_max`** (Padrão: 20): Peso do título da vaga e área.
- **`modalidade_max`** (Padrão: 20): Bônus para vagas remotas ou híbridas.
- **`localidade_max`** (Padrão: 10): Bônus por proximidade geográfica.
- **`senioridade_max`** (Padrão: 10): Compatibilidade do nível de experiência.
- **`score_minimo_para_buscar_recrutadores`** (Padrão: 70): Apenas vagas que atingirem esse score terão recrutadores pesquisados automaticamente.

---

## 5. Regras de Deduplicação (`config/deduplication_rules.yaml`)

- **`sanitizacao_url`**: Lista de parâmetros de rastreamento removidos para evitar links duplicados.
- **`dias_validade_vaga`**: Intervalo em dias antes que uma vaga previamente vista possa ser analisada novamente caso reaberta.

---

## 6. Agendamento de Horários (`config/scheduler.yaml`)

- **`horarios_diarios`**: Horários do dia em que a rotina será executada automaticamente (padrão: `["08:00", "12:30", "18:00"]`).
- **`dias_da_semana`**: Dias ativos para a coleta de vagas.
