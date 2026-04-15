# Configuração GitHub — ETL Oracle → JSON → Dashboard

## Estrutura do Projeto

```
DB_JasonGitHub/
├── .github/
│   └── workflows/
│       └── etl.yml                        ← workflow do GitHub Actions
├── data/
│   ├── queries/                           ← todas as queries SQL
│   │   ├── saldocontabil_funcao_subfuncao.sql
│   │   ├── RECEITA.sql
│   │   ├── DESPESA.sql
│   │   └── CREDITOS_ADICIONAIS.sql
│   └── *.json                             ← gerados pelo ETL localmente (não sobem ao git)
│                                            publicados na GitHub Release dados-etl
├── balanco_orcamentario/
│   ├── index.html
│   ├── receita_orcamentaria.html
│   └── despesa_orcamentaria.html
├── funcao-subfuncao/
│   └── index.html
├── index.html                             ← página inicial com menu
├── etl.py
├── requirements.txt
├── .gitignore                             ← contém .env
└── .env                                   ← credenciais locais (não sobe ao GitHub)
```

---

## Passo 1 — Criar o repositório no GitHub

1. Acesse https://github.com/new
2. Dê um nome ao repositório (ex: `db-dashboard-gdf`)
3. Visibilidade: **Public** (necessário para GitHub Pages gratuito) ou **Private** (requer plano pago para Pages)
4. Clique em **Create repository** — sem marcar README, .gitignore ou licença

---

## Passo 2 — Configurar os Secrets (credenciais do banco)

No repositório: **Settings → Secrets and variables → Actions → New repository secret**

| Nome do Secret           | Valor                        |
|--------------------------|------------------------------|
| `DB_USER`                | usuário Oracle               |
| `DB_PASSWORD`            | senha Oracle                 |
| `DB_DSN`                 | `10.69.1.118:1521/oraprd06`  |
| `DB_MIN_CONNECTIONS`     | `1`                          |
| `DB_MAX_CONNECTIONS`     | `5`                          |
| `DB_INCREMENT_CONNECTIONS` | `1`                        |

---

## Passo 3 — Instalar o Git (se não tiver)

Baixe em: https://git-scm.com/download/win

Após instalar, feche e reabra o PowerShell. Confirme com:
```powershell
git --version
```

---

## Passo 4 — Subir o código (primeiro push)

Abrir PowerShell dentro da pasta do projeto e rodar:

```powershell
git init
git branch -M main
git remote add origin https://github.com/contadoria2026/db-dashboard-gdf.git
git add .
git commit -m "feat: setup inicial ETL Oracle → JSON"
git push -u origin main
```

### Se o remote já existir com URL errada:
```powershell
git remote set-url origin https://github.com/contadoria2026/db-dashboard-gdf.git
git remote -v   # confirma a URL
git push -u origin main
```

---

## Passo 5 — Habilitar GitHub Pages

**Settings → Pages → Source → Deploy from a branch**

- Branch: `main`
- Folder: `/ (root)`
- Clicar em **Save**

Dashboard ficará em: `https://contadoria2026.github.io/db-dashboard-gdf/`

### ⚠️ Pages não aparece no menu?

Causa mais comum: repositório **Private** em conta gratuita.

**Solução A — Tornar público:**
Settings → General → rolar até o fim → "Change visibility" → "Make public"

**Solução B — Usar GitHub Pro** (conta paga) para manter privado com Pages ativo.

> Dados do GDF são públicos — repositório público é aceitável na maioria dos casos.

---

## Passo 6 — Testar o workflow manualmente

No repositório: **Actions → ETL Oracle → JSON → Run workflow**

Executa o ETL imediatamente sem esperar o agendamento (06h horário de Brasília).
Os logs aparecem em tempo real. Se tudo estiver correto, os JSONs são publicados
na GitHub Release `dados-etl` e os dashboards passam a lê-los automaticamente.

---

## Agendamento configurado (etl.yml)

