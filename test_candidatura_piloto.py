"""Script de Teste Piloto Unitário para Candidatura Assistida (1 Vaga).

Executa a leitura da planilha, seleciona a vaga mais relevante e recente não processada,
inspeciona os requisitos e apresenta o mapeamento exato dos campos que serão preenchidos
com os dados oficiais de Maria Cecília Jesus Oliveira.
"""

import sys
import os

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.abspath("."))

from agents.applicant import ApplicationAgent


def run_pilot_test():
    print("=" * 76)
    print("  🚀 RADAR DE VAGAS — TESTE PILOTO DE CANDIDATURA ASSISTIDA")
    print("=" * 76)

    agent = ApplicationAgent()
    pending = agent.get_pending_jobs(limit=1)

    if not pending:
        print("Nenhuma vaga pendente encontrada na planilha!")
        return

    job = pending[0]
    inspection = agent.inspect_job_url(job)
    draft = agent.prepare_application_draft(job)

    print(f"\n📍 VAGA SELECIONADA PARA O TESTE PILOTO:")
    print(f"  • Cargo       : {job.titulo}")
    print(f"  • Empresa     : {job.empresa}")
    print(f"  • Modalidade  : {job.modalidade}")
    print(f"  • Localização : {job.localizacao}")
    print(f"  • Score       : {job.score:.1f}% ({job.classificacao})")
    print(f"  • Plataforma  : {inspection['plataforma']}")
    print(f"  • Link Oficial: {job.url}")

    print("\n🔍 ANÁLISE DE SEGURANÇA E ACESSO:")
    print(f"  • Link válido?       : {'Sim' if inspection['valido'] else 'Não'}")
    print(f"  • Tipo de processo   : {inspection['tipo_processo']}")
    for obs in inspection["observacoes"]:
        print(f"  • Observação         : {obs}")

    print("\n📝 CAMPOS MAPEADOS PARA PREENCHIMENTO (ZERO ALUCINAÇÃO):")
    pessoais = draft["dados_pessoais"]
    print(f"  [1] Nome Completo     : {pessoais['nome_completo']}")
    print(f"  [2] E-mail            : {pessoais['email']}")
    print(f"  [3] Telefones         : {pessoais['telefone_principal']} / {pessoais['telefone_secundario']}")
    print(f"  [4] Localização / CEP : {pessoais['localizacao']} | CEP: {pessoais['cep']}")
    print(f"  [5] CNH               : {pessoais['cnh']}")
    print(f"  [6] LinkedIn          : {draft['links_profissionais']['linkedin']}")
    print(f"  [7] Portfólio/Site    : {draft['links_profissionais']['portfolio_site']}")
    print(f"  [8] Currículo Anexo   : {'Aprovado e Disponível (curriculo_maria_cecilia_oliveira.pdf)' if draft['curriculo_anexo_disponivel'] else 'Pendente de arquivo'}")

    print("\n🎓 FORMAÇÃO & HISTÓRICO MAPEADO:")
    print(f"  • Graduação 1 : Bacharelado em Administração (UNOPAR - Concluído)")
    print(f"  • Graduação 2 : Tecnólogo em Logística (UNOPAR - Concluído)")
    print(f"  • Graduação 3 : Tecnólogo em Comércio Exterior (FATEC Indaiatuba - Cursando)")
    print(f"  • Pós/MBA     : MBA em Análise de Dados e Inteligência Artificial")
    print(f"  • Experiência : Aperam Serviços e Soluções (Key User SAP, CRM, Processos)")
    print(f"  • Experiência : Claudinha Lanches (Subgerente Operacional, Dashboards, Gestão)")

    print("\n🛡️ PONTOS DE ATENÇÃO / INTERVENÇÃO HUMANA OBRIGATÓRIA:")
    for bloq in draft["campos_bloqueados_ou_requeridos"]:
        print(f"  ⚠️  {bloq}")

    # Atualizar planilha para registrar o início da análise
    print("\n💾 ATUALIZANDO STATUS NA PLANILHA...")
    sucesso = agent.update_job_status(
        job_url=job.url,
        status=agent.STATUS_AGUARDANDO_REVISAO,
        etapa="Inspeção e Mapeamento de Campos Concluído",
        pendentes="Aguardando autorização da usuária para submissão",
        proxima_acao="Usuária validar campos e autorizar envio"
    )

    if sucesso:
        print("  ✅ Planilha atualizada com sucesso! Linha marcada como 'Aguardando minha revisão'.")
    else:
        print("  ℹ️ Não foi possível gravar na planilha (pode estar aberta no Excel).")

    print("\n" + "=" * 76)
    print("  ✋ PARADA DE SEGURANÇA:")
    print("  Conforme as diretrizes, NENHUM formulário externo foi enviado.")
    print("  Aguardando autorização expressa para prosseguir com a interação externa.")
    print("=" * 76 + "\n")


if __name__ == "__main__":
    run_pilot_test()
