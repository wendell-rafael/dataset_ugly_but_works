# UBW Mining Infrastructure

Infraestrutura de software para mineração de artefatos do GitHub em escala,
desenvolvida como suporte ao estudo empírico **UBW ("Ugly But It Works")** —
uma pesquisa de mestrado (PPGCC/UFCG, orientação do Prof. João Arthur Brunet
Monteiro) sobre comentários de "resignação funcional" (o desenvolvedor admite
que uma solução é feia/hack, mas a mantém porque funciona), minerados em
quatro tipos de artefato: comentário de código, mensagem de commit, corpo de
issue e corpo de pull request.

Este README documenta a **infraestrutura de software** (coleta, resiliência,
desempenho) para fins de registro. Para a metodologia científica completa
(critérios de inclusão, léxico, RQs), ver [`plano.md`](plano.md); para
resultados já obtidos, ver `RESULTADOS_*.md`.

## Por que isso é mais do que "um script de scraping"

Minerar dezenas de milhares de repositórios do GitHub por múltiplos tipos de
artefato esbarra em problemas de engenharia não triviais, que este projeto
resolve de forma explícita e testada:

- **Rate limiting da API do GitHub**: rotação de múltiplos tokens
  (`ubw/github_api.py`) com round-robin por token, cada um mantendo seu
  próprio orçamento de requisições.
- **Otimização de throughput**: a Search API do GitHub aceita múltiplos
  qualificadores `repo:` numa única query (semântica OR, verificada
  empiricamente). A coleta agrupa repositórios em lotes por query
  (respeitando o teto de 256 caracteres do parâmetro `q`), reduzindo a fase
  de busca via API de ~5,8h para ~48min num corpus de referência de 784
  repositórios.
- **Tolerância a falhas / checkpoint incremental**: todas as etapas do
  pipeline (triagem, coleta multi-artefato, pré-triagem por LLM, mineração
  de padrões) gravam progresso em disco incrementalmente — o próprio
  arquivo de saída funciona como checkpoint — e retomam automaticamente de
  onde pararam em caso de interrupção (queda de processo, reinício de
  máquina, limite de rate limit). Motivado por perdas reais de dados em
  execuções de horas que foram interrompidas sem essa proteção.
- **Robustez de rede / TLS**: dois workarounds documentados para problemas
  reais do serviço de terceiros usado na triagem (SEART-GHS) — completar
  uma cadeia de certificados incompleta via extensão AIA (como um
  navegador faz), e uma fixação de impressão digital SHA-256 para tolerar
  um certificado expirado sem desabilitar a verificação TLS de forma
  genérica (`ubw/tls_fix.py`).
- **Canonicalização de identidade de repositório**: repositórios renomeados
  entre a indexação do SEART-GHS e a coleta quebram o qualificador `repo:`
  da Search API (HTTP 422) e podem duplicar entradas no corpus;
  `scripts/05_canonicalize_repos.py` resolve o nome atual via redirect da
  REST API antes da coleta.
- **Filtros de precisão** aprendidos a partir de falsos positivos reais
  encontrados durante a mineração: detecção de código vendorizado (por
  caminho e por nome de arquivo), exclusão de artefatos de bots,
  correspondência de frase por linha (evita que uma frase do léxico "cole"
  através de uma quebra de linha ou item de lista), e exigência de
  correspondência textual normalizada (a Search API do GitHub faz
  stemming e pode retornar falsos positivos).
- **Identidade de autor com pseudonimização**: cada registro guarda os
  identificadores brutos disponíveis do autor de introdução (nome/login/
  e-mail, conforme o canal) mais um hash SHA-256 derivado, para permitir
  contato em pesquisa futura sem expor os dados brutos na publicação.

## Estrutura do repositório

```
ubw/                        pacote de suporte compartilhado por todos os scripts
├── schema.py                schema de coleta (colunas, critérios de inclusão, hash de autor)
├── lexicon.py                léxico fechado de expressões + filtros de precisão
├── patterns.py                padrões estruturais exploratórios (regex)
├── github_api.py              cliente HTTP com rotação de tokens e rate limiting
├── tls_fix.py                  workarounds de TLS para o SEART-GHS
└── envutil.py                   utilitário de carregamento de .env

scripts/
├── 01_screening_seart.py      Fase 1 — triagem de repositórios (SEART-GHS)
├── 05_canonicalize_repos.py   canonicalização de nomes (pré-passo da coleta)
├── 02_collect_multiartifact.py Fase 1 — coleta multi-artefato do léxico
├── 03_metrics_llm_triage.py    amostragem, pré-triagem LLM, métricas de concordância
├── 04_pattern_mining.py         mineração exploratória de novas expressões
└── generate_report_figures.py   geração dos gráficos usados nos relatórios

plano.md                     metodologia científica completa (fonte de verdade das RQs)
LEXICO.md                    documentação de todas as expressões/padrões em uso
RESULTADOS_*.md              relatórios de cada rodada de coleta
```

## Instalação

Requer Python 3.10+ (testado nesta máquina com `python3.10` especificamente —
ver nota de ambiente no `CHANGELOG.md`).

```bash
pip install -r requirements.txt
cp .env.example .env  # preencher GITHUB_TOKEN(S) e, opcionalmente, ANTHROPIC_API_KEY/OPENROUTER_API_KEY
```

## Uso (ordem típica do pipeline)

```bash
cd scripts

# 1. Triagem: descobre repositórios elegíveis (Seção 2.2 do plano)
python 01_screening_seart.py --out ../data/repos_to_mine.csv

# 2. Canonicalização: resolve renomeações antes da coleta
python 05_canonicalize_repos.py --repos-csv ../data/repos_to_mine.csv \
    --out ../data/repos_to_mine_canonical.csv

# 3. Coleta multi-artefato: aplica o léxico aos 4 tipos de artefato
python 02_collect_multiartifact.py \
    --repos-csv ../data/repos_to_mine_canonical.csv --out-dir ../data

# 4. (opcional) Pré-triagem por LLM antes da anotação humana
python 03_metrics_llm_triage.py llm-triage \
    --candidates ../data/ubw_collected_full.csv --out ../data/llm_triage_results.csv
```

Todos os scripts com etapas longas (1, 2, 3, 4) suportam interrupção e
retomada — basta rodar o mesmo comando de novo. Nenhum precisa de flag
especial para retomar; a exceção é `01_screening_seart.py`, que aceita
`--resume-from-page N` para retomar manualmente de uma página conhecida.

## Limitações conhecidas (débito técnico, honesto)

- Sem suíte de testes automatizada — a validação de correções foi feita via
  smoke tests manuais (scripts ad-hoc), não via CI/pytest. Ver
  `CHANGELOG.md` para o histórico de bugs pegos dessa forma.
- Acoplado às particularidades desta pesquisa (schema do plano, léxico
  fechado, endpoint específico do SEART-GHS) — não é uma biblioteca
  genérica de mineração de GitHub, embora `ubw/github_api.py` e o padrão de
  checkpoint incremental sejam reutilizáveis em outros contextos.
- O workaround de fixação de certificado TLS (`ubw/tls_fix.py`) é
  temporário por definição — deve ser removido do uso normal assim que o
  SEART-GHS renovar o certificado deles.
- Caminhos relativos (`../data/...`) assumem execução a partir de `scripts/`.

## Autoria e citação

Desenvolvido por Wendell Rafael Oliveira Nascimento (PPGCC/UFCG), sob
orientação do Prof. João Arthur Brunet Monteiro, como infraestrutura de
suporte à dissertação de mestrado sobre o fenômeno UBW. Licenciado sob MIT
(ver `LICENSE`).
