import sys, json, os
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')

from agents.recruiter_hunter import RecruiterHunterAgent

with open('data/dry_run_results.json', encoding='utf-8') as f:
    results = json.load(f)

# Filtrar vagas com Alta Aderencia
qualified = [r for r in results if float(r.get('score','0%').replace('%','')) >= 65]
print(f'Vagas qualificadas (score >= 65%): {len(qualified)}')

companies = []
seen = set()
for r in qualified[:3]:
    emp = r['empresa'].strip()
    if emp.lower() not in seen:
        seen.add(emp.lower())
        cargo_preview = r['cargo'][:50]
        companies.append({'empresa': emp, 'vaga_relacionada': r['cargo']})
        print(f'  - {emp} | {cargo_preview}')

print()
agent = RecruiterHunterAgent()
recruiters = agent.find_recruiters_for_companies(companies)

print(f'\nTotal recrutadores encontrados: {len(recruiters)}')
for rec in recruiters:
    nome = rec.get("nome", "—")
    cargo = rec.get("cargo", "—")
    empresa = rec.get("empresa", "—")
    prior = rec.get("prioridade", "—")
    url = rec.get("linkedin_url", "—")
    print(f'  [{prior}] {nome} | {cargo} | {empresa}')
    print(f'         {url}')
