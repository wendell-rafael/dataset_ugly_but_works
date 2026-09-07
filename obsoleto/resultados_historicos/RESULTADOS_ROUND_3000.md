# UBW: Resultados da Rodada 3.000 (primeiro bloco do corpus final)

**Data de corte:** 2026-07-14/15 | **Corpus:** primeiros 3.000 repositórios canônicos (de 74.807 totais, `data/full_run/repos_to_mine_full_canonical.csv`) | **Dataset:** `data/full_run/ubw_collected_full.csv` (filtrado aos 3.000 primeiros repos por ordem canônica)

Esta é a segunda rodada em escala real, imediatamente após `RESULTADOS_ROUND_800.md` (784 repos). Roda dentro da cadeia automática (`data/full_run/run_chain.sh`) que recoletou `code_comment` dos 3.000 primeiros repos com o fix de contaminação (ver Seção 2) e, na sequência, segue avançando até um teto de 18.000.

## 1. Nota metodológica: comparação justa com round_800

Durante a preparação deste relatório foi descoberto que **`round_800` sofre do mesmo bug de contaminação** corrigido nesta rodada (Seção 2) — ele é anterior ao fix, então nunca teve o filtro novo aplicado. Uma comparação bruta ("931 registros do round_800" vs. números já limpos do round_3000) seria injusta e enganosa.

Para viabilizar uma comparação honesta, os números de `round_800` citados abaixo foram **recalculados aplicando o mesmo filtro/dedup em pós-processamento** sobre o CSV já coletado (sem re-clonar nem re-coletar — script único, `is_vendored_path` atualizado + dedup de texto exato por repo). Isso NÃO reprocessa os pares de introdução/remoção que dependiam de eventos agora filtrados, mas dá uma base de contagem comparável. Os números *originais* (não corrigidos) permanecem em `RESULTADOS_ROUND_800.md` como estavam — este relatório não os reescreve, só apresenta a versão corrigida lado a lado.

| | round_800 (bruto, relatório original) | round_800 (limpo, retroativo) | round_3000 (limpo, nativo) |
|---|---|---|---|
| Total de registros | 931 | 780 | 3.217 |
| Repos com ocorrência | 244 | 241 | 932 |
| code_comment | 439 | 288 | 934 |
| RQ2 (≥3 ocorrências) | 66 | 55 | 332 |

A queda de 244→241 repos com ocorrência (não só a contagem de registros) mostra que alguns repositórios só apareciam no dataset por causa de artefato gerado/build duplicado — sem eles, não tinham nenhum registro UBW genuíno.

## 2. O que mudou desde round_800: fix de contaminação por arquivo gerado/build

Achado na análise da coleta bruta desta rodada (3.741 registros antes do fix): **31,2% dos `code_comment`** eram duplicata exata de texto dentro do mesmo repositório — o mesmo comentário replicado em `dist/`, `build/`, arquivos `.min.js`/`.min.css`, e principalmente `search_index.js` gerado pelo Documenter.jl (uma cópia por versão de documentação commitada). Exemplo extremo: `Catlab.jl` tinha 65 registros, todos vindos de `vX.Y.Z/search_index.js`.

Corrigido em duas camadas (commits `26aa576`, `1d8bf2a`):
1. `is_vendored_path`/`VENDORED_FILENAMES` (`ubw/lexicon.py`) ganhou `search_index.js`, sufixos `.min.js`/`.min.css`, e marcadores de pasta `dist/`/`build/`.
2. `_dedup_identical_body_text()` novo (`scripts/02_collect_multiartifact.py`) — rede de segurança para bundles com nome hasheado que muda a cada build e escapa de qualquer filtro por nome.

Validado com Catlab.jl (65→0 registros) e replicado retroativamente sobre `round_800` para a comparação da Seção 1.

## 3. O dataset coletado (round_3000, limpo)

**3.217 registros em 932 repositórios** (dos 3.000 processados). **Por artefato:** code_comment 934, commit_message 1.063, issue_body 629, pr_body 591. **Por categoria:** B (workaround/urgência) 2.454, A (estética/hack explícito) 753, C (resignação/incerteza) 10 — C segue rara, mesmo padrão de round_800 e da rodada de 134 repos.

**Top expressões:**

| Expressão | Registros |
|---|---|
| temporary fix | 1.125 |
| temp fix | 397 |
| stopgap | 381 |
| this is a hack | 300 |
| quick and dirty | 268 |

**Linguagens mais presentes:** Python (734), C++ (496), TypeScript (477), JavaScript (289), Java (206). Estrelas medianas dos repos com ocorrência: 803.

**RQ2 (threshold ≥3 ocorrências):** 332 repositórios — mais de 6x o volume de round_800 (55, já com o fix aplicado retroativamente), crescimento consistente com o aumento ~3,75x no número de repos processados (784→3.000).

## 4. Sobrevivência (RQ2) — code_comment apenas

Como já estabelecido em round_800, `issue_body`/`pr_body`/`commit_message` não medem remoção real de dívida técnica: "removido" para issue/PR reflete fechamento/merge (ciclo de vida do artefato), e commit_message é imutável (nunca "remove"). Só `code_comment` mede a remoção genuína do comentário.

| | round_800 (limpo) | round_3000 (limpo) |
|---|---|---|
| code_comment total | 288 | 934 |
| % removido (`is_censored=0`) | 53,8% | 54,6% |
| Mediana dias até remoção | 194 | 85 |
| Média dias até remoção | 636 | 427 |
| Mediana commits até remoção | 4 | 3 |

A taxa de remoção (~54%) é estável entre as duas rodadas — bom sinal de que não é artefato de amostra pequena. A mediana de dias caiu de 194 para 85: com 3.000 repos a amostra tem mais casos de remoção rápida capturados, o que também aproxima o UBW code_comment do benchmark de Maldonado 2017 (SATD genérico, 18–172 dias) — permanece na faixa baixa desse intervalo, consistente com a hipótese de que "resignação funcional" tende a ser resolvida mais rápido que SATD genérico quando é resolvida.

## 5. Estado da execução

Esta rodada roda dentro de uma cadeia automática com checkpoint incremental (log append-only + snapshot periódico, O(1) por chamada — fix aplicado nesta mesma janela de trabalho, ver `CHANGELOG.md`), DLQ para falhas permanentes, circuit breaker no cliente do GitHub, e paralelização de 4 threads por repo nas 25 expressões do léxico (`git log -S` é local, sem rate limit de rede — só o clone é limitado pelos 8 workers por causa da detecção de abuso do GitHub).

Um watchdog (`data/full_run/watchdog_check.sh`) monitora liveness do processo e reinicia automaticamente se cair sem terminar, checado periodicamente via wakeup agendado. A cadeia segue para um segundo bloco (repos 3.001–18.000, todos os 4 tipos de artefato) antes de decidir, junto com o usuário, se avança para o corpus completo de 74.807.

## 6. Próximos passos

1. Aguardar conclusão do bloco até 18.000 repos (etapa 2 da cadeia).
2. Decisão conjunta com o usuário: continuar para o corpus completo (74.807) ou pausar para anotação/triagem LLM neste volume.
3. Anotação humana (Kappa/AC1) segue pendente — volume de RQ2 já justifica retomar essa frente em paralelo à coleta.
