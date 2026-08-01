# CLAUDE.md — Discovery Reviews

> Este arquivo é a constituição do projeto. O Claude Code lê ele a cada sessão.
> Regras aqui têm precedência sobre conveniência.

## O que é este projeto

Um motor que coleta reviews públicas de apps, extrai insights e oportunidades de
produto, e entrega um dashboard para um PM decidir. É um projeto **build-to-learn**
e peça de **portfólio** de Matheus Prais. Não afiliado a nenhum app analisado.

O caso inicial é o app **Hevy** (musculação), mas o sistema deve servir para
**qualquer app**.

---

## ⚠️ Regras inegociáveis (valem em TODA sessão)

1. **TDD é obrigatório.** Escreva os testes que falham ANTES de qualquer
   implementação. NÃO escreva código de produção até o Matheus aprovar os testes.
   Qualquer implementação sem teste será recusada.
2. **Alinhar antes de executar.** Proponha o plano e espere aprovação antes de
   criar ou editar arquivos (use plan mode). Este projeto valoriza discussão antes
   do build.
3. **Sem otimização prematura.** Nos dias de código (DIA 4), o foco é passar nos
   testes. Otimização, jobs e refactoring só no DIA 5.
4. **Governança de dados.** Só feed público, cadência baixa, sem burlar proteção
   anti-bot. Autor de review é PII → pseudonimizar. Segredos só em `.env` (nunca
   commitado). Ver `docs/governanca.md`.
5. **Honestidade metodológica.** Nunca fabricar métricas. A amostra de reviews é
   enviesada; código e relatórios devem deixar isso explícito.

---

## Decisões de arquitetura

- **Portas e adaptadores.** Uma interface neutra `ReviewSource` define o contrato de
  coleta. Hoje existe só `GooglePlaySource`. O adaptador de App Store entra depois,
  sem tocar no resto do sistema.
- **App-agnóstico + projeto de análise.** O sistema analisa qualquer app. Um
  "projeto de análise" tem um app **central** + N **concorrentes**. O motor trata
  todos igual; "central vs concorrente" é só um papel (flag). Apenas a montagem do
  relatório usa esse papel: a seção de concorrência é a mesma análise rodada nos
  concorrentes, pela ótica do app central.
- **Schema canônico neutro de plataforma.** Todo adaptador devolve o mesmo registro
  de review. É o que permite somar Google + App Store no futuro.

---

## Stack

- **Motor:** Python. Testes com **pytest**. Coleta com **google-play-scraper**.
- **Banco:** SQLite (arquivo único, simples) — suficiente para build-to-learn.
  Postgres fica como opção futura.
- **Enriquecimento:** LLM (Claude via API Anthropic) para rotular
  tema/sentimento/pedido-de-feature e canonicalizar nomes; agrupamento semântico por
  embeddings — biblioteca a definir no DIA 2/3 (recomendação: `sentence-transformers`
  local, grátis).
- **Dashboard:** HTML self-contained (dark, dourado #FFC000, Bebas Neue + Barlow —
  mesmo padrão do protótipo já feito). Lê os dados que o estágio de relatório gera.
- **Estrutura:** monorepo.
- **Idioma:** identificadores de código em **inglês** (padrão de portfólio
  internacional); texto de review preserva o idioma original; docs e comentários
  podem ser em português. (Se preferir tudo em pt, é só avisar.)

---

## Pipeline (5 estágios — cada um testável isolado)

1. **collect** — puxa reviews de um app via adaptador.
2. **normalize** — converte pro schema canônico, gera chave de dedup, remove
   repetidas entre execuções.
3. **enrich** — LLM rotula e agrupa queixas semelhantes em candidatos canônicos.
4. **store** — persiste no banco de forma idempotente.
5. **report** — agrega em insights + oportunidades e gera os dados do dashboard.

---

## Contrato de dado — Review canônica

Todo adaptador devolve este registro:

| campo | descrição |
|---|---|
| `dedup_id` | hash de plataforma+app+autor+data+texto |
| `platform` | `google_play` \| `app_store` |
| `app_id` | pacote / id da loja |
| `country` | storefront (ex.: `br`) |
| `rating` | 1–5 |
| `title` | título (pode ser vazio no Google Play) |
| `body` | texto da review |
| `author_hash` | **PII pseudonimizada** — nunca guardar autor cru |
| `app_version` | versão avaliada |
| `review_date` | ISO 8601 |
| `helpful_votes` | votos "útil" |
| `dev_reply` | resposta do desenvolvedor (texto ou nulo) |
| `lang` | idioma detectado |
| `collected_at` | timestamp da coleta |

Campos de enriquecimento (adicionados no estágio `enrich`):
`themes[]`, `sentiment`, `is_feature_request`, `opportunity_tag`.

---

## Estrutura de pastas

```
discovery-reviews/
├── CLAUDE.md
├── README.md
├── .gitignore
├── .env.example            # template de variáveis (nunca commitar .env real)
├── pyproject.toml          # deps do motor
├── docs/
│   ├── governanca.md       # DIA 1: PII, ToS, sandbox
│   ├── contrato-dados.md   # schema canônico da review
│   └── plano-8-dias.md
├── motor/                  # backend Python
│   ├── __init__.py
│   ├── sources/            # adaptadores (portas & adaptadores)
│   │   ├── __init__.py
│   │   ├── base.py         # interface ReviewSource (abstrata)
│   │   └── google_play.py  # GooglePlaySource (único agora)
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── collect.py
│   │   ├── normalize.py
│   │   ├── enrich.py
│   │   ├── store.py
│   │   └── report.py
│   ├── models/             # dataclasses: Review, Project, App
│   │   └── __init__.py
│   └── db/
│       └── schema.sql      # DIA 2: criação do banco
├── dashboard/              # HTML self-contained (saída DIA 6)
│   └── template.html
├── contrato/               # schemas compartilhados
│   └── review.schema.json
└── tests/                  # pytest (DIA 3: escritos ANTES do código)
    ├── __init__.py
    ├── test_google_play.py
    ├── test_normalize.py
    ├── test_enrich.py
    └── test_store.py
```

---

## Plano de 8 dias

- **DIA 0 — Definição do problema.** Feito (ver `docs/`).
- **DIA 1 — Sandbox: isolamento e governança.** git, `.gitignore`, `.env.example`,
  `docs/governanca.md`, política de PII e postura de ToS. Nenhum código de coleta.
- **DIA 2 — Fundação.** Monorepo, este CLAUDE.md, schema do banco, interface
  `ReviewSource` e modelos.
- **DIA 3 — TDD.** Escrever TODOS os testes antes de qualquer código.
- **DIA 4 — Código.** Implementar até passar nos testes (sem otimizar).
- **DIA 5 — Otimização.** Jobs, processamento pesado, refactoring.
- **DIA 6 — Interface de saída.** Dashboard HTML mobile-first.
- **DIA 7 — Esteira.** CI/CD, linters, code smells, testes, varredura de
  vulnerabilidades.
- **DIA 8 — Deploy.**

---

## Governança & PII (resumo — detalhe em `docs/governanca.md`)

- Só feed/scraper público; cadência baixa com backoff; não burlar anti-bot.
- `author` nunca é armazenado cru → guardar `author_hash`.
- `.env` com segredos (`ANTHROPIC_API_KEY` etc.) nunca vai pro git.
- Banco e dados coletados (`*.db`, `/dados/`) ficam fora do git.

## Convenções

- Commits pequenos e descritivos. Branch principal: `main`.
- Nenhum segredo no código ou no histórico do git.
