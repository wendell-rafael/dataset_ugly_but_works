# Contribuindo

Este projeto é a infraestrutura de coleta que sustenta uma dissertação de
mestrado (PPGCC/UFCG). Contribuições externas são bem-vindas, mas algumas
partes têm restrições metodológicas que precisam ser respeitadas — ver
"O que não mexer sem aprovação" abaixo.

## Configuração do ambiente

```bash
pip install -r requirements.txt
cp .env.example .env  # preencher GITHUB_TOKEN(S)
```

Nesta máquina de desenvolvimento, `python3` pode não apontar para o
interpretador com as dependências instaladas — use `python3.10`
explicitamente se `import pandas` falhar (ver `CHANGELOG.md`, "Nota de
ambiente").

## Organização do código

- `ubw/` — pacote de suporte compartilhado por todos os scripts (schema,
  léxico, cliente HTTP, workarounds de TLS). Mudanças aqui afetam todo o
  pipeline; teste manualmente contra uma amostra pequena antes de rodar em
  escala.
- `scripts/` — um script por fase do pipeline, numerados na ordem de
  execução (`01_...` a `05_...`). `04_pattern_mining.py` é exploratório e
  não faz parte da coleta oficial.

## O que não mexer sem aprovação

- **O léxico oficial (`ubw/lexicon.py`)** é fechado desde o fim do piloto
  (Seção 3.1 do plano) — é uma decisão metodológica do orientador, não uma
  escolha de engenharia. Qualquer alteração (adicionar, remover ou reescrever
  uma expressão) precisa de justificativa registrada e aprovação explícita
  antes de rodar contra o corpus oficial. Novas expressões candidatas devem
  primeiro passar pela mineração exploratória (`scripts/04_pattern_mining.py`
  + `ubw/patterns.py`), não entrar direto no léxico fechado.
- **O schema de coleta (`ubw.schema.COLLECTION_SCHEMA_COLUMNS` /
  `UBWRecord`)** define o formato dos CSVs já coletados. Adicionar colunas é
  seguro (retrocompatível); remover ou renomear colunas existentes quebra
  comparabilidade entre rodadas — evite, ou documente a migração no
  `CHANGELOG.md`.
- **Os critérios de inclusão (Seção 2.2 do plano, `ubw/schema.py`)** também
  são uma decisão metodológica, não um parâmetro de conveniência.

## Convenções deste projeto

- **Toda etapa de execução longa (minutos a horas) precisa de checkpoint
  incremental.** Este projeto já perdeu dados reais mais de uma vez por
  gravar resultado só no final de um loop longo (ver `CHANGELOG.md`,
  entradas de 2026-07-08/09). O padrão usado é: grave o resultado assim que
  cada unidade de trabalho (página, repositório, candidato) terminar, com
  flush em disco, e faça o próprio arquivo de saída funcionar como
  checkpoint de retomada.
- **Bugs de precisão/metodologia encontrados na mineração** (falsos
  positivos, contaminação por código vendorizado, etc.) devem ser
  documentados no `CHANGELOG.md` com a causa raiz e o exemplo real que
  motivou a correção, não só a mudança de código — isso importa para a
  seção de ameaças à validade da dissertação.
- Sem suíte de testes automatizada ainda. A prática atual é smoke test
  manual: rodar a mudança contra uma amostra pequena (dezenas de
  repositórios) e inspecionar a saída antes de rodar em escala. Se você
  adicionar testes automatizados (`pytest`), é uma contribuição bem-vinda.

## Como reportar um problema

Abra uma issue ou entre em contato diretamente com o autor (ver
`CITATION.cff`). Inclua: o comando exato rodado, o repositório/expressão
envolvido (se for um bug de precisão), e o trecho de log relevante.
