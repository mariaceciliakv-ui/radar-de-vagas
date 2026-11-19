"""Utilitário de Inicialização do Navegador para Login Manual.

Abre o Google Chrome no perfil persistente dedicado do Radar de Vagas
para que a usuária possa realizar o login manual no LinkedIn, Indeed e Gupy.

REGRAS RÍGIDAS DE SEGURANÇA:
1. O agente NÃO captura, NÃO solicita e NÃO armazena senhas ou códigos 2FA.
2. As sessões ficam salvas de forma nativa e criptografada pelo próprio Google Chrome.
3. Após o login, as próximas execuções do Radar reutilizarão essas sessões ativas.
"""

import sys
import os
import time
from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

PROFILE_DIR = os.path.abspath("data/browser_profile")
os.makedirs(PROFILE_DIR, exist_ok=True)


def check_auth_status(page, platform: str) -> bool:
    """Verifica se a plataforma está com sessão autenticada."""
    try:
        url = page.url.lower()
        content = page.content().lower()
        
        if platform == "indeed":
            if "entrar" not in content and ("sair" in content or "minha conta" in content or "gnav-account" in content):
                return True
            if "security check" in content or "bot-detection" in url:
                return False
        elif platform == "linkedin":
            if "feed" in url and "login" not in url and "authwall" not in url:
                return True
        elif platform == "gupy":
            if "candidato" in url or "dashboard" in url or "perfil" in url:
                return True
            if "login" not in url and "entrar" not in content:
                return True
    except Exception:
        pass
    return False


def run_login_helper():
    print("=" * 76)
    print("  🔐 RADAR DE VAGAS — AUTENTICAÇÃO MANUAL NO NAVEGADOR AUTORIZADO")
    print("=" * 76)
    print(f"Perfil de navegação persistente: {PROFILE_DIR}\n")
    print("INSTRUÇÕES:")
    print("1. O navegador Google Chrome será aberto na sua tela.")
    print("2. Faça o login manualmente nas plataformas desejadas (Indeed, LinkedIn, Gupy).")
    print("   - Você pode usar o botão 'Continuar com o Google' ou 'Entrar com o LinkedIn'.")
    print("3. O sistema NUNCA tem acesso a sua senha.")
    print("4. Quando terminar, volte a este terminal e pressione ENTER para validar as sessões.")
    print("=" * 76)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            channel="chrome",
            headless=False,
            args=["--start-maximized", "--no-first-run", "--no-default-browser-check"]
        )

        page_indeed = context.pages[0] if context.pages else context.new_page()
        page_indeed.goto("https://br.indeed.com/")

        page_li = context.new_page()
        page_li.goto("https://www.linkedin.com/login")

        page_gupy = context.new_page()
        page_gupy.goto("https://login.gupy.io/")

        print("\n🌐 Abas abertas: Indeed, LinkedIn e Gupy.")
        print("Aguardando você realizar o login no navegador aberto...")
        
        input("\n>>> Pressione [ENTER] quando tiver concluído o login no navegador... <<<")

        print("\nVerificando autenticação...")
        st_indeed = check_auth_status(page_indeed, "indeed")
        st_li = check_auth_status(page_li, "linkedin")
        st_gupy = check_auth_status(page_gupy, "gupy")

        print(f"  • Indeed   : {'🟢 Autenticado' if st_indeed else '🔴 Não Autenticado'}")
        print(f"  • LinkedIn : {'🟢 Autenticado' if st_li else '🔴 Não Autenticado'}")
        print(f"  • Gupy     : {'🟢 Autenticado' if st_gupy else '🔴 Não Autenticado'}")

        print("\nFechando navegador com as credenciais salvas no perfil seguro...")
        context.close()

    print("\n✅ Sessões registradas com sucesso no perfil local!")


if __name__ == "__main__":
    run_login_helper()
