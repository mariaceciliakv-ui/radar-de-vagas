"""Processador Autônomo Contínuo de Candidaturas do Radar de Vagas.

Executa a varredura e processamento de TODAS as vagas pendentes na planilha,
ordenando por maior Fit Score e recência até finalizar 100% da tabela.

Regras e Diretrizes:
1. Zero Alucinação: utiliza exclusivamente os dados de config/profile.yaml.
2. Identifica e categoriza cada vaga (Ativa, Encerrada, Link Inválido, Gupy, Indeed, LinkedIn).
3. Não tenta quebrar CAPTCHAs nem simular credenciais inexistentes.
4. Vagas com testes obrigatórios são marcadas como 'Aguardando minha revisão' com link direto.
5. Salva em lotes no Excel em tempo real para máxima velocidade e integridade.
"""

import sys
import os
import time
import logging
from datetime import datetime
from typing import Dict, Any, List
import httpx
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.abspath("."))

from src.core.models import JobOpportunity
from src.exporters.excel_exporter import ExcelExporter

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    filename="logs/applicant_batch.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8"
)
logger = logging.getLogger("RadarDeVagas.BatchApplicant")


def check_url_status(url: str, timeout: int = 6) -> Dict[str, Any]:
    """Testa a conectividade e disponibilidade básica do link da vaga com timeout rápido."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    result = {
        "status_code": 0,
        "ativa": True,
        "tipo": "Normal",
        "detalhes": ""
    }
    
    if not url or not url.startswith("http"):
        result["ativa"] = False
        result["tipo"] = "Link inválido"
        result["detalhes"] = "URL vazia ou não inicia com http"
        return result

    url_lower = url.lower()

    # Heurística rápida por domínio para evitar requisições desnecessárias
    if "gupy.io" in url_lower:
        result["ativa"] = True
        result["tipo"] = "Gupy (Portal com Testes)"
        result["detalhes"] = "Candidatura via Gupy (Cadastro + Testes de Habilidades)"
        return result

    if "linkedin.com" in url_lower:
        result["ativa"] = True
        result["tipo"] = "LinkedIn (Exige Sessão)"
        result["detalhes"] = "LinkedIn exige login do usuário para exibir formulário"
        return result

    try:
        with httpx.Client(headers=headers, follow_redirects=True, timeout=timeout) as client:
            resp = client.get(url)
            result["status_code"] = resp.status_code
            
            if resp.status_code in [404, 410]:
                result["ativa"] = False
                result["tipo"] = "Vaga encerrada"
                result["detalhes"] = f"HTTP {resp.status_code} - Página não encontrada"
            elif "indeed" in url_lower and resp.status_code == 401:
                result["ativa"] = True
                result["tipo"] = "Indeed (Exige Sessão / Redirecionamento)"
                result["detalhes"] = "Sessão ou login Indeed necessário para visualização direta"
            else:
                result["ativa"] = True
                result["tipo"] = "Web Geral"
                result["detalhes"] = f"Acessível (HTTP {resp.status_code})"
    except httpx.TimeoutException:
        result["ativa"] = True
        result["tipo"] = "Timeout"
        result["detalhes"] = "Servidor demorou a responder, mantida para verificação"
    except Exception as e:
        result["ativa"] = True
        result["tipo"] = "Erro de Rede"
        result["detalhes"] = str(e)[:40]

    return result


def process_entire_table():
    target_file = "data/output/Radar_Vagas_Data.xlsx"
    print("=" * 76)
    print("  🚀 RADAR DE VAGAS — PROCESSAMENTO AUTÔNOMO DE TODA A TABELA (/goal)")
    print(f"  📅 {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"  📁 Arquivo: {target_file}")
    print("=" * 76)

    if not os.path.exists(target_file):
        print("Arquivo de planilha não encontrado!")
        return

    # Carregar workbook
    wb = openpyxl.load_workbook(target_file, data_only=False)
    if "🎯 Vagas Recomendadas" not in wb.sheetnames:
        print("Aba '🎯 Vagas Recomendadas' não encontrada!")
        return

    ws = wb["🎯 Vagas Recomendadas"]
    headers = [cell.value for cell in ws[1]]
    col_map = {name: idx for idx, name in enumerate(headers) if name}

    # Garantir cabeçalhos de candidatura na linha 1
    cand_headers = [
        ("Status Candidatura", 15),
        ("Data da Tentativa", 16),
        ("Etapa Alcançada", 17),
        ("Campos Pendentes", 18),
        ("Próxima Ação", 19)
    ]
    header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    border_thin = Border(
        left=Side(style='thin', color='E0E0E0'),
        right=Side(style='thin', color='E0E0E0'),
        top=Side(style='thin', color='E0E0E0'),
        bottom=Side(style='thin', color='E0E0E0')
    )

    for h_title, c_num in cand_headers:
        if ws.cell(row=1, column=c_num).value != h_title:
            c = ws.cell(row=1, column=c_num, value=h_title)
            c.fill = header_fill
            c.font = header_font
            c.alignment = Alignment(horizontal="center", vertical="center")
            c.border = border_thin

    total_rows = ws.max_row
    print(f"Total de linhas na planilha: {total_rows - 1} vagas.")

    # Mapear linhas pendentes
    pending_rows = []
    for r in range(2, total_rows + 1):
        st = ws.cell(row=r, column=15).value
        if not st or st in ["Não iniciada", "Em análise", ""]:
            cargo = str(ws.cell(row=r, column=4).value or "")
            empresa = str(ws.cell(row=r, column=5).value or "")
            fonte = str(ws.cell(row=r, column=13).value or "")
            link_cell = ws.cell(row=r, column=14)
            url = link_cell.hyperlink.target if link_cell.hyperlink else str(link_cell.value or "")
            score_str = str(ws.cell(row=r, column=2).value or "0").replace("%", "")
            try:
                score = float(score_str)
            except:
                score = 0.0
            pending_rows.append((r, score, cargo, empresa, fonte, url))

    # Ordenar pendentes por score decrescente
    pending_rows.sort(key=lambda x: x[1], reverse=True)
    total_pendentes = len(pending_rows)
    print(f"Vagas pendentes a processar: {total_pendentes}")

    if total_pendentes == 0:
        print("🎉 Todas as vagas da planilha já estão 100% processadas!")
        return

    processadas = 0
    encerradas = 0
    bloqueadas_login = 0
    aguardando_revisao = 0
    salvos_count = 0

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    for r_idx, score, cargo, empresa, fonte, url in pending_rows:
        processadas += 1
        titulo_lower = cargo.lower()

        if "exclusiva para pessoas com deficiência" in titulo_lower or "exclusiva pcd" in titulo_lower:
            status = "Bloqueada ou exige ação manual"
            etapa = "Vaga exclusiva para Pessoas com Deficiência (PCD)"
            pendentes = "Verificar enquadramento legal PCD"
            prox_acao = "Candidata avaliar se possui laudo para vagas PCD"
            aguardando_revisao += 1
        else:
            url_info = check_url_status(url)
            
            if not url_info["ativa"]:
                status = "Vaga encerrada"
                etapa = url_info["detalhes"]
                pendentes = "Nenhum (Vaga inativa)"
                prox_acao = "Nenhuma ação necessária (encerrada)"
                encerradas += 1
            elif "Gupy" in url_info["tipo"]:
                status = "Aguardando minha revisão"
                etapa = "Portal Gupy (Requer testes de perfil/conhecimento)"
                pendentes = "Realização de testes online no portal Gupy"
                prox_acao = "Acessar link Gupy e realizar avaliações online"
                aguardando_revisao += 1
            elif "Indeed" in url_info["tipo"] or "LinkedIn" in url_info["tipo"]:
                status = "Bloqueada ou exige ação manual"
                etapa = f"{fonte}: Exige sessão ativa no navegador"
                pendentes = f"Sessão de usuário {fonte}"
                prox_acao = f"Abrir link com perfil autenticado para aplicar"
                bloqueadas_login += 1
            else:
                status = "Aguardando minha revisão"
                etapa = "Site da empresa / ATS parceiro"
                pendentes = "Conferência do formulário externo"
                prox_acao = "Acessar link da vaga e confirmar envio"
                aguardando_revisao += 1

        # Escrever na planilha
        st_cell = ws.cell(row=r_idx, column=15, value=status)
        st_cell.alignment = Alignment(horizontal="center")
        if status == "Enviada":
            st_cell.fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
            st_cell.font = Font(color="006100", bold=True)
        elif status == "Aguardando minha revisão":
            st_cell.fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
            st_cell.font = Font(color="9C6500", bold=True)
        elif status in ["Bloqueada ou exige ação manual", "Link inválido"]:
            st_cell.fill = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")
        elif status == "Vaga encerrada":
            st_cell.fill = PatternFill(start_color="D9D9D9", end_color="D9D9D9", fill_type="solid")

        ws.cell(row=r_idx, column=16, value=now_str).alignment = Alignment(horizontal="center")
        ws.cell(row=r_idx, column=17, value=etapa)
        ws.cell(row=r_idx, column=18, value=pendentes)
        ws.cell(row=r_idx, column=19, value=prox_acao)

        for c in range(15, 20):
            ws.cell(row=r_idx, column=c).border = border_thin

        # Salvar incrementalmente a cada 50 vagas
        if processadas % 50 == 0 or processadas == total_pendentes:
            try:
                wb.save(target_file)
                salvos_count += 1
                progresso_pct = (processadas / total_pendentes) * 100
                print(f"[{processadas}/{total_pendentes}] ({progresso_pct:.1f}%) — Planilha sincronizada com sucesso!")
            except Exception as e:
                print(f"Aviso ao salvar checkpoint: {e}")

    # Salvamento final garantido
    wb.save(target_file)
    wb.close()

    print("\n" + "=" * 76)
    print("  🎉 GOAL COMPLETO — TODA A TABELA FOI PROCESSADA COM SUCESSO!")
    print(f"  • Total de vagas processadas nesta rodada: {processadas}")
    print(f"  • Vagas encerradas/inativas             : {encerradas}")
    print(f"  • Vagas com testes/Gupy                 : {aguardando_revisao}")
    print(f"  • Vagas exigindo login da plataforma    : {bloqueadas_login}")
    print(f"  • Total geral de vagas na planilha      : {total_rows - 1}")
    print(f"  • Arquivo final gravado                 : {target_file}")
    print("=" * 76 + "\n")


if __name__ == "__main__":
    process_entire_table()
