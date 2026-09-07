# PontuaLattes

Projeto de extensão desenvolvido na disciplina EXA618: Programação para Redes, da Universidade Estadual de Feira de Santana (UEFS).

Sistema que analisa o currículo Lattes e calcula automaticamente o barema para avaliação de candidatos a bolsas de **Iniciação Científica (IC)**, **Assessoria Especial de Relações Institucionais (AERI)** e **Extensão (PIBEX)** da UEFS.

- Repositório: [github.com/joaorochajr/PontuaLattes](https://github.com/joaorochajr/PontuaLattes)
- Planilha de backup: [Google Sheets](https://docs.google.com/spreadsheets/d/1f78in2E1nG3cuPPQq884jU1-7XRQxHvgEHYLU5SRNUo/edit?gid=149912474#gid=149912474)
- Desenvolvedores: Abel Galvão, Alex Júnior e Bruno Campos

---

## Sumário

1. [Visão geral](#visão-geral)
2. [Funcionalidades](#funcionalidades)
3. [Baremas suportados](#baremas-suportados)
4. [Estrutura do projeto](#estrutura-do-projeto)
5. [Como executar localmente](#como-executar-localmente)
6. [Banco de dados — Turso](#banco-de-dados--turso)
7. [Backup no Google Sheets](#backup-no-google-sheets)
8. [Deploy no Vercel](#deploy-no-vercel)

---

## Visão geral

O sistema recebe uma URL pública do currículo Lattes (ou apenas o código), consulta os dados públicos disponíveis no CNPq/Buscatextual, extrai indicadores bibliográficos e calcula automaticamente a pontuação do barema conforme as regras do edital selecionado (IC, AERI ou PIBEX).

O backend é um único servidor Python (`BaseHTTPRequestHandler`) que serve a SPA e expõe os endpoints da API. O banco de dados é o [Turso](https://turso.tech) (libSQL).

---

## Funcionalidades

- Consulta pública do barema sem necessidade de login
- Suporte a editais de **IC**, **AERI** e **PIBEX (Extensão)** com regras de pontuação distintas
- No PIBEX, escolha entre o barema do **docente/orientador** (Anexo II-A) e o do **discente/candidato** (Anexo II-B)
- Link dinâmico para o edital vigente configurável pelo dashboard
- Autenticação com token de sessão para acesso ao dashboard
- Histórico de consultas com paginação
- Dashboard administrativo para configurar URLs dos editais
- Interface web em SPA (HTML/CSS/JS puro, sem framework)
- **Backup automático no Google Sheets** a cada consulta bem-sucedida
- Endpoint `POST /api/sync-sheets` para sincronização manual sob demanda

---

## Baremas suportados

O edital escolhido na tela inicial define o `tipo` enviado à API e a tabela em que a pontuação é gravada.

| Opção na tela | `tipo` na API | Tabela no banco | Máximo | Período |
|---|---|---|---|---|
| Edital IC | `ic` | `barema` | 60 | últimos 5 anos |
| Edital AERI | `aeri` | `barema_aeri` | 40 | currículo completo |
| Edital PIBEX → Docente/Orientador | `extensao_docente` | `barema_extensao_docente` | 40 | currículo completo |
| Edital PIBEX → Discente/Candidato | `extensao_discente` | `barema_extensao_discente` | 20 | currículo completo |

### PIBEX — Anexo II do Edital PIBEX 01/2026 (PROEX/UEFS)

**A — Docente/Orientador (40 pontos)**

| Seção | Máximo | Origem |
|---|---|---|
| I — Titulação (maior titulação, não cumulativa) | 4 | Lattes |
| II — Atuação na extensão | 8 | preenchimento manual |
| III — Indicadores de produção científica, tecnológica e artística | 18 | Lattes |
| IV — Formação de recursos humanos (orientações concluídas) | 10 | Lattes |

**B — Discente/Candidato (20 pontos)**

| Seção | Máximo | Origem |
|---|---|---|
| I — Atuação na extensão (bolsista/voluntário) | 6 | preenchimento manual |
| II — Indicadores de produção científica, tecnológica e artística | 5 | Lattes |
| III — Participação/organização de eventos acadêmicos | 9 | preenchimento manual |

O item **C — Plano de Trabalho** (40 pontos) do edital é avaliação humana e não faz parte do sistema.

As seções marcadas como *preenchimento manual* aparecem na tela com todos os critérios e pesos do edital, porém zeradas: os gráficos públicos do Lattes não expõem projetos de extensão nem participação em eventos. O avaliador soma esses pontos manualmente e o sistema registra uma observação indicando isso.

Os pesos, critérios e tetos ficam concentrados nas constantes `_EXTENSAO_*` do arquivo `API/controller.py` — basta editá-las quando um novo edital mudar a pontuação.

---

## Estrutura do projeto

```
PontuaLattes/
├── API/
│   ├── main.py                # servidor HTTP, roteamento e endpoints
│   ├── controller.py          # lógica de scraping, cálculo dos baremas IC, AERI e PIBEX
│   ├── service.py             # coleta dos dados públicos do Lattes
│   ├── database.py            # fachada do banco (reexporta funções do turso_store)
│   ├── turso_store.py         # camada de persistência — Turso/libSQL
│   ├── local_store.py         # banco local em SQLite (usado sem TURSO_URL)
│   ├── google_sheets_store.py # camada de backup — Google Sheets
│   ├── sync_to_sheets.py      # script CLI para sincronização manual
│   └── requirements.txt       # dependências Python
├── SPA/
│   ├── index.html             # página principal — consulta do barema
│   ├── app.js                 # lógica da consulta e renderização do barema
│   ├── auth.js                # autenticação e sessão
│   ├── login.html             # formulário de login
│   ├── dashboard.html         # dashboard administrativo
│   ├── dashboard.js           # lógica do dashboard
│   └── styles.css             # estilos da interface
├── api/
│   ├── index.py               # entrypoint Vercel (importa ICCollectHandler)
│   └── requirements.txt       # dependências instaladas pelo Vercel
├── vercel.json                # configuração do deploy serverless
└── README.md
```

---

## Como executar localmente

### Pré-requisitos

- Python 3.10 ou superior
- Acesso à internet (para consultar o Lattes)

### Modo local — sem Turso (mais rápido)

Se a variável `TURSO_URL` não estiver definida, o sistema grava tudo em um arquivo SQLite
(`pontualattes.db`, criado na raiz do projeto). Não é preciso criar conta em lugar nenhum.

```bash
pip install requests
cd API
python main.py
```

Acesse `http://localhost:8000`. O terminal mostra um aviso de modo local com o caminho do
banco e as credenciais do dashboard.

O usuário do dashboard é `admin` e a senha vem de `DEFAULT_DASHBOARD_PASSWORD`
(vazia se a variável não for definida). Para escolher outro caminho de banco, use
`LOCAL_DB_PATH`.

No Windows (PowerShell), para definir a senha antes de subir:

```powershell
$env:DEFAULT_DASHBOARD_PASSWORD = "pontualattes"
cd API
python main.py
```

### Modo Turso (usado em produção)

#### 1. Clone o repositório

```bash
git clone https://github.com/argalvao/PontuaLattes.git
cd PontuaLattes
```

#### 2. Crie e ative o ambiente virtual

```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### 3. Instale as dependências

```bash
pip install -r API/requirements.txt
```

#### 4. Configure as variáveis de ambiente

Crie um arquivo `.env` na raiz do projeto:

```env
TURSO_URL=https://SEU-BANCO.turso.io
TURSO_AUTH_TOKEN=seu_token_aqui
DEFAULT_DASHBOARD_USERNAME=admin
DEFAULT_DASHBOARD_PASSWORD=sua_senha_aqui
HOST=0.0.0.0
PORT=8000

# Backup Google Sheets (opcional — veja seção específica)
GOOGLE_SHEETS_SPREADSHEET_ID=
GOOGLE_SERVICE_ACCOUNT_JSON=
```

#### 5. Inicie o servidor

```bash
cd API
env $(cat ../.env | grep -v '^#' | xargs) python3 main.py
```

Acesse em: `http://localhost:8000`

---

## Banco de dados — Turso

O projeto usa o [Turso](https://turso.tech) como banco de dados (SQLite distribuído) quando `TURSO_URL` está definida — é assim que roda em produção. Sem essa variável, ele cai automaticamente no modo local com SQLite em arquivo (veja a seção anterior). Siga os passos abaixo para criar sua própria instância gratuitamente.

### 1. Crie uma conta no Turso

Acesse https://turso.tech e cadastre-se com GitHub ou e-mail.

### 2. Instale a CLI do Turso

```bash
curl -sSfL https://get.tur.so/install.sh | bash
```

### 3. Faça login

```bash
turso auth login
```

### 4. Crie o banco de dados

```bash
turso db create pontualattes
```

### 5. Obtenha a URL do banco

```bash
turso db show pontualattes --url
# Exemplo: https://pontualattes-seuusuario.aws-us-east-1.turso.io
```

### 6. Gere o token de autenticação

```bash
turso db tokens create pontualattes
# Copie o token gerado — ele não será exibido novamente
```

### 7. Preencha o `.env`

```env
TURSO_URL=https://pontualattes-seuusuario.aws-us-east-1.turso.io
TURSO_AUTH_TOKEN=token_copiado_acima
```

As tabelas são criadas automaticamente na primeira execução (`turso_store.py`).

---

## Backup no Google Sheets

O sistema pode espelhar automaticamente todos os dados do Turso em uma planilha Google Sheets. A sincronização ocorre após cada consulta bem-sucedida ao Lattes e também pode ser disparada manualmente.

As seguintes abas são criadas/atualizadas na planilha:

| Aba | Conteúdo |
|---|---|
| `barema` | Pontuações do barema IC |
| `barema_aeri` | Pontuações do barema AERI |
| `barema_extensao_docente` | Pontuações do barema PIBEX (docente) |
| `barema_extensao_discente` | Pontuações do barema PIBEX (discente) |
| `consultas` | Histórico completo de consultas |
| `editais` | Editais cadastrados |

### 1. Crie um projeto no Google Cloud

Acesse https://console.cloud.google.com, crie um projeto e ative a **Google Sheets API** e a **Google Drive API**.

### 2. Crie uma Service Account

1. No menu lateral, vá em **IAM e administrador → Contas de serviço**
2. Clique em **Criar conta de serviço**, dê um nome e confirme
3. Na conta criada, vá na aba **Chaves → Adicionar chave → Criar nova chave → JSON**
4. Salve o arquivo `.json` gerado

### 3. Compartilhe a planilha com a Service Account

Abra a planilha no Google Sheets, clique em **Compartilhar** e adicione o e-mail da Service Account (termina em `@...gserviceaccount.com`) com permissão de **Editor**.

### 4. Configure as variáveis de ambiente

```env
# ID da planilha — parte final da URL:
# https://docs.google.com/spreadsheets/d/<ID>/edit
GOOGLE_SHEETS_SPREADSHEET_ID=seu_id_aqui

# Conteúdo completo do arquivo JSON da Service Account (em uma única linha)
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account",...}
```

> **Dica:** para evitar problemas com quebras de linha na variável de ambiente, você pode codificar o JSON em base64:
> ```bash
> base64 -w 0 service_account.json
> ```
> e colar o resultado em `GOOGLE_SERVICE_ACCOUNT_JSON`.

### 5. Sincronização manual via script

Para sincronizar sob demanda a partir da linha de comando:

```bash
cd API
env $(cat ../.env | grep -v '^#' | xargs) python3 sync_to_sheets.py
```

### 6. Sincronização manual via endpoint

Com o servidor rodando, faça um `POST /api/sync-sheets` autenticado:

```bash
curl -X POST https://seu-app.vercel.app/api/sync-sheets \
  -H "Authorization: Bearer SEU_TOKEN"
```

> Se as variáveis `GOOGLE_SHEETS_SPREADSHEET_ID` e `GOOGLE_SERVICE_ACCOUNT_JSON` não estiverem definidas, o backup é simplesmente ignorado — o sistema continua funcionando normalmente.

### Pré-requisitos

- Conta no [Vercel](https://vercel.com) (plano Hobby é suficiente)
- Repositório hospedado no GitHub
- Banco Turso configurado (seção anterior)

### 1. Acesse o Vercel e crie um novo projeto

Vá em https://vercel.com/new e clique em **Import Git Repository**.

Selecione o repositório `PontuaLattes` (ou o fork que você criou).

### 2. Configure o projeto

Na tela de configuração, use os seguintes valores:

| Campo | Valor |
|---|---|
| Framework Preset | **Other** |
| Root Directory | *(deixe em branco ou `./`)* |
| Build Command | *(deixe em branco)* |
| Output Directory | *(deixe em branco)* |

### 3. Adicione as variáveis de ambiente

Ainda na tela de configuração, clique em **Environment Variables** e adicione:

| Nome | Valor |
|---|---|
| `TURSO_URL` | URL do banco Turso |
| `TURSO_AUTH_TOKEN` | Token de autenticação do Turso |
| `DEFAULT_DASHBOARD_USERNAME` | Nome de usuário do dashboard (ex: `admin`) |
| `DEFAULT_DASHBOARD_PASSWORD` | Senha do dashboard |
| `GOOGLE_SHEETS_SPREADSHEET_ID` | *(opcional)* ID da planilha para backup |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | *(opcional)* JSON da Service Account (string ou base64) |

> **Atenção:** nunca comite o arquivo `.env` no repositório.

### 4. Faça o deploy

Clique em **Deploy**. O Vercel irá:

1. Clonar o repositório
2. Instalar as dependências de `api/requirements.txt`
3. Publicar `api/index.py` como função serverless Python
4. Rotear todas as requisições para essa função via `vercel.json`

### 5. Acesse a aplicação

Após o deploy bem-sucedido, o Vercel fornece uma URL no formato:

```
https://pontua-lattes-xxx.vercel.app
```

### Redeploy após mudanças

Qualquer `git push` para a branch `main` dispara um novo deploy automaticamente.

Para forçar um redeploy sem alterar código:

```bash
git commit --allow-empty -m "chore: redeploy" && git push origin main
```

### Limitações do plano Hobby

- Timeout máximo por requisição: **10 segundos**
- Currículos Lattes muito extensos podem ultrapassar esse limite
- Para eliminar o timeout, faça upgrade para o plano Pro e ajuste `maxDuration` em `vercel.json`

---

## Variáveis de ambiente — referência completa

| Variável | Obrigatória | Descrição |
|---|---|---|
| `TURSO_URL` | Não | URL do banco Turso (ex: `https://...turso.io`). Sem ela, o sistema usa SQLite local |
| `TURSO_AUTH_TOKEN` | Se `TURSO_URL` | Token JWT de autenticação do Turso |
| `DEFAULT_DASHBOARD_USERNAME` | Não | Usuário administrador criado na primeira inicialização (padrão: `admin`) |
| `DEFAULT_DASHBOARD_PASSWORD` | Não | Senha do usuário administrador (padrão: vazia) |
| `GOOGLE_SHEETS_SPREADSHEET_ID` | Não | ID da planilha Google Sheets para backup |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Não | JSON da Service Account (string direta ou base64) |
| `LOCAL_DB_PATH` | Não | Caminho do SQLite no modo local (padrão: `pontualattes.db` na raiz) |
| `HOST` | Não | Endereço de bind local (padrão: `0.0.0.0`) |
| `PORT` | Não | Porta local (padrão: `8000`) |

---

## Licença

Uso educacional — Projeto de extensão UEFS / EXA618.
