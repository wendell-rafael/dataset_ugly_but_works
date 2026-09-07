# Revisão final da amostra oficial de validação (2026-07-27)

Auditoria feita sobre `validation/sample_final/` depois da geração inicial,
com correção de um defeito de dados encontrado no caminho. Este documento é o
registro do que foi checado, do que foi corrigido e do porquê a amostra final
pode ser defendida como está.

## 1. Defeito encontrado e corrigido no consolidado

A primeira geração da amostra revelou uma linha corrompida vinda da fatia B:
o commit `d419e713` de `satijalab/seurat` tinha mensagem com quebra de linha
gravada sem aspas de fechamento, virando **duas** linhas físicas defeituosas
(uma truncada sem datas, uma com todos os campos deslocados uma coluna). Era o
único caso em 116.193 registros — varredura por `artifact_type` inválido,
`category_ubw` inválida e `created_at` vazio não achou nenhum outro.

Correção: os dois fragmentos foram **reconstruídos em um único registro
válido** (todos os campos existiam, só desalinhados), com asserções de
sanidade antes da gravação e backup em
`ubw_collected_consolidated.csv.bak_prerepair`. O consolidado passou de
116.193 para **116.192 registros**, agora com schema 100% íntegro. A amostra
foi **regenerada do zero** (mesmo seed 42) sobre o arquivo reparado; a versão
pré-reparo está preservada em `validation/sample_final_prerepair/` para
auditoria.

## 2. Checagens que passaram na amostra regenerada

| Checagem | Resultado |
|---|---|
| Overlap entre os 5 pools (mesmo item em dois pools) | 0 |
| Duplicatas internas em cada pool | 0 |
| Calibração = exatamente 50 × 4 artefatos | 200 ✓ (antes do reparo era 201, com a linha lixo dentro) |
| Censo da Categoria C | 419 no pool + 1 na calibração = 420 = total do corpus ✓ |
| Pesos de reponderação somam 1 e cobrem todo o corpus | 1,000000 / 116.192 ✓ |
| Campos essenciais (`body_text`, `url`) sem vazios | ✓ |
| Seed fixado e registrado no manifest (reprodutível) | 42 ✓ |

**Nota metodológica a registrar na dissertação:** 1 item da Categoria C caiu
na calibração e por isso está fora do pool de censo — comportamento correto
(itens de calibração não entram no κ final, guideline §3), mas significa que a
estimativa de precisão da Categoria C cobre 419/420 itens (99,8%). Declarar
isso em vez de esconder.

## 3. Posição frente à literatura (por que dá pra defender como está)

- **Tamanho e nível de confiança do pool principal:** 385 itens para
  95%/±5% é exatamente o padrão de Bavota & Russo (2016), a âncora citada no
  plano. Nenhum dos estudos de SATD levantados pelo Agente A usa nível mais
  exigente que esse. Subir para 99%/±5% (~660 itens) ou 95%/±4% (~600) é
  possível e daria margem extra, mas estaria **acima** do padrão do campo, ao
  custo de ~55% mais anotação humana — decisão de orçamento, não de rigor
  mínimo.
- **O que já está acima do padrão do campo:** censo integral da categoria
  rara (nenhum estudo levantado faz), pool adversarial de near-miss para medir
  especificidade (idem), AC1 em paralelo ao κ contra o paradoxo de
  prevalência, pesos de reponderação para a precisão global, calibração
  50×4 fora do κ final, e guarda-corpo que impede amostra oficial sobre corpus
  provisório.
- **Limitação declarada:** os estratos pequenos do pool principal (ex.:
  A|pr_body com 9 itens) não sustentam estimativa de precisão *por estrato* —
  só a global reponderada. Se a dissertação quiser afirmar precisão por
  artefato individualmente, será preciso um piso por estrato (~30/estrato) em
  uma rodada complementar. Não é defeito da amostra atual; é um limite de
  escopo a declarar.

## 4. Estado final

- Corpus canônico: `data/full_run/ubw_collected_consolidated.csv` — 116.192
  registros, fatias A+B, filtro de bot aplicado, schema íntegro.
- Amostra oficial: `validation/sample_final/` — 1.181 itens a anotar
  (385 main + 419 censo C + 77 watch + 100 near-miss + 200 calibração).
- Próximo passo: `03c_generate_batches.py` para gerar os batches cegos por
  anotador.
