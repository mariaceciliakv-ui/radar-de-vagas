import os
import json
import re
import sys

def test_web_dashboard():
    print("Iniciando auditoria técnica do Dashboard Web (Front-End)...")
    
    # 1. Verifica existência dos arquivos
    assert os.path.exists("index.html"), "index.html não encontrado na raiz!"
    assert os.path.exists("docs/index.html"), "docs/index.html não encontrado na pasta docs/!"
    
    root_size = os.path.getsize("index.html")
    docs_size = os.path.getsize("docs/index.html")
    print(f"✓ Arquivos encontrados (Raiz: {root_size:,} bytes | Docs: {docs_size:,} bytes)")
    assert root_size == docs_size, "Tamanho dos arquivos index.html diferem!"
    assert root_size > 500_000, "Arquivo HTML parece incompleto (< 500KB)"
    
    with open("index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
        
    # 2. Verifica IDs cruciais no DOM
    required_ids = [
        "tab-jobs", "tab-resume", "tab-multiarea", "tab-recruiters", "tab-analytics", "tab-architecture",
        "searchInput", "sortSelect", "modalidadeSelect", "scoreSelect", "statusSelect",
        "jobsTableBody", "paginationControls", "paginationInfo",
        "simulatedScoreText", "simulatedProgressBar", "skillsCheckboxes", "bulletPointsContainer",
        "resumeAreaSelect", "atsCardsContainer", "hunterAreaSelect", "hunterLocationInput", "hunterCompanyInput",
        "jobModal", "modalContent"
    ]
    for element_id in required_ids:
        assert f'id="{element_id}"' in html_content, f"Elemento com id='{element_id}' não encontrado no HTML!"
    print(f"✓ Todos os {len(required_ids)} elementos interativos essenciais do DOM foram verificados!")
    
    # 3. Extrai e valida o JSON embarcado RADAR_DATA
    match = re.search(r'const RADAR_DATA\s*=\s*(\{.*?\});\s*(?:let|const|var|\/\/|function)', html_content, re.DOTALL)
    assert match, "Declaração const RADAR_DATA não encontrada ou mal formatada!"
    
    json_str = match.group(1)
    data = json.loads(json_str)
    
    jobs = data.get("jobs", [])
    recruiters = data.get("recruiters", [])
    stats = data.get("stats", {})
    
    print(f"✓ JSON embarcado íntegro: {len(jobs)} vagas | {len(recruiters)} recrutadores")
    assert len(jobs) >= 2000, f"Quantidade de vagas abaixo do esperado: {len(jobs)}"
    assert len(recruiters) >= 30, f"Quantidade de recrutadores abaixo do esperado: {len(recruiters)}"
    assert stats.get("total_jobs") == len(jobs), "Estatísticas de vagas divergentes!"
    
    # 4. Verifica ordenação cronológica decrescente dos dados exportados
    first_job_date = jobs[0].get("data_busca") or jobs[0].get("data_pub")
    last_job_date = jobs[-1].get("data_busca") or jobs[-1].get("data_pub")
    print(f"✓ Data da primeira vaga: {first_job_date} | Data da última vaga: {last_job_date}")
    assert first_job_date >= last_job_date, "Vagas não estão ordenadas cronologicamente de forma decrescente!"
    
    # 5. Verifica funções JavaScript essenciais
    required_functions = [
        "switchTab", "sortJobs", "handleFilterChange", "renderJobs", "setQuickPill",
        "initResumeOptimizer", "recalculateSimulator", "renderBulletPoints", "copyText",
        "updateHunterQueries", "updateRecruiterDork", "launchRecruiterDork",
        "openJobModal", "closeModal", "closeModalOnBackdrop", "downloadJSON"
    ]
    for func in required_functions:
        assert f"function {func}" in html_content, f"Função JS '{func}' não encontrada no script!"
    print(f"✓ Todas as {len(required_functions)} funções JavaScript foram auditadas e estão presentes!")
    
    print("\n🎉 AUDITORIA CONCLUÍDA COM 100% DE SUCESSO! DASHBOARD WEB PRONTO PARA PRODUÇÃO.")

if __name__ == "__main__":
    test_web_dashboard()
