# 🚀 Guia de Publicação no GitHub Pages — Radar de Vagas

Este guia explica como colocar o **Dashboard Interativo do Radar de Vagas** no ar gratuitamente através do **GitHub Pages** e como utilizá-lo para divulgar seu projeto no LinkedIn, currículo e portfólio.

---

## 📁 Estrutura dos Arquivos Gerados

O gerador cria dois arquivos idênticos e 100% autônomos (HTML + CSS + JS em arquivo único):
* **`index.html`** (na raiz do repositório)
* **`docs/index.html`** (na pasta `docs/`)

Isso permite que você use qualquer uma das duas configurações de deploy padrão do GitHub Pages (raiz `/` ou `/docs`).

---

## ⚙️ Como Ativar o GitHub Pages (Passo a Passo)

1. Faça o commit e push dos arquivos para o seu repositório no GitHub:
   ```bash
   git add index.html docs/index.html export_web_dashboard.py
   git commit -m "feat: adiciona dashboard web interativo para GitHub Pages"
   git push origin main
   ```

2. No GitHub, acesse seu repositório:
   * Vá em **Settings** (Configurações) na barra superior do repositório.
   * No menu lateral esquerdo, clique em **Pages** (sob a seção *Code and automation*).

3. Na seção **Build and deployment**:
   * **Source**: Selecione `Deploy from a branch`.
   * **Branch**: Selecione a branch `main` (ou `master`).
   * **Folder**: Selecione `/ (root)` ou `/docs` (ambos funcionam!).
   * Clique em **Save**.

4. Pronto! Em cerca de 1 a 2 minutos, o GitHub irá gerar a URL pública:
   > `https://<seu-usuario>.github.io/RADAR-DE-VAGAS/`

---

## 🔄 Como Atualizar os Dados do Site no Futuro

Sempre que você rodar uma nova busca de vagas (`python buscar_vagas.py` ou `python run_full_goal.py`), o dashboard é sincronizado automaticamente!

Se quiser atualizar manualmente a qualquer momento, basta rodar:
```bash
python export_web_dashboard.py
```
E em seguida subir as alterações:
```bash
git add index.html docs/index.html
git commit -m "data: atualiza vagas do radar no dashboard"
git push
```

---

## 💼 Dicas para Postagem no LinkedIn / Portfólio

Para divulgar este projeto e atrair a atenção de recrutadores e gestores de tecnologia/dados:

### Exemplo de Pitch para Post:
> 🚀 **Construí um Radar Autônomo de Vagas & Recrutadores com IA!**
> 
> Para otimizar minha busca e entender a fundo a demanda real do mercado de dados e tecnologia, desenvolvi uma automação orientada a agentes em Python que:
> 
> 🔎 Monitora em tempo real LinkedIn, Indeed, Glassdoor e Gupy;  
> 🧠 Calcula algoritmamente a aderência de cada oportunidade (Fit Score 0–100%) com base nas competências requeridas;  
> 👥 Mapeia automaticamente profissionais de Talent Acquisition das empresas com maior afinidade;  
> 📊 Consolida tudo em um Dashboard interativo open-source.
> 
> 🔗 Acesse o Dashboard interativo ao vivo: `https://<seu-usuario>.github.io/RADAR-DE-VAGAS/`  
> 💻 Código-fonte completo: `https://github.com/<seu-usuario>/RADAR-DE-VAGAS`  
> 
> #Python #DataAnalytics #FrontEnd #Automation #TechCareer
