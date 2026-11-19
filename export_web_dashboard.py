"""Gerador de Dashboard Web Standalone (GitHub Pages Ready) — Versão Expandida.

Exporta os dados consolidados da planilha Radar_Vagas_Data.xlsx
em um arquivo único HTML + CSS + JS (index.html) de alta performance,
com:
1. Ordenação cronológica (mais recentes primeiro) e atualização contínua de rank;
2. Nova aba: Otimizador de Currículo & Compatibilidade ATS (simulador, gaps, bullet points);
3. Nova aba: Busca Multi-Áreas & ATS Hunter (Gupy, Greenhouse, Lever, Workday, Kenoby, LinkedIn, Indeed);
4. Diretório de Recrutadores & Talent Acquisition;
5. Métricas e Inteligência de Mercado.
"""

import sys
import os
import json
import re
from datetime import datetime
import openpyxl

def clean_val(v):
    if v is None:
        return ""
    return str(v).strip()

def export_dashboard(excel_path="data/output/Radar_Vagas_Data.xlsx", output_html="index.html"):
    print(f"📖 Carregando planilha: {excel_path}")
    if not os.path.exists(excel_path):
        print(f"❌ Arquivo não encontrado: {excel_path}")
        return False

    wb = openpyxl.load_workbook(excel_path, data_only=True)
    
    # ── 1. Extrair Vagas ───────────────────────────────────────────────────────
    ws_vagas = wb["🎯 Vagas Recomendadas"]
    headers_vagas = [clean_val(c.value) for c in ws_vagas[1]]
    col_v = {name: idx for idx, name in enumerate(headers_vagas) if name}

    raw_jobs = []
    for r_idx in range(2, ws_vagas.max_row + 1):
        row = ws_vagas[r_idx]
        cargo = clean_val(row[col_v.get("Cargo", 3)].value)
        if not cargo:
            continue
        
        link_cell = row[col_v.get("Link da Vaga", 13)]
        url = link_cell.hyperlink.target if link_cell.hyperlink else clean_val(link_cell.value)
        
        raw_score = clean_val(row[col_v.get("Score (%)", 1)].value).replace("%", "")
        try:
            score_num = float(raw_score)
        except ValueError:
            score_num = 0.0

        data_busca = clean_val(row[col_v.get("Data da Busca", 9)].value)
        data_pub = clean_val(row[col_v.get("Data Publicação", 8)].value)
        
        raw_jobs.append({
            "original_rank": clean_val(row[col_v.get("Rank", 0)].value),
            "score": score_num,
            "prioridade": clean_val(row[col_v.get("Prioridade", 2)].value),
            "cargo": cargo,
            "empresa": clean_val(row[col_v.get("Empresa", 4)].value),
            "modalidade": clean_val(row[col_v.get("Modalidade", 5)].value) or "Presencial",
            "localizacao": clean_val(row[col_v.get("Localização", 6)].value),
            "salario": clean_val(row[col_v.get("Salário", 7)].value),
            "data_pub": data_pub,
            "data_busca": data_busca,
            "skills_match": clean_val(row[col_v.get("Skills Encontradas", 10)].value),
            "skills_gap": clean_val(row[col_v.get("Oportunidades Desenvolvimento", 11)].value),
            "fonte": clean_val(row[col_v.get("Fonte", 12)].value),
            "url": url,
            "status": clean_val(row[col_v.get("Status Candidatura", 14)].value) or "Não iniciada",
            "data_tentativa": clean_val(row[col_v.get("Data da Tentativa", 15)].value),
            "etapa": clean_val(row[col_v.get("Etapa Alcançada", 16)].value),
            "pendencias": clean_val(row[col_v.get("Campos Pendentes", 17)].value),
            "proxima_acao": clean_val(row[col_v.get("Próxima Ação", 18)].value),
        })

    # ── 1.1 Ordenação Cronológica (Mais Recentes Primeiro) e Re-Rankeamento ────
    # Ordena por Data da Busca / Data Publicação decrescente; desempatando por maior score
    raw_jobs.sort(
        key=lambda j: (j.get("data_busca") or j.get("data_pub") or "", j.get("score") or 0.0),
        reverse=True
    )
    for idx, j in enumerate(raw_jobs, 1):
        j["rank"] = idx

    jobs = raw_jobs

    # ── 2. Extrair Recrutadores ────────────────────────────────────────────────
    recruiters = []
    if "👥 Recrutadores" in wb.sheetnames:
        ws_rec = wb["👥 Recrutadores"]
        headers_rec = [clean_val(c.value) for c in ws_rec[1]]
        col_r = {name: idx for idx, name in enumerate(headers_rec) if name}
        for r_idx in range(2, ws_rec.max_row + 1):
            row = ws_rec[r_idx]
            empresa = clean_val(row[col_r.get("Empresa", 0)].value)
            if not empresa:
                continue
            
            link_cell = row[col_r.get("Link do Perfil LinkedIn", 8) if "Link do Perfil LinkedIn" in col_r else 6]
            url = link_cell.hyperlink.target if link_cell.hyperlink else clean_val(link_cell.value)
            
            recruiters.append({
                "empresa": empresa,
                "vaga_relacionada": clean_val(row[col_r.get("Vaga Relacionada", 1)].value),
                "nome": clean_val(row[col_r.get("Nome do Contato", 2)].value),
                "cargo": clean_val(row[col_r.get("Cargo / Título", 3)].value),
                "localidade": clean_val(row[col_r.get("Localidade", 4)].value),
                "tipo": clean_val(row[col_r.get("Tipo de Contato", 5)].value),
                "mapeado_em": clean_val(row[col_r.get("Mapeado Em", 6) if "Mapeado Em" in col_r else 7].value),
                "prioridade": clean_val(row[col_r.get("Prioridade", 7) if "Prioridade" in col_r else 8].value) or "Média",
                "url": url,
            })

    wb.close()
    print(f"📊 Processadas: {len(jobs)} vagas e {len(recruiters)} recrutadores.")

    # ── 3. Métricas Resumidas ──────────────────────────────────────────────────
    total_jobs = len(jobs)
    total_remotas = sum(1 for j in jobs if "remot" in j["modalidade"].lower())
    total_hibridas = sum(1 for j in jobs if "híb" in j["modalidade"].lower() or "hib" in j["modalidade"].lower())
    total_presenciais = total_jobs - total_remotas - total_hibridas
    total_score_80 = sum(1 for j in jobs if j["score"] >= 80.0)
    total_score_65 = sum(1 for j in jobs if j["score"] >= 65.0)
    total_enviadas = sum(1 for j in jobs if j["status"] == "Enviada")
    total_revisao = sum(1 for j in jobs if j["status"] == "Aguardando minha revisão")
    top_score_job = max(jobs, key=lambda x: x["score"]) if jobs else None

    # Top skills demandadas (contagem)
    skill_counts = {}
    for j in jobs:
        for s in j["skills_match"].split(","):
            s_clean = s.strip()
            if s_clean and len(s_clean) > 1 and s_clean != "-":
                skill_counts[s_clean] = skill_counts.get(s_clean, 0) + 1
    top_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:15]

    stats = {
        "total_jobs": total_jobs,
        "total_remotas": total_remotas,
        "total_hibridas": total_hibridas,
        "total_presenciais": total_presenciais,
        "total_score_80": total_score_80,
        "total_score_65": total_score_65,
        "total_enviadas": total_enviadas,
        "total_revisao": total_revisao,
        "total_recrutadores": len(recruiters),
        "top_job": {
            "cargo": top_score_job["cargo"] if top_score_job else "",
            "empresa": top_score_job["empresa"] if top_score_job else "",
            "score": top_score_job["score"] if top_score_job else 0,
            "modalidade": top_score_job["modalidade"] if top_score_job else "",
        } if top_score_job else None,
        "top_skills": top_skills,
        "updated_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
    }

    # ── 4. Gerar HTML Standalone ──────────────────────────────────────────────
    html_content = generate_html_template(jobs, recruiters, stats)
    
    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    os.makedirs("docs", exist_ok=True)
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"✨ Dashboard gerado com sucesso!")
    print(f"   📁 Arquivo 1 (Raiz): {output_html}")
    print(f"   📁 Arquivo 2 (Docs): docs/index.html (Pronto para GitHub Pages)")
    return True


