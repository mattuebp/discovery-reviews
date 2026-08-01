# Governança de Dados — Discovery Reviews

> Referenciado pelo `CLAUDE.md` (raiz). Regras aqui têm precedência sobre
> conveniência de implementação.

## Política de PII

- O autor de uma review é **dado pessoal (PII)**.
- Nunca armazenar o identificador do autor em texto cru, em nenhuma etapa do
  pipeline (coleta, normalização, banco).
- Sempre persistir `author_hash`: uma versão pseudonimizada (hash) do autor.
  A partir do `author_hash` não deve ser possível recuperar o identificador
  original.
- Nenhum outro campo pessoalmente identificável do autor é coletado além do
  necessário para pseudonimização.

## Postura de ToS / coleta

- Coletar **apenas** de feed público — reviews já visíveis publicamente na
  página do app na loja. Nenhum endpoint autenticado, privado ou pago.
- Cadência de requisições **baixa**, com **backoff** entre chamadas.
- **Não burlar proteção anti-bot**: sem falsificação de headers para se passar
  por navegador, sem rotação de IP/proxy para evasão de bloqueio, sem
  resolução automática de captcha.
- Se a fonte sinalizar bloqueio ou limite, o coletor deve parar — não
  contornar.

## O que entra / não entra no repositório

**Entra no git:**
- Código-fonte (`motor/`, `dashboard/`, `contrato/`)
- Documentação (`docs/`)
- Testes (`tests/`)
- `.env.example` (template de variáveis, **sem valores reais**)
- Arquivos de configuração de projeto (`pyproject.toml`, `.gitignore`, etc.)

**Não entra no git** (ver `.gitignore`):
- `.env` real com segredos (ex.: `ANTHROPIC_API_KEY`)
- Banco de dados (`*.db`)
- Dados coletados (`/dados/`)
- Artefatos de execução Python (`__pycache__/`, `*.pyc`, `.venv/`)

## Honestidade metodológica

- A amostra de reviews coletada é enviesada (quem escreve review não
  representa toda a base de usuários). Código e relatórios devem deixar essa
  limitação explícita — nunca apresentar métricas derivadas da amostra como
  se fossem representativas do universo total de usuários.
- Nenhuma métrica é fabricada ou extrapolada sem indicar a fonte e o método.