```yaml
on:
  schedule:
    - cron: "0 9 * * *"   # Todo dia às 09:00 UTC = 06:00 Brasília
  workflow_dispatch:        # Permite rodar manualmente
```

---

## GitHub Release — Publicação dos JSONs sem limite de tamanho

### Por que usar?

O GitHub rejeita arquivos acima de 100 MB no repositório. Os JSONs gerados pelo ETL
(especialmente `despesa.json`) ultrapassam esse limite. A solução é publicá-los como
**assets de uma GitHub Release**, que suporta arquivos de até 2 GB em repositórios públicos.

Os dashboards passam a fazer `fetch()` direto da Release, sem depender dos arquivos
dentro do repositório.

```
Runner local
  → gera JSONs (qualquer tamanho)
  → gh release create dados-etl data/*.json
  → GitHub Release armazena os arquivos
  → Dashboard faz fetch() da Release URL
```

### URLs dos JSONs na Release

```
https://github.com/contadoria2026/db-dashboard-gdf/releases/latest/download/despesa.json
https://github.com/contadoria2026/db-dashboard-gdf/releases/latest/download/receita.json
https://github.com/contadoria2026/db-dashboard-gdf/releases/latest/download/creditos_adicionais.json
https://github.com/contadoria2026/db-dashboard-gdf/releases/latest/download/saldo_funcao_subfuncao.json
```

Todos os dashboards já estão apontados para essas URLs.

### Trecho do etl.yml responsável pela publicação

```yaml
- name: Publicar JSONs na GitHub Release
  env:
    GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
  shell: bash
  run: |
    gh release delete dados-etl --yes 2>/dev/null || true
    gh release create dados-etl \
      data/despesa.json \
      data/receita.json \
      data/creditos_adicionais.json \
      data/saldo_funcao_subfuncao.json \
      --title "Dados ETL $(date -u '+%Y-%m-%d %H:%M UTC')" \
      --notes "Atualizado automaticamente pelo ETL" \
      --latest
```

> `GITHUB_TOKEN` é fornecido automaticamente pelo GitHub Actions — não precisa configurar como Secret.

### O que é o `gh` CLI?

O `gh` é a **interface de linha de comando oficial do GitHub**. Ele permite interagir com o GitHub diretamente pelo terminal, sem precisar abrir o navegador.

No contexto deste projeto, ele é usado para criar e atualizar a GitHub Release com os JSONs gerados pelo ETL:

```bash
gh release delete dados-etl --yes          # apaga a release anterior
gh release create dados-etl data/*.json    # cria uma nova com os JSONs frescos
```

Sem o `gh`, seria necessário usar a API REST do GitHub manualmente com `curl` e tokens — bem mais trabalhoso.

**Dentro do GitHub Actions** o `gh` funciona sem configuração extra: o GitHub Actions injeta automaticamente o `GITHUB_TOKEN` — um token temporário com permissão para operar no repositório durante aquela execução. O `gh` usa esse token quando você define `GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}` no passo. Nenhum login manual é necessário na nuvem.

**Na máquina do runner local** é diferente: como o runner roda no Windows, o `gh` precisa ser instalado e autenticado uma vez. O `gh auth login` abre o navegador e vincula sua conta GitHub — depois disso fica salvo e o runner usa automaticamente em todas as execuções.

### ⚠️ Pré-requisito: `gh` CLI instalado na máquina do runner

Baixe em: https://cli.github.com

Após instalar, autentique uma vez:
```powershell
gh auth login
```

---

## Self-Hosted Runner — Acesso ao Oracle via rede privada

### Por que usar?

O GitHub Actions executa os workflows em servidores da nuvem, que não têm acesso à rede interna do GDF (`10.69.1.118`). A solução é instalar um **runner local** na máquina Windows que já tem acesso ao Oracle — o GitHub Actions passa a executar o ETL nessa máquina, dentro da rede privada.

