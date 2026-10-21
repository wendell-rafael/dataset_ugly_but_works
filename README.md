# gh-satd-miner

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22861637.svg)](https://doi.org/10.5281/zenodo.22861637)

Infraestrutura de coleta usada no estudo empírico **UBW ("Ugly But It Works")**
— pesquisa de mestrado (PPGCC/UFCG, orientação do Prof. João Arthur Brunet
Monteiro, com participação do Prof. David Candeia Medeiros Maia, IFPB) sobre
comentários de aceitação pragmática: o desenvolvedor admite que uma solução é
feia ou é um hack, mas a mantém porque funciona. O léxico é
minerado em quatro tipos de artefato do GitHub — comentário de código,
mensagem de commit, corpo de issue e corpo de pull request.

Esta é uma ferramenta de mineração de escopo mais amplo que a primeira versão
do **UBWSet**. O dataset publicado contém somente comentários de código; o
minerador preserva suporte aos quatro tipos de artefato para permitir novas
coletas e estudos posteriores. O dataset e o software recebem citações e
identificadores persistentes separados.

O UBWSet v1.0.0 está disponível em
[10.5281/zenodo.22775107](https://doi.org/10.5281/zenodo.22775107). Seu DOI
conceitual, que aponta para a versão mais recente do dataset, é
[10.5281/zenodo.22775104](https://doi.org/10.5281/zenodo.22775104).

A versão 1.0.1 do dataset, descrita no artigo submetido ao MSR 2027, está
pronta para depósito. Ela tem 26.030 registros de 9.584 repositórios: os
contextos de código recuperaram as quebras de linha, o dicionário de dados e
as diretrizes de anotação foram traduzidos para o inglês, e um registro antes
excluído voltou a ter a expressão visível. O pacote é gerado em
`release/ubw-code-comments-v1.0.1.zip` pelos scripts `22`, `24` e `25`.

Para citar a última versão arquivada do software, utilize o DOI da versão
1.0.1: [10.5281/zenodo.22861637](https://doi.org/10.5281/zenodo.22861637).
O DOI conceitual, que aponta para a versão mais recente do software, é
[10.5281/zenodo.22861636](https://doi.org/10.5281/zenodo.22861636).

O código-fonte atual corresponde à versão 1.0.2 do software, ainda não
depositada. Essa versão fixa uma única data de corte entre retomadas da coleta,
restaura as quebras de linha dos contextos de código e acrescenta a geração,
validação e embalagem reproduzível do UBWSet 1.0.1. Depois do depósito, os
metadados devem receber o novo DOI específico de versão.

## Licenças dos trechos de código e pedidos de remoção

Os trechos de código do UBWSet continuam sujeitos às licenças dos repositórios
de origem; ser público no GitHub não concede, por si só, direito de
redistribuição. Mantenedores que quiserem retirar registros dos seus
repositórios de versões futuras do dataset podem abrir uma
[issue](https://github.com/wendell-rafael/dataset_ugly_but_works/issues)
informando o nome do repositório. Os registros retirados são listados no
changelog da versão seguinte.

Este README cobre a infraestrutura de software (coleta, resiliência,
desempenho). Para a metodologia científica (critérios de inclusão, léxico,
RQs), ver [`plano.md`](plano.md); para resultados de cada rodada, ver os
`RESULTADOS_*.md`.

## O que a infraestrutura resolve

Minerar dezenas de milhares de repositórios por quatro tipos de artefato
esbarra em rate limit, timeout, e serviços de terceiro instáveis. O que foi
implementado pra isso:

Rotação de múltiplos tokens do GitHub (`ubw/github_api.py`), round-robin,
cada token com seu próprio estado de rate limit — multiplica o throughput
sem violar o limite de nenhum token individual.

A Search API aceita múltiplos qualificadores `repo:` numa mesma query
(semântica OR, verificada empiricamente). A coleta agrupa repositórios em
lotes por query, respeitando o teto de 256 caracteres do parâmetro `q`, o
que reduziu a fase de busca via API de ~5,8h para ~48min num corpus de 784
repositórios. Quando uma expressão comum estoura o teto de 1000 resultados
da Search API dentro de um lote, a coleta detecta e refaz a busca por
repositório individual pra não perder recall.

Checkpoint incremental em todas as etapas longas (triagem, coleta,
pré-triagem por LLM, mineração de padrões): o próprio arquivo de saída
funciona como checkpoint, e uma interrupção (crash, reinício de máquina,
rate limit) não derruba o progresso já feito. Isso não era assim desde o
início — o projeto já perdeu execuções inteiras de horas por gravar
resultado só no final, ver `CHANGELOG.md`.

Um circuit breaker no cliente HTTP (`ubw/github_api.py`) detecta outage
sustentado do GitHub e falha rápido em vez de insistir em retry+backoff
completo a cada chamada. Uma Dead Letter Queue (`ubw/dlq.py`) registra
repositórios que falham repetidamente em `code_comment` (clone impossível,
repo apagado) e para de retentá-los depois de N tentativas, em vez de
ficarem "pendentes pra sempre" a cada retomada.

O serviço de triagem (SEART-GHS) tem dois problemas reais de TLS do lado
deles: não envia o certificado intermediário no handshake, e o certificado
expirou em julho/2026. `ubw/tls_fix.py` completa a cadeia via AIA (como um
navegador faz) e usa fixação de impressão digital SHA-256 pra tolerar o
certificado vencido sem desabilitar verificação TLS de forma genérica.

Repositórios renomeados entre a indexação do SEART-GHS e a coleta quebram
o qualificador `repo:` da Search API (HTTP 422) e podem duplicar entradas
no corpus. `scripts/05_canonicalize_repos.py` resolve o nome atual via
redirect da REST API antes de coletar.

Filtros de precisão vieram de falsos positivos reais encontrados na
mineração: código vendorizado (por caminho e por nome de arquivo), autores
bot, frase do léxico "colando" através de quebra de linha ou item de
lista, e correspondência textual normalizada (a Search API faz stemming e
retorna falso positivo).

Cada registro guarda os identificadores brutos disponíveis do autor de
introdução (nome/login/e-mail, conforme o canal) mais um hash SHA-256 —
pra permitir contato numa survey futura sem expor o dado bruto quando o
dataset for publicado.

## Estrutura do repositório

```
ubw/                        pacote de suporte compartilhado por todos os scripts
├── schema.py                schema de coleta (colunas, critérios de inclusão, hash de autor)
├── lexicon.py                léxico fechado de expressões + filtros de precisão
├── patterns.py                padrões estruturais exploratórios (regex)
├── github_api.py              cliente HTTP com rotação de tokens, rate limiting e circuit breaker
├── dlq.py                      Dead Letter Queue para falhas persistentes de repositório
├── tls_fix.py                    workarounds de TLS para o SEART-GHS
└── envutil.py                   utilitário de carregamento de .env

scripts/
├── 01_screening_seart.py      triagem de repositórios (SEART-GHS)
├── 05_canonicalize_repos.py   canonicalização de nomes (pré-passo da coleta)
├── 02_collect_multiartifact.py coleta multi-artefato do léxico
├── 03_metrics_llm_triage.py    amostragem, pré-triagem LLM, métricas de concordância
├── 04_pattern_mining.py         mineração exploratória de novas expressões
└── generate_report_figures.py   geração dos gráficos usados nos relatórios

plano.md                     metodologia científica completa (fonte de verdade das RQs)
LEXICO.md                    documentação de todas as expressões/padrões em uso
RESULTADOS_*.md              relatórios de cada rodada de coleta
```

## Instalação

Requer Python 3.10+ (nesta máquina, `python3` aponta pra 3.12 sem pandas —
usar `python3.10` explicitamente; ver `CHANGELOG.md`).

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
    --repos-csv ../data/repos_to_mine_canonical.csv --out-dir ../data \
    --collection-cutoff 2026-07-23T23:59:59Z

# 4. (opcional) Pré-triagem por LLM antes da anotação humana
python 03_metrics_llm_triage.py llm-triage \
    --candidates ../data/ubw_collected_full.csv --out ../data/llm_triage_results.csv
```

Na primeira execução, a coleta grava a data de corte em
`OUT_DIR/COLLECTION_CUTOFF`. Toda retomada reutiliza esse valor. Se uma data
explícita diferente for fornecida para o mesmo diretório, o processo é
interrompido para evitar durações censuradas incompatíveis.

## Geração do pacote UBWSet

O snapshot publicado pode ser regenerado a partir do corpus consolidado sem
alterar a versão 1.0.0:

```bash
python scripts/22_prepare_code_comment_release.py \
    --release-version 1.0.1 \
    --collection-cutoff 2026-07-23T23:59:59Z
python scripts/24_validate_code_comment_release.py \
    release/ubw-code-comments-v1.0.1
python scripts/25_package_code_comment_release.py \
    release/ubw-code-comments-v1.0.1
```

O validador confere schema, chaves, votos, contagens, hashes, consistência
temporal, cobertura do dicionário de dados e o exemplo de uso. O pacote gerado
fica em `release/ubw-code-comments-v1.0.1.zip`.

Os testes locais da regra de data de corte podem ser executados com:

```bash
python -m unittest discover -s tests -v
```

Todos os scripts de etapa longa (1 a 4) suportam interrupção e retomada —
basta rodar o mesmo comando de novo, sem flag especial. A exceção é
`01_screening_seart.py`, que aceita `--resume-from-page N` pra retomar
manualmente de uma página conhecida.

## Limitações conhecidas

- A suíte automatizada atual cobre a persistência da data de corte e a
  consistência temporal do release, mas ainda não cobre toda a coleta contra
  GitHub e SEART-GHS. Mudanças nesses caminhos também exigem smoke tests em
  amostras pequenas antes de uma execução em escala.
- Acoplado a esta pesquisa (schema do plano, léxico fechado, endpoint do
  SEART-GHS) — não é uma biblioteca genérica, embora `ubw/github_api.py` e
  o padrão de checkpoint incremental sirvam em outros contextos.
- O workaround de certificado TLS (`ubw/tls_fix.py`) é temporário: remover
  do uso normal assim que o SEART-GHS renovar o certificado deles.
- Caminhos relativos (`../data/...`) assumem execução a partir de `scripts/`.

## Autoria e citação

Desenvolvido por Wendell Rafael Oliveira Nascimento, David Candeia Medeiros
Maia, João Arthur Brunet Monteiro e Fabio Jorge Almeida Morais, como infraestrutura de suporte à
pesquisa sobre o fenômeno UBW. Licenciado sob MIT (ver `LICENSE`).

Ao utilizar o software, cite uma versão arquivada no Zenodo. Os metadados da
versão em preparação estão em [`CITATION.cff`](CITATION.cff). O DOI específico
da versão 1.0.2 deverá ser acrescentado depois do novo depósito.
