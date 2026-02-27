#!/usr/bin/env python3
"""
Script de deploy automático do DB Sentinel para o GitHub.
Execute: python3 deploy.py
"""

import subprocess, sys, base64, json, urllib.request, urllib.error, os

# TOKEN deve ser configurado como variável de ambiente GITHUB_TOKEN
TOKEN    = os.getenv("GITHUB_TOKEN")
REPO     = "db-sentinel"
HEADERS  = {
    "Authorization": f"token {TOKEN}" if TOKEN else "",
    "Accept": "application/vnd.github.v3+json",
    "Content-Type": "application/json",
    "User-Agent": "DBSentinel-Deploy"
}

def gh(method, path, data=None):
    url = f"https://api.github.com{path}"
    body = json.dumps(data).encode() if data else None
    req  = urllib.request.Request(url, data=body, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read()), r.status
    except urllib.error.HTTPError as e:
        return json.loads(e.read()), e.code

def encode(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

print("DB Sentinel - Deploy Automatico")
print("=" * 40)

# 1. Verificar usuário
user, status = gh("GET", "/user")
if status != 200:
    print(f"Error: Token invalido. Status: {status}")
    sys.exit(1)
username = user["login"]
print(f"OK: Autenticado como: {username}")

# 2. Criar repositório
print(f"Dir: Criando repositorio '{REPO}'...")
repo, status = gh("POST", "/user/repos", {
    "name": REPO, "description": "DB Sentinel - Intelligent Database Monitoring",
    "private": False, "auto_init": False
})
if status in (201, 422):
    if status == 422:
        print(f"Info: Repositorio ja existe, continuando...")
    else:
        print(f"OK: Repositorio criado: https://github.com/{username}/{REPO}")
else:
    print(f"Error: Erro ao criar repo: {status}")
    sys.exit(1)

# 3. Upload dos arquivos
files = {"app.py": "app.py", "requirements.txt": "requirements.txt"}
for fname, fpath in files.items():
    print(f"Push: Enviando {fname}...")
    # verificar se já existe para pegar SHA
    existing, s = gh("GET", f"/repos/{username}/{REPO}/contents/{fname}")
    sha = existing.get("sha") if s == 200 else None
    payload = {
        "message": f"Add {fname}",
        "content": encode(fpath),
        **({"sha": sha} if sha else {})
    }
    _, s2 = gh("PUT", f"/repos/{username}/{REPO}/contents/{fname}", payload)
    if s2 in (200, 201):
        print(f"   OK: {fname} enviado!")
    else:
        print(f"   Error: Erro ao enviar {fname}: {s2}")

print()
print("Deploy concluido!")
print(f"Repo: https://github.com/{username}/{REPO}")
print()
print("-" * 40)
print("PROXIMO PASSO - Publicar no Streamlit Cloud:")
print("1. Acesse: https://share.streamlit.io")
print("2. Clique em 'New app'")
print(f"3. Repositorio: {username}/{REPO}")
print("4. Branch: main | Main file: app.py")
print("5. Clique 'Deploy!'")
print()
print(f"URL: https://{username}-{REPO}.streamlit.app")