```
GitHub Actions (nuvem)
        ↓  despacha job
Runner local (máquina Windows na rede do GDF)
        ↓  conecta via oracledb
Oracle 10.69.1.118:1521/oraprd06
        ↓  salva JSON
data/*.json  →  git push  →  GitHub Pages
```

---

### Passo 7 — Criar o runner no GitHub

No repositório: **Settings → Actions → Runners → New self-hosted runner**

- Sistema operacional: **Windows**
- Arquitetura: **x64**

Copie o token gerado — ele será usado no próximo passo (expira em 1 hora).

---

### Passo 8 — Instalar o runner na máquina local

Abrir **PowerShell como Administrador** e executar:

```powershell
# Criar pasta do runner
mkdir C:\actions-runner
cd C:\actions-runner

# Baixar o runner (versão mais recente — confira em github.com/actions/runner/releases)
Invoke-WebRequest -Uri https://github.com/actions/runner/releases/download/v2.322.0/actions-runner-win-x64-2.322.0.zip -OutFile actions-runner-win-x64.zip

# Extrair
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::ExtractToDirectory("$PWD\actions-runner-win-x64.zip", "$PWD")

# Configurar (substitua SEU_TOKEN pelo token copiado do GitHub)
.\config.cmd --url https://github.com/contadoria2026/db-dashboard-gdf --token SEU_TOKEN
```

Durante a configuração, aceite os padrões (Enter em tudo) ou dê um nome ao runner.

---

### Passo 9 — Instalar como serviço Windows (execução automática)

```powershell
# Ainda em C:\actions-runner como Administrador
.\svc.ps1 install
.\svc.ps1 start
```

O runner agora inicia automaticamente com o Windows e fica aguardando jobs.

Para verificar o status:
```powershell
.\svc.ps1 status
```

Para parar ou desinstalar:
```powershell
.\svc.ps1 stop
.\svc.ps1 uninstall
```

---

### Passo 10 — Verificar Python na máquina runner

O runner executa `pip install -r requirements.txt` e `python etl.py` diretamente. Confirme que o Python está no PATH:

```powershell
python --version
pip --version
```

Se não estiver, instale em https://python.org e marque **"Add Python to PATH"** durante a instalação.

---

### Passo 11 — Ajustar `etl.yml` para usar o runner local

O arquivo `.github/workflows/etl.yml` já está configurado com:

```yaml
jobs:
  etl:
    runs-on: self-hosted
```

Essa linha instrui o GitHub Actions a despachar o job para o runner local em vez dos servidores da nuvem.

---

### Passo 12 — Fazer push e testar

```powershell
git add .github/workflows/etl.yml
git commit -m "ci: configura self-hosted runner"
git push
```

Depois, no repositório: **Actions → ETL Oracle → JSON → Run workflow**

Acompanhe os logs em tempo real. Se tudo estiver correto, os JSONs serão publicados
na Release `dados-etl` e estarão acessíveis em:
`https://github.com/contadoria2026/db-dashboard-gdf/releases/tag/dados-etl`

---

### ⚠️ Observações importantes

| Ponto | Detalhe |
|-------|---------|
| **Máquina ligada** | O runner precisa estar rodando no horário agendado (06h Brasília). Se a máquina estiver desligada, o job é pulado. |
| **Sem `.env` no runner** | As credenciais vêm dos **Secrets** do GitHub (`DB_USER`, `DB_PASSWORD` etc.), não do `.env` local. |
| **`ORACLE_CLIENT_PATH`** | Se usar thick mode (Oracle Client instalado), configure esse Secret com o caminho da DLL (ex: `C:\oracle\instantclient_21_9`). Deixe em branco para thin mode. |
| **Tamanho dos JSONs** | Os JSONs são publicados via GitHub Release (até 2 GB), não commitados no repositório. O limite de 100 MB do git não se aplica. |
| **Segurança** | O runner executa código do repositório — mantenha o repositório privado ou restrinja quem pode abrir Pull Requests. |
