# 🛰️ RADAR DE VAGAS

Sistema inteligente, modular e orientado a agentes para monitoramento passivo de oportunidades de emprego, cálculo de aderência de perfil (Fit Score), ranqueamento de vagas, mapeamento de recrutadores e exportação estruturada em planilha.

---

## 🎯 Objetivo
Automatizar a triagem e curadoria de vagas de forma ética e 100% passiva (sem envio automático de candidaturas ou mensagens), gerando uma lista qualificada e priorizada para sua tomada de decisão.

---

## 📁 Estrutura de Diretórios
- **`/config`**: Arquivos YAML para personalização do perfil, cargos, cidades, palavras-chave, regras de pontuação, deduplicação e agendamentos.
- **`/agents`**: Agentes modulares (Coordinator, Harvester, Scorer, Recruiter Hunter, Reporter).
- **`/data`**: Banco de histórico SQLite (`job_vault.db`) e planilhas geradas (`Radar_Vagas_Data.xlsx`).
- **`/reports`**: Relatórios analíticos de cada rodada de execução em Markdown/HTML.
- **`/logs`**: Histórico operacional e rastreabilidade do sistema.
- **`/docs`**: Documentação técnica e manuais de configuração.

---

## ⚙️ Configurações Principais
Consulte a documentação em [`docs/GUIA_DE_CONFIGURACAO.md`](file:///c:/Users/mahce/OneDrive/Desktop/RADAR-DE-VAGAS/docs/GUIA_DE_CONFIGURACAO.md) para detalhes de parametrização.

---

## 🌐 Dashboard Web Interativo (GitHub Pages)

O projeto inclui um **Dashboard Web completo de alta performance** em arquivo único (`index.html` e `docs/index.html`), pronto para deploy gratuito no **GitHub Pages**:

* **🎯 Vagas Ranqueadas em Ordem Cronológica**: Vagas ordenadas das mais recentes para as mais antigas por padrão, com Fit Score e `#Rank` dinâmico em tempo real.
* **📄 Otimizador de Currículo & ATS**: Simulador interativo de aderência com feedback ao vivo, banco de palavras-chave mais buscadas e gerador de bullet points de alto impacto por área de atuação.
* **🌐 Central Multi-Áreas & ATS Hunter**: Busca profunda em 7 verticais de carreira (Dados, Logística, Comercial, Operações, RH, Financeiro e CS) com Google Dorks avançados para Gupy, Greenhouse, Lever, Workday e Kenoby.
* **👥 OSINT Recruiter Finder**: Localizador de Talent Acquisition, Tech Recruiters e lideranças de RH por empresa diretamente no LinkedIn.
* **📱 100% Responsivo & Dark Mode**: Visual moderno, responsivo para celular e desktop, sem frameworks externos ou dependências em tempo de execução.

Para colocar o seu dashboard no ar em menos de 2 minutos, consulte o [`docs/GUIA_GITHUB_PAGES.md`](file:///c:/Users/mahce/OneDrive/Desktop/RADAR-DE-VAGAS/docs/GUIA_GITHUB_PAGES.md).

