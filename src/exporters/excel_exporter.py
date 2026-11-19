"""Exportador e Sincronizador de Planilha Excel (.xlsx) com Histórico e Deduplicação."""

import os
from datetime import datetime
from typing import List, Dict, Any, Tuple, Set
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from src.core.models import JobOpportunity
from src.core.deduplication import DeduplicationEngine


class ExcelExporter:
    """Gerencia a leitura, mesclagem incremental e estilização da planilha de vagas e recrutadores."""

    def __init__(self, output_dir: str = "data/output"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.default_file = os.path.join(self.output_dir, "Radar_Vagas_Data.xlsx")

    @staticmethod
    def _safe_load_workbook(target_file: str, data_only: bool = False):
        """Carrega o workbook com segurança mesmo se o Excel estiver com o arquivo aberto."""
        try:
            return openpyxl.load_workbook(target_file, data_only=data_only)
        except PermissionError:
            import shutil
            temp_copy = target_file + f".temp_read_{os.getpid()}.xlsx"
            shutil.copy2(target_file, temp_copy)
            wb = openpyxl.load_workbook(temp_copy, data_only=data_only)
            try:
                os.remove(temp_copy)
            except Exception:
                pass
            return wb

    @staticmethod
    def _safe_save_workbook(wb, target_file: str) -> str:
        """Salva no arquivo principal ou em _atualizada.xlsx se bloqueado pelo Excel."""
        try:
            wb.save(target_file)
            return target_file
        except PermissionError:
            temp_dest = target_file.replace(".xlsx", "_atualizada.xlsx")
            wb.save(temp_dest)
            print(f"⚠ Planilha original está aberta no Excel! Gravado com sucesso em: {temp_dest}")
            return temp_dest

    def read_existing_jobs(self, file_path: str = None) -> List[JobOpportunity]:
        """Lê as vagas já cadastradas na planilha existente."""
        target_file = file_path or self.default_file
        if not os.path.exists(target_file):
            return []

        existing_jobs: List[JobOpportunity] = []
        try:
            wb = self._safe_load_workbook(target_file, data_only=False)

            if "🎯 Vagas Recomendadas" not in wb.sheetnames:
                return []

            
            ws = wb["🎯 Vagas Recomendadas"]
            # Encontrar índices de cabeçalho
            headers = [cell.value for cell in ws[1]]
            col_map = {name: idx for idx, name in enumerate(headers) if name}

            for row in ws.iter_rows(min_row=2, values_only=False):
                if not row or not row[col_map.get("Cargo", 3)].value:
                    continue

                titulo = str(row[col_map.get("Cargo", 3)].value or "")
                empresa = str(row[col_map.get("Empresa", 4)].value or "")
                modalidade = str(row[col_map.get("Modalidade", 5)].value or "Presencial")
                localizacao = str(row[col_map.get("Localização", 6)].value or "Brasil")
                salario = str(row[col_map.get("Salário", 7)].value or "A combinar")
                data_pub = str(row[col_map.get("Data Publicação", 8)].value or "Recente")
                data_busca = str(row[col_map.get("Data da Busca", 9)].value or "")
                skills = str(row[col_map.get("Skills Encontradas", 10)].value or "").split(", ")
                dev = str(row[col_map.get("Oportunidades Desenvolvimento", 11)].value or "").split(", ")
                fonte = str(row[col_map.get("Fonte", 12)].value or "Web")
                
                # Extrair link real do hyperlink ou valor da célula
                url_cell = row[col_map.get("Link da Vaga", 13)]
                url = url_cell.hyperlink.target if url_cell.hyperlink else str(url_cell.value or "")
                
                score_str = str(row[col_map.get("Score (%)", 1)].value or "0").replace("%", "")
                try:
                    score = float(score_str)
                except ValueError:
                    score = 0.0

                classificacao = str(row[col_map.get("Prioridade", 2)].value or "Média Aderência")

                # Candidatura
                status_candidatura = str(row[col_map.get("Status Candidatura", 14)].value or "Não iniciada") if "Status Candidatura" in col_map and col_map["Status Candidatura"] < len(row) else "Não iniciada"
                data_tentativa = str(row[col_map.get("Data da Tentativa", 15)].value or "") if "Data da Tentativa" in col_map and col_map["Data da Tentativa"] < len(row) else None
                etapa_alcancada = str(row[col_map.get("Etapa Alcançada", 16)].value or "Nenhuma") if "Etapa Alcançada" in col_map and col_map["Etapa Alcançada"] < len(row) else "Nenhuma"
                campos_pendentes = str(row[col_map.get("Campos Pendentes", 17)].value or "-") if "Campos Pendentes" in col_map and col_map["Campos Pendentes"] < len(row) else "-"
                proxima_acao = str(row[col_map.get("Próxima Ação", 18)].value or "Aguardando início") if "Próxima Ação" in col_map and col_map["Próxima Ação"] < len(row) else "Aguardando início"

                job_hash = DeduplicationEngine.generate_job_hash(empresa, titulo, localizacao, url)

                job = JobOpportunity(
                    id=job_hash,
                    titulo=titulo,
                    empresa=empresa,
                    localizacao=localizacao,
                    modalidade=modalidade,
                    salario=salario,
                    data_publicacao=data_pub,
                    coletado_em=data_busca or datetime.now().strftime("%Y-%m-%d %H:%M"),
                    url=url,
                    fonte=fonte,
                    score=score,
                    classificacao=classificacao,
                    pontos_fortes=[s for s in skills if s and s != "-"],
                    oportunidades_desenvolvimento=[d for d in dev if d and d != "-"],
                    status_candidatura=status_candidatura,
                    data_tentativa=data_tentativa,
                    etapa_alcancada=etapa_alcancada,
                    campos_pendentes=campos_pendentes,
                    proxima_acao=proxima_acao
                )
                existing_jobs.append(job)

        except Exception as e:
            print(f"Aviso ao ler planilha existente: {e}")

        return existing_jobs

    def sync_and_save(self, new_jobs: List[JobOpportunity], file_path: str = None) -> Tuple[int, int, str]:
        """Mescla vagas inéditas com as já existentes na planilha, ordenando por Fit Score.
        Retorna (total_vagas_na_planilha, novas_inseridas, caminho_do_arquivo).
        """
        target_file = file_path or self.default_file

        # 1. Ler vagas pré-existentes na planilha
        existing_jobs = self.read_existing_jobs(target_file)
        existing_hashes: Set[str] = {
            j.id or DeduplicationEngine.generate_job_hash(j.empresa, j.titulo, j.localizacao, j.url)
            for j in existing_jobs
        }

        # 2. Filtrar apenas as vagas verdadeiramente novas
        truly_new_jobs: List[JobOpportunity] = []
        for job in new_jobs:
            if not job.id:
                job.id = DeduplicationEngine.generate_job_hash(job.empresa, job.titulo, job.localizacao, job.url)
            
            if job.id not in existing_hashes:
                existing_hashes.add(job.id)
                truly_new_jobs.append(job)

        # 3. Consolidar todas as vagas (antigas + novas)
        all_consolidated_jobs = existing_jobs + truly_new_jobs
        # Ordenar cronologicamente das mais recentes para as mais antigas, com desempate por maior Fit Score
        all_consolidated_jobs.sort(
            key=lambda x: (str(x.data_busca or x.data_publicacao or ""), x.score),
            reverse=True
        )

        # 4. Criar / Atualizar o Workbook formatado
        wb = openpyxl.Workbook()
        ws_jobs = wb.active
        ws_jobs.title = "🎯 Vagas Recomendadas"

        # Estilos visuais
        header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        border_thin = Border(
            left=Side(style='thin', color='E0E0E0'),
            right=Side(style='thin', color='E0E0E0'),
            top=Side(style='thin', color='E0E0E0'),
            bottom=Side(style='thin', color='E0E0E0')
        )

        headers = [
            "Rank", "Score (%)", "Prioridade", "Cargo", "Empresa", "Modalidade",
            "Localização", "Salário", "Data Publicação", "Data da Busca",
            "Skills Encontradas", "Oportunidades Desenvolvimento", "Fonte", "Link da Vaga",
            "Status Candidatura", "Data da Tentativa", "Etapa Alcançada", "Campos Pendentes", "Próxima Ação"
        ]

        for col_num, header_title in enumerate(headers, 1):
            cell = ws_jobs.cell(row=1, column=col_num, value=header_title)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        ws_jobs.row_dimensions[1].height = 28

        for row_idx, job in enumerate(all_consolidated_jobs, 2):
            # Rank
            ws_jobs.cell(row=row_idx, column=1, value=row_idx - 1).alignment = Alignment(horizontal="center")
            
            # Score
            score_cell = ws_jobs.cell(row=row_idx, column=2, value=f"{job.score:.1f}%")
            score_cell.alignment = Alignment(horizontal="center")
            score_cell.font = Font(bold=True)
            if job.score >= 80:
                score_cell.fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid") # Verde
                score_cell.font = Font(color="006100", bold=True)
            elif job.score >= 65:
                score_cell.fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid") # Amarelo
                score_cell.font = Font(color="9C6500", bold=True)
            else:
                score_cell.fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")

            # Prioridade
            ws_jobs.cell(row=row_idx, column=3, value=job.classificacao)

            # Cargo e Empresa
            ws_jobs.cell(row=row_idx, column=4, value=job.titulo).font = Font(bold=True)
            ws_jobs.cell(row=row_idx, column=5, value=job.empresa)

            # Modalidade
            ws_jobs.cell(row=row_idx, column=6, value=job.modalidade).alignment = Alignment(horizontal="center")
            
            # Localização
            ws_jobs.cell(row=row_idx, column=7, value=job.localizacao)
            
            # Salário
            ws_jobs.cell(row=row_idx, column=8, value=job.salario or "A combinar").alignment = Alignment(horizontal="center")
            
            # Data de Publicação e Data da Busca
            ws_jobs.cell(row=row_idx, column=9, value=job.data_publicacao or "Recente").alignment = Alignment(horizontal="center")
            data_busca_str = job.coletado_em[:10] if job.coletado_em else datetime.now().strftime("%Y-%m-%d")
            ws_jobs.cell(row=row_idx, column=10, value=data_busca_str).alignment = Alignment(horizontal="center")
            
            # Skills e Desenvolvimento
            ws_jobs.cell(row=row_idx, column=11, value=", ".join(job.pontos_fortes) if job.pontos_fortes else "-")
            ws_jobs.cell(row=row_idx, column=12, value=", ".join(job.oportunidades_desenvolvimento) if job.oportunidades_desenvolvimento else "-")
            
            # Fonte
            ws_jobs.cell(row=row_idx, column=13, value=job.fonte).alignment = Alignment(horizontal="center")

            # Link Clicável Preservado
            link_cell = ws_jobs.cell(row=row_idx, column=14, value="Acessar Vaga")
            link_cell.hyperlink = job.url
            link_cell.font = Font(color="0563C1", underline="single", bold=True)
            link_cell.alignment = Alignment(horizontal="center")

            # Status Candidatura e Acompanhamento
            status_val = job.status_candidatura or "Não iniciada"
            st_cell = ws_jobs.cell(row=row_idx, column=15, value=status_val)
            st_cell.alignment = Alignment(horizontal="center")
            if status_val == "Enviada":
                st_cell.fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
                st_cell.font = Font(color="006100", bold=True)
            elif status_val == "Aguardando minha revisão":
                st_cell.fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
                st_cell.font = Font(color="9C6500", bold=True)
            elif status_val == "Candidatura em preenchimento":
                st_cell.fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
            elif status_val in ["Bloqueada ou exige ação manual", "Link inválido"]:
                st_cell.fill = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")

            ws_jobs.cell(row=row_idx, column=16, value=job.data_tentativa or "-").alignment = Alignment(horizontal="center")
            ws_jobs.cell(row=row_idx, column=17, value=job.etapa_alcancada or "Nenhuma")
            ws_jobs.cell(row=row_idx, column=18, value=job.campos_pendentes or "-")
            ws_jobs.cell(row=row_idx, column=19, value=job.proxima_acao or "Aguardando início")

            for c in range(1, 20):
                ws_jobs.cell(row=row_idx, column=c).border = border_thin
            ws_jobs.row_dimensions[row_idx].height = 20

        # Aba de Recrutadores
        ws_rec = wb.create_sheet(title="👥 Recrutadores")
        rec_headers = [
            "Empresa", "Vaga Relacionada", "Nome do Contato", "Cargo / Título",
            "Localidade", "Tipo de Contato", "Link do Perfil LinkedIn", "Mapeado Em"
        ]
        rec_fill = PatternFill(start_color="333f48", end_color="333f48", fill_type="solid")
        for col_num, h_title in enumerate(rec_headers, 1):
            cell = ws_rec.cell(row=1, column=col_num, value=h_title)
            cell.fill = rec_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
        ws_rec.row_dimensions[1].height = 28

        # Ajuste de largura das colunas
        for ws in [ws_jobs, ws_rec]:
            for col in ws.columns:
                max_len = max(len(str(cell.value or '')) for cell in col)
                col_letter = get_column_letter(col[0].column)
                ws.column_dimensions[col_letter].width = min(max(max_len + 4, 12), 45)

        saved_file = self._safe_save_workbook(wb, target_file)
        return len(all_consolidated_jobs), len(truly_new_jobs), saved_file

    # ------------------------------------------------------------------
    # Sincronização de Recrutadores
    # ------------------------------------------------------------------

    def read_existing_recruiters(self, file_path: str = None) -> List[Dict[str, Any]]:
        """Lê os recrutadores já cadastrados na aba '👥 Recrutadores'."""
        target_file = file_path or self.default_file
        if not os.path.exists(target_file):
            return []

        existing: List[Dict[str, Any]] = []
        try:
            wb = self._safe_load_workbook(target_file, data_only=False)
            if "👥 Recrutadores" not in wb.sheetnames:
                return []

            ws = wb["👥 Recrutadores"]
            headers = [cell.value for cell in ws[1]]
            col_map = {name: idx for idx, name in enumerate(headers) if name}

            for row in ws.iter_rows(min_row=2, values_only=False):
                if not row:
                    continue
                empresa_cell = row[col_map.get("Empresa", 0)]
                if not empresa_cell.value:
                    continue

                # Extrair URL do hyperlink ou valor da célula
                url_cell = row[col_map.get("Link do Perfil LinkedIn", 6)]
                url = url_cell.hyperlink.target if url_cell.hyperlink else str(url_cell.value or "")

                existing.append({
                    "empresa": str(empresa_cell.value or ""),
                    "vaga_relacionada": str(row[col_map.get("Vaga Relacionada", 1)].value or ""),
                    "nome": str(row[col_map.get("Nome do Contato", 2)].value or ""),
                    "cargo": str(row[col_map.get("Cargo / Título", 3)].value or ""),
                    "localidade": str(row[col_map.get("Localidade", 4)].value or ""),
                    "tipo_contato": str(row[col_map.get("Tipo de Contato", 5)].value or ""),
                    "linkedin_url": url,
                    "mapeado_em": str(row[col_map.get("Mapeado Em", 7)].value or ""),
                    "prioridade": str(row[col_map.get("Prioridade", 8)].value or "Média") if col_map.get("Prioridade") is not None else "Média",
                })
        except Exception as exc:
            print(f"Aviso ao ler recrutadores existentes: {exc}")

        return existing

    def sync_recruiters(
        self, new_recruiters: List[Dict[str, Any]], file_path: str = None
    ) -> Tuple[int, int, str]:
        """Mescla novos recrutadores com os já cadastrados, evitando duplicatas.

        A deduplicação é feita pelo URL do perfil LinkedIn.
        Retorna (total_na_planilha, novos_inseridos, caminho_arquivo).
        """
        target_file = file_path or self.default_file

        # Verificar se planilha existe (deve ter sido criada pelo sync_and_save)
        if not os.path.exists(target_file):
            print("⚠ Planilha não encontrada. Execute sync_and_save primeiro.")
            return 0, 0, target_file

        existing = self.read_existing_recruiters(target_file)
        existing_urls = {r["linkedin_url"] for r in existing if r["linkedin_url"]}
        # Também deduplicar por empresa + nome (para perfis sem URL)
        existing_keys = {
            (r["empresa"].lower(), r["nome"].lower())
            for r in existing
            if r["empresa"] and r["nome"]
        }

        truly_new: List[Dict[str, Any]] = []
        for rec in new_recruiters:
            url = rec.get("linkedin_url", "")
            empresa = rec.get("empresa", "").lower()
            nome = rec.get("nome", "").lower()

            # Descartar duplicatas
            if url and url in existing_urls:
                continue
            if empresa and nome and (empresa, nome) in existing_keys:
                continue

            truly_new.append(rec)
            if url:
                existing_urls.add(url)
            if empresa and nome:
                existing_keys.add((empresa, nome))

        if not truly_new:
            return len(existing), 0, target_file

        # Carregar workbook existente e atualizar a aba de Recrutadores
        wb = self._safe_load_workbook(target_file)

        if "👥 Recrutadores" not in wb.sheetnames:
            ws_rec = wb.create_sheet(title="👥 Recrutadores")
            self._write_recruiter_header(ws_rec)
            start_row = 2
        else:
            ws_rec = wb["👥 Recrutadores"]
            # Encontrar próxima linha vazia
            start_row = ws_rec.max_row + 1
            if ws_rec.max_row == 1:
                start_row = 2

        # Estilos
        border_thin = Border(
            left=Side(style='thin', color='E0E0E0'),
            right=Side(style='thin', color='E0E0E0'),
            top=Side(style='thin', color='E0E0E0'),
            bottom=Side(style='thin', color='E0E0E0'),
        )
        fill_alta = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
        fill_media = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")

        for row_idx, rec in enumerate(truly_new, start_row):
            prioridade = rec.get("prioridade", "Média")

            ws_rec.cell(row=row_idx, column=1, value=rec.get("empresa", ""))
            ws_rec.cell(row=row_idx, column=2, value=rec.get("vaga_relacionada", ""))
            ws_rec.cell(row=row_idx, column=3, value=rec.get("nome", "")).font = Font(bold=True)
            ws_rec.cell(row=row_idx, column=4, value=rec.get("cargo", ""))
            ws_rec.cell(row=row_idx, column=5, value=rec.get("localidade", ""))
            ws_rec.cell(row=row_idx, column=6, value=rec.get("tipo_contato", ""))
            ws_rec.cell(row=row_idx, column=7, value=rec.get("mapeado_em", "")).alignment = Alignment(horizontal="center")

            # Prioridade com cor
            prio_cell = ws_rec.cell(row=row_idx, column=8, value=prioridade)
            prio_cell.alignment = Alignment(horizontal="center")
            if prioridade == "Alta":
                prio_cell.fill = fill_alta
                prio_cell.font = Font(color="006100", bold=True)
            else:
                prio_cell.fill = fill_media
                prio_cell.font = Font(color="9C6500", bold=True)

            # Link clicável do LinkedIn
            link_url = rec.get("linkedin_url", "")
            link_cell = ws_rec.cell(row=row_idx, column=9, value="Ver Perfil" if link_url else "—")
            if link_url:
                link_cell.hyperlink = link_url
                link_cell.font = Font(color="0563C1", underline="single")
            link_cell.alignment = Alignment(horizontal="center")

            # Bordas em toda a linha
            for c in range(1, 10):
                ws_rec.cell(row=row_idx, column=c).border = border_thin
            ws_rec.row_dimensions[row_idx].height = 20

        # Ajustar larguras
        for col in ws_rec.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws_rec.column_dimensions[col_letter].width = min(max(max_len + 4, 12), 45)

        saved_file = self._safe_save_workbook(wb, target_file)
        total = len(existing) + len(truly_new)
        return total, len(truly_new), saved_file

    def _write_recruiter_header(self, ws) -> None:
        """Escreve o cabeçalho formatado na aba de Recrutadores."""
        rec_headers = [
            "Empresa", "Vaga Relacionada", "Nome do Contato", "Cargo / Título",
            "Localidade", "Tipo de Contato", "Mapeado Em", "Prioridade",
            "Link do Perfil LinkedIn",
        ]
        header_fill = PatternFill(start_color="333f48", end_color="333f48", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        for col_num, h_title in enumerate(rec_headers, 1):
            cell = ws.cell(row=1, column=col_num, value=h_title)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[1].height = 28

    def update_application_status(
        self,
        job_url: str,
        status: str,
        etapa: str = "Nenhuma",
        pendentes: str = "-",
        proxima_acao: str = "Aguardando início",
        file_path: str = None
    ) -> bool:
        """Atualiza os campos de acompanhamento de candidatura diretamente na linha correspondente da planilha."""
        target_file = file_path or self.default_file
        if not os.path.exists(target_file):
            return False

        try:
            wb = openpyxl.load_workbook(target_file, data_only=False)
            if "🎯 Vagas Recomendadas" not in wb.sheetnames:
                return False
            ws = wb["🎯 Vagas Recomendadas"]
            headers = [cell.value for cell in ws[1]]
            col_map = {name: idx for idx, name in enumerate(headers) if name}

            # Garantir que os cabeçalhos de acompanhamento de candidatura existam na linha 1
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

            link_col_idx = col_map.get("Link da Vaga", 13) + 1

            found = False
            for row_idx in range(2, ws.max_row + 1):
                cell = ws.cell(row=row_idx, column=link_col_idx)
                target_url = cell.hyperlink.target if cell.hyperlink else str(cell.value or "")
                if job_url in target_url or (target_url and target_url in job_url):
                    found = True
                    st_cell = ws.cell(row=row_idx, column=15, value=status)
                    ws.cell(row=row_idx, column=16, value=datetime.now().strftime("%Y-%m-%d %H:%M")).alignment = Alignment(horizontal="center")
                    ws.cell(row=row_idx, column=17, value=etapa)
                    ws.cell(row=row_idx, column=18, value=pendentes)
                    ws.cell(row=row_idx, column=19, value=proxima_acao)

                    for c in range(15, 20):
                        ws.cell(row=row_idx, column=c).border = border_thin

                    # Cores dinâmicas para o status
                    st_cell.alignment = Alignment(horizontal="center")
                    if status == "Enviada":
                        st_cell.fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
                        st_cell.font = Font(color="006100", bold=True)
                    elif status == "Aguardando minha revisão":
                        st_cell.fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
                        st_cell.font = Font(color="9C6500", bold=True)
                    elif status == "Candidatura em preenchimento":
                        st_cell.fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
                    elif status in ["Bloqueada ou exige ação manual", "Link inválido"]:
                        st_cell.fill = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")
                        st_cell.font = Font(color="C00000", bold=True)
                    break

            if found:
                wb.save(target_file)
                return True
        except PermissionError:
            print("⚠ Atenção: A planilha está aberta no Excel. Salve e feche para gravar o status.")
        except Exception as e:
            print(f"Aviso ao atualizar status de candidatura na planilha: {e}")
        return False

