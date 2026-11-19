# RADAR DE VAGAS — Documentação da Estrutura do Projeto

Este documento detalha o propósito e a responsabilidade de cada diretório e arquivo na estrutura inicial do **RADAR DE VAGAS**.

---

## 1. Visão Geral da Árvore de Diretórios

```text
RADAR-DE-VAGAS/
├── .gitignore                      # Regras de exclusão do Git (logs, banco e planilhas)
├── README.md                       # Apresentação do projeto e instruções gerais
│
├── config/                         # Arquivos YAML de configuração e parametrização
│   ├── profile.yaml                # Perfil da candidata (skills, senioridade, formação)
│   ├── search_queries.yaml         # Cargos, localidades, modalidades e fontes
│   ├── keywords.yaml               # Palavras-chave essenciais, sinônimos e termos negativos
│   ├── scoring_rules.yaml          # Pesos e regras de cálculo do Fit Score (0 a 100)
│   ├── deduplication_rules.yaml    # Regras de normalização, chaves canônicas e banco local
│   └── scheduler.yaml              # Horários e parâmetros de agendamento automático
│
├── agents/                         # Módulos dos agentes especializados
│   ├── __init__.py                 # Exportação dos agentes
│   ├── coordinator.py              # Orquestrador do pipeline de ponta a ponta
│   ├── harvester.py                # Agente de coleta de vagas multi-fonte (scraping ético)
│   ├── scorer.py                   # Agente de cálculo de aderência e ranking
│   ├── recruiter_hunter.py         # Agente de prospecção pública de recrutadores (OSINT)
│   └── reporter.py                 # Agente de consolidação de métricas e relatórios
│
├── data/                           # Armazenamento de dados persistentes e saída tabular
│   ├── .gitkeep                    # Preserva o diretório no controle de versão
│   ├── job_vault.db                # (Gerado em execução) Banco SQLite de controle de histórico
│   └── output/                     # (Gerado em execução) Planilhas formatadas (.xlsx)
│
├── reports/                        # Relatórios executivos de cada rodada
│   ├── .gitkeep                    # Preserva o diretório no controle de versão
│   └── *.md / *.html               # (Gerados em execução) Resumos das melhores oportunidades
│
├── logs/                           # Logs operacionais do sistema
│   ├── .gitkeep                    # Preserva o diretório no controle de versão
│   └── radar.log                   # (Gerado em execução) Registro de eventos e diagnósticos
│
└── docs/                           # Documentação de engenharia e guias
    ├── ESTRUTURA_DO_PROJETO.md     # Este documento
    └── GUIA_DE_CONFIGURACAO.md     # Manual de parametrização dos arquivos YAML
```

---

## 2. Detalhamento dos Diretórios e Arquivos

### 📁 `/config`
Centraliza toda a inteligência configurável do sistema sem necessidade de alterar código-fonte:
- **`profile.yaml`**: Contém o perfil da candidata, dividindo competências técnicas em avançadas, intermediárias e básicas, além de senioridade e nichos de interesse.
- **`search_queries.yaml`**: Define os cargos procurados (segmentados por Dados/BI, Performance, Operações, Comercial e Logística), cidades prioritárias, aceitação de trabalho remoto/híbrido e fontes ativas (LinkedIn, Indeed, etc.).
- **`keywords.yaml`**: Mapeia termos essenciais com alto peso de match, sinônimos tecnológicos e filtros negativos (ex: termos que descartam vagas não pertinentes como estágios ou áreas não correlatas).
- **`scoring_rules.yaml`**: Define a pontuação máxima de cada critério (skills, área, modalidade, localidade, senioridade) e a nota de corte para acionar a busca de recrutadores.
- **`deduplication_rules.yaml`**: Estabelece os identificadores canônicos, campos de composição do hash SHA-256 e regras de limpeza de URLs de rastreamento.
- **`scheduler.yaml`**: Configura os horários automáticos diários (ex: 08:00, 12:30, 18:00), fuso horário e parâmetros para o Agendador de Tarefas do Windows.

---

### 📁 `/agents`
Implementa o padrão arquitetural multiagente, garantindo isolamento e especialização:
- **`coordinator.py` (`CoordinatorAgent`)**: O maestro do sistema. Coordena a ordem de execução dos demais agentes, gerencia erros e status do fluxo.
- **`harvester.py` (`JobHarvesterAgent`)**: Executa a coleta passiva de oportunidades em múltiplas fontes públicas com rotação de headers e sem envio de dados.
- **`scorer.py` (`FitScorerAgent`)**: Avalia o texto de cada vaga e calcula o percentual de aderência (0 a 100%) contra o perfil configurado.
- **`recruiter_hunter.py` (`RecruiterHunterAgent`)**: Localiza perfis públicos de recrutadores e gestores para as vagas que atingiram alta pontuação.
- **`reporter.py` (`ReporterAgent`)**: Produz resumos visuais no terminal e arquivos em Markdown/HTML com os destaques de cada rodada.

---

### 📁 `/data`
Responsável pelo armazenamento persistente local:
- **`job_vault.db`**: Banco SQLite para impedir reprocessamento de vagas já vistas e garantir histórico contínuo.
- **`output/`**: Diretório onde serão gravadas as planilhas finais `.xlsx` com as duas abas (*🎯 Vagas Recomendadas* e *👥 Recrutadores & Contatos*).

---

### 📁 `/reports`
Armazena os relatórios consolidados gerados ao final de cada execução do pipeline, contendo:
- Total de vagas mineradas e novas vagas descobertas.
- Top vagas com maior aderência.
- Novas empresas e recrutadores mapeados.

---

### 📁 `/logs`
Armazena os arquivos de log estruturados (`radar.log`) para auditoria, rastreamento de erros e controle de requisições.

---

### 📁 `/docs`
Contém a documentação técnica, manuais de personalização e diretrizes operacionais.