def generate_html_template(jobs, recruiters, stats):
    total_jobs = stats['total_jobs'] or len(jobs) or 1
    data_json = json.dumps({"jobs": jobs, "recruiters": recruiters, "stats": stats}, ensure_ascii=False)
    
    return f"""<!DOCTYPE html>
<html lang="pt-BR" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Radar de Vagas | Automação Inteligente de Oportunidades & Recrutadores</title>
  <meta name="description" content="Dashboard interativo do Radar de Vagas - Monitoramento autônomo multi-área, cálculo de Fit Score com IA, otimizador de currículo para ATS e mapeamento de contatos-chave de RH.">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
  
  <style>
    /* ─── RESET & DESIGN TOKENS ─── */
    :root {{
      --bg-main: #090d16;
      --bg-surface: #0f172a;
      --bg-surface-elevated: #1e293b;
      --bg-surface-hover: #273549;
      --border-subtle: #1e293b;
      --border-strong: #334155;
      
      --text-primary: #f8fafc;
      --text-secondary: #94a3b8;
      --text-muted: #64748b;
      
      --primary: #3b82f6;
      --primary-hover: #2563eb;
      --primary-glow: rgba(59, 130, 246, 0.25);
      
      --accent-green: #10b981;
      --accent-green-bg: rgba(16, 185, 129, 0.12);
      --accent-green-border: rgba(16, 185, 129, 0.3);
      
      --accent-amber: #f59e0b;
      --accent-amber-bg: rgba(245, 158, 11, 0.12);
      --accent-amber-border: rgba(245, 158, 11, 0.3);

      --accent-blue: #0ea5e9;
      --accent-purple: #8b5cf6;
      --accent-pink: #ec4899;
      
      --radius-sm: 8px;
      --radius-md: 12px;
      --radius-lg: 18px;
      --radius-full: 9999px;
      
      --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.3);
      --shadow-md: 0 8px 24px rgba(0, 0, 0, 0.4);
      --shadow-glow: 0 0 25px rgba(59, 130, 246, 0.15);
      
      --transition-fast: 0.18s cubic-bezier(0.4, 0, 0.2, 1);
      --transition-smooth: 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }}

    * {{
      margin: 0;
      padding: 0;
      box-sizing: border-box;
      -webkit-font-smoothing: antialiased;
    }}

    body {{
      font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
      background: radial-gradient(circle at 50% -10%, #1e1b4b 0%, var(--bg-main) 45%);
      color: var(--text-primary);
      min-height: 100vh;
      line-height: 1.5;
      overflow-x: hidden;
    }}

    a {{
      color: inherit;
      text-decoration: none;
    }}

    .container {{
      max-width: 1400px;
      margin: 0 auto;
      padding: 0 24px;
    }}

    /* ─── HEADER / NAVBAR ─── */
    header.site-header {{
      border-bottom: 1px solid var(--border-subtle);
      background: rgba(15, 23, 42, 0.82);
      backdrop-filter: blur(16px);
      position: sticky;
      top: 0;
      z-index: 50;
    }}

    .header-inner {{
      height: 72px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }}

    .logo-group {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}

    .logo-icon {{
      width: 42px;
      height: 42px;
      background: linear-gradient(135deg, #3b82f6, #8b5cf6);
      border-radius: var(--radius-md);
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 0 16px rgba(139, 92, 246, 0.4);
      font-size: 22px;
    }}

    .logo-text h1 {{
      font-size: 1.15rem;
      font-weight: 800;
      letter-spacing: -0.02em;
      background: linear-gradient(to right, #ffffff, #94a3b8);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }}

    .logo-text p {{
      font-size: 0.75rem;
      color: var(--accent-green);
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 6px;
    }}

    .pulse-dot {{
      width: 7px;
      height: 7px;
      background-color: var(--accent-green);
      border-radius: 50%;
      box-shadow: 0 0 8px var(--accent-green);
      animation: pulse 2s infinite;
    }}

    @keyframes pulse {{
      0%, 100% {{ opacity: 1; transform: scale(1); }}
      50% {{ opacity: 0.4; transform: scale(0.85); }}
    }}

    .header-actions {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}

    .btn {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      padding: 9px 16px;
      border-radius: var(--radius-sm);
      font-size: 0.85rem;
      font-weight: 600;
      cursor: pointer;
      transition: all var(--transition-fast);
      border: 1px solid transparent;
      outline: none;
    }}

    .btn-primary {{
      background: linear-gradient(135deg, var(--primary), #2563eb);
      color: #fff;
      box-shadow: 0 4px 12px var(--primary-glow);
    }}

    .btn-primary:hover {{
      transform: translateY(-1px);
      box-shadow: 0 6px 16px rgba(59, 130, 246, 0.4);
    }}

    .btn-secondary {{
      background: var(--bg-surface-elevated);
      color: var(--text-primary);
      border-color: var(--border-strong);
    }}

    .btn-secondary:hover {{
      background: var(--bg-surface-hover);
      border-color: var(--primary);
    }}

    /* ─── HERO SECTION ─── */
    .hero {{
      padding: 44px 0 28px;
      text-align: center;
    }}

    .badge-pill {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 14px;
      background: rgba(59, 130, 246, 0.1);
      border: 1px solid rgba(59, 130, 246, 0.25);
      border-radius: var(--radius-full);
      font-size: 0.8rem;
      font-weight: 600;
      color: #93c5fd;
      margin-bottom: 20px;
    }}

    .hero-title {{
      font-size: 2.6rem;
      font-weight: 800;
      letter-spacing: -0.03em;
      line-height: 1.15;
      margin-bottom: 14px;
      max-width: 960px;
      margin-left: auto;
      margin-right: auto;
    }}

    .hero-title span {{
      background: linear-gradient(135deg, #60a5fa 20%, #c084fc 80%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }}

    .hero-subtitle {{
      color: var(--text-secondary);
      font-size: 1.02rem;
      max-width: 720px;
      margin: 0 auto 34px;
      line-height: 1.6;
    }}

    /* ─── METRIC CARDS ─── */
    .metrics-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 16px;
      margin-bottom: 36px;
    }}

    .metric-card {{
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      padding: 20px;
      transition: all var(--transition-smooth);
      position: relative;
      overflow: hidden;
    }}

    .metric-card:hover {{
      transform: translateY(-2px);
      border-color: var(--border-strong);
      box-shadow: var(--shadow-md);
    }}

    .metric-card::before {{
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 3px;
      background: linear-gradient(90deg, var(--primary), var(--accent-purple));
      opacity: 0.8;
    }}

    .metric-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      color: var(--text-muted);
      font-size: 0.78rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      margin-bottom: 8px;
    }}

    .metric-val {{
      font-size: 1.85rem;
      font-weight: 800;
      letter-spacing: -0.02em;
      color: var(--text-primary);
    }}

    .metric-sub {{
      font-size: 0.78rem;
      color: var(--text-secondary);
      margin-top: 4px;
    }}

    /* ─── TABS & CONTROLS ─── */
    .nav-tabs {{
      display: flex;
      align-items: center;
      gap: 8px;
      border-bottom: 1px solid var(--border-subtle);
      margin-bottom: 24px;
      overflow-x: auto;
      padding-bottom: 4px;
    }}

    .tab-btn {{
      padding: 10px 18px;
      background: transparent;
      border: none;
      color: var(--text-secondary);
      font-size: 0.9rem;
      font-weight: 600;
      cursor: pointer;
      position: relative;
      border-radius: var(--radius-sm);
      transition: all var(--transition-fast);
      white-space: nowrap;
    }}

    .tab-btn:hover {{
      color: var(--text-primary);
      background: var(--bg-surface-elevated);
    }}

    .tab-btn.active {{
      color: #fff;
      background: var(--bg-surface-elevated);
    }}

    .tab-btn.active::after {{
      content: '';
      position: absolute;
      bottom: -5px;
      left: 12px;
      right: 12px;
      height: 2px;
      background: var(--primary);
      border-radius: 2px;
    }}

    /* ─── SEARCH & FILTERS BAR ─── */
    .filter-panel {{
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      padding: 18px;
      margin-bottom: 24px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }}

    .search-row {{
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
    }}

    .search-input-wrapper {{
      flex: 1;
      min-width: 260px;
      position: relative;
    }}

    .search-icon {{
      position: absolute;
      left: 14px;
      top: 50%;
      transform: translateY(-50%);
      color: var(--text-muted);
      pointer-events: none;
    }}

    .search-input {{
      width: 100%;
      padding: 12px 14px 12px 42px;
      background: var(--bg-main);
      border: 1px solid var(--border-strong);
      border-radius: var(--radius-sm);
      color: var(--text-primary);
      font-size: 0.9rem;
      outline: none;
      transition: all var(--transition-fast);
    }}

    .search-input:focus {{
      border-color: var(--primary);
      box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
    }}

    .select-dropdown {{
      padding: 12px 16px;
      background: var(--bg-main);
      border: 1px solid var(--border-strong);
      border-radius: var(--radius-sm);
      color: var(--text-primary);
      font-size: 0.88rem;
      outline: none;
      cursor: pointer;
      min-width: 160px;
    }}

    .select-dropdown:focus {{
      border-color: var(--primary);
    }}

    .pills-row {{
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }}

    .pill-filter {{
      padding: 5px 12px;
      border-radius: var(--radius-full);
      background: var(--bg-surface-elevated);
      border: 1px solid var(--border-subtle);
      color: var(--text-secondary);
      font-size: 0.78rem;
      font-weight: 600;
      cursor: pointer;
      transition: all var(--transition-fast);
      user-select: none;
    }}

    .pill-filter:hover {{
      background: var(--bg-surface-hover);
      color: var(--text-primary);
    }}

    .pill-filter.active {{
      background: var(--primary);
      border-color: var(--primary);
      color: #fff;
    }}

    .results-count {{
      font-size: 0.85rem;
      color: var(--text-muted);
      margin-left: auto;
    }}

    /* ─── DATA TABLE ─── */
    .table-container {{
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      overflow-x: auto;
      margin-bottom: 24px;
      box-shadow: var(--shadow-sm);
    }}

    table.data-table {{
      width: 100%;
      border-collapse: collapse;
      text-align: left;
      font-size: 0.88rem;
    }}

    table.data-table th {{
      padding: 14px 16px;
      background: #111827;
      color: var(--text-secondary);
      font-weight: 700;
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      border-bottom: 1px solid var(--border-strong);
      white-space: nowrap;
    }}

    table.data-table td {{
      padding: 14px 16px;
      border-bottom: 1px solid var(--border-subtle);
      vertical-align: middle;
      color: var(--text-secondary);
    }}

    table.data-table tr:hover td {{
      background: var(--bg-surface-elevated);
      color: var(--text-primary);
    }}

    .job-title-col {{
      font-weight: 700;
      color: var(--text-primary);
      max-width: 320px;
      display: block;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}

    .company-col {{
      color: #cbd5e1;
      font-weight: 500;
    }}

    .date-col {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.78rem;
      color: var(--text-muted);
      white-space: nowrap;
    }}

    .score-badge {{
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 4px 10px;
      border-radius: var(--radius-full);
      font-weight: 700;
      font-size: 0.8rem;
      font-family: 'JetBrains Mono', monospace;
    }}

    .score-80 {{
      background: rgba(16, 185, 129, 0.15);
      border: 1px solid rgba(16, 185, 129, 0.4);
      color: #34d399;
    }}

    .score-65 {{
      background: rgba(245, 158, 11, 0.15);
      border: 1px solid rgba(245, 158, 11, 0.4);
      color: #fbbf24;
    }}

    .score-low {{
      background: rgba(148, 163, 184, 0.1);
      border: 1px solid rgba(148, 163, 184, 0.2);
      color: #94a3b8;
    }}

    .tag-pill {{
      display: inline-block;
      padding: 3px 8px;
      background: var(--bg-main);
      border: 1px solid var(--border-strong);
      border-radius: 4px;
      font-size: 0.72rem;
      font-weight: 500;
      color: #cbd5e1;
    }}

    .status-badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 4px 10px;
      border-radius: var(--radius-full);
      font-size: 0.75rem;
      font-weight: 600;
    }}

    .status-enviada {{
      background: rgba(16, 185, 129, 0.15);
      color: #34d399;
      border: 1px solid rgba(16, 185, 129, 0.3);
    }}

    .status-revisao {{
      background: rgba(245, 158, 11, 0.15);
      color: #fbbf24;
      border: 1px solid rgba(245, 158, 11, 0.3);
    }}

    .status-manual {{
      background: rgba(59, 130, 246, 0.12);
      color: #93c5fd;
      border: 1px solid rgba(59, 130, 246, 0.25);
    }}

    .action-btn {{
      padding: 6px 12px;
      border-radius: var(--radius-sm);
      font-size: 0.78rem;
      font-weight: 600;
      background: var(--bg-surface-hover);
      border: 1px solid var(--border-strong);
      color: #fff;
      display: inline-flex;
      align-items: center;
      gap: 4px;
      transition: all var(--transition-fast);
    }}

    .action-btn:hover {{
      background: var(--primary);
      border-color: var(--primary);
    }}

    /* ─── PAGINATION ─── */
    .pagination-bar {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 12px 4px;
      flex-wrap: wrap;
    }}

    .page-info {{
      font-size: 0.85rem;
      color: var(--text-muted);
    }}

    .page-controls {{
      display: flex;
      align-items: center;
      gap: 6px;
    }}

    .page-btn {{
      padding: 6px 12px;
      background: var(--bg-surface);
      border: 1px solid var(--border-strong);
      color: var(--text-secondary);
      border-radius: var(--radius-sm);
      font-size: 0.85rem;
      cursor: pointer;
      font-weight: 600;
      transition: all var(--transition-fast);
    }}

    .page-btn:hover:not(:disabled) {{
      background: var(--bg-surface-hover);
      color: #fff;
    }}

    .page-btn.active {{
      background: var(--primary);
      border-color: var(--primary);
      color: #fff;
    }}

    .page-btn:disabled {{
      opacity: 0.35;
      cursor: not-allowed;
    }}

    /* ─── RECRUITERS GRID ─── */
    .recruiters-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 18px;
      margin-bottom: 32px;
    }}

    .recruiter-card {{
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      padding: 20px;
      transition: all var(--transition-smooth);
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 14px;
    }}

    .recruiter-card:hover {{
      transform: translateY(-2px);
      border-color: var(--border-strong);
      box-shadow: var(--shadow-md);
    }}

    .rec-company {{
      font-size: 1.05rem;
      font-weight: 700;
      color: var(--text-primary);
    }}

    .rec-role {{
      font-size: 0.85rem;
      color: var(--text-secondary);
      margin-top: 2px;
    }}

    .rec-job-rel {{
      font-size: 0.78rem;
      color: var(--text-muted);
      background: var(--bg-main);
      padding: 8px 10px;
      border-radius: 6px;
      border: 1px solid var(--border-subtle);
      margin: 8px 0;
    }}

    /* ─── CURRICULO & ATS TAB ─── */
    .resume-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;
      margin-bottom: 36px;
    }}

    .resume-card {{
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      padding: 24px;
    }}

    .skill-sim-box {{
      background: var(--bg-main);
      border: 1px solid var(--border-strong);
      border-radius: var(--radius-sm);
      padding: 16px;
      margin-top: 14px;
    }}

    .skill-checkbox-label {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      margin: 4px;
      padding: 6px 12px;
      background: var(--bg-surface-elevated);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-full);
      font-size: 0.8rem;
      cursor: pointer;
      user-select: none;
      transition: all var(--transition-fast);
    }}

    .skill-checkbox-label input {{
      accent-color: var(--primary);
    }}

    .skill-checkbox-label:hover {{
      border-color: var(--primary);
    }}

    .bullet-box {{
      background: var(--bg-main);
      border: 1px solid var(--border-subtle);
      border-left: 3px solid var(--primary);
      border-radius: 6px;
      padding: 12px 14px;
      margin-bottom: 12px;
      font-size: 0.86rem;
      color: var(--text-secondary);
      position: relative;
    }}

    .copy-btn {{
      position: absolute;
      top: 10px;
      right: 10px;
      padding: 4px 8px;
      background: var(--bg-surface-elevated);
      border: 1px solid var(--border-strong);
      border-radius: 4px;
      font-size: 0.72rem;
      color: var(--text-primary);
      cursor: pointer;
    }}

    .copy-btn:hover {{
      background: var(--primary);
    }}

    /* ─── ATS HUNTER TAB ─── */
    .ats-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 16px;
      margin-top: 16px;
    }}

    .ats-card {{
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      padding: 20px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 12px;
    }}

    .ats-card h4 {{
      font-size: 1rem;
      font-weight: 700;
      color: var(--text-primary);
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    .ats-card p {{
      font-size: 0.82rem;
      color: var(--text-muted);
      line-height: 1.5;
    }}

    /* ─── ARCHITECTURE TAB ─── */
    .arch-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 20px;
      margin-bottom: 40px;
    }}

    .arch-card {{
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      padding: 24px;
    }}

    .arch-card h3 {{
      font-size: 1.1rem;
      font-weight: 700;
      margin-bottom: 12px;
      color: var(--primary);
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    .arch-card p {{
      color: var(--text-secondary);
      font-size: 0.9rem;
      line-height: 1.6;
    }}

    /* ─── MODAL ─── */
    .modal-backdrop {{
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.7);
      backdrop-filter: blur(8px);
      display: none;
      align-items: center;
      justify-content: center;
      z-index: 100;
      padding: 20px;
    }}

    .modal-backdrop.open {{
      display: flex;
    }}

    .modal-box {{
      background: var(--bg-surface);
      border: 1px solid var(--border-strong);
      border-radius: var(--radius-lg);
      max-width: 650px;
      width: 100%;
      padding: 28px;
      box-shadow: var(--shadow-md);
      max-height: 90vh;
      overflow-y: auto;
      position: relative;
    }}

    .modal-close {{
      position: absolute;
      top: 20px;
      right: 20px;
      background: var(--bg-surface-elevated);
      border: none;
      color: var(--text-muted);
      width: 32px;
      height: 32px;
      border-radius: 50%;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 18px;
      transition: all var(--transition-fast);
    }}

    .modal-close:hover {{
      background: var(--bg-surface-hover);
      color: var(--text-primary);
    }}

    /* ─── FOOTER ─── */
    footer.site-footer {{
      border-top: 1px solid var(--border-subtle);
      padding: 36px 0;
      color: var(--text-muted);
      font-size: 0.85rem;
      text-align: center;
    }}

    @media (max-width: 900px) {{
      .resume-grid {{ grid-template-columns: 1fr; }}
    }}

    @media (max-width: 768px) {{
      .hero-title {{ font-size: 2rem; }}
      .header-actions .btn-secondary {{ display: none; }}
      .metrics-grid {{ grid-template-columns: repeat(2, 1fr); }}
    }}
  </style>
</head>
<body>

  <!-- HEADER -->
  <header class="site-header">
    <div class="container">
      <div class="header-inner">
        <div class="logo-group">
          <div class="logo-icon">🛰️</div>
          <div class="logo-text">
            <h1>Radar de Vagas</h1>
            <p><span class="pulse-dot"></span> Automação Ativa • Atualizado</p>
          </div>
        </div>
        <div class="header-actions">
          <a href="https://github.com" target="_blank" class="btn btn-secondary">
            <svg width="16" height="16" fill="currentColor" viewBox="0 0 24 24"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/></svg>
            Repositório
          </a>
          <button onclick="downloadJSON()" class="btn btn-primary">
            <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
            Exportar Dados
          </button>
        </div>
      </div>
    </div>
  </header>

  <!-- HERO -->
  <section class="hero">
    <div class="container">
      <div class="badge-pill">
        <span>⚡ Automação Inteligente de Carreira</span>
        <span>•</span>
        <span>Ordenação Cronológica Ativa</span>
        <span>•</span>
        <span>Atualizado: {stats['updated_at']}</span>
      </div>
      <h2 class="hero-title">
        Monitoramento Contínuo & <br><span>Curadoria Inteligente de Vagas</span>
      </h2>
      <p class="hero-subtitle">
        Pipeline autônomo que captura dados em tempo real no LinkedIn, Indeed, Glassdoor e Gupy, aplicando cálculo algorítmico de aderência de perfil, mapeando recrutadores-chave e otimizando currículos para ATS.
      </p>

      <!-- KPI METRIC CARDS -->
      <div class="metrics-grid">
        <div class="metric-card">
          <div class="metric-header">Total de Oportunidades <span>💼</span></div>
          <div class="metric-val" id="metric-total">{stats['total_jobs']}</div>
          <div class="metric-sub">100% categorizadas e auditadas</div>
        </div>
        <div class="metric-card">
          <div class="metric-header">Vagas Remotas <span>🌐</span></div>
          <div class="metric-val">{stats['total_remotas']}</div>
          <div class="metric-sub">{stats['total_hibridas']} Híbridas adicionais</div>
        </div>
        <div class="metric-card">
          <div class="metric-header">Maior Fit Score <span>⭐</span></div>
          <div class="metric-val" style="color: #34d399;">{stats['top_job']['score'] if stats['top_job'] else 0}%</div>
          <div class="metric-sub">{stats['top_job']['empresa'] if stats['top_job'] else '-'}</div>
        </div>
        <div class="metric-card">
          <div class="metric-header">Recrutadores Mapeados <span>👥</span></div>
          <div class="metric-val" style="color: #c084fc;">{stats['total_recrutadores']}</div>
          <div class="metric-sub">Empresas com RHs indexados</div>
        </div>
        <div class="metric-card">
          <div class="metric-header">Em Acompanhamento <span>📋</span></div>
          <div class="metric-val" style="color: #60a5fa;">{stats['total_revisao'] + stats['total_enviadas']}</div>
          <div class="metric-sub">{stats['total_enviadas']} candidatura enviada</div>
        </div>
      </div>
    </div>
  </section>

  <!-- MAIN DASHBOARD CONTENT -->
  <main class="container">
    
    <!-- NAVIGATION TABS -->
    <div class="nav-tabs">
      <button class="tab-btn active" onclick="switchTab('jobs')">🎯 Oportunidades Recomendadas (<span id="tab-jobs-count">{len(jobs)}</span>)</button>
      <button class="tab-btn" onclick="switchTab('resume')">📄 Otimizador de Currículo & ATS</button>
      <button class="tab-btn" onclick="switchTab('multiarea')">🌐 Busca Multi-Áreas & ATS Hunter</button>
      <button class="tab-btn" onclick="switchTab('recruiters')">👥 Recrutadores & Talent Acquisition ({len(recruiters)})</button>
      <button class="tab-btn" onclick="switchTab('analytics')">📊 Inteligência de Mercado</button>
      <button class="tab-btn" onclick="switchTab('architecture')">⚙️ Arquitetura do Sistema</button>
    </div>

    <!-- TAB 1: JOBS TABLE (COM ORDENAÇÃO CRONOLÓGICA) -->
    <div id="tab-jobs">
      <!-- FILTERS -->
      <div class="filter-panel">
        <div class="search-row">
          <div class="search-input-wrapper">
            <svg class="search-icon" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
            <input type="text" id="searchInput" class="search-input" placeholder="Buscar por cargo, empresa, tecnologia ou palavra-chave..." oninput="handleFilterChange()">
          </div>
          
          <!-- ORDENAÇÃO (CRONOLÓGICA PADRÃO) -->
          <select id="sortSelect" class="select-dropdown" onchange="handleFilterChange()">
            <option value="date_desc">🕒 Mais Recentes Primeiro (Cronológica)</option>
            <option value="score_desc">⭐ Maior Fit Score Primeiro</option>
            <option value="score_asc">📉 Menor Fit Score</option>
            <option value="company_asc">🔤 Empresa (A-Z)</option>
          </select>

          <select id="modalidadeSelect" class="select-dropdown" onchange="handleFilterChange()">
            <option value="">Todas as Modalidades</option>
            <option value="Remoto">Apenas Remotas</option>
            <option value="Híbrido">Apenas Híbridas</option>
            <option value="Presencial">Presencial</option>
          </select>
          <select id="scoreSelect" class="select-dropdown" onchange="handleFilterChange()">
            <option value="0">Qualquer Fit Score</option>
            <option value="80">⭐ Excelente (&ge; 80%)</option>
            <option value="70">🟢 Alta Aderência (&ge; 70%)</option>
            <option value="65">🟡 Média Aderência (&ge; 65%)</option>
          </select>
          <select id="statusSelect" class="select-dropdown" onchange="handleFilterChange()">
            <option value="">Todos os Status</option>
            <option value="Enviada">Candidatura Enviada</option>
            <option value="Aguardando minha revisão">Aguardando Revisão</option>
            <option value="Bloqueada ou exige ação manual">Exige Ação Manual</option>
          </select>
        </div>

        <div class="pills-row">
          <span style="font-size: 0.8rem; color: var(--text-muted); font-weight: 600;">Filtros rápidos:</span>
          <button class="pill-filter active" onclick="setQuickPill('', this)">Todas ({len(jobs)})</button>
          <button class="pill-filter" onclick="setQuickPill('recent', this)">Última Semana</button>
          <button class="pill-filter" onclick="setQuickPill('remoto', this)">Remoto ({stats['total_remotas']})</button>
          <button class="pill-filter" onclick="setQuickPill('high-score', this)">Score &ge; 65% ({stats['total_score_65']})</button>
          <button class="pill-filter" onclick="setQuickPill('revisao', this)">Gupy / Revisão ({stats['total_revisao']})</button>
          <button class="pill-filter" onclick="setQuickPill('enviada', this)">Enviadas ({stats['total_enviadas']})</button>
          <span class="results-count" id="filtered-count">Exibindo {len(jobs)} vagas</span>
        </div>
      </div>

      <!-- TABLE -->
      <div class="table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th>Rank</th>
              <th>Data</th>
              <th>Score</th>
              <th>Cargo & Empresa</th>
              <th>Modalidade</th>
              <th>Localização</th>
              <th>Skills Identificadas</th>
              <th>Status</th>
              <th style="text-align: right;">Ação</th>
            </tr>
          </thead>
          <tbody id="jobsTableBody">
            <!-- Dynamic rows injected by JS -->
          </tbody>
        </table>
      </div>

      <!-- PAGINATION -->
      <div class="pagination-bar">
        <div class="page-info" id="paginationInfo">Mostrando 1-20 de {len(jobs)} vagas</div>
        <div class="page-controls" id="paginationControls">
          <!-- Injected by JS -->
        </div>
      </div>
    </div>

    <!-- TAB 2: OTIMIZADOR DE CURRÍCULO PARA ATS (NOVA ABA) -->
    <div id="tab-resume" style="display: none;">
      <div class="resume-grid">
        <!-- DIAGNÓSTICO E SIMULADOR DE FIT SCORE -->
        <div class="resume-card">
          <h3 style="font-size: 1.15rem; font-weight: 700; color: #60a5fa; margin-bottom: 12px; display: flex; align-items: center; gap: 8px;">
            <span>🧠</span> Simulador de Compatibilidade & ATS
          </h3>
          <p style="font-size: 0.88rem; color: var(--text-secondary); line-height: 1.6; margin-bottom: 16px;">
            Os robôs de triagem (Gupy, Greenhouse, Workday) eliminam currículos sem palavras-chave idênticas ao anúncio. Marque as habilidades presentes no seu currículo para calcular sua aderência estimada:
          </p>

          <div style="background: var(--bg-main); padding: 14px; border-radius: var(--radius-sm); border: 1px solid var(--border-strong); margin-bottom: 16px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
              <span style="font-size: 0.85rem; font-weight: 700; color: var(--text-primary);">Aderência Estimada no Radar:</span>
              <span id="simulatedScoreText" style="font-size: 1.4rem; font-weight: 800; color: #34d399; font-family: monospace;">68.5%</span>
            </div>
            <div style="height: 10px; background: #1e293b; border-radius: 6px; overflow: hidden;">
              <div id="simulatedProgressBar" style="width: 68.5%; height: 100%; background: linear-gradient(90deg, #3b82f6, #10b981); transition: width 0.3s ease;"></div>
            </div>
            <p id="simulatedFeedback" style="font-size: 0.78rem; color: var(--accent-amber); margin-top: 8px;">
              💡 <em>Adicione mais 2 competências técnicas chave para ultrapassar 80% de aderência média.</em>
            </p>
          </div>

          <div style="font-size: 0.82rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; margin-bottom: 10px;">
            Marque as ferramentas e skills presentes no seu currículo:
          </div>

          <div style="display: flex; flex-wrap: wrap; gap: 4px;" id="skillsCheckboxes">
            <!-- Injected by JS -->
          </div>
        </div>

        <!-- GERADOR DE BULLET POINTS DE ALTO IMPACTO -->
        <div class="resume-card">
          <h3 style="font-size: 1.15rem; font-weight: 700; color: #c084fc; margin-bottom: 12px; display: flex; align-items: center; gap: 8px;">
            <span>✨</span> Bullet Points de Alta Conversão (ATS Ready)
          </h3>
          <p style="font-size: 0.88rem; color: var(--text-secondary); line-height: 1.6; margin-bottom: 14px;">
            Modelos de redação validados para passar nos filtros automáticos usando a fórmula <strong>Ação + Ferramenta + Impacto Mensurável</strong>:
          </p>

          <div style="margin-bottom: 16px;">
            <select id="resumeAreaSelect" class="select-dropdown" style="width: 100%;" onchange="renderBulletPoints()">
              <option value="dados">Área: Análise de Dados, BI & Métricas</option>
              <option value="operacoes">Área: Operações, Processos & Backoffice</option>
              <option value="comercial">Área: Comercial, Sales Ops & Atendimento</option>
              <option value="logistica">Área: Logística, PCP & Supply Chain</option>
              <option value="rh">Área: Recursos Humanos & Recrutamento (R&S)</option>
            </select>
          </div>

          <div id="bulletPointsContainer">
            <!-- Injected by JS -->
          </div>
        </div>
      </div>

      <!-- CHECKLIST DE FORMATAÇÃO ATS -->
      <div class="arch-card" style="margin-bottom: 32px;">
        <h3 style="color: var(--accent-green);">📋 Checklist Anti-Eliminação nos Robôs de RH (Gupy / Kenoby / Workday)</h3>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; margin-top: 14px;">
          <div style="background: var(--bg-main); padding: 14px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle); font-size: 0.85rem; color: var(--text-secondary); line-height: 1.6;">
            <strong style="color: var(--text-primary);">1. Layout em Coluna Única:</strong><br>
            Evite colunas duplas, caixas de texto flutuantes e tabelas. Os parsers da Gupy e Kenoby leem da esquerda para a direita de forma linear.
          </div>
          <div style="background: var(--bg-main); padding: 14px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle); font-size: 0.85rem; color: var(--text-secondary); line-height: 1.6;">
            <strong style="color: var(--text-primary);">2. Seção de Competências Textuais:</strong><br>
            Nunca coloque barras de nível ou gráficos de bolinhas (ex: "Excel 80%"). Escreva por extenso: <em>"Ferramentas: Excel Avançado (PROCV, Tabela Dinâmica), Power BI (DAX, Power Query), SQL"</em>.
          </div>
          <div style="background: var(--bg-main); padding: 14px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle); font-size: 0.85rem; color: var(--text-secondary); line-height: 1.6;">
            <strong style="color: var(--text-primary);">3. Títulos de Cargos Padrão:</strong><br>
            Em vez de termos inventados como "Ninja de Soluções", use títulos indexáveis como <em>"Assistente Administrativo / Operacional"</em> ou <em>"Analista de BI Jr"</em>.
          </div>
          <div style="background: var(--bg-main); padding: 14px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle); font-size: 0.85rem; color: var(--text-secondary); line-height: 1.6;">
            <strong style="color: var(--text-primary);">4. Formato de Exportação:</strong><br>
            Salve sempre em PDF com texto selecionável (não em imagem escaneada) ou em .DOCX quando solicitado explicitamente pela ATS.
          </div>
        </div>
      </div>
    </div>

    <!-- TAB 3: BUSCA MULTI-ÁREAS & ATS HUNTER (NOVA ABA) -->
    <div id="tab-multiarea" style="display: none;">
      <div class="filter-panel">
        <h3 style="font-size: 1.15rem; font-weight: 700; color: var(--text-primary); margin-bottom: 6px;">
          🌐 Central de Busca Multi-Áreas & ATS Hunter
        </h3>
        <p style="color: var(--text-secondary); font-size: 0.9rem; line-height: 1.6;">
          Amplie o monitoramento para além de Dados: explore novas áreas do mercado (Logística, Comercial, RH, Financeiro, Operações) e acesse diretamente os portais de recrutamento (Gupy, Greenhouse, Lever, Workday e Kenoby).
        </p>

        <!-- CONTROLES INTERATIVOS DE BUSCA MULTI-ÁREAS -->
        <div style="display: flex; gap: 12px; flex-wrap: wrap; margin-top: 10px;">
          <select id="hunterAreaSelect" class="select-dropdown" onchange="updateHunterQueries()">
            <option value="dados">📊 Área: Dados, BI & Analytics</option>
            <option value="logistica">📦 Área: Logística, Supply Chain & PCP</option>
            <option value="comercial">💼 Área: Comercial, Vendas & Sales Ops</option>
            <option value="operacoes">⚙️ Área: Operações, Backoffice & Processos</option>
            <option value="rh">👥 Área: Recursos Humanos, DP & Talent Acquisition</option>
            <option value="financeiro">💰 Área: Financeiro, Controladoria & Faturamento</option>
            <option value="cs">🎧 Área: Customer Success, Atendimento & CX</option>
          </select>
          <input type="text" id="hunterLocationInput" class="search-input" style="max-width: 260px;" placeholder="Localização (ex: Remoto, Campinas)" value="Remoto" oninput="updateHunterQueries()">
        </div>
      </div>

      <!-- CARDS DE ATS E LANÇADORES DIRETOS -->
      <div class="ats-grid" id="atsCardsContainer">
        <!-- Injected by JS -->
      </div>

      <!-- GERADOR DE QUERY RECRUTADORES -->
      <div class="arch-card" style="margin-top: 24px; margin-bottom: 32px;">
        <h3 style="color: var(--accent-purple);">🔎 Localizador Avançado de RHs e Recrutadores (OSINT)</h3>
        <p style="margin-bottom: 14px; font-size: 0.9rem;">
          Encontre os responsáveis de contratação (Talent Acquisition, Tech Recruiters, Gerentes de RH) de qualquer empresa na área selecionada:
        </p>
        <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 12px;">
          <input type="text" id="hunterCompanyInput" class="search-input" style="max-width: 320px;" placeholder="Nome da Empresa (ex: Nubank, Ambev, Heineken)" value="Ambev" oninput="updateRecruiterDork()">
          <button onclick="launchRecruiterDork()" class="btn btn-primary">
            Buscar Recrutadores no LinkedIn &rarr;
          </button>
        </div>
        <div style="background: var(--bg-main); border: 1px solid var(--border-subtle); padding: 10px 14px; border-radius: 6px; font-family: monospace; font-size: 0.8rem; color: #94a3b8;" id="recruiterDorkPreview">
          <!-- Injected by JS -->
        </div>
      </div>
    </div>

    <!-- TAB 4: RECRUITERS -->
    <div id="tab-recruiters" style="display: none;">
      <div class="filter-panel">
        <p style="color: var(--text-secondary); font-size: 0.9rem;">
          💼 <strong>Mapeamento de Contatos Estratégicos:</strong> Empresas com vagas com Fit Score &ge; 65% possuem atalhos diretos e pesquisa pública de Talent Acquisition / RH para contato e candidatura ativa.
        </p>
      </div>

      <div class="recruiters-grid" id="recruitersGrid">
        <!-- Injected by JS -->
      </div>
    </div>

    <!-- TAB 5: ANALYTICS -->
    <div id="tab-analytics" style="display: none;">
      <div class="arch-grid">
        <div class="arch-card">
          <h3>📊 Distribuição de Modalidade</h3>
          <p style="margin-bottom: 16px;">Presença majoritária de oportunidades remotas e híbridas focadas no perfil.</p>
          <div style="display: flex; flex-direction: column; gap: 10px;">
            <div>
              <div style="display: flex; justify-content: space-between; font-size: 0.85rem; margin-bottom: 4px;">
                <span>Presencial ({stats['total_presenciais']})</span>
                <span>{round(stats['total_presenciais']/total_jobs*100, 1)}%</span>
              </div>
              <div style="height: 8px; background: #1e293b; border-radius: 4px; overflow: hidden;">
                <div style="width: {round(stats['total_presenciais']/total_jobs*100, 1)}%; height: 100%; background: #64748b;"></div>
              </div>
            </div>
            <div>
              <div style="display: flex; justify-content: space-between; font-size: 0.85rem; margin-bottom: 4px;">
                <span>Remoto ({stats['total_remotas']})</span>
                <span>{round(stats['total_remotas']/total_jobs*100, 1)}%</span>
              </div>
              <div style="height: 8px; background: #1e293b; border-radius: 4px; overflow: hidden;">
                <div style="width: {round(stats['total_remotas']/total_jobs*100, 1)}%; height: 100%; background: var(--accent-blue);"></div>
              </div>
            </div>
            <div>
              <div style="display: flex; justify-content: space-between; font-size: 0.85rem; margin-bottom: 4px;">
                <span>Híbrido ({stats['total_hibridas']})</span>
                <span>{round(stats['total_hibridas']/total_jobs*100, 1)}%</span>
              </div>
              <div style="height: 8px; background: #1e293b; border-radius: 4px; overflow: hidden;">
                <div style="width: {round(stats['total_hibridas']/total_jobs*100, 1)}%; height: 100%; background: var(--accent-purple);"></div>
              </div>
            </div>
          </div>
        </div>

        <div class="arch-card">
          <h3>🔥 Top Competências em Alta</h3>
          <p style="margin-bottom: 16px;">Habilidades técnicas e funcionais mais frequentes identificadas pelo FitScorer:</p>
          <div style="display: flex; flex-wrap: wrap; gap: 8px;">
            {''.join([f'<span class="tag-pill" style="font-size: 0.82rem; padding: 6px 12px; background: #1e293b; border-color: #334155;"><strong style="color: var(--primary);">{skill}</strong>: {count} vagas</span>' for skill, count in stats['top_skills']])}
          </div>
        </div>

        <div class="arch-card">
          <h3>📈 Resumo de Aderência</h3>
          <p style="margin-bottom: 16px;">Qualificação por faixas de pontuação no perfil da candidata:</p>
          <ul style="color: var(--text-secondary); font-size: 0.9rem; line-height: 1.8; list-style: none;">
            <li>⭐ <strong>Score &ge; 80% (Prioridade Máxima):</strong> {stats['total_score_80']} vaga</li>
            <li>🟢 <strong>Score &ge; 70% (Alta Aderência):</strong> {sum(1 for j in jobs if j['score'] >= 70.0)} vagas</li>
            <li>🟡 <strong>Score &ge; 65% (Média Aderência):</strong> {stats['total_score_65']} vagas</li>
            <li>🔵 <strong>Score &lt; 65%:</strong> {total_jobs - stats['total_score_65']} vagas</li>
          </ul>
        </div>
      </div>
    </div>

    <!-- TAB 6: ARCHITECTURE -->
    <div id="tab-architecture" style="display: none;">
      <div class="arch-grid">
        <div class="arch-card">
          <h3>🛰️ JobHarvester Multi-Fonte</h3>
          <p>
            Integração com <strong>JobSpy</strong> e raspagem ética pública para cruzar vagas simultaneamente do <strong>LinkedIn, Indeed, Glassdoor e Gupy</strong>, com normalização de campos, localização e modalidade de trabalho.
          </p>
        </div>
        <div class="arch-card">
          <h3>🧠 FitScorer Algorítmico</h3>
          <p>
            Motor determinístico sem alucinações que pontua vagas de 0 a 100 com pesos parametrizáveis em YAML: match de cargo, stack de ferramentas (Excel, Power BI, SQL, SAP), regras de localidade e filtros negativos.
          </p>
        </div>
        <div class="arch-card">
          <h3>🛡️ Deduplicação & Vault SQLite</h3>
          <p>
            Hashing criptográfico baseado em normalização de texto (empresa, título, cidade, link) garantindo zero duplicatas ao longo de semanas de varredura contínua no banco local <code>job_vault.db</code>.
          </p>
        </div>
        <div class="arch-card">
          <h3>👥 Recruiter Hunter (OSINT)</h3>
          <p>
            Agente que mapeia tomadores de decisão e profissionais de RH/Talent Acquisition para vagas de alto fit, gerando links diretos de busca e perfis públicos sem exigir login nem violação de termos.
          </p>
        </div>
        <div class="arch-card">
          <h3>📊 Excel Exporter & Sync</h3>
          <p>
            Módulo que sincroniza os dados formatados na planilha corporativa <code>Radar_Vagas_Data.xlsx</code> com colorização condicional, links clicáveis e colunas de gestão de candidaturas em lote.
          </p>
        </div>
        <div class="arch-card">
          <h3>🚀 CI/CD & GitHub Pages</h3>
          <p>
            Arquitetura estática self-contained em um único arquivo HTML+CSS+JS, pronta para hospedar gratuitamente no GitHub Pages sem necessidade de backend, com carregamento instantâneo.
          </p>
        </div>
      </div>
    </div>

  </main>

  <!-- MODAL DETAILS -->
  <div class="modal-backdrop" id="jobModal" onclick="closeModalOnBackdrop(event)">
    <div class="modal-box">
      <button class="modal-close" onclick="closeModal()">&times;</button>
      <div id="modalContent">
        <!-- Injected by JS -->
      </div>
    </div>
  </div>

  <!-- FOOTER -->
  <footer class="site-footer">
    <div class="container">
      <p>Radar de Vagas — Sistema de Monitoramento & Curadoria Inteligente</p>
      <p style="margin-top: 6px; font-size: 0.75rem;">Desenvolvido com arquitetura limpa em Python & Front-end Vanilla de alta performance para GitHub Pages.</p>
    </div>
  </footer>

  <!-- ─── JAVASCRIPT APPLICATION CODE ─── -->
  <script>
    // Embedded Data injected by Generator
    const RADAR_DATA = {data_json};

    // State
    let currentPage = 1;
    const pageSize = 20;
    let filteredJobs = [...RADAR_DATA.jobs];

    // Dom Elements
    const searchInput = document.getElementById('searchInput');
    const sortSelect = document.getElementById('sortSelect');
    const modalidadeSelect = document.getElementById('modalidadeSelect');
    const scoreSelect = document.getElementById('scoreSelect');
    const statusSelect = document.getElementById('statusSelect');
    const jobsTableBody = document.getElementById('jobsTableBody');
    const filteredCount = document.getElementById('filtered-count');
    const paginationInfo = document.getElementById('paginationInfo');
    const paginationControls = document.getElementById('paginationControls');

    // Init
    document.addEventListener('DOMContentLoaded', () => {{
      // Initial chronological sort (most recent first)
      sortJobs('date_desc');
      renderJobs();
      renderRecruiters();
      initResumeOptimizer();
      updateHunterQueries();
      updateRecruiterDork();
    }});

    // Tab Switching
    function switchTab(tabName) {{
      const tabs = ['jobs', 'resume', 'multiarea', 'recruiters', 'analytics', 'architecture'];
      tabs.forEach(t => {{
        const el = document.getElementById('tab-' + t);
        if (el) el.style.display = (t === tabName) ? 'block' : 'none';
      }});

      document.querySelectorAll('.tab-btn').forEach((btn, idx) => {{
        btn.classList.toggle('active', tabs[idx] === tabName);
      }});
    }}

    // Sorting Function
    function sortJobs(mode) {{
      if (mode === 'date_desc') {{
        // Mais recentes primeiro (data_busca / data_pub desc)
        filteredJobs.sort((a, b) => {{
          const dateA = a.data_busca || a.data_pub || '';
          const dateB = b.data_busca || b.data_pub || '';
          if (dateA !== dateB) return dateB.localeCompare(dateA);
          return (b.score || 0) - (a.score || 0);
        }});
      }} else if (mode === 'score_desc') {{
        filteredJobs.sort((a, b) => (b.score || 0) - (a.score || 0));
      }} else if (mode === 'score_asc') {{
        filteredJobs.sort((a, b) => (a.score || 0) - (b.score || 0));
      }} else if (mode === 'company_asc') {{
        filteredJobs.sort((a, b) => (a.empresa || '').localeCompare(b.empresa || ''));
      }}
    }}

    // Filter Logic
    function handleFilterChange() {{
      const query = (searchInput.value || '').toLowerCase().trim();
      const modalidade = modalidadeSelect.value;
      const minScore = parseFloat(scoreSelect.value) || 0;
      const status = statusSelect.value;
      const sortMode = sortSelect.value;

      filteredJobs = RADAR_DATA.jobs.filter(job => {{
        // Search text
        if (query) {{
          const matchTitle = (job.cargo || '').toLowerCase().includes(query);
          const matchCompany = (job.empresa || '').toLowerCase().includes(query);
          const matchSkills = (job.skills_match || '').toLowerCase().includes(query);
          const matchLoc = (job.localizacao || '').toLowerCase().includes(query);
          if (!matchTitle && !matchCompany && !matchSkills && !matchLoc) return false;
        }}

        // Modalidade
        if (modalidade && !job.modalidade.toLowerCase().includes(modalidade.toLowerCase())) {{
          return false;
        }}

        // Min Score
        if (job.score < minScore) {{
          return false;
        }}

        // Status
        if (status && job.status !== status) {{
          return false;
        }}

        return true;
      }});

      sortJobs(sortMode);
      currentPage = 1;
      renderJobs();
    }}

    // Quick Pill Filters
    function setQuickPill(type, btnElement) {{
      document.querySelectorAll('.pill-filter').forEach(b => b.classList.remove('active'));
      btnElement.classList.add('active');

      modalidadeSelect.value = '';
      scoreSelect.value = '0';
      statusSelect.value = '';
      sortSelect.value = 'date_desc';

      if (type === 'recent') {{
        sortSelect.value = 'date_desc';
      }} else if (type === 'remoto') {{
        modalidadeSelect.value = 'Remoto';
      }} else if (type === 'high-score') {{
        scoreSelect.value = '65';
        sortSelect.value = 'score_desc';
      }} else if (type === 'revisao') {{
        statusSelect.value = 'Aguardando minha revisão';
      }} else if (type === 'enviada') {{
        statusSelect.value = 'Enviada';
      }}

      handleFilterChange();
    }}

    // Render Table Rows
    function renderJobs() {{
      filteredCount.textContent = `Exibindo ${{filteredJobs.length}} vagas`;
      const start = (currentPage - 1) * pageSize;
      const end = start + pageSize;
      const pageData = filteredJobs.slice(start, end);

      if (pageData.length === 0) {{
        jobsTableBody.innerHTML = `
          <tr>
            <td colspan="9" style="text-align: center; padding: 48px; color: var(--text-muted);">
              <div style="font-size: 2rem; margin-bottom: 8px;">🔍</div>
              Nenhuma vaga encontrada com os filtros selecionados.
            </td>
          </tr>
        `;
        paginationInfo.textContent = 'Nenhum resultado';
        paginationControls.innerHTML = '';
        return;
      }}

      let html = '';
      pageData.forEach((job, index) => {{
        const dynamicRank = start + index + 1;
        let scoreClass = 'score-low';
        let starIcon = '🔵';
        if (job.score >= 80) {{
          scoreClass = 'score-80';
          starIcon = '⭐';
        }} else if (job.score >= 65) {{
          scoreClass = 'score-65';
          starIcon = '🟢';
        }}

        let statusClass = 'status-manual';
        if (job.status === 'Enviada') statusClass = 'status-enviada';
        else if (job.status === 'Aguardando minha revisão') statusClass = 'status-revisao';

        const displayDate = job.data_busca || job.data_pub || '-';

        const skillsList = job.skills_match ? job.skills_match.split(',').slice(0, 3) : [];
        const skillsHtml = skillsList.map(s => `<span class="tag-pill">${{s.trim()}}</span>`).join(' ');

        html += `
          <tr>
            <td style="font-family: monospace; color: var(--text-muted); font-weight: 600;">#${{dynamicRank}}</td>
            <td><span class="date-col">${{displayDate}}</span></td>
            <td>
              <span class="score-badge ${{scoreClass}}">${{starIcon}} ${{job.score}}%</span>
            </td>
            <td>
              <span class="job-title-col" title="${{escapeHtml(job.cargo)}}">${{escapeHtml(job.cargo)}}</span>
              <span class="company-col">${{escapeHtml(job.empresa)}}</span>
            </td>
            <td>
              <span style="font-size: 0.8rem; font-weight: 600; color: ${{job.modalidade.includes('Remoto') ? 'var(--accent-blue)' : (job.modalidade.includes('Híbrido') ? 'var(--accent-purple)' : 'var(--text-secondary)')}}">
                ${{escapeHtml(job.modalidade)}}
              </span>
            </td>
            <td style="max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
              ${{escapeHtml(job.localizacao || '-')}}
            </td>
            <td>${{skillsHtml || '<span style="color: var(--text-muted);">-</span>'}}</td>
            <td>
              <span class="status-badge ${{statusClass}}">${{escapeHtml(job.status)}}</span>
            </td>
            <td style="text-align: right; white-space: nowrap;">
              <button class="action-btn" onclick="openJobModal('${{job.cargo}}', '${{job.empresa}}')">
                <span>Ver Detalhes</span>
              </button>
            </td>
          </tr>
        `;
      }});

      jobsTableBody.innerHTML = html;
      renderPagination(filteredJobs.length, start, end);
    }}

    // Pagination Renderer
    function renderPagination(total, start, end) {{
      const totalPages = Math.ceil(total / pageSize) || 1;
      paginationInfo.textContent = `Mostrando ${{start + 1}}-${{Math.min(end, total)}} de ${{total}} vagas`;

      let controlsHtml = '';
      controlsHtml += `<button class="page-btn" onclick="changePage(${{currentPage - 1}})" ${{currentPage === 1 ? 'disabled' : ''}}>&larr; Anterior</button>`;
      
      let startP = Math.max(1, currentPage - 2);
      let endP = Math.min(totalPages, currentPage + 2);

      for (let p = startP; p <= endP; p++) {{
        controlsHtml += `<button class="page-btn ${{p === currentPage ? 'active' : ''}}" onclick="changePage(${{p}})">${{p}}</button>`;
      }}

      controlsHtml += `<button class="page-btn" onclick="changePage(${{currentPage + 1}})" ${{currentPage === totalPages ? 'disabled' : ''}}>Próxima &rarr;</button>`;
      paginationControls.innerHTML = controlsHtml;
    }}

    function changePage(page) {{
      currentPage = page;
      renderJobs();
      window.scrollTo({{ top: 400, behavior: 'smooth' }});
    }}

    // ─── ABA DE OTIMIZAÇÃO DE CURRÍCULO (ATS OPTIMIZER) ───
    const KEY_SKILLS = [
      {{ name: "Power BI (DAX / M)", weight: 12, default: true }},
      {{ name: "Excel Avançado (PROCV/X)", weight: 10, default: true }},
      {{ name: "SQL (Consultas / JOINs)", weight: 10, default: false }},
      {{ name: "Dashboards & KPIs", weight: 9, default: true }},
      {{ name: "SAP (ERP)", weight: 8, default: false }},
      {{ name: "Gestão de Processos", weight: 7, default: true }},
      {{ name: "CRM (Salesforce/Hubspot)", weight: 7, default: false }},
      {{ name: "Logística & Supply Chain", weight: 6, default: false }},
      {{ name: "Metodologias Ágeis (Scrum)", weight: 6, default: false }},
      {{ name: "Python para Dados", weight: 8, default: false }},
      {{ name: "Faturamento & DRE", weight: 5, default: false }},
      {{ name: "Gupy / Testes Online", weight: 5, default: true }},
    ];

    const BULLET_POINTS = {{
      dados: [
        "Desenvolvimento e manutenção de dashboards gerenciais em Power BI, integrando bases em SQL e Excel para acompanhamento de KPIs operacionais e comerciais.",
        "Automatização de rotinas de relatórios e conciliação de dados em Power Query, reduzindo em 35% o tempo de fechamento semanal.",
        "Modelagem de métricas e indicadores de desempenho (SLA, Churn, Conversão) apresentados para lideranças e diretoria."
      ],
      operacoes: [
        "Mapeamento e padronização de procedimentos operacionais (POPs), identificando gargalos e elevando a produtividade da equipe em 25%.",
        "Gestão de rotinas de Backoffice e controle de chamados com foco no cumprimento estrito de SLAs contratuais.",
        "Controle de inventário e elaboração de relatórios gerenciais no sistema ERP (SAP), garantindo acuracidade de 99% nas informações."
      ],
      comercial: [
        "Estruturação e qualificação de pipeline de vendas através de CRM (Salesforce/Hubspot), apoiando a equipe comercial no atingimento de metas.",
        "Análise de dados de mercado e histórico de compras de clientes para identificar oportunidades de cross-sell e expansão de receita.",
        "Atendimento consultivo B2B e elaboração de propostas comerciais personalizadas com acompanhamento contínuo de status."
      ],
      logistica: [
        "Planejamento e controle de estoque e expedição através de sistema SAP, otimizando o fluxo logístico e reduzindo atrasos em 30%.",
        "Acompanhamento de entregas e negociação com transportadoras parceiras, monitorando taxas de OTIF (On-Time In-Full).",
        "Elaboração de relatórios de giro de produtos e estoques de segurança em Excel avançado."
      ],
      rh: [
        "Condução de processos seletivos de ponta a ponta na plataforma Gupy, desde a triagem de currículos e aplicação de testes até a entrevista final.",
        "Mapeamento de perfis e caça ativa (hunting) de candidatos estratégicos via LinkedIn Recruiter com foco em diversidade e inclusão.",
        "Gestão de indicadores de R&S (Time-to-Hire, Cost-per-Hire e taxa de retenção no período de experiência)."
      ]
    }};

    function initResumeOptimizer() {{
      const container = document.getElementById('skillsCheckboxes');
      if (!container) return;

      let html = '';
      KEY_SKILLS.forEach((skill, idx) => {{
        html += `
          <label class="skill-checkbox-label">
            <input type="checkbox" id="skill_chk_${{idx}}" ${{skill.default ? 'checked' : ''}} onchange="recalculateSimulator()">
            ${{skill.name}} (+${{skill.weight}}%)
          </label>
        `;
      }});
      container.innerHTML = html;
      recalculateSimulator();
      renderBulletPoints();
    }}

    function recalculateSimulator() {{
      let score = 40; // Base score
      KEY_SKILLS.forEach((skill, idx) => {{
        const chk = document.getElementById('skill_chk_' + idx);
        if (chk && chk.checked) {{
          score += (skill.weight * 0.45);
        }}
      }});
      score = Math.min(Math.round(score * 10) / 10, 95);

      const textEl = document.getElementById('simulatedScoreText');
      const barEl = document.getElementById('simulatedProgressBar');
      const feedbackEl = document.getElementById('simulatedFeedback');

      if (textEl) textEl.textContent = score.toFixed(1) + '%';
      if (barEl) barEl.style.width = score + '%';

      if (feedbackEl) {{
        if (score >= 80) {{
          feedbackEl.innerHTML = '⭐ <strong>Excelente!</strong> Seu currículo está na faixa dos 5% mais compatíveis com as vagas do radar.';
          feedbackEl.style.color = '#34d399';
        }} else if (score >= 70) {{
          feedbackEl.innerHTML = '🟢 <strong>Alta Aderência!</strong> Você passará com facilidade na triagem dos robôs ATS da maioria das vagas.';
          feedbackEl.style.color = '#60a5fa';
        }} else {{
          feedbackEl.innerHTML = '💡 <em>Adicione mais 2 competências técnicas chave para ultrapassar 75% de aderência média.</em>';
          feedbackEl.style.color = '#fbbf24';
        }}
      }}
    }}

    function renderBulletPoints() {{
      const area = document.getElementById('resumeAreaSelect').value;
      const container = document.getElementById('bulletPointsContainer');
      const points = BULLET_POINTS[area] || BULLET_POINTS['dados'];

      let html = '';
      points.forEach((pt, i) => {{
        html += `
          <div class="bullet-box">
            ${{pt}}
            <button class="copy-btn" onclick="copyText('${{escapeJs(pt)}}', this)">Copiar</button>
          </div>
        `;
      }});
      container.innerHTML = html;
    }}

    function copyText(txt, btn) {{
      navigator.clipboard.writeText(txt).then(() => {{
        const orig = btn.textContent;
        btn.textContent = 'Copiado!';
        btn.style.background = '#10b981';
        setTimeout(() => {{
          btn.textContent = orig;
          btn.style.background = '';
        }}, 1500);
      }});
    }}

    // ─── ABA DE BUSCA MULTI-ÁREAS & ATS HUNTER ───
    const ATS_PLATFORMS = [
      {{ name: "Gupy", badge: "Líder no Brasil", icon: "🟢", dork: 'site:gupy.io', desc: "Milhares de vagas diretas em empresas nacionais e multinacionais sem intermediários." }},
      {{ name: "Greenhouse", badge: "Tech & Startups", icon: "🌿", dork: 'site:boards.greenhouse.io', desc: "Padrão de ouro das startups, scale-ups e empresas de tecnologia globais." }},
      {{ name: "Lever", badge: "Scale-ups", icon: "⚡", dork: 'site:jobs.lever.co', desc: "Utilizado por fintechs e empresas com processos seletivos ágeis." }},
      {{ name: "Kenoby / Senior", badge: "Grandes Grupos", icon: "🔵", dork: 'site:jobs.kenoby.com OR site:jobs.senior.com.br', desc: "Plataforma muito adotada em indústrias, logística e redes de varejo." }},
      {{ name: "Workday", badge: "Multinacionais", icon: "🏢", dork: 'site:myworkdayjobs.com', desc: "Portal corporativo padrão de gigantes como IBM, Ambev, Heineken, Dell e Unilever." }},
      {{ name: "LinkedIn Jobs", badge: "Global", icon: "💼", direct: true, desc: "Busca pública direta com filtros avançados de senioridade e modelo remoto." }}
    ];

    const AREA_KEYWORDS = {{
      dados: "Analista de Dados OR Analista de BI OR Power BI",
      logistica: "Analista de Logistica OR Assistente de Logistica OR PCP OR Supply Chain",
      comercial: "Analista Comercial OR Assistente Comercial OR Sales Ops",
      operacoes: "Analista de Operacoes OR Assistente de Operacoes OR Backoffice",
      rh: "Analista de RH OR Recrutamento OR Talent Acquisition",
      financeiro: "Analista Financeiro OR Assistente Financeiro OR Controladoria",
      cs: "Customer Success OR Atendimento OR Suporte ao Cliente"
    }};

    function updateHunterQueries() {{
      const area = document.getElementById('hunterAreaSelect').value;
      const loc = (document.getElementById('hunterLocationInput').value || 'Remoto').trim();
      const kw = AREA_KEYWORDS[area] || AREA_KEYWORDS['dados'];
      const container = document.getElementById('atsCardsContainer');

      let html = '';
      ATS_PLATFORMS.forEach(ats => {{
        let searchUrl = '';
        if (ats.direct) {{
          searchUrl = `https://www.linkedin.com/jobs/search/?keywords=${{encodeURIComponent(kw)}}&location=${{encodeURIComponent(loc)}}`;
        }} else {{
          const fullQuery = `${{ats.dork}} (${{kw}}) "${{loc}}"`;
          searchUrl = `https://www.google.com/search?q=${{encodeURIComponent(fullQuery)}}`;
        }}

        html += `
          <div class="ats-card">
            <div>
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <h4>${{ats.icon}} ${{ats.name}}</h4>
                <span class="tag-pill" style="color: var(--primary);">${{ats.badge}}</span>
              </div>
              <p>${{ats.desc}}</p>
            </div>
            <div>
              <a href="${{searchUrl}}" target="_blank" rel="noopener noreferrer" class="btn btn-primary" style="width: 100%; font-size: 0.82rem; padding: 8px;">
                Buscar Vagas no ${{ats.name}} &rarr;
              </a>
            </div>
          </div>
        `;
      }});
      container.innerHTML = html;
      updateRecruiterDork();
    }}

    function updateRecruiterDork() {{
      const company = (document.getElementById('hunterCompanyInput').value || 'Empresa').trim();
      const area = document.getElementById('hunterAreaSelect').value;
      const dork = `site:linkedin.com/in ("Talent Acquisition" OR "Recruiter" OR "Recursos Humanos" OR "RH") "${{company}}"`;
      const preview = document.getElementById('recruiterDorkPreview');
      if (preview) preview.textContent = dork;
    }}

    function launchRecruiterDork() {{
      const company = (document.getElementById('hunterCompanyInput').value || '').trim();
      const dork = `site:linkedin.com/in ("Talent Acquisition" OR "Tech Recruiter" OR "Recrutador" OR "Recursos Humanos" OR "RH") "${{company}}"`;
      const url = `https://www.google.com/search?q=${{encodeURIComponent(dork)}}`;
      window.open(url, '_blank');
    }}

    // Render Recruiters Cards
    function renderRecruiters() {{
      const grid = document.getElementById('recruitersGrid');
      if (!grid) return;

      let html = '';
      RADAR_DATA.recruiters.forEach((rec) => {{
        html += `
          <div class="recruiter-card">
            <div>
              <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 6px;">
                <div class="rec-company">${{escapeHtml(rec.empresa)}}</div>
                <span class="tag-pill" style="color: var(--accent-amber);">${{rec.prioridade}}</span>
              </div>
              <div class="rec-role">${{escapeHtml(rec.cargo)}}</div>
              <div class="rec-job-rel">
                <strong style="color: var(--text-secondary);">Vaga Associada:</strong><br>
                ${{escapeHtml(rec.vaga_relacionada || 'Oportunidade Mapeada')}}
              </div>
            </div>
            <div>
              <a href="${{rec.url}}" target="_blank" rel="noopener noreferrer" class="btn btn-secondary" style="width: 100%; justify-content: center; font-size: 0.8rem; padding: 8px;">
                <svg width="14" height="14" fill="currentColor" viewBox="0 0 24 24"><path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.28 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.75M6.88 8.56a1.68 1.68 0 0 0 1.68-1.68c0-.93-.75-1.69-1.68-1.69a1.69 1.69 0 0 0-1.69 1.69c0 .93.76 1.68 1.69 1.68m1.39 9.94v-8.37H5.5v8.37h2.77z"/></svg>
                Buscar Contato no LinkedIn &rarr;
              </a>
            </div>
          </div>
        `;
      }});

      grid.innerHTML = html;
    }}

    // Job Modal Details
    function openJobModal(cargo, empresa) {{
      const job = RADAR_DATA.jobs.find(j => j.cargo === cargo && j.empresa === empresa) || RADAR_DATA.jobs[0];
      if (!job) return;

      const modalContent = document.getElementById('modalContent');
      modalContent.innerHTML = `
        <div style="margin-bottom: 20px;">
          <div style="display: flex; gap: 8px; margin-bottom: 8px; flex-wrap: wrap;">
            <span class="score-badge ${{job.score >= 80 ? 'score-80' : (job.score >= 65 ? 'score-65' : 'score-low')}}">
              Fit Score: ${{job.score}}%
            </span>
            <span class="tag-pill">${{escapeHtml(job.modalidade)}}</span>
            <span class="tag-pill">${{escapeHtml(job.fonte || 'Web')}}</span>
            <span class="tag-pill">${{job.data_busca ? 'Coletada: ' + job.data_busca : ''}}</span>
          </div>
          <h2 style="font-size: 1.35rem; font-weight: 800; color: #fff; margin-bottom: 4px;">${{escapeHtml(job.cargo)}}</h2>
          <p style="font-size: 1rem; color: #94a3b8; font-weight: 600;">${{escapeHtml(job.empresa)}} &bull; ${{escapeHtml(job.localizacao || 'Brasil')}}</p>
        </div>

        <div style="background: var(--bg-main); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: 16px; margin-bottom: 20px;">
          <div style="font-size: 0.8rem; text-transform: uppercase; color: var(--text-muted); font-weight: 700; margin-bottom: 8px;">Competências Identificadas</div>
          <p style="color: #34d399; font-size: 0.9rem; font-weight: 500; margin-bottom: 12px;">
            ${{job.skills_match || 'Nenhuma competência direta listada'}}
          </p>
          <div style="font-size: 0.8rem; text-transform: uppercase; color: var(--text-muted); font-weight: 700; margin-bottom: 8px;">Oportunidades de Desenvolvimento</div>
          <p style="color: #cbd5e1; font-size: 0.85rem;">
            ${{job.skills_gap || 'Perfil altamente aderente'}}
          </p>
        </div>

        <div style="margin-bottom: 24px; font-size: 0.88rem; color: var(--text-secondary); line-height: 1.6;">
          <p><strong>Status Atual:</strong> ${{escapeHtml(job.status)}}</p>
          <p><strong>Etapa:</strong> ${{escapeHtml(job.etapa || '-')}}</p>
          <p><strong>Próxima Ação:</strong> ${{escapeHtml(job.proxima_acao || '-')}}</p>
          ${{job.salario ? `<p><strong>Faixa Salarial:</strong> ${{escapeHtml(job.salario)}}</p>` : ''}}
        </div>

        <div style="display: flex; gap: 12px;">
          <a href="${{job.url}}" target="_blank" rel="noopener noreferrer" class="btn btn-primary" style="flex: 1;">
            Acessar Vaga Original &rarr;
          </a>
          <button onclick="closeModal()" class="btn btn-secondary">Fechar</button>
        </div>
      `;

      document.getElementById('jobModal').classList.add('open');
    }}

    function closeModal() {{
      document.getElementById('jobModal').classList.remove('open');
    }}

    function closeModalOnBackdrop(e) {{
      if (e.target.id === 'jobModal') closeModal();
    }}

    // Export dataset to JSON
    function downloadJSON() {{
      const blob = new Blob([JSON.stringify(RADAR_DATA, null, 2)], {{ type: 'application/json' }});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `radar_vagas_${{new Date().toISOString().slice(0, 10)}}.json`;
      a.click();
      URL.revokeObjectURL(url);
    }}

    function escapeHtml(str) {{
      if (!str) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    }}

    function escapeJs(str) {{
      if (!str) return '';
      return String(str).replace(/'/g, "\\\\'").replace(/"/g, '\\\\"');
    }}
  </script>
</body>
</html>
"""

if __name__ == "__main__":
    export_dashboard()
